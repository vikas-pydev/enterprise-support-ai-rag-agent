"""Deterministic unit tests for ChromaDB vector store operations, chunk indexing, and metadata search."""

import unittest

from app.embeddings import create_embedding
from app.vector_store import (
    add_documents,
    search,
    delete_document,
    collection,
)


class TestVectorStore(unittest.TestCase):
    """Automated unit test suite validating vector store CRUD, metadata indexing, and similarity search."""

    @classmethod
    def setUpClass(cls):
        """Ensure test documents are indexed with distinct metadata."""
        cls.test_doc_id = "test_doc_vector_store"
        cls.test_chunks = [
            "Test Section 1: Standard annual leave policy permits carryover of 10 days.",
            "Test Section 2: Travel expense reimbursement requires itemized receipts above 50 dollars.",
        ]
        cls.test_embeddings = [create_embedding(c) for c in cls.test_chunks]
        cls.metadata = {
            "document_id": cls.test_doc_id,
            "filename": "test_policy.txt",
            "title": "Test Policy",
            "source": "data/documents/test_policy.txt",
            "version": "v1.0",
        }
        add_documents(
            chunks=cls.test_chunks,
            embeddings=cls.test_embeddings,
            metadata=cls.metadata,
        )

    @classmethod
    def tearDownClass(cls):
        """Clean up test document chunks from collection."""
        delete_document(cls.test_doc_id)

    def test_01_search_returns_expected_structure(self):
        """Verify search returns dictionary containing documents, distances, metadatas, and ids."""
        query_emb = create_embedding("How many days can I carry forward?")
        results = search(query_emb, top_k=2)

        self.assertIsInstance(results, dict)
        expected_keys = {"documents", "distances", "metadatas", "ids"}
        self.assertTrue(expected_keys.issubset(results.keys()))
        self.assertGreaterEqual(len(results["documents"][0]), 1)
        self.assertEqual(len(results["documents"][0]), len(results["distances"][0]))
        self.assertEqual(len(results["documents"][0]), len(results["metadatas"][0]))
        self.assertEqual(len(results["documents"][0]), len(results["ids"][0]))

    def test_02_search_with_metadata_filter(self):
        """Verify search with 'where' dictionary filters results strictly by metadata attributes."""
        query_emb = create_embedding("expense receipt requirement")
        filtered_results = search(
            query_emb,
            top_k=5,
            where={"document_id": self.test_doc_id},
        )

        for meta in filtered_results["metadatas"][0]:
            self.assertEqual(meta.get("document_id"), self.test_doc_id)

    def test_03_top_k_bounds_enforced(self):
        """Verify search respects requested top_k boundary."""
        query_emb = create_embedding("annual leave")
        res_1 = search(query_emb, top_k=1)
        self.assertLessEqual(len(res_1["documents"][0]), 1)

    def test_04_chunk_metadata_enrichment(self):
        """Verify add_documents automatically enriches chunks with chunk_id, chunk_uid, and content_hash."""
        query_emb = create_embedding("annual leave carryover")
        results = search(
            query_emb,
            top_k=2,
            where={"document_id": self.test_doc_id},
        )

        for meta in results["metadatas"][0]:
            self.assertIn("chunk_id", meta)
            self.assertIn("chunk_uid", meta)
            self.assertIn("content_hash", meta)
            self.assertEqual(meta["document_id"], self.test_doc_id)

    def test_05_delete_document_removes_specific_chunks(self):
        """Verify delete_document removes only chunks for specified document_id."""
        temp_doc_id = "temp_ephemeral_doc_999"
        temp_chunks = ["Temporary chunk to be deleted."]
        temp_emb = [create_embedding(c) for c in temp_chunks]

        add_documents(
            chunks=temp_chunks,
            embeddings=temp_emb,
            metadata={"document_id": temp_doc_id, "title": "Temp"},
        )

        # Verify added
        pre_search = search(temp_emb[0], top_k=3, where={"document_id": temp_doc_id})
        self.assertGreaterEqual(len(pre_search["documents"][0]), 1)

        # Delete
        delete_document(temp_doc_id)

        # Verify deleted
        post_search = search(temp_emb[0], top_k=3, where={"document_id": temp_doc_id})
        self.assertEqual(len(post_search["documents"][0]), 0)


if __name__ == "__main__":
    unittest.main()