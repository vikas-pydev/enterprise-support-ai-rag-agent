from app.bm25 import BM25Index, tokenize, get_bm25_index
from app.fusion import reciprocal_rank_fusion
from app.retriever import (
    retrieve_from_vector_store,
    retrieve_from_bm25,
    retrieve_hybrid_candidates,
    retrieve,
)


def test_bm25_tokenize():
    tokens = tokenize("Travel Policy POL-TRV-301 requires VP approval for >$200 hotel & 401(k) match.")
    assert "pol-trv-301" in tokens
    assert "vp" in tokens
    assert "200" in tokens
    assert "401" in tokens
    assert "k" in tokens
    print("[PASS] test_bm25_tokenize passed.")


def test_bm25_exact_keyword_and_number_retrieval():
    bm25 = get_bm25_index()

    # Exact numeric term query: '$75' meal allowance
    results_75 = bm25.search("75 per diem allowance", top_k=2)
    assert len(results_75) > 0
    top_doc, score, meta = results_75[0]
    assert "75" in top_doc
    assert meta["document_id"] == "travel_policy"

    # Exact time / schedule: '10:00 AM'
    results_time = bm25.search("10:00 AM core hours", top_k=2)
    assert len(results_time) > 0
    top_doc, score, meta = results_time[0]
    assert "10:00 AM" in top_doc
    assert meta["document_id"] == "attendance_policy"

    print("[PASS] test_bm25_exact_keyword_and_number_retrieval passed.")


def test_bm25_empty_and_missing_terms():
    bm25 = get_bm25_index()
    # Empty query
    assert bm25.search("") == []
    assert bm25.search("    ") == []

    # Non-existent gibberish term
    assert bm25.search("zyxwvutsrqponmlkjihgfedcba") == []
    print("[PASS] test_bm25_empty_and_missing_terms passed.")


def test_bm25_metadata_filtering():
    bm25 = get_bm25_index()
    # Query matching multiple docs, but filtered to benefits_policy
    results = bm25.search(
        "policy employee",
        top_k=5,
        where={"document_id": "benefits_policy"},
    )
    assert len(results) > 0
    for doc, score, meta in results:
        assert meta["document_id"] == "benefits_policy"
    print("[PASS] test_bm25_metadata_filtering passed.")


def test_rrf_fusion_logic():
    dense_list = [
        ("doc_A", 0.1, {"chunk_uid": "chunk_A"}),
        ("doc_B", 0.3, {"chunk_uid": "chunk_B"}),
    ]
    sparse_list = [
        ("doc_B", 8.5, {"chunk_uid": "chunk_B"}),
        ("doc_C", 5.0, {"chunk_uid": "chunk_C"}),
    ]

    fused = reciprocal_rank_fusion([dense_list, sparse_list], k=60)
    assert len(fused) == 3
    # doc_B appears in both rank lists (dense rank 2, sparse rank 1)
    # RRF score for B: 1/(60+2) + 1/(60+1) = 0.01613 + 0.01639 = 0.03252
    # RRF score for A: 1/(60+1) = 0.01639
    # RRF score for C: 1/(60+2) = 0.01613
    top_doc, top_score, top_meta = fused[0]
    assert top_meta["chunk_uid"] == "chunk_B", "Candidate appearing in both lists must rank first"
    assert "rrf_score" in top_meta
    assert "dense_rank" in top_meta
    assert "sparse_rank" in top_meta
    print("[PASS] test_rrf_fusion_logic passed.")


def test_hybrid_retrieval_end_to_end():
    # Query with semantic intent and exact number
    query = "What is the $75 per diem meal allowance?"
    results = retrieve(query, top_k=1, mode="hybrid")
    assert len(results) == 1
    doc, score, meta = results[0]
    assert meta["document_id"] == "travel_policy"
    assert "75" in doc
    assert "chunk_uid" in meta
    print("[PASS] test_hybrid_retrieval_end_to_end passed.")


def test_retrieval_mode_switching():
    query = "401k contribution match"
    dense_res = retrieve(query, top_k=2, mode="dense")
    sparse_res = retrieve(query, top_k=2, mode="sparse")
    hybrid_res = retrieve(query, top_k=2, mode="hybrid")

    assert len(dense_res) > 0
    assert len(sparse_res) > 0
    assert len(hybrid_res) > 0

    assert dense_res[0][2]["document_id"] == "benefits_policy"
    assert sparse_res[0][2]["document_id"] == "benefits_policy"
    assert hybrid_res[0][2]["document_id"] == "benefits_policy"
    print("[PASS] test_retrieval_mode_switching passed.")


if __name__ == "__main__":
    print("\n--- Running Hybrid Search & BM25 Unit Tests ---")
    test_bm25_tokenize()
    test_bm25_exact_keyword_and_number_retrieval()
    test_bm25_empty_and_missing_terms()
    test_bm25_metadata_filtering()
    test_rrf_fusion_logic()
    test_hybrid_retrieval_end_to_end()
    test_retrieval_mode_switching()
    print("\nAll hybrid search tests passed successfully!")
