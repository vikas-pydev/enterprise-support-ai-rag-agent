"""Deterministic unit tests for dense, sparse, and hybrid retrieval interfaces and context selection."""

import unittest

from app.retriever import (
    retrieve,
    retrieve_from_vector_store,
    retrieve_from_bm25,
    retrieve_hybrid_candidates,
    retrieve_with_rerank,
)
from app.context_selector import ContextSelectionStats


class TestRetriever(unittest.TestCase):
    """Automated unit test suite validating multi-stage retrieval, hybrid search, and ranking invariants."""

    def test_01_retrieve_leave_policy_returns_structured_results(self):
        """Verify retrieve returns list of tuples: (document_text, score, metadata)."""
        query = "How many annual leave days do employees receive?"
        results = retrieve(query, top_k=3, score_threshold=0.0)

        self.assertIsInstance(results, list)
        self.assertGreaterEqual(len(results), 1)
        self.assertLessEqual(len(results), 3)

        for doc_text, score, metadata in results:
            self.assertIsInstance(doc_text, str)
            self.assertIsInstance(score, float)
            self.assertIsInstance(metadata, dict)
            self.assertIn("document_id", metadata)
            self.assertIn("chunk_id", metadata)
            self.assertIn("title", metadata)

    def test_02_empty_and_whitespace_query_returns_empty_list(self):
        """Verify empty or whitespace query immediately returns empty list."""
        self.assertEqual(retrieve(""), [])
        self.assertEqual(retrieve("   \n\t  "), [])
        self.assertEqual(retrieve_from_vector_store(""), [])
        self.assertEqual(retrieve_from_bm25(""), [])

    def test_03_dense_retrieval_mode(self):
        """Verify dense retrieval from vector store."""
        query = "annual leave carry forward rules"
        results = retrieve_from_vector_store(query, top_k=2)

        self.assertIsInstance(results, list)
        for doc_text, distance, metadata in results:
            self.assertIsInstance(doc_text, str)
            self.assertIsInstance(distance, float)
            self.assertLessEqual(distance, 0.7)  # max_distance threshold

    def test_04_sparse_bm25_retrieval_mode(self):
        """Verify sparse retrieval from BM25 index."""
        query = "carry forward unused annual leave"
        results = retrieve_from_bm25(query, top_k=2)

        self.assertIsInstance(results, list)
        for doc_text, score, metadata in results:
            self.assertIsInstance(doc_text, str)
            self.assertIsInstance(score, float)
            self.assertGreater(score, 0.0)

    def test_05_hybrid_candidate_fusion(self):
        """Verify reciprocal rank fusion combines dense and sparse candidate lists."""
        query = "annual leave allocation"
        candidates = retrieve_hybrid_candidates(query, initial_top_k=5)

        self.assertIsInstance(candidates, list)
        for doc_text, rrf_score, metadata in candidates:
            self.assertIsInstance(doc_text, str)
            self.assertIsInstance(rrf_score, float)
            self.assertGreater(rrf_score, 0.0)

    def test_06_metadata_filtering_parameter(self):
        """Verify metadata where filter is respected across retrieval pipeline."""
        query = "leave and expense rules"
        filtered_results = retrieve(
            query,
            top_k=5,
            where={"document_id": "leave_policy"},
            score_threshold=0.0,
        )

        for doc_text, score, metadata in filtered_results:
            self.assertEqual(metadata.get("document_id"), "leave_policy")

    def test_07_retrieve_with_return_stats(self):
        """Verify return_stats=True returns tuple of (results, ContextSelectionStats)."""
        query = "annual leave"
        res, stats = retrieve(query, top_k=3, return_stats=True, score_threshold=0.0)

        self.assertIsInstance(res, list)
        self.assertIsInstance(stats, ContextSelectionStats)
        self.assertGreaterEqual(stats.final_chunks, 0)
        self.assertGreaterEqual(stats.final_chars, 0)


if __name__ == "__main__":
    unittest.main()