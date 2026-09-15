"""Deterministic unit tests for single and multi-format document loading and metadata extraction."""

import tempfile
import unittest
from pathlib import Path

from app.document_loader import (
    Document,
    load_document,
    load_directory,
    register_loader,
    _extract_title,
    _generate_document_id,
    _compute_sha256,
)


class TestDocumentLoader(unittest.TestCase):
    """Automated unit test suite validating document loading, format registry, and metadata extraction."""

    def test_01_load_leave_policy_text_document(self):
        """Verify loading the canonical leave_policy.txt document."""
        file_path = "data/documents/leave_policy.txt"
        doc = load_document(file_path)

        self.assertIsInstance(doc, str)
        self.assertIsInstance(doc, Document)
        self.assertGreater(len(doc), 100)
        self.assertEqual(doc.filename, "leave_policy.txt")
        self.assertEqual(doc.document_id, "leave_policy")
        self.assertEqual(doc.file_extension, ".txt")
        self.assertTrue(len(doc.content_hash) == 64)  # SHA-256 hex length
        self.assertEqual(doc.version, doc.content_hash[:8])
        self.assertIn("leave", doc.title.lower())
        self.assertIn("leave_policy.txt", doc.source)

    def test_02_document_metadata_dictionary(self):
        """Verify the Document.metadata property returns all required metadata keys."""
        doc = load_document("data/documents/leave_policy.txt")
        meta = doc.metadata

        self.assertIsInstance(meta, dict)
        expected_keys = {
            "document_id",
            "filename",
            "title",
            "source",
            "file_extension",
            "content_hash",
            "version",
            "created_at",
        }
        self.assertTrue(expected_keys.issubset(meta.keys()))
        self.assertEqual(meta["document_id"], "leave_policy")
        self.assertEqual(meta["filename"], "leave_policy.txt")

    def test_03_title_extraction_rules(self):
        """Verify title extraction handles markdown headers, plain lines, and filename fallbacks."""
        # 1. Markdown # heading
        t1 = _extract_title("# Employee Code of Conduct\nSome text...", "conduct.md")
        self.assertEqual(t1, "Employee Code of Conduct")

        # 2. Markdown ### heading
        t2 = _extract_title("### Travel Expense Guidelines\nExpense rules", "travel.md")
        self.assertEqual(t2, "Travel Expense Guidelines")

        # 3. Short plain line without punctuation
        t3 = _extract_title("Information Security Policy\nRules follow", "sec.txt")
        self.assertEqual(t3, "Information Security Policy")

        # 4. Long text first line -> falls back to stem title
        long_line = "This is a very long introductory sentence that exceeds eighty characters and ends with a period."
        t4 = _extract_title(long_line, "remote_work_policy.txt")
        self.assertEqual(t4, "Remote Work Policy")

    def test_04_document_id_generation_is_deterministic(self):
        """Verify deterministic slug generation for document IDs."""
        id1 = _generate_document_id(Path("leave_policy.txt"))
        id2 = _generate_document_id(Path("data/docs/remote-work.policy.2026.md"))
        self.assertEqual(id1, "leave_policy")
        self.assertEqual(id2, "remote_work_policy_2026")

    def test_05_sha256_computation(self):
        """Verify SHA256 computation handles string whitespace consistently."""
        h1 = _compute_sha256("Policy content here")
        h2 = _compute_sha256("  Policy content here  \n")
        self.assertEqual(h1, h2)
        self.assertEqual(len(h1), 64)

    def test_06_nonexistent_file_raises_filenotfound(self):
        """Verify loading a nonexistent file raises FileNotFoundError."""
        with self.assertRaises(FileNotFoundError):
            load_document("data/documents/non_existent_policy_12345.txt")

    def test_07_unsupported_file_extension_raises_valueerror(self):
        """Verify loading an unregistered file extension raises ValueError."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tf:
            tf.write(b"%PDF-1.4 dummy content")
            temp_path = tf.name

        try:
            with self.assertRaises(ValueError) as ctx:
                load_document(temp_path)
            self.assertIn("Unsupported file format", str(ctx.exception))
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_08_custom_loader_registration(self):
        """Verify the extensible loader registry allows registering custom formats."""
        def custom_csv_loader(path: Path) -> str:
            return f"CUSTOM CSV CONTENT: {path.name}"

        register_loader(".custom_csv", custom_csv_loader)

        with tempfile.NamedTemporaryFile(suffix=".custom_csv", mode="w", delete=False) as tf:
            tf.write("col1,col2\nval1,val2")
            temp_path = tf.name

        try:
            doc = load_document(temp_path)
            self.assertIn("CUSTOM CSV CONTENT", doc)
            self.assertEqual(doc.file_extension, ".custom_csv")
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_09_load_directory_returns_sorted_documents(self):
        """Verify load_directory scans and loads all policy documents with valid metadata."""
        docs = load_directory("data/documents")
        self.assertIsInstance(docs, list)
        self.assertGreaterEqual(len(docs), 1)

        doc_ids = [d.document_id for d in docs]
        self.assertEqual(doc_ids, sorted(doc_ids))
        self.assertIn("leave_policy", doc_ids)

        for d in docs:
            self.assertIsInstance(d, Document)
            self.assertGreater(len(d.content_hash), 0)
            self.assertGreater(len(d.title), 0)


if __name__ == "__main__":
    unittest.main()