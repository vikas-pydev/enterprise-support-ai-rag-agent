import shutil
import tempfile
from pathlib import Path

from app.document_loader import (
    load_document,
    load_directory,
    Document,
    register_loader,
    LOADER_REGISTRY,
)
from app.ingestion import ingest_document, ingest_directory, get_document_registry
from app.retriever import retrieve


def test_loading_single_document_metadata():
    doc = load_document("data/documents/leave_policy.txt")
    assert isinstance(doc, str), "Document must behave as a string subclass"
    assert isinstance(doc, Document), "Must be an instance of Document"
    assert doc.document_id == "leave_policy"
    assert doc.title == "Employee Leave Policy"
    assert doc.filename == "leave_policy.txt"
    assert doc.file_extension == ".txt"
    assert len(doc.content_hash) == 64, "SHA-256 must be 64 hex characters"
    assert doc.version == doc.content_hash[:8]
    assert doc.metadata["document_id"] == "leave_policy"
    print("[PASS] test_loading_single_document_metadata passed.")


def test_loading_markdown_document():
    doc = load_document("data/documents/travel_policy.md")
    assert doc.file_extension == ".md"
    assert doc.document_id == "travel_policy"
    assert doc.title == "Corporate Travel and Expense Policy"
    assert "Per Diem and Meals" in doc
    print("[PASS] test_loading_markdown_document passed.")


def test_unsupported_extension_rejection():
    with tempfile.TemporaryDirectory() as tmp_dir:
        dummy_file = Path(tmp_dir) / "image.png"
        dummy_file.write_bytes(b"\x89PNG\r\n\x1a\n")

        try:
            load_document(dummy_file)
            assert False, "Should have raised ValueError for unsupported extension"
        except ValueError as e:
            assert "Unsupported file format '.png'" in str(e)

    print("[PASS] test_unsupported_extension_rejection passed.")


def test_load_directory():
    docs = load_directory("data/documents")
    assert len(docs) >= 4, f"Expected at least 4 documents, found {len(docs)}"
    doc_ids = [d.document_id for d in docs]
    assert "attendance_policy" in doc_ids
    assert "benefits_policy" in doc_ids
    assert "leave_policy" in doc_ids
    assert "travel_policy" in doc_ids
    print("[PASS] test_load_directory passed.")


def test_stable_document_and_chunk_ids():
    with tempfile.TemporaryDirectory() as tmp_dir:
        test_file = Path(tmp_dir) / "sample_guide.txt"
        test_file.write_text("Sample Guide Title\n\nParagraph 1.\n\nParagraph 2.")

        doc1 = load_document(test_file)
        doc2 = load_document(test_file)
        assert doc1.document_id == doc2.document_id == "sample_guide"
        assert doc1.version == doc2.version
        assert doc1.content_hash == doc2.content_hash

    print("[PASS] test_stable_document_and_chunk_ids passed.")


def test_versioning_and_change_detection():
    with tempfile.TemporaryDirectory() as tmp_dir:
        test_file = Path(tmp_dir) / "temp_policy.txt"
        test_file.write_text("Temporary Policy\n\nVersion 1 text.")

        doc_v1 = load_document(test_file)
        res_v1 = ingest_document(doc_v1)
        assert res_v1.status == "ingested"

        # Ingesting same file again should be skipped (cached)
        res_cached = ingest_document(doc_v1)
        assert res_cached.status == "skipped"

        # Modifying content creates a new version
        test_file.write_text("Temporary Policy\n\nVersion 2 updated text.")
        doc_v2 = load_document(test_file)
        assert doc_v2.version != doc_v1.version
        assert doc_v2.content_hash != doc_v1.content_hash

        res_v2 = ingest_document(doc_v2)
        assert res_v2.status == "ingested"
        assert res_v2.version == doc_v2.version

    print("[PASS] test_versioning_and_change_detection passed.")


def test_multi_document_retrieval_and_citation():
    # Test retrieving from the travel policy (markdown)
    results = retrieve("What is the meal per diem allowance for domestic travel?", top_k=1)
    assert len(results) > 0
    doc_text, score, meta = results[0]
    assert meta["document_id"] == "travel_policy"
    assert "75" in doc_text
    assert meta["title"] == "Corporate Travel and Expense Policy"
    assert "chunk_uid" in meta
    assert meta["chunk_uid"].startswith("travel_policy_chunk_")

    # Test retrieving from attendance policy
    att_results = retrieve("What are the core collaboration hours?", top_k=1)
    assert len(att_results) > 0
    att_text, att_score, att_meta = att_results[0]
    assert att_meta["document_id"] == "attendance_policy"
    assert "10:00 AM" in att_text

    print("[PASS] test_multi_document_retrieval_and_citation passed.")


if __name__ == "__main__":
    print("\n--- Running Multi-Document & Versioning Tests ---")
    test_loading_single_document_metadata()
    test_loading_markdown_document()
    test_unsupported_extension_rejection()
    test_load_directory()
    test_stable_document_and_chunk_ids()
    test_versioning_and_change_detection()
    test_multi_document_retrieval_and_citation()
    print("\nAll multi-document loader & versioning tests passed successfully!")
