"""Deterministic CPU ONNX Runtime Cross-Encoder reranker inference for ms-marco-MiniLM-L-6-v2.

Replaces heavyweight PyTorch / CrossEncoder runtime with lightweight,
thread-safe lazy-loaded ONNX Runtime and tokenizers.
Preserves relevance logit outputs, threshold filtering, candidate ordering,
and metadata enrichment for multi-stage RAG retrieval.
"""

import os
import threading
from pathlib import Path
from typing import Sequence

import numpy as np
import onnxruntime as ort
from tokenizers import Tokenizer


DEFAULT_MODEL_DIR = Path(os.getenv("MODEL_DIR", "data/models")) / "ms-marco-MiniLM-L-6-v2"
HF_REPO_ID = "cross-encoder/ms-marco-MiniLM-L-6-v2"


class OnnxCrossEncoderModel:
    """Thread-safe ONNX Runtime inference wrapper for cross-encoder/ms-marco-MiniLM-L-6-v2."""

    def __init__(self, model_dir: Path | str = DEFAULT_MODEL_DIR):
        self.model_dir = Path(model_dir)
        self.session: ort.InferenceSession | None = None
        self.tokenizer: Tokenizer | None = None
        self._init_model()

    def _resolve_paths(self) -> tuple[str, str]:
        """Resolves model.onnx and tokenizer.json from local disk or HF hub."""
        onnx_file = self.model_dir / "model.onnx"
        tok_file = self.model_dir / "tokenizer.json"

        if onnx_file.is_file() and tok_file.is_file():
            return str(onnx_file), str(tok_file)

        # Fallback to Hugging Face cache/download
        from huggingface_hub import hf_hub_download

        resolved_onnx = hf_hub_download(repo_id=HF_REPO_ID, filename="onnx/model.onnx")
        resolved_tok = hf_hub_download(repo_id=HF_REPO_ID, filename="tokenizer.json")
        return resolved_onnx, resolved_tok

    def _init_model(self):
        onnx_path, tok_path = self._resolve_paths()

        # Tokenizer setup for sequence pair encoding
        self.tokenizer = Tokenizer.from_file(tok_path)
        self.tokenizer.enable_padding(direction="right", pad_id=0, pad_token="[PAD]")
        self.tokenizer.enable_truncation(max_length=512)

        # Session setup optimized for low CPU/memory footprint
        opts = ort.SessionOptions()
        opts.intra_op_num_threads = 1
        opts.inter_op_num_threads = 1
        opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL

        self.session = ort.InferenceSession(
            onnx_path,
            sess_options=opts,
            providers=["CPUExecutionProvider"],
        )

    def predict(self, pairs: Sequence[tuple[str, str]]) -> list[float]:
        """Scores a sequence of (query, document) pairs and returns relevance logits."""
        if not pairs:
            return []

        # Tokenize sequence pairs
        encoded = self.tokenizer.encode_batch(list(pairs))
        input_ids = np.array([e.ids for e in encoded], dtype=np.int64)
        attention_mask = np.array([e.attention_mask for e in encoded], dtype=np.int64)
        token_type_ids = np.array([e.type_ids for e in encoded], dtype=np.int64)

        inputs = {
            "input_ids": input_ids,
            "attention_mask": attention_mask,
            "token_type_ids": token_type_ids,
        }

        # Run ONNX inference
        outputs = self.session.run(None, inputs)
        # outputs[0] is logits array with shape [batch_size, 1] or [batch_size]
        raw_logits = outputs[0].flatten()
        return [float(score) for score in raw_logits]


# Global thread-safe lazy-loaded singleton
_reranker_lock = threading.Lock()
_reranker_instance: OnnxCrossEncoderModel | None = None


def get_reranker_model() -> OnnxCrossEncoderModel:
    """Returns the singleton OnnxCrossEncoderModel, lazily loading it on first access."""
    global _reranker_instance
    if _reranker_instance is None:
        with _reranker_lock:
            if _reranker_instance is None:
                _reranker_instance = OnnxCrossEncoderModel()
    return _reranker_instance


def score_pairs(query: str, documents: list[str]) -> list[float]:
    """Score query-document pairs using the cross-encoder model.

    Returns a list of raw relevance scores (logits).
    """
    if not documents:
        return []

    pairs = [(query, doc) for doc in documents]
    model = get_reranker_model()
    return model.predict(pairs)


def rerank_candidates(
    query: str,
    candidates: list[tuple[str, float, dict]],
    top_k: int = 3,
    score_threshold: float | None = None,
) -> list[tuple[str, float, dict]]:
    """Rerank first-stage candidate documents using cross-encoder.

    Args:
        query: The user search query.
        candidates: List of (document, vector_distance, metadata) from first stage.
        top_k: Maximum number of reranked documents to return.
        score_threshold: Minimum cross-encoder score to keep. If None, no filtering by score.

    Returns:
        List of (document, rerank_score, metadata) sorted by rerank_score descending.
    """
    if not candidates:
        return []

    documents = [doc for doc, _, _ in candidates]
    scores = score_pairs(query, documents)

    # Attach score to candidate
    scored_candidates = [
        (
            doc,
            score,
            {
                **metadata,
                "vector_distance": orig_distance,
                "rerank_score": score,
            },
        )
        for (doc, orig_distance, metadata), score in zip(candidates, scores)
    ]

    # Sort descending by reranker score
    scored_candidates.sort(key=lambda item: item[1], reverse=True)

    # Apply score threshold if configured
    if score_threshold is not None:
        scored_candidates = [
            item for item in scored_candidates if item[1] >= score_threshold
        ]

    return scored_candidates[:top_k]
