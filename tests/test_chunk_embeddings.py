"""Deterministic unit tests for chunk generation and embedding pipeline validation."""

import math
import unittest

from app.document_loader import load_document
from app.chunker import chunk_text
from app.embeddings import create_embedding


class TestChunkEmbeddings(unittest.TestCase):
    """Automated unit test suite validating chunk-to-embedding integration and vector invariants."""

    @classmethod
    def setUpClass(cls):
        """Load standard policy document and generate chunks once for suite."""
        cls.document = load_document("data/documents/leave_policy.txt")
        cls.chunks = chunk_text(cls.document)

    def test_01_document_produces_valid_chunks(self):
        """Verify chunk_text returns a non-empty list of well-formed string chunks."""
        self.assertIsInstance(self.chunks, list)
        self.assertGreaterEqual(len(self.chunks), 2)
        for idx, chunk in enumerate(self.chunks):
            self.assertIsInstance(chunk, str)
            self.assertGreater(len(chunk.strip()), 20, f"Chunk {idx} is unexpectedly short.")

    def test_02_chunk_embedding_dimensions_and_types(self):
        """Verify create_embedding produces 384-dimensional float vectors for every chunk."""
        for idx, chunk in enumerate(self.chunks):
            embedding = create_embedding(chunk)
            self.assertIsInstance(embedding, list)
            self.assertEqual(
                len(embedding),
                384,
                f"Chunk {idx} embedding dimension was {len(embedding)}, expected 384 (all-MiniLM-L6-v2).",
            )
            for val_idx, val in enumerate(embedding[:10]):
                self.assertIsInstance(val, float)
                self.assertFalse(math.isnan(val), f"NaN detected at index {val_idx} of chunk {idx}.")
                self.assertFalse(math.isinf(val), f"Inf detected at index {val_idx} of chunk {idx}.")

    def test_03_chunk_embedding_unit_normalization(self):
        """Verify generated embeddings are L2 normalized (Euclidean norm ≈ 1.0)."""
        for idx, chunk in enumerate(self.chunks):
            embedding = create_embedding(chunk)
            l2_norm = math.sqrt(sum(v * v for v in embedding))
            self.assertAlmostEqual(
                l2_norm,
                1.0,
                places=3,
                msg=f"Chunk {idx} embedding vector is not unit normalized: L2 norm = {l2_norm}",
            )

    def test_04_chunk_embedding_determinism(self):
        """Verify encoding the same chunk twice produces identical floating-point vectors."""
        chunk = self.chunks[0]
        emb1 = create_embedding(chunk)
        emb2 = create_embedding(chunk)
        self.assertEqual(len(emb1), len(emb2))
        for v1, v2 in zip(emb1, emb2):
            self.assertAlmostEqual(v1, v2, places=6)

    def test_05_distinct_chunks_produce_distinct_embeddings(self):
        """Verify different policy chunks have distinct vector representations."""
        if len(self.chunks) >= 2:
            emb1 = create_embedding(self.chunks[0])
            emb2 = create_embedding(self.chunks[1])
            dot_product = sum(v1 * v2 for v1, v2 in zip(emb1, emb2))
            # Two different policy sections should not have an exact 1.0 cosine similarity
            self.assertLess(dot_product, 0.99)


if __name__ == "__main__":
    unittest.main()