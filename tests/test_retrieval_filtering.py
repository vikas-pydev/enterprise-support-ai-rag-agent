from app.retriever import retrieve_from_vector_store, retrieve_with_rerank, retrieve
from app.rag import generate_answer


def test_metadata_filtering_positive():
    # Filter for known title
    results = retrieve(
        "How many annual leave days do employees receive?",
        where={"title": "Employee Leave Policy"},
    )
    assert len(results) > 0, "Expected at least 1 result for matching metadata filter"
    for doc, score, meta in results:
        assert meta["title"] == "Employee Leave Policy"
    print("[PASS] test_metadata_filtering_positive passed.")


def test_metadata_filtering_negative():
    # Filter for a non-matching title
    results = retrieve(
        "How many annual leave days do employees receive?",
        where={"title": "Nonexistent Document Policy"},
    )
    assert len(results) == 0, f"Expected 0 results for non-matching metadata filter, got {len(results)}"
    print("[PASS] test_metadata_filtering_negative passed.")


def test_empty_and_whitespace_query():
    # Empty query
    assert retrieve("") == []
    # Whitespace query
    assert retrieve("    \n\t  ") == []
    # Pure vector retrieve with empty query
    assert retrieve_from_vector_store("") == []
    print("[PASS] test_empty_and_whitespace_query passed.")


def test_unanswerable_query_rejection():
    # Unanswerable question should be rejected by threshold
    results = retrieve(
        "What is the company's reimbursement policy for home gym equipment?",
        score_threshold=5.0,
    )
    assert len(results) == 0, f"Expected 0 results for unrelated query, got {len(results)}"
    print("[PASS] test_unanswerable_query_rejection passed.")


def test_empty_context_llm_guardrail():
    # When no contexts survive retrieval, generate_answer should short-circuit
    answer = generate_answer("Any question", contexts=[])
    assert "not available in the provided documents" in answer
    print("[PASS] test_empty_context_llm_guardrail passed.")


def test_provenance_and_metadata_preservation():
    results = retrieve("How do I get my annual leave approved?", top_k=1)
    assert len(results) == 1
    doc, score, meta = results[0]
    assert "chunk_id" in meta, "chunk_id missing in metadata"
    assert "source" in meta, "source missing in metadata"
    assert "title" in meta, "title missing in metadata"
    assert "vector_distance" in meta, "vector_distance missing in metadata"
    assert "rerank_score" in meta, "rerank_score missing in metadata"
    assert meta["chunk_id"] == 1, f"Expected chunk 1 for approval query, got {meta['chunk_id']}"
    print("[PASS] test_provenance_and_metadata_preservation passed.")


if __name__ == "__main__":
    print("\n--- Running Retrieval Filtering & Edge Case Tests ---")
    test_metadata_filtering_positive()
    test_metadata_filtering_negative()
    test_empty_and_whitespace_query()
    test_unanswerable_query_rejection()
    test_empty_context_llm_guardrail()
    test_provenance_and_metadata_preservation()
    print("\nAll retrieval filtering tests passed successfully!")
