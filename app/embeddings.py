"""Deterministic CPU ONNX Runtime embedding inference for all-MiniLM-L6-v2.

Replaces heavyweight PyTorch / SentenceTransformer runtime with lightweight,
thread-safe lazy-loaded ONNX Runtime and tokenizers.
Preserves 384-dimensional vector output, mean pooling, and L2 normalization
compatible with ChromaDB cosine distance space.
"""

import os
import threading
from pathlib import Path
from typing import Sequence

import numpy as np
import onnxruntime as ort
from tokenizers import Tokenizer


DEFAULT_MODEL_DIR = Path(os.getenv("MODEL_DIR", "data/models")) / "all-MiniLM-L6-v2"
HF_REPO_ID = "sentence-transformers/all-MiniLM-L6-v2"


class OnnxEmbeddingModel:
    """Thread-safe ONNX Runtime inference wrapper for all-MiniLM-L6-v2."""

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

        # Tokenizer setup
        self.tokenizer = Tokenizer.from_file(tok_path)
        self.tokenizer.enable_padding(direction="right", pad_id=0, pad_token="[PAD]")
        self.tokenizer.enable_truncation(max_length=256)

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

    def encode(self, texts: Sequence[str]) -> np.ndarray:
        """Encodes a sequence of texts into L2-normalized 384-dimensional embeddings."""
        if not texts:
            return np.empty((0, 384), dtype=np.float32)

        # Tokenize batch
        encoded = self.tokenizer.encode_batch(list(texts))
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
        token_embeddings = outputs[0]  # shape: [batch_size, seq_len, 384]

        # Mean pooling with attention mask
        input_mask_expanded = np.expand_dims(attention_mask, -1).astype(np.float32)
        sum_embeddings = np.sum(token_embeddings * input_mask_expanded, axis=1)
        sum_mask = np.clip(input_mask_expanded.sum(axis=1), a_min=1e-9, a_max=None)
        mean_pooled = sum_embeddings / sum_mask

        # L2 normalize
        norm = np.linalg.norm(mean_pooled, axis=-1, keepdims=True)
        norm = np.maximum(norm, 1e-12)
        return mean_pooled / norm


# Global thread-safe lazy-loaded singleton
_model_lock = threading.Lock()
_embedding_instance: OnnxEmbeddingModel | None = None


def get_embedding_model() -> OnnxEmbeddingModel:
    """Returns the singleton OnnxEmbeddingModel, lazily loading it on first access."""
    global _embedding_instance
    if _embedding_instance is None:
        with _model_lock:
            if _embedding_instance is None:
                _embedding_instance = OnnxEmbeddingModel()
    return _embedding_instance


def create_embedding(text: str) -> list[float]:
    """Generates a 384-dimensional embedding vector for a single string.

    Preserves exact backward-compatible signature.
    """
    model = get_embedding_model()
    embeddings = model.encode([text])
    return embeddings[0].tolist()


def create_embeddings(texts: list[str]) -> list[list[float]]:
    """Generates 384-dimensional embeddings for a batch of strings."""
    if not texts:
        return []
    model = get_embedding_model()
    embeddings = model.encode(texts)
    return embeddings.tolist()