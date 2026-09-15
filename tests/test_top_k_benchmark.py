"""Automated benchmark and quality gate for Top-K tuning and context selection optimization."""

import sys
import time
import unittest
from unittest.mock import patch

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.retriever import retrieve
from app.rag import generate_answer
from app.context_config import (
    RetrievalContextConfig,
    SMALL_CONFIG,
    MEDIUM_CONFIG,
    LARGE_CONFIG,
)
from app.evaluation import (
    evaluate_retrieval_metrics,
    evaluate_citation_correctness,
    evaluate_faithfulness,
    evaluate_answer_relevance,
)

BENCHMARK_DATASET = [
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
        "question": "What are the core collaboration hours?",
        "expected": "answerable",
        "relevant_chunks": [0],
    },
    {
        "question": "What is the meal per diem allowance for domestic travel?",
        "expected": "answerable",
        "relevant_chunks": [2],
    },
    {
        "question": "How much does the company match 401(k) contributions?",
        "expected": "answerable",
        "relevant_chunks": [1],
    },
    {
        "question": "How many sick leave days does an employee receive?",
        "expected": "unanswerable",
        "relevant_chunks": [],
    },
    {
        "question": "What is the company pet insurance reimbursement policy?",
        "expected": "unanswerable",
        "relevant_chunks": [],
    },
]


def run_single_config_benchmark(config_name: str, config: RetrievalContextConfig) -> dict:
    """Evaluates a retrieval context configuration against the benchmark dataset."""
    recalls = []
    precisions = []
    faithfulness_scores = []
    relevance_scores = []
    citation_scores = []
    retrieval_latencies = []
    total_latencies = []
    initial_chunks_list = []
    final_chunks_list = []
    char_reductions = []

    for item in BENCHMARK_DATASET:
        q = item["question"]
        expected_type = item["expected"]
        expected_chunks = item["relevant_chunks"]

        # 1. Timed Retrieval with Context Selection
        t0 = time.perf_counter()
        results, stats = retrieve(q, config=config, return_stats=True)
        t_ret = (time.perf_counter() - t0) * 1000.0
        retrieval_latencies.append(t_ret)

        contexts = [doc for doc, score, meta in results]
        retrieved_chunk_ids = [meta["chunk_id"] for doc, score, meta in results]

        initial_chunks_list.append(stats.initial_chunks)
        final_chunks_list.append(stats.final_chunks)
        char_reductions.append(stats.char_reduction_pct)

        # 2. Timed RAG Generation
        t_gen_start = time.perf_counter()
        answer = generate_answer(q, contexts)
        t_total = t_ret + ((time.perf_counter() - t_gen_start) * 1000.0)
        total_latencies.append(t_total)

        # 3. Metrics Evaluation
        ret_metrics = evaluate_retrieval_metrics(
            retrieved_chunk_ids=retrieved_chunk_ids,
            expected_chunk_ids=expected_chunks,
        )
        recalls.append(ret_metrics["recall_score"])
        precisions.append(ret_metrics["precision_score"])

        is_ans = expected_type == "answerable"
        cite_metrics = evaluate_citation_correctness(
            cited_chunk_ids=retrieved_chunk_ids,
            retrieved_chunk_ids=retrieved_chunk_ids,
            is_answerable=is_ans,
        )
        citation_scores.append(cite_metrics["citation_score"])

        faith_metrics = evaluate_faithfulness(context="\n\n".join(contexts), answer=answer)
        faithfulness_scores.append(faith_metrics["score"])

        rel_metrics = evaluate_answer_relevance(question=q, answer=answer, is_answerable=is_ans)
        relevance_scores.append(rel_metrics["score"])

    avg_recall = sum(recalls) / len(recalls)
    avg_precision = sum(precisions) / len(precisions)
    avg_faith = sum(faithfulness_scores) / len(faithfulness_scores)
    avg_rel = sum(relevance_scores) / len(relevance_scores)
    avg_cite = sum(citation_scores) / len(citation_scores)
    avg_ret_lat = sum(retrieval_latencies) / len(retrieval_latencies)
    avg_tot_lat = sum(total_latencies) / len(total_latencies)
    avg_init_chunks = sum(initial_chunks_list) / len(initial_chunks_list)
    avg_final_chunks = sum(final_chunks_list) / len(final_chunks_list)
    avg_char_red = sum(char_reductions) / len(char_reductions)

    return {
        "config_name": config_name,
        "config": config,
        "recall": avg_recall,
        "precision": avg_precision,
        "faithfulness": avg_faith,
        "relevance": avg_rel,
        "citation": avg_cite,
        "ret_lat_ms": avg_ret_lat,
        "tot_lat_ms": avg_tot_lat,
        "init_chunks": avg_init_chunks,
        "final_chunks": avg_final_chunks,
        "char_red_pct": avg_char_red,
    }


class TestTopKBenchmark(unittest.TestCase):
    """Automated benchmark asserting retrieval accuracy and context budget limits across Top-K configs."""

    @classmethod
    def setUpClass(cls):
        """Execute benchmarks across Small, Medium, Large configs with deterministic LLM mocks."""
        mock_answer = "Employees receive 24 days of annual leave according to enterprise policy."
        mock_judge = '{"score": 1.0, "faithful": true, "relevant": true, "reason": "Accurate."}'
        with patch("app.rag.ask_llm", return_value=mock_answer):
            with patch("app.evaluation.ask_llm", return_value=mock_judge):
                cls.small_res = run_single_config_benchmark("Small Pool", SMALL_CONFIG)
                cls.medium_res = run_single_config_benchmark("Medium Pool (Default)", MEDIUM_CONFIG)
                cls.large_res = run_single_config_benchmark("Large Pool", LARGE_CONFIG)

    def test_01_small_config_quality_gate(self):
        """Quality Gate: Small pool configuration achieves minimum required recall and precision."""
        self.assertGreaterEqual(
            self.small_res["recall"],
            0.85,
            f"Small config recall below threshold: actual={self.small_res['recall']:.2f}, required>=0.85",
        )
        self.assertGreaterEqual(
            self.small_res["precision"],
            0.75,
            f"Small config precision below threshold: actual={self.small_res['precision']:.2f}, required>=0.75",
        )

    def test_02_medium_default_config_quality_gate(self):
        """Quality Gate: Medium default configuration achieves minimum required recall and precision."""
        self.assertGreaterEqual(
            self.medium_res["recall"],
            0.85,
            f"Medium config recall below threshold: actual={self.medium_res['recall']:.2f}, required>=0.85",
        )
        self.assertGreaterEqual(
            self.medium_res["precision"],
            0.75,
            f"Medium config precision below threshold: actual={self.medium_res['precision']:.2f}, required>=0.75",
        )

    def test_03_large_config_quality_gate(self):
        """Quality Gate: Large pool configuration achieves minimum required recall and precision."""
        self.assertGreaterEqual(
            self.large_res["recall"],
            0.85,
            f"Large config recall below threshold: actual={self.large_res['recall']:.2f}, required>=0.85",
        )
        self.assertGreaterEqual(
            self.large_res["precision"],
            0.75,
            f"Large config precision below threshold: actual={self.large_res['precision']:.2f}, required>=0.75",
        )

    def test_04_citation_integrity_maintained_across_all_configs(self):
        """Quality Gate: Citation integrity score is 1.00 across all candidate pool sizes."""
        for res in [self.small_res, self.medium_res, self.large_res]:
            self.assertEqual(
                res["citation"],
                1.00,
                f"Citation integrity violated in {res['config_name']}: score={res['citation']:.2f}",
            )

    def test_05_context_budget_enforcement(self):
        """Invariant: Average final chunks never exceeds the configured final_context_k limit."""
        for res in [self.small_res, self.medium_res, self.large_res]:
            max_allowed = res["config"].final_context_k
            self.assertLessEqual(
                res["final_chunks"],
                max_allowed,
                f"{res['config_name']} exceeded chunk limit: actual={res['final_chunks']}, max={max_allowed}",
            )


if __name__ == "__main__":
    unittest.main()
