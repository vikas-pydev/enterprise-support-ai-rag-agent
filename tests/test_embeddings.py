"""Deterministic unit tests for sentence embedding generation, dimensions, and semantic properties."""

import math
import unittest

from app.embeddings import create_embedding


def _cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


class TestEmbeddings(unittest.TestCase):
    """Automated unit test suite validating embedding model outputs, dimensions, and semantic vector invariants."""

    def test_01_embedding_dimension_and_type(self):
        """Verify create_embedding returns a 384-dimensional list of floats."""
        text = "Employees may carry forward 10 unused annual leave days."
        embedding = create_embedding(text)

        self.assertIsInstance(embedding, list)
        self.assertEqual(len(embedding), 384)
        for i, val in enumerate(embedding):
            self.assertIsInstance(val, float)
            self.assertFalse(math.isnan(val), f"NaN at vector position {i}")
            self.assertFalse(math.isinf(val), f"Inf at vector position {i}")

    def test_02_embedding_determinism(self):
        """Verify identical input strings produce strictly identical embedding vectors."""
        text = "Standard enterprise travel allowance policy."
        emb1 = create_embedding(text)
        emb2 = create_embedding(text)

        self.assertEqual(len(emb1), len(emb2))
        for v1, v2 in zip(emb1, emb2):
            self.assertAlmostEqual(v1, v2, places=6)

    def test_03_semantic_similarity_ranking(self):
        """Verify semantically similar sentences have higher cosine similarity than unrelated sentences."""
        query = "How many unused vacation days can I carry over?"
        similar_target = "Employees are allowed to roll over up to 10 annual leave days into next year."
        unrelated_target = "PostgreSQL query execution plans rely on cost-based optimization and indexing."

        emb_query = create_embedding(query)
        emb_similar = create_embedding(similar_target)
        emb_unrelated = create_embedding(unrelated_target)

        sim_score = _cosine_similarity(emb_query, emb_similar)
        unrelated_score = _cosine_similarity(emb_query, emb_unrelated)

        self.assertGreater(
            sim_score,
            unrelated_score + 0.20,
            f"Expected similar score ({sim_score:.3f}) to be significantly higher than unrelated score ({unrelated_score:.3f}).",
        )

    def test_04_handling_various_input_formats(self):
        """Verify embedding generation handles numbers, punctuation, multi-line text, and unicode."""
        inputs = [
            "12345 67890 $100.50 €50.00",
            "Special characters: !@#$%^&*()_+-=[]{}|;:,.<>?",
            "Line 1\nLine 2\nLine 3\n\nParagraph 2",
            "Policy section: § 4.2.1 - Bereavement Leave Guidelines (2026)",
        ]
        for item in inputs:
            emb = create_embedding(item)
            self.assertIsInstance(emb, list)
            self.assertEqual(len(emb), 384)
            self.assertTrue(all(isinstance(x, float) and not math.isnan(x) for x in emb))

    def test_05_empty_and_whitespace_input(self):
        """Verify empty string or whitespace generates a valid vector without crashing."""
        for empty_val in ["", "   ", "\n\t"]:
            emb = create_embedding(empty_val)
            self.assertIsInstance(emb, list)
            self.assertEqual(len(emb), 384)


if __name__ == "__main__":
    unittest.main()