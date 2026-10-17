"""Deterministic unit test suite validating ONNX Runtime inference, numerical correctness,
thread-safe lazy loading, and ranking invariants.
"""

import math
import sys
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

# Ensure repository root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np

import app.embeddings as emb_module
import app.reranker as rerank_module


def _cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


class TestOnnxInferenceAndParity(unittest.TestCase):
    """Tests ONNX runtime embeddings and cross-encoder models."""

    def test_01_embedding_shape_and_unit_norm(self):
        """Verifies ONNX embeddings produce 384-dimensional unit vectors."""
        text = "Employees are entitled to 20 days of annual leave."
        vec = emb_module.create_embedding(text)

        self.assertIsInstance(vec, list)
        self.assertEqual(len(vec), 384)
        for val in vec:
            self.assertIsInstance(val, float)
            self.assertFalse(math.isnan(val))
            self.assertFalse(math.isinf(val))

        norm = math.sqrt(sum(x * x for x in vec))
        self.assertAlmostEqual(norm, 1.0, places=5)

    def test_02_embedding_semantic_separation(self):
        """Verifies semantic similarity between related vs unrelated text."""
        query = "How much can I spend on meals while traveling?"
        relevant = "The meal per diem allowance for domestic travel is $75 per day."
        unrelated = "PostgreSQL multi-version concurrency control manages transaction snapshots."

        q_vec = emb_module.create_embedding(query)
        rel_vec = emb_module.create_embedding(relevant)
        unrel_vec = emb_module.create_embedding(unrelated)

        sim_rel = _cosine_similarity(q_vec, rel_vec)
        sim_unrel = _cosine_similarity(q_vec, unrel_vec)

        self.assertGreater(
            sim_rel,
            sim_unrel + 0.25,
            f"Expected relevant similarity ({sim_rel:.3f}) >> unrelated ({sim_unrel:.3f})",
        )

    def test_03_cross_encoder_scoring_and_ordering(self):
        """Verifies CrossEncoder outputs valid logits and orders relevant above irrelevant."""
        query = "What is the policy for carry-forward leave?"
        relevant = "Employees may carry forward up to 10 unused annual leave days into the next year."
        irrelevant = "All employees are provided with high-speed internet access in corporate offices."

        scores = rerank_module.score_pairs(query, [relevant, irrelevant])
        self.assertEqual(len(scores), 2)
        self.assertIsInstance(scores[0], float)
        self.assertIsInstance(scores[1], float)
        self.assertGreater(
            scores[0],
            scores[1] + 5.0,
            f"Expected relevant logit ({scores[0]:.2f}) > irrelevant logit ({scores[1]:.2f})",
        )

    def test_04_thread_safe_concurrent_embedding(self):
        """Verifies multiple threads can call create_embedding concurrently without errors."""
        sentences = [
            f"Test sentence {i} for concurrent execution and stability validation."
            for i in range(20)
        ]

        results = []
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(emb_module.create_embedding, s)
                for s in sentences
            ]
            for f in futures:
                results.append(f.result())

        self.assertEqual(len(results), 20)
        for vec in results:
            self.assertEqual(len(vec), 384)
            norm = math.sqrt(sum(x * x for x in vec))
            self.assertAlmostEqual(norm, 1.0, places=5)

    def test_05_thread_safe_concurrent_reranker(self):
        """Verifies multiple threads can call rerank_candidates concurrently."""
        candidates = [
            ("Doc A: Annual leave details.", 0.2, {"id": 1}),
            ("Doc B: Irrelevant cafeteria menu.", 0.9, {"id": 2}),
        ]

        def worker():
            return rerank_module.rerank_candidates("annual leave", candidates, top_k=2)

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(worker) for _ in range(10)]
            results = [f.result() for f in futures]

        self.assertEqual(len(results), 10)
        for res in results:
            self.assertEqual(len(res), 2)
            self.assertEqual(res[0][2]["id"], 1)

    def test_06_no_torch_in_inference_path(self):
        """Verifies ONNX inference path does not require or import PyTorch."""
        # Note: If torch was already imported in the process by an unrelated test,
        # we check that our modules don't reference torch.
        self.assertFalse(hasattr(emb_module, "torch"))
        self.assertFalse(hasattr(rerank_module, "torch"))
        self.assertFalse(hasattr(emb_module, "SentenceTransformer"))
        self.assertFalse(hasattr(rerank_module, "CrossEncoder"))


if __name__ == "__main__":
    unittest.main()
