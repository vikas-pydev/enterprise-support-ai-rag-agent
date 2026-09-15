"""Automated evaluation and benchmark suite for Dense, Sparse (BM25), and Hybrid Retrieval modes."""

import sys
import unittest

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.retriever import retrieve

# Benchmark queries specifically designed to stress-test Lexical (BM25) vs Semantic (Dense) vs Hybrid
HYBRID_EVAL_DATASET = [
    # --- Exact Number / Lexical Code Queries (Favors BM25) ---
    {
        "query": "What is the $75 per diem meal allowance?",
        "expected_doc": "travel_policy",
        "expected_chunk": 2,
        "type": "exact_number",
    },
    {
        "query": "Which policy specifies 10:00 AM core collaboration hours?",
        "expected_doc": "attendance_policy",
        "expected_chunk": 0,
        "type": "exact_time",
    },
    {
        "query": "What is the $500 annual reimbursement for fitness and gym?",
        "expected_doc": "benefits_policy",
        "expected_chunk": 2,
        "type": "exact_amount",
    },
    {
        "query": "How much does the company match on 401(k) contributions?",
        "expected_doc": "benefits_policy",
        "expected_chunk": 1,
        "type": "abbreviation_number",
    },
    # --- Paraphrased Semantic Queries (Favors Dense Vector) ---
    {
        "query": "Can I take time off for unforeseen personal emergencies?",
        "expected_doc": "leave_policy",
        "expected_chunk": 1,
        "type": "paraphrased_semantic",
    },
    {
        "query": "How do I submit requests for vacation days to my manager?",
        "expected_doc": "leave_policy",
        "expected_chunk": 1,
        "type": "paraphrased_semantic",
    },
    {
        "query": "When am I allowed to fly in premium cabins on business trips?",
        "expected_doc": "travel_policy",
        "expected_chunk": 1,
        "type": "paraphrased_semantic",
    },
    {
        "query": "What is the policy for being over 30 minutes late to work?",
        "expected_doc": "attendance_policy",
        "expected_chunk": 2,
        "type": "mixed_lexical_semantic",
    },
    # --- Unanswerable Queries (Tests Rejection Across All Modes) ---
    {
        "query": "What is the company reimbursement policy for pet insurance?",
        "expected_doc": None,
        "expected_chunk": None,
        "type": "unanswerable",
    },
    {
        "query": "How many sick leave days does an employee receive?",
        "expected_doc": None,
        "expected_chunk": None,
        "type": "unanswerable",
    },
]


def evaluate_retrieval_mode(mode: str, use_reranker: bool = True) -> dict:
    """Evaluates retrieval accuracy and precision for a given mode."""
    label = f"{mode.upper()} {'+ Rerank' if use_reranker else '(No Rerank)'}"
    recall_hits = []
    precisions = []

    for item in HYBRID_EVAL_DATASET:
        q = item["query"]
        expected_doc = item["expected_doc"]
        expected_chunk = item["expected_chunk"]
        is_unanswerable = expected_doc is None

        results = retrieve(q, top_k=3, mode=mode, use_reranker=use_reranker)

        retrieved_keys = [
            (meta.get("document_id"), meta.get("chunk_id"))
            for doc, score, meta in results
        ]

        if is_unanswerable:
            hit = len(results) == 0
            prec = 1.0 if hit else 0.0
        else:
            hit = (expected_doc, expected_chunk) in retrieved_keys
            relevant_count = sum(
                1 for d, c in retrieved_keys if d == expected_doc and c == expected_chunk
            )
            prec = (relevant_count / len(retrieved_keys)) if retrieved_keys else 0.0

        recall_hits.append(1 if hit else 0)
        precisions.append(prec)

    mean_recall = sum(recall_hits) / len(recall_hits)
    mean_precision = sum(precisions) / len(precisions)
    return {
        "mode": label,
        "recall": mean_recall,
        "precision": mean_precision,
    }


class TestHybridEvaluation(unittest.TestCase):
    """Automated benchmark asserting retrieval correctness across Dense, Sparse, and Hybrid modes."""

    @classmethod
    def setUpClass(cls):
        """Execute evaluation across all retrieval configurations once for suite."""
        cls.dense_raw = evaluate_retrieval_mode("dense", use_reranker=False)
        cls.sparse_raw = evaluate_retrieval_mode("sparse", use_reranker=False)
        cls.hybrid_raw = evaluate_retrieval_mode("hybrid", use_reranker=False)

        cls.dense_reranked = evaluate_retrieval_mode("dense", use_reranker=True)
        cls.sparse_reranked = evaluate_retrieval_mode("sparse", use_reranker=True)
        cls.hybrid_reranked = evaluate_retrieval_mode("hybrid", use_reranker=True)

    def test_01_dense_raw_retrieval_quality_gate(self):
        """Quality Gate: First-stage dense retrieval recall must meet baseline threshold (>= 0.75)."""
        actual = self.dense_raw["recall"]
        required = 0.75
        self.assertGreaterEqual(
            actual,
            required,
            f"Dense raw recall below threshold: actual={actual:.2f}, required>={required:.2f}",
        )

    def test_02_sparse_bm25_raw_retrieval_quality_gate(self):
        """Quality Gate: First-stage BM25 retrieval recall must meet baseline threshold (>= 0.65)."""
        actual = self.sparse_raw["recall"]
        required = 0.65
        self.assertGreaterEqual(
            actual,
            required,
            f"BM25 raw recall below threshold: actual={actual:.2f}, required>={required:.2f}",
        )

    def test_03_hybrid_fusion_raw_retrieval_quality_gate(self):
        """Quality Gate: First-stage hybrid RRF retrieval recall must meet baseline threshold (>= 0.75)."""
        actual = self.hybrid_raw["recall"]
        required = 0.75
        self.assertGreaterEqual(
            actual,
            required,
            f"Hybrid raw recall below threshold: actual={actual:.2f}, required>={required:.2f}",
        )

    def test_04_reranking_improves_precision_across_all_modes(self):
        """Invariant: Cross-encoder reranking yields higher precision than raw candidate pools."""
        for mode_name, raw_res, reranked_res in [
            ("Dense", self.dense_raw, self.dense_reranked),
            ("Sparse", self.sparse_raw, self.sparse_reranked),
            ("Hybrid", self.hybrid_raw, self.hybrid_reranked),
        ]:
            self.assertGreater(
                reranked_res["precision"],
                raw_res["precision"],
                f"{mode_name} reranking did not improve precision: raw={raw_res['precision']:.2f}, reranked={reranked_res['precision']:.2f}",
            )

    def test_05_hybrid_retrieval_handles_lexical_and_semantic_queries(self):
        """Verify hybrid search returns valid results for exact code/number queries and semantic queries."""
        lexical_query = "What is the $75 per diem meal allowance?"
        lex_results = retrieve(lexical_query, top_k=3, mode="hybrid")
        self.assertGreaterEqual(len(lex_results), 1)
        self.assertTrue(any(meta.get("document_id") == "travel_policy" for doc, score, meta in lex_results))

        semantic_query = "How many annual leave days do employees receive?"
        sem_results = retrieve(semantic_query, top_k=3, mode="hybrid")
        self.assertGreaterEqual(len(sem_results), 1)
        self.assertTrue(any(meta.get("document_id") == "leave_policy" for doc, score, meta in sem_results))


if __name__ == "__main__":
    unittest.main()
