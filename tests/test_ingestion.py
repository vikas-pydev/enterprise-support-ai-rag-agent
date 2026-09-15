"""Deterministic unit tests for incremental document ingestion, version registry, and change detection."""

import tempfile
import unittest
from pathlib import Path

from app.document_loader import load_document, Document
from app.ingestion import (
    ingest_document,
    ingest_directory,
    get_document_registry,
    IngestResult,
)


class TestDocumentIngestion(unittest.TestCase):
    """Automated unit test suite validating incremental ingestion, chunk counting, and registry tracking."""

    def test_01_ingest_leave_policy_document(self):
        """Verify ingest_document successfully loads, chunks, embeds, and records a policy document."""
        file_path = "data/documents/leave_policy.txt"
        result = ingest_document(file_path, reset=False, force=True)

        self.assertIsInstance(result, int)
        self.assertIsInstance(result, IngestResult)
        self.assertGreaterEqual(int(result), 2)
        self.assertEqual(result.status, "ingested")
        self.assertEqual(result.document_id, "leave_policy")
        self.assertTrue(len(result.version) == 8)
        self.assertEqual(result.chunks_stored, int(result))

    def test_02_ingest_result_to_dict_serialization(self):
        """Verify IngestResult.to_dict() serialization format."""
        file_path = "data/documents/leave_policy.txt"
        result = ingest_document(file_path, reset=False, force=True)
        res_dict = result.to_dict()

        self.assertIsInstance(res_dict, dict)
        self.assertEqual(res_dict["status"], "ingested")
        self.assertEqual(res_dict["document_id"], "leave_policy")
        self.assertEqual(res_dict["chunks_stored"], int(result))
        self.assertTrue(len(res_dict["version"]) == 8)

    def test_03_content_hash_change_detection_skips_identical_document(self):
        """Verify re-ingesting an unchanged document returns status='skipped' without re-embedding."""
        file_path = "data/documents/leave_policy.txt"
        # First ensure it's in registry
        ingest_document(file_path, reset=False, force=True)

        # Second call without force should skip
        second_result = ingest_document(file_path, reset=False, force=False)
        self.assertIsInstance(second_result, IngestResult)
        self.assertEqual(second_result.status, "skipped")
        self.assertEqual(second_result.document_id, "leave_policy")

    def test_04_force_flag_overrides_skip_behavior(self):
        """Verify force=True re-ingests document even when content hash matches."""
        file_path = "data/documents/leave_policy.txt"
        res = ingest_document(file_path, reset=False, force=True)
        self.assertEqual(res.status, "ingested")

    def test_05_document_registry_structure(self):
        """Verify get_document_registry returns valid schema with document tracking metadata."""
        registry = get_document_registry()
        self.assertIsInstance(registry, dict)
        self.assertIn("leave_policy", registry)

        entry = registry["leave_policy"]
        self.assertIn("filename", entry)
        self.assertIn("title", entry)
        self.assertIn("content_hash", entry)
        self.assertIn("version", entry)
        self.assertIn("chunk_count", entry)
        self.assertIn("last_ingested_at", entry)
        self.assertGreater(entry["chunk_count"], 0)

    def test_06_ingest_directory_summary(self):
        """Verify ingest_directory scans directory and produces a structured summary report."""
        summary = ingest_directory("data/documents", reset=False, force=False)

        self.assertIsInstance(summary, dict)
        expected_keys = {"total_documents", "ingested_count", "skipped_count", "total_chunks", "documents"}
        self.assertTrue(expected_keys.issubset(summary.keys()))
        self.assertGreaterEqual(summary["total_documents"], 1)
        self.assertGreaterEqual(summary["total_chunks"], 2)
        self.assertEqual(summary["total_documents"], summary["ingested_count"] + summary["skipped_count"])


if __name__ == "__main__":
    unittest.main()