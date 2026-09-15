from app.chunker import chunk_text, ChunkerConfig, ChunkingStrategy
from app.document_loader import load_document


def test_default_paragraph_chunking():
    doc = load_document("data/documents/leave_policy.txt")
    chunks = chunk_text(doc)
    assert len(chunks) == 2, f"Expected 2 chunks for leave_policy, got {len(chunks)}"
    assert "Annual Leave:" in chunks[0]
    assert "Approval:" in chunks[1]
    print("[PASS] test_default_paragraph_chunking passed.")


def test_configurable_chunk_size():
    doc = load_document("data/documents/leave_policy.txt")
    # Small chunk size should force more splits
    small_chunks = chunk_text(doc, chunk_size=150)
    assert len(small_chunks) > 2, f"Expected >2 chunks with size 150, got {len(small_chunks)}"

    # Large chunk size should keep entire document in one chunk
    large_chunks = chunk_text(doc, chunk_size=1000)
    assert len(large_chunks) == 1, f"Expected 1 chunk with size 1000, got {len(large_chunks)}"
    print("[PASS] test_configurable_chunk_size passed.")


def test_overlap_preservation():
    text = (
        "Alpha section begins here and sets initial rules. "
        "Beta section expands upon the concepts with more detail. "
        "Gamma section completes the discussion with concluding remarks."
    )
    # Using small chunk size with overlap
    chunks = chunk_text(text, chunk_size=75, chunk_overlap=30)
    assert len(chunks) >= 2

    # Check that adjacent chunks share overlapping terms
    has_shared_content = False
    for i in range(len(chunks) - 1):
        words1 = set(chunks[i].split())
        words2 = set(chunks[i + 1].split())
        shared = words1.intersection(words2)
        if len(shared) > 0:
            has_shared_content = True
            break
    assert has_shared_content, "Expected shared words between overlapping chunks"
    print("[PASS] test_overlap_preservation passed.")


def test_markdown_heading_preservation():
    doc = load_document("data/documents/travel_policy.md")
    chunks = chunk_text(doc, chunk_size=350, strategy="markdown")
    assert len(chunks) == 4, f"Expected 4 chunks for travel_policy.md, got {len(chunks)}"

    # Check each chunk retains a markdown header
    for i, c in enumerate(chunks):
        assert c.startswith("#"), f"Chunk {i} does not start with a markdown header:\n{c[:50]}"
    print("[PASS] test_markdown_heading_preservation passed.")


def test_markdown_header_context_injection():
    # When a single section is larger than chunk_size, subsequent chunks must inherit the header
    long_markdown = (
        "## Long Policy Section\n\n"
        "First long paragraph detailing the fundamental provisions and scope of the policy.\n\n"
        "Second long paragraph covering operational responsibilities and mandatory protocols.\n\n"
        "Third long paragraph specifying non-compliance consequences and review timelines."
    )
    chunks = chunk_text(long_markdown, chunk_size=150, preserve_headers=True)
    assert len(chunks) > 1
    for chunk in chunks:
        assert "## Long Policy Section" in chunk, (
            f"Chunk missing section header context:\n{chunk}"
        )
    print("[PASS] test_markdown_header_context_injection passed.")


def test_no_lost_information():
    text = "Important clause one. Crucial condition two. Mandatory protocol three."
    chunks = chunk_text(text, chunk_size=40, chunk_overlap=10)
    reconstructed = " ".join(chunks)
    assert "Important clause one" in reconstructed
    assert "Crucial condition two" in reconstructed
    assert "Mandatory protocol three" in reconstructed
    print("[PASS] test_no_lost_information passed.")


def test_empty_and_whitespace():
    assert chunk_text("") == []
    assert chunk_text("   \n\n\t  ") == []
    print("[PASS] test_empty_and_whitespace passed.")


if __name__ == "__main__":
    print("\n--- Running Advanced Chunker Unit Tests ---")
    test_default_paragraph_chunking()
    test_configurable_chunk_size()
    test_overlap_preservation()
    test_markdown_heading_preservation()
    test_markdown_header_context_injection()
    test_no_lost_information()
    test_empty_and_whitespace()
    print("\nAll chunker tests passed successfully!")