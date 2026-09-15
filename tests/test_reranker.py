from app.reranker import score_pairs, rerank_candidates


def test_score_pairs_ordering():
    query = "How many days of annual leave do employees get?"
    relevant_doc = "Employees receive 24 days of annual leave per calendar year."
    irrelevant_doc = "The office cafeteria is located on the 4th floor and serves lunch from 12pm."

    scores = score_pairs(query, [relevant_doc, irrelevant_doc])

    assert len(scores) == 2
    assert scores[0] > scores[1], f"Expected relevant doc score ({scores[0]}) > irrelevant doc score ({scores[1]})"
    print("[PASS] test_score_pairs_ordering passed.")


def test_rerank_candidates_with_metadata():
    query = "How do I get my annual leave approved?"
    candidates = [
        (
            "Employees receive 24 days of annual leave per calendar year.",
            0.35,
            {"chunk_id": 0, "title": "Employee Leave Policy"},
        ),
        (
            "Annual leave requests must be submitted through the employee portal and approved by the employee's manager.",
            0.45,
            {"chunk_id": 1, "title": "Employee Leave Policy"},
        ),
    ]

    reranked = rerank_candidates(query, candidates, top_k=2)

    assert len(reranked) == 2
    # The approval chunk (chunk_id 1) should be reranked to rank 1
    top_doc, top_score, top_meta = reranked[0]
    assert top_meta["chunk_id"] == 1, f"Expected chunk 1 at rank 1, got chunk {top_meta['chunk_id']}"
    assert "vector_distance" in top_meta, "Metadata should preserve original vector_distance"
    assert "rerank_score" in top_meta, "Metadata should include rerank_score"
    print("[PASS] test_rerank_candidates_with_metadata passed.")


def test_rerank_score_threshold_filtering():
    query = "What is the employee work-from-home policy?"
    candidates = [
        (
            "Employees receive 24 days of annual leave per calendar year.",
            0.65,
            {"chunk_id": 0, "title": "Employee Leave Policy"},
        ),
    ]

    # With a threshold of 0.0, completely unrelated chunks (which have negative logits like -6.0) get filtered out
    filtered = rerank_candidates(query, candidates, top_k=2, score_threshold=0.0)

    assert len(filtered) == 0, f"Expected 0 chunks after filtering unrelated query, got {len(filtered)}"
    print("[PASS] test_rerank_score_threshold_filtering passed.")


def test_rerank_empty_candidates():
    query = "Any question"
    candidates = []
    result = rerank_candidates(query, candidates)
    assert result == []
    print("[PASS] test_rerank_empty_candidates passed.")


if __name__ == "__main__":
    print("\n--- Running Reranker Unit Tests ---")
    test_score_pairs_ordering()
    test_rerank_candidates_with_metadata()
    test_rerank_score_threshold_filtering()
    test_rerank_empty_candidates()
    print("\nAll reranker tests passed successfully!")
