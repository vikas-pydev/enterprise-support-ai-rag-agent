"""Deterministic model packaging script for ONNX Runtime models.

Downloads official upstream ONNX model weights and tokenizer configurations
from Hugging Face Hub into local directory data/models/ for offline,
zero-network container execution.
"""

import os
import shutil
from pathlib import Path
from huggingface_hub import hf_hub_download

MODELS_DIR = Path(os.getenv("MODEL_DIR", "data/models"))

EMBED_MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"
CE_MODEL_ID = "cross-encoder/ms-marco-MiniLM-L-6-v2"

FILES_TO_DOWNLOAD = [
    # Embedding model files
    (EMBED_MODEL_ID, "onnx/model.onnx", "all-MiniLM-L6-v2/model.onnx"),
    (EMBED_MODEL_ID, "tokenizer.json", "all-MiniLM-L6-v2/tokenizer.json"),
    (EMBED_MODEL_ID, "tokenizer_config.json", "all-MiniLM-L6-v2/tokenizer_config.json"),
    (EMBED_MODEL_ID, "special_tokens_map.json", "all-MiniLM-L6-v2/special_tokens_map.json"),
    (EMBED_MODEL_ID, "vocab.txt", "all-MiniLM-L6-v2/vocab.txt"),
    
    # Cross-encoder model files
    (CE_MODEL_ID, "onnx/model.onnx", "ms-marco-MiniLM-L-6-v2/model.onnx"),
    (CE_MODEL_ID, "tokenizer.json", "ms-marco-MiniLM-L-6-v2/tokenizer.json"),
    (CE_MODEL_ID, "tokenizer_config.json", "ms-marco-MiniLM-L-6-v2/tokenizer_config.json"),
    (CE_MODEL_ID, "special_tokens_map.json", "ms-marco-MiniLM-L-6-v2/special_tokens_map.json"),
    (CE_MODEL_ID, "vocab.txt", "ms-marco-MiniLM-L-6-v2/vocab.txt"),
]


def download_models(target_dir: Path = MODELS_DIR):
    """Downloads and places all required ONNX and tokenizer files."""
    target_dir = Path(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    
    for repo_id, filename, relative_dest in FILES_TO_DOWNLOAD:
        dest_path = target_dir / relative_dest
        if dest_path.exists() and dest_path.stat().st_size > 0:
            print(f"[EXISTS] {relative_dest} ({dest_path.stat().st_size} bytes)")
            continue
        
        print(f"[DOWNLOADING] {repo_id}:{filename} -> {relative_dest}...")
        downloaded = hf_hub_download(repo_id=repo_id, filename=filename)
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(downloaded, dest_path)
        print(f"[SAVED] {dest_path} ({dest_path.stat().st_size} bytes)")

    print(f"\nAll models successfully packaged in {target_dir.resolve()}")


if __name__ == "__main__":
    download_models()
