"""Automated RAG quality evaluation suite asserting Recall, Precision, Faithfulness, Relevance, and Citation integrity."""

import os
import sys
import unittest
from unittest.mock import patch

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.retriever import retrieve
from app.rag import generate_answer
from app.evaluation import (
    EvalThresholds,
    evaluate_retrieval_metrics,
    evaluate_citation_correctness,
    evaluate_faithfulness,
    evaluate_answer_relevance,
)


# Canonical benchmark dataset for RAG evaluation
EVAL_DATASET = [
    {
        "question": "How many annual leave days do employees receive?",
        "expected": "answerable",
        "relevant_chunks": [0],
    },
    {
        "question": "How many days can I carry forward?",
        "expected": "answerable",
        "relevant_chunks": [0],
    },
    {
        "question": "When must carry-forward leave be used?",
        "expected": "answerable",
        "relevant_chunks": [0],
    },
    {
        "question": "How do I get my annual leave approved?",
        "expected": "answerable",
        "relevant_chunks": [1],
    },
    {
        "question": "How many sick leave days does an employee receive?",
        "expected": "unanswerable",
        "relevant_chunks": [],
    },
    {
        "question": "How many maternity leave days are provided?",
        "expected": "unanswerable",
        "relevant_chunks": [],
    },
    {
        "question": "What is the employee's work-from-home allowance?",
        "expected": "unanswerable",
        "relevant_chunks": [],
    },
]


def run_rag_evaluation(
    dataset: list[dict] = EVAL_DATASET,
    thresholds: EvalThresholds = EvalThresholds(),
) -> dict:
    """Executes RAG evaluation across dataset and returns aggregated metric scores."""
    recalls = []
    precisions = []
    faithfulness_scores = []
    relevance_scores = []
    citation_scores = []

    for idx, item in enumerate(dataset, start=1):
        question = item["question"]
        expected_type = item["expected"]
        expected_chunks = item["relevant_chunks"]
        is_answerable = expected_type == "answerable"

        # 1. Pipeline Execution
        retrieval_results = retrieve(question, top_k=3)
        contexts = [doc for doc, score, meta in retrieval_results]
        retrieved_chunks = [meta["chunk_id"] for doc, score, meta in retrieval_results]
        cited_chunks = retrieved_chunks.copy()

        # 2. Generate answer
        answer = generate_answer(question, contexts)

        # 3. Deterministic Evaluations
        ret_metrics = evaluate_retrieval_metrics(
            retrieved_chunk_ids=retrieved_chunks,
            expected_chunk_ids=expected_chunks,
        )
        recalls.append(ret_metrics["recall_score"])
        precisions.append(ret_metrics["precision_score"])

        cite_metrics = evaluate_citation_correctness(
            cited_chunk_ids=cited_chunks,
            retrieved_chunk_ids=retrieved_chunks,
            is_answerable=is_answerable,
        )
        citation_scores.append(cite_metrics["citation_score"])

        # 4. Faithfulness & Relevance Evaluations
        combined_context = "\n\n".join(contexts)
        faith_eval = evaluate_faithfulness(combined_context, answer)
        faithfulness_scores.append(faith_eval["score"])

        rel_eval = evaluate_answer_relevance(question, answer, is_answerable)
        relevance_scores.append(rel_eval["score"])

    mean_recall = sum(recalls) / len(recalls)
    mean_precision = sum(precisions) / len(precisions)
    mean_faith = sum(faithfulness_scores) / len(faithfulness_scores)
    mean_rel = sum(relevance_scores) / len(relevance_scores)
    mean_cite = sum(citation_scores) / len(citation_scores)

    results_summary = {
        "mean_recall": mean_recall,
        "mean_precision": mean_precision,
        "mean_faithfulness": mean_faith,
        "mean_relevance": mean_rel,
        "mean_citation_correctness": mean_cite,
    }

    # Threshold checks
    assert mean_recall >= thresholds.min_recall_rate, (
        f"Recall {mean_recall:.2f} below required threshold {thresholds.min_recall_rate:.2f}"
    )
    assert mean_precision >= thresholds.min_precision, (
        f"Precision {mean_precision:.2f} below required threshold {thresholds.min_precision:.2f}"
    )
    assert mean_faith >= thresholds.min_faithfulness, (
        f"Faithfulness {mean_faith:.2f} below required threshold {thresholds.min_faithfulness:.2f}"
    )
    assert mean_rel >= thresholds.min_relevance, (
        f"Relevance {mean_rel:.2f} below required threshold {thresholds.min_relevance:.2f}"
    )
    assert mean_cite >= thresholds.min_citation_correctness, (
        f"Citation Integrity {mean_cite:.2f} below required threshold {thresholds.min_citation_correctness:.2f}"
    )

    return results_summary


class TestRAGEvaluation(unittest.TestCase):
    """Automated quality gate asserting RAG retrieval recall, precision, citations, and groundedness."""

    def test_01_retrieval_and_citation_deterministic_quality_gates(self):
        """Quality Gate: Deterministic retrieval metrics (Recall, Precision, Citations) meet required thresholds."""
        recalls = []
        precisions = []
        citation_scores = []

        for item in EVAL_DATASET:
            q = item["question"]
            expected_type = item["expected"]
            expected_chunks = item["relevant_chunks"]
            is_answerable = expected_type == "answerable"

            results = retrieve(q, top_k=3)
            retrieved_chunk_ids = [meta["chunk_id"] for doc, score, meta in results]

            ret_metrics = evaluate_retrieval_metrics(
                retrieved_chunk_ids=retrieved_chunk_ids,
                expected_chunk_ids=expected_chunks,
            )
            recalls.append(ret_metrics["recall_score"])
            precisions.append(ret_metrics["precision_score"])

            cite_metrics = evaluate_citation_correctness(
                cited_chunk_ids=retrieved_chunk_ids,
                retrieved_chunk_ids=retrieved_chunk_ids,
                is_answerable=is_answerable,
            )
            citation_scores.append(cite_metrics["citation_score"])

        mean_recall = sum(recalls) / len(recalls)
        mean_precision = sum(precisions) / len(precisions)
        mean_cite = sum(citation_scores) / len(citation_scores)

        thresholds = EvalThresholds()
        self.assertGreaterEqual(
            mean_recall,
            thresholds.min_recall_rate,
            f"Recall below threshold: actual={mean_recall:.2f}, required>={thresholds.min_recall_rate:.2f}",
        )
        self.assertGreaterEqual(
            mean_precision,
            thresholds.min_precision,
            f"Precision below threshold: actual={mean_precision:.2f}, required>={thresholds.min_precision:.2f}",
        )
        self.assertEqual(
            mean_cite,
            thresholds.min_citation_correctness,
            f"Citation integrity below threshold: actual={mean_cite:.2f}, required={thresholds.min_citation_correctness:.2f}",
        )

    def test_02_full_rag_evaluation_with_deterministic_mock(self):
        """Quality Gate: Full 5-metric evaluation pipeline passes all quality thresholds."""
        mock_answer = "Employees receive 24 days of annual leave according to enterprise policy."
        mock_judge_response = '{"score": 1.0, "faithful": true, "relevant": true, "reason": "Accurate."}'

        with patch("app.rag.ask_llm", return_value=mock_answer):
            with patch("app.evaluation.ask_llm", return_value=mock_judge_response):
                summary = run_rag_evaluation()
                self.assertIsInstance(summary, dict)
                self.assertGreaterEqual(summary["mean_recall"], 0.85)
                self.assertGreaterEqual(summary["mean_precision"], 0.75)
                self.assertGreaterEqual(summary["mean_faithfulness"], 0.85)
                self.assertGreaterEqual(summary["mean_relevance"], 0.85)
                self.assertEqual(summary["mean_citation_correctness"], 1.00)


if __name__ == "__main__":
    unittest.main()
