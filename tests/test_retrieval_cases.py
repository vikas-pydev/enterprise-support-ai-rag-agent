"""Automated quality gate and benchmark suite for multi-document retrieval and cross-encoder reranking."""

import sys
import unittest

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.retriever import retrieve_from_vector_store, retrieve_with_rerank


test_cases = [
    # --- Leave Policy ---
    {
        "question": "How many annual leave days do employees receive?",
        "expected": "answerable",
        "expected_doc_id": "leave_policy",
        "relevant_chunks": [0],
    },
    {
        "question": "How many days can I carry forward?",
        "expected": "answerable",
        "expected_doc_id": "leave_policy",
        "relevant_chunks": [0],
    },
    {
        "question": "When must carry-forward leave be used?",
        "expected": "answerable",
        "expected_doc_id": "leave_policy",
        "relevant_chunks": [0],
    },
    {
        "question": "How do I get my annual leave approved?",
        "expected": "answerable",
        "expected_doc_id": "leave_policy",
        "relevant_chunks": [1],
    },
    # --- Attendance Policy ---
    {
        "question": "What are the core collaboration hours?",
        "expected": "answerable",
        "expected_doc_id": "attendance_policy",
        "relevant_chunks": [0],
    },
    {
        "question": "When must unexpected absences or tardiness be reported?",
        "expected": "answerable",
        "expected_doc_id": "attendance_policy",
        "relevant_chunks": [2],
    },
    # --- Travel Policy (Markdown) ---
    {
        "question": "What is the meal per diem allowance for domestic travel?",
        "expected": "answerable",
        "expected_doc_id": "travel_policy",
        "relevant_chunks": [2],
    },
    {
        "question": "When can an employee book business class flights?",
        "expected": "answerable",
        "expected_doc_id": "travel_policy",
        "relevant_chunks": [1],
    },
    # --- Benefits Policy ---
    {
        "question": "How much does the company match 401(k) contributions?",
        "expected": "answerable",
        "expected_doc_id": "benefits_policy",
        "relevant_chunks": [1],
    },
    {
        "question": "What is the annual wellness and fitness stipend?",
        "expected": "answerable",
        "expected_doc_id": "benefits_policy",
        "relevant_chunks": [2],
    },
    # --- Unanswerable Across Entire Corpus ---
    {
        "question": "How many sick leave days does an employee receive?",
        "expected": "unanswerable",
        "expected_doc_id": None,
        "relevant_chunks": [],
    },
    {
        "question": "How many maternity leave days are provided?",
        "expected": "unanswerable",
        "expected_doc_id": None,
        "relevant_chunks": [],
    },
    {
        "question": "What is the employee's work-from-home allowance?",
        "expected": "unanswerable",
        "expected_doc_id": None,
        "relevant_chunks": [],
    },
    {
        "question": "What is the company's pet insurance reimbursement policy?",
        "expected": "unanswerable",
        "expected_doc_id": None,
        "relevant_chunks": [],
    },
]


def evaluate_retrieval_mode(mode_name: str, retrieve_fn) -> dict:
    """Evaluates a retrieval function against test_cases benchmark dataset."""
    recall_hits = []
    precisions = []
    answerable_precisions = []
    unanswerable_precisions = []

    for case in test_cases:
        question = case["question"]
        expected = case["expected"]
        expected_doc = case.get("expected_doc_id")
        relevant_chunks = case["relevant_chunks"]

        results = retrieve_fn(question)

        retrieved_items = [
            (
                metadata.get("document_id", "doc"),
                metadata.get("chunk_id", 0),
            )
            for document, score_or_dist, metadata in results
        ]

        relevant_retrieved = [
            (doc_id, chunk_id)
            for doc_id, chunk_id in retrieved_items
            if (doc_id == expected_doc and chunk_id in relevant_chunks)
        ]

        if relevant_chunks:
            recall_hit = any(
                doc_id == expected_doc and chunk_id in relevant_chunks
                for doc_id, chunk_id in retrieved_items
            )
            recall_hits.append(1 if recall_hit else 0)
        else:
            recall_hit = len(results) == 0
            recall_hits.append(1 if recall_hit else 0)

        if results:
            precision = (
                len(relevant_retrieved)
                / len(retrieved_items)
            )
        else:
            precision = 1.0 if not relevant_chunks else 0.0

        precisions.append(precision)
        if expected == "answerable":
            answerable_precisions.append(precision)
        else:
            unanswerable_precisions.append(precision)

    mean_recall = sum(recall_hits) / len(recall_hits)
    mean_precision = sum(precisions) / len(precisions)
    mean_ans_precision = (
        sum(answerable_precisions) / len(answerable_precisions)
        if answerable_precisions
        else 0.0
    )
    mean_unans_precision = (
        sum(unanswerable_precisions) / len(unanswerable_precisions)
        if unanswerable_precisions
        else 0.0
    )

    return {
        "mode_name": mode_name,
        "recall_rate": mean_recall,
        "mean_precision": mean_precision,
        "ans_precision": mean_ans_precision,
        "unans_precision": mean_unans_precision,
    }


class TestRetrievalCases(unittest.TestCase):
    """Automated quality gate asserting retrieval accuracy, precision, and unanswerable rejection thresholds."""

    @classmethod
    def setUpClass(cls):
        """Execute baseline vector and two-stage reranked evaluations once for test suite."""
        cls.vector_metrics = evaluate_retrieval_mode(
            "Vector-Only",
            lambda q: retrieve_from_vector_store(q, top_k=3),
        )
        cls.reranked_metrics = evaluate_retrieval_mode(
            "Two-Stage Reranked",
            lambda q: retrieve_with_rerank(
                q,
                initial_top_k=10,
                final_top_k=3,
                score_threshold=5.0,
            ),
        )

    def test_01_reranked_retrieval_recall_gate(self):
        """Quality Gate: Two-stage retrieval recall must meet or exceed required threshold (>= 0.85)."""
        actual_recall = self.reranked_metrics["recall_rate"]
        min_required = 0.85
        self.assertGreaterEqual(
            actual_recall,
            min_required,
            f"Recall@K below required threshold: actual={actual_recall:.2f}, required>={min_required:.2f}",
        )

    def test_02_reranked_retrieval_precision_gate(self):
        """Quality Gate: Two-stage retrieval overall precision must meet or exceed required threshold (>= 0.75)."""
        actual_precision = self.reranked_metrics["mean_precision"]
        min_required = 0.75
        self.assertGreaterEqual(
            actual_precision,
            min_required,
            f"Precision below required threshold: actual={actual_precision:.2f}, required>={min_required:.2f}",
        )

    def test_03_reranked_answerable_precision_gate(self):
        """Quality Gate: Two-stage retrieval answerable precision must meet or exceed threshold (>= 0.85)."""
        actual_ans_prec = self.reranked_metrics["ans_precision"]
        min_required = 0.85
        self.assertGreaterEqual(
            actual_ans_prec,
            min_required,
            f"Answerable precision below required threshold: actual={actual_ans_prec:.2f}, required>={min_required:.2f}",
        )

    def test_04_reranked_unanswerable_rejection_gate(self):
        """Quality Gate: Two-stage retrieval unanswerable rejection precision must meet or exceed threshold (>= 0.85)."""
        actual_unans_prec = self.reranked_metrics["unans_precision"]
        min_required = 0.85
        self.assertGreaterEqual(
            actual_unans_prec,
            min_required,
            f"Unanswerable precision below required threshold: actual={actual_unans_prec:.2f}, required>={min_required:.2f}",
        )

    def test_05_two_stage_reranking_improves_unanswerable_rejection_over_baseline(self):
        """Invariant: Cross-encoder reranker score thresholding improves unanswerable rejection over raw vector retrieval."""
        vector_unans = self.vector_metrics["unans_precision"]
        reranked_unans = self.reranked_metrics["unans_precision"]
        self.assertGreater(
            reranked_unans,
            vector_unans,
            f"Two-stage reranking failed to improve unanswerable rejection: vector={vector_unans:.2f}, reranked={reranked_unans:.2f}",
        )

    def test_06_two_stage_reranking_improves_overall_precision_over_baseline(self):
        """Invariant: Cross-encoder reranking produces higher overall precision than raw vector retrieval."""
        vector_prec = self.vector_metrics["mean_precision"]
        reranked_prec = self.reranked_metrics["mean_precision"]
        self.assertGreater(
            reranked_prec,
            vector_prec,
            f"Two-stage reranking failed to improve precision: vector={vector_prec:.2f}, reranked={reranked_prec:.2f}",
        )


if __name__ == "__main__":
    unittest.main()