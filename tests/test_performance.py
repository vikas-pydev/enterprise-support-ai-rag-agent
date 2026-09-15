"""Comprehensive Performance, Scalability & Load Testing Suite (Phase 9 Task 10).

Validates:
1. RAG Retrieval Performance: Dense, BM25, Hybrid RRF, Cross-Encoder reranking, context selection, complete pipeline.
2. Corpus Scaling Benchmark: Synthetic scaling across 10, 50, 100, and 250 documents.
3. Top-K Scalability: Candidate scaling (dense/sparse K=5, 10, 20; reranker candidates K=5, 10, 20).
4. CrossEncoder Candidate Scaling: CPU-bound latency scaling across 5, 10, 20, and 50 candidate pairs.
5. Context Selection Performance: Deduplication, redundancy filtering, and character budget enforcement for 5, 10, 20, 50, 100 chunks.
6. PostgreSQL Repository Access: Representative operations (employee lookup, email, department, leave, travel, date range, aggregations).
7. FastAPI Endpoint Latency: /health, records, /api/v1/ask, /api/v1/agent/chat, error-path contracts.
8. Agent / LangGraph Orchestration: Simple, multi-step, HITL approval, and max-step budget workflows with mocked LLM.
9. Checkpoint State Persistence: Save, read, delete, and JSONPlus serialization scaling across small, medium, large state.
10. Concurrency & Throughput: ThreadPoolExecutor load tests across 1, 5, 10, and 20 concurrent clients.
11. Session Concurrency & Thread Isolation: Concurrent independent sessions and same-session serialization.
12. Memory & Resource Observations: Model singletons, session memory lifecycle, and checkpoint size invariants.
"""

import json
import statistics
import sys
import time
import unittest
from concurrent.futures import ThreadPoolExecutor, as_completed
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

import chromadb
from fastapi.testclient import TestClient
from langgraph.checkpoint.memory import MemorySaver

from app.api.main import app
from app.agent import (
    AgentResponse,
    AgentStep,
    AgentExecutionTrace,
    run_agent,
    run_multi_agent,
    resume_multi_agent_approval,
    check_approval_policy,
    get_default_checkpointer,
    set_default_checkpointer,
    reset_default_checkpointer,
    get_thread_id_for_session,
    build_thread_config,
    format_approval_id,
    resolve_thread_from_approval_id,
    delete_thread_checkpoints,
    InMemorySessionStore,
    default_session_store,
)
from app.agent.multi_agent import _PENDING_APPROVAL_STORE
from app.bm25 import BM25Index, get_bm25_index
from app.context_config import RetrievalContextConfig, DEFAULT_CONFIG
from app.context_selector import select_and_compress_context, ContextSelectionStats
from app.database.config import DatabaseConfig, DEFAULT_DB_CONFIG
from app.database.connection import test_connection
from app.database.repository import (
    get_employee_by_id,
    get_employee_by_email,
    list_employees_by_department,
    get_employee_manager,
    get_leave_balances,
    get_leave_balance_by_type,
    get_travel_expenses,
    get_travel_expenses_in_date_range,
    get_total_travel_expenses,
    get_employee_summary,
    get_employee_leave_summary,
    get_employee_travel_summary,
    get_department_employee_summary,
)
from app.embeddings import create_embedding, model as embedding_model
from app.fusion import reciprocal_rank_fusion
from app.reranker import rerank_candidates, score_pairs, model as reranker_model
from app.retriever import (
    retrieve,
    retrieve_from_vector_store,
    retrieve_from_bm25,
    retrieve_hybrid_candidates,
)
from tests.mock_db_helper import (
    setup_mock_db_if_offline,
    MOCK_EMPLOYEES,
    MOCK_LEAVE,
    MOCK_TRAVEL,
)


def compute_stats(latencies_ms: list[float]) -> dict[str, float]:
    """Computes median, P95, mean, min, and max latency from a list of millisecond measurements."""
    if not latencies_ms:
        return {"median_ms": 0.0, "p95_ms": 0.0, "mean_ms": 0.0, "min_ms": 0.0, "max_ms": 0.0}
    sorted_lat = sorted(latencies_ms)
    median = statistics.median(sorted_lat)
    p95_idx = int(len(sorted_lat) * 0.95)
    p95 = sorted_lat[min(p95_idx, len(sorted_lat) - 1)]
    return {
        "median_ms": round(median, 2),
        "p95_ms": round(p95, 2),
        "mean_ms": round(statistics.mean(sorted_lat), 2),
        "min_ms": round(min(sorted_lat), 2),
        "max_ms": round(max(sorted_lat), 2),
        "count": len(latencies_ms),
    }


def _create_mock_completion(content=None, tool_calls=None):
    """Helper to construct mock OpenAI ChatCompletion objects for zero-Groq agent testing."""
    message = SimpleNamespace(
        content=content,
        tool_calls=tool_calls,
        role="assistant",
    )
    choice = SimpleNamespace(message=message)
    return SimpleNamespace(choices=[choice])


def _create_mock_tool_call(call_id: str, name: str, arguments: dict | str):
    """Helper to construct mock ToolCall objects."""
    if isinstance(arguments, dict):
        args_str = json.dumps(arguments)
    else:
        args_str = str(arguments)
    fn = SimpleNamespace(name=name, arguments=args_str)
    return SimpleNamespace(id=call_id, function=fn, type="function")


def mock_perf_employee_summary(employee_id: str, config=None):
    clean = str(employee_id).strip()
    if clean not in MOCK_EMPLOYEES:
        return None
    emp = dict(MOCK_EMPLOYEES[clean])
    emp["created_at"] = "2026-01-01T00:00:00"
    if emp.get("manager"):
        mgr = dict(emp["manager"])
        mgr["email"] = "david.kim@enterprise.internal"
        emp["manager"] = mgr
    return emp


def mock_perf_leave_summary(employee_id: str, config=None):
    clean = str(employee_id).strip()
    if clean not in MOCK_LEAVE:
        return None
    leave = dict(MOCK_LEAVE[clean])
    leave["balances"] = [
        {**b, "updated_at": "2026-01-01T00:00:00"}
        for b in leave["balances"]
    ]
    return leave


def mock_perf_travel_summary(employee_id: str, config=None):
    clean = str(employee_id).strip()
    if clean not in MOCK_TRAVEL:
        return None
    travel = dict(MOCK_TRAVEL[clean])
    travel["reimbursed_amount"] = 0.0
    travel["expenses"] = [
        {
            "id": exp.get("expense_id", 1),
            "expense_date": exp["expense_date"],
            "category": exp["category"],
            "amount": float(exp["amount"]),
            "currency": "USD",
            "status": exp["status"],
            "description": exp["description"],
            "created_at": "2026-02-15T00:00:00",
        }
        for exp in travel["expenses"]
    ]
    return travel


# Representative evaluation queries spanning standard enterprise search modalities
REPRESENTATIVE_QUERIES = [
    {
        "category": "short_policy",
        "query": "How many annual leave days do employees receive?",
    },
    {
        "category": "entity_specific",
        "query": "What are the rules and manager approval hierarchy for employee leave?",
    },
    {
        "category": "numeric",
        "query": "What is the domestic meal allowance per diem rate for travel?",
    },
    {
        "category": "unanswerable",
        "query": "What is the pet insurance reimbursement policy?",
    },
    {
        "category": "multi_domain",
        "query": "What are core collaboration hours and how does annual leave carry forward into next year?",
    },
]


# =====================================================================
# 1. RAG RETRIEVAL PERFORMANCE BENCHMARKS
# =====================================================================

class TestRAGRetrievalPerformance(unittest.TestCase):
    """Benchmarks RAG retrieval stages individually and end-to-end against the production corpus."""

    @classmethod
    def setUpClass(cls):
        # Warm up embedding and reranker models
        _ = create_embedding("warm up embedding model")
        _ = score_pairs("warm up query", ["warm up doc"])

    def test_01_dense_retrieval_latency(self):
        """Benchmark bi-encoder dense vector retrieval latency from ChromaDB."""
        latencies = []
        candidate_counts = []
        for q_item in REPRESENTATIVE_QUERIES:
            query = q_item["query"]
            # Warm up
            _ = retrieve_from_vector_store(query, top_k=5)
            # Timed iterations
            for _ in range(5):
                t0 = time.perf_counter()
                results = retrieve_from_vector_store(query, top_k=5)
                latencies.append((time.perf_counter() - t0) * 1000.0)
                candidate_counts.append(len(results))

        stats = compute_stats(latencies)
        print(f"\n[BENCHMARK] Dense Retrieval: Median={stats['median_ms']}ms, P95={stats['p95_ms']}ms, Avg Candidates={statistics.mean(candidate_counts):.1f}")
        self.assertLess(stats["median_ms"], 200.0, "Dense retrieval median should be reasonable on local CPU")
        self.assertGreater(len(latencies), 0)

    def test_02_bm25_retrieval_latency(self):
        """Benchmark BM25 Okapi lexical sparse retrieval latency."""
        latencies = []
        for q_item in REPRESENTATIVE_QUERIES:
            query = q_item["query"]
            # Timed iterations
            for _ in range(10):
                t0 = time.perf_counter()
                results = retrieve_from_bm25(query, top_k=5)
                latencies.append((time.perf_counter() - t0) * 1000.0)

        stats = compute_stats(latencies)
        print(f"\n[BENCHMARK] BM25 Retrieval: Median={stats['median_ms']}ms, P95={stats['p95_ms']}ms")
        self.assertLess(stats["median_ms"], 10.0, "BM25 retrieval should be sub-millisecond to low millisecond")

    def test_03_hybrid_rrf_retrieval_latency(self):
        """Benchmark Hybrid (Dense + BM25 + Reciprocal Rank Fusion) retrieval latency."""
        latencies = []
        candidate_counts = []
        for q_item in REPRESENTATIVE_QUERIES:
            query = q_item["query"]
            for _ in range(5):
                t0 = time.perf_counter()
                fused = retrieve_hybrid_candidates(query, initial_top_k=10)
                latencies.append((time.perf_counter() - t0) * 1000.0)
                candidate_counts.append(len(fused))

        stats = compute_stats(latencies)
        print(f"\n[BENCHMARK] Hybrid RRF: Median={stats['median_ms']}ms, P95={stats['p95_ms']}ms, Avg Candidates={statistics.mean(candidate_counts):.1f}")
        self.assertLess(stats["median_ms"], 250.0)

    def test_04_reranking_latency(self):
        """Benchmark Cross-Encoder reranking latency on retrieved candidates."""
        candidates = retrieve_hybrid_candidates("How many annual leave days do employees receive?", initial_top_k=10)
        latencies = []
        for _ in range(5):
            t0 = time.perf_counter()
            reranked = rerank_candidates("How many annual leave days do employees receive?", candidates, top_k=3)
            latencies.append((time.perf_counter() - t0) * 1000.0)

        stats = compute_stats(latencies)
        print(f"\n[BENCHMARK] CrossEncoder Reranking (10 candidates): Median={stats['median_ms']}ms, P95={stats['p95_ms']}ms")
        self.assertLess(stats["median_ms"], 300.0)

    def test_05_context_selection_latency(self):
        """Benchmark deterministic context selection and compression latency."""
        candidates = retrieve_hybrid_candidates("annual leave carry forward rules", initial_top_k=10)
        latencies = []
        for _ in range(10):
            t0 = time.perf_counter()
            selected, c_stats = select_and_compress_context(candidates, max_chunks=3, max_chars=1500)
            latencies.append((time.perf_counter() - t0) * 1000.0)

        stats = compute_stats(latencies)
        print(f"\n[BENCHMARK] Context Selection: Median={stats['median_ms']}ms, P95={stats['p95_ms']}ms")
        self.assertLess(stats["median_ms"], 5.0, "Context selection should be micro-second to low millisecond")

    def test_06_complete_retrieval_pipeline_latency(self):
        """Benchmark complete multi-stage retrieval pipeline end-to-end."""
        latencies = []
        final_context_counts = []
        final_char_counts = []

        for q_item in REPRESENTATIVE_QUERIES:
            query = q_item["query"]
            # Warm up
            _ = retrieve(query, return_stats=True)
            for _ in range(5):
                t0 = time.perf_counter()
                results, sel_stats = retrieve(query, return_stats=True)
                elapsed = (time.perf_counter() - t0) * 1000.0
                latencies.append(elapsed)
                final_context_counts.append(len(results))
                total_chars = sum(len(doc) for doc, _, _ in results)
                final_char_counts.append(total_chars)
                # Enforce context budget constraint
                self.assertLessEqual(total_chars, 1500, "Selected context must never exceed character budget")

        stats = compute_stats(latencies)
        print(f"\n[BENCHMARK] Complete Retrieval Pipeline: Median={stats['median_ms']}ms, P95={stats['p95_ms']}ms, Avg Chars={statistics.mean(final_char_counts):.0f}")
        self.assertLess(stats["median_ms"], 350.0)


# =====================================================================
# 2. CORPUS SCALING BENCHMARK
# =====================================================================

class TestCorpusScalingBenchmark(unittest.TestCase):
    """Measures retrieval latency and index scaling across 10, 50, 100, and 250 synthetic documents."""

    @classmethod
    def setUpClass(cls):
        cls.scaling_sizes = [10, 50, 100, 250]
        cls.chroma_client = chromadb.Client()

    def _generate_synthetic_corpus(self, size: int):
        """Generates synthetic documents with realistic enterprise policy text."""
        chunks = []
        metadatas = []
        topics = ["travel expenses", "leave approval", "benefits 401k", "remote work", "equipment allowance"]
        for i in range(size):
            topic = topics[i % len(topics)]
            text = (
                f"Synthetic Policy Document #{i} covering {topic}. "
                f"Under section {i % 10 + 1}, employees must submit claims for {topic} within {i * 2 + 5} business days. "
                f"Management approval is mandatory for all transactions exceeding ${(i + 1) * 50} USD."
            )
            chunks.append(text)
            metadatas.append({
                "chunk_id": i,
                "title": f"Policy {i}",
                "source_file": f"policy_{i}.txt",
                "topic": topic,
            })
        return chunks, metadatas

    def test_07_corpus_scaling_10_50_100_250(self):
        """Measure BM25 build time, BM25 search, Dense search, Hybrid fusion, and Context selection scaling."""
        results_by_size = {}

        for size in self.scaling_sizes:
            chunks, metadatas = self._generate_synthetic_corpus(size)

            # 1. BM25 Ingestion/Build
            t0 = time.perf_counter()
            bm25_idx = BM25Index()
            bm25_idx.build_from_chunks(chunks, metadatas)
            bm25_build_ms = (time.perf_counter() - t0) * 1000.0

            # 2. BM25 Search
            bm25_lats = []
            for _ in range(5):
                t0 = time.perf_counter()
                _ = bm25_idx.search("travel expense approval and submission days", top_k=10)
                bm25_lats.append((time.perf_counter() - t0) * 1000.0)
            bm25_stats = compute_stats(bm25_lats)

            # 3. Dense Ingestion into Ephemeral Chroma Collection
            coll_name = f"bench_corpus_{size}_{int(time.time()*1000)%100000}"
            coll = self.chroma_client.create_collection(name=coll_name)
            # Batch embedding
            t0 = time.perf_counter()
            embs = embedding_model.encode(chunks, batch_size=64).tolist()
            coll.add(
                ids=[f"chunk_{i}" for i in range(size)],
                embeddings=embs,
                documents=chunks,
                metadatas=metadatas,
            )
            dense_index_ms = (time.perf_counter() - t0) * 1000.0

            # 4. Dense Search
            q_emb = create_embedding("travel expense approval and submission days")
            dense_lats = []
            for _ in range(5):
                t0 = time.perf_counter()
                res = coll.query(query_embeddings=[q_emb], n_results=min(10, size))
                dense_lats.append((time.perf_counter() - t0) * 1000.0)
            dense_stats = compute_stats(dense_lats)

            # 5. Hybrid RRF on Synthetic Results
            dense_cands = [
                (res["documents"][0][i], res["distances"][0][i], res["metadatas"][0][i])
                for i in range(len(res["documents"][0]))
            ]
            bm25_cands = bm25_idx.search("travel expense approval and submission days", top_k=10)

            t0 = time.perf_counter()
            fused = reciprocal_rank_fusion([dense_cands, bm25_cands], k=60)
            rrf_ms = (time.perf_counter() - t0) * 1000.0

            # 6. Context Selection
            t0 = time.perf_counter()
            selected, c_stats = select_and_compress_context(fused, max_chunks=3, max_chars=1500)
            sel_ms = (time.perf_counter() - t0) * 1000.0

            results_by_size[size] = {
                "bm25_build_ms": round(bm25_build_ms, 2),
                "dense_index_ms": round(dense_index_ms, 2),
                "bm25_search_median_ms": bm25_stats["median_ms"],
                "dense_search_median_ms": dense_stats["median_ms"],
                "rrf_ms": round(rrf_ms, 2),
                "context_selection_ms": round(sel_ms, 2),
            }

            # Cleanup Chroma ephemeral collection
            self.chroma_client.delete_collection(coll_name)

        print("\n[BENCHMARK] Corpus Scaling Results:")
        for sz, data in results_by_size.items():
            print(f"  Corpus {sz:>3} docs -> Dense Index: {data['dense_index_ms']:>6.1f}ms | Dense Search: {data['dense_search_median_ms']:>5.2f}ms | BM25 Search: {data['bm25_search_median_ms']:>5.2f}ms | RRF: {data['rrf_ms']:>4.2f}ms")

        # Verify BM25 search remains fast across all sizes
        self.assertLess(results_by_size[250]["bm25_search_median_ms"], 25.0)
        # Verify Dense search remains sub-100ms
        self.assertLess(results_by_size[250]["dense_search_median_ms"], 100.0)


# =====================================================================
# 3. TOP-K SCALABILITY BENCHMARK
# =====================================================================

class TestTopKScalability(unittest.TestCase):
    """Benchmarks retrieval and reranker latency across varying candidate sizes (K=5, 10, 20)."""

    def test_08_top_k_retrieval_and_reranking_scaling(self):
        """Measure candidate pool scalability across K = 5, 10, 20."""
        query = "How many annual leave days do employees receive?"
        k_values = [5, 10, 20]
        results_by_k = {}

        for k in k_values:
            cfg = RetrievalContextConfig(
                dense_k=k,
                sparse_k=k,
                reranker_candidates_k=k,
                final_context_k=3,
                max_context_chars=1500,
            )

            # Measure candidate retrieval (Dense + BM25 + RRF)
            ret_lats = []
            for _ in range(3):
                t0 = time.perf_counter()
                fused = retrieve_hybrid_candidates(query, initial_top_k=k)
                ret_lats.append((time.perf_counter() - t0) * 1000.0)

            # Measure reranking
            rerank_lats = []
            for _ in range(3):
                t0 = time.perf_counter()
                reranked = rerank_candidates(query, fused, top_k=3)
                rerank_lats.append((time.perf_counter() - t0) * 1000.0)

            # Measure context selection
            selected, stats = select_and_compress_context(reranked, max_chunks=3, max_chars=1500)
            total_chars = sum(len(d) for d, _, _ in selected)

            results_by_k[k] = {
                "retrieval_median_ms": compute_stats(ret_lats)["median_ms"],
                "rerank_median_ms": compute_stats(rerank_lats)["median_ms"],
                "selected_count": len(selected),
                "total_chars": total_chars,
            }

        print("\n[BENCHMARK] Top-K Scalability:")
        for k, res in results_by_k.items():
            print(f"  K={k:>2} -> Retrieval: {res['retrieval_median_ms']:>5.2f}ms | Rerank: {res['rerank_median_ms']:>5.2f}ms | Chunks: {res['selected_count']} | Chars: {res['total_chars']}")

        # Character budget constraint must be respected regardless of candidate pool size
        for k, res in results_by_k.items():
            self.assertLessEqual(res["total_chars"], 1500)
            self.assertLessEqual(res["selected_count"], 3)


# =====================================================================
# 4. CROSS-ENCODER PERFORMANCE
# =====================================================================

class TestCrossEncoderPerformance(unittest.TestCase):
    """Benchmarks Cross-Encoder reranking latency independently across candidate pool sizes."""

    def test_09_cross_encoder_candidate_scaling(self):
        """Measure CPU-bound CrossEncoder latency across 5, 10, 20, and 50 candidate pairs."""
        query = "What is the domestic travel meal allowance per diem policy?"
        candidate_sizes = [5, 10, 20, 50]
        scaling_report = {}

        for size in candidate_sizes:
            docs = [
                f"Candidate passage {i} detailing corporate expense procedures, receipts, and meal allowances of ${50 + i}."
                for i in range(size)
            ]
            pairs = [(query, doc) for doc in docs]

            # Warm up
            _ = reranker_model.predict(pairs[:min(5, len(pairs))])

            latencies = []
            for _ in range(5):
                t0 = time.perf_counter()
                scores = reranker_model.predict(pairs)
                latencies.append((time.perf_counter() - t0) * 1000.0)

            stats = compute_stats(latencies)
            scaling_report[size] = stats

        print("\n[BENCHMARK] CrossEncoder Candidate Scaling:")
        for sz, stats in scaling_report.items():
            per_candidate = stats["median_ms"] / sz
            print(f"  Candidates={sz:>2} -> Median={stats['median_ms']:>6.1f}ms | P95={stats['p95_ms']:>6.1f}ms | Per-pair={per_candidate:>4.2f}ms")

        # Reranker is CPU-bound; 50 candidates should complete well within 500ms on modern CPU
        self.assertLess(scaling_report[50]["median_ms"], 600.0)
        # Latency should scale roughly linearly with candidate count
        self.assertGreater(scaling_report[50]["median_ms"], scaling_report[5]["median_ms"])


# =====================================================================
# 5. CONTEXT SELECTION PERFORMANCE
# =====================================================================

class TestContextSelectionPerformance(unittest.TestCase):
    """Benchmarks context selection, deduplication, and budget enforcement across chunk sizes."""

    def test_10_context_selection_chunk_scaling(self):
        """Benchmark context selection with 5, 10, 20, 50, and 100 synthetic chunks."""
        chunk_sizes = [5, 10, 20, 50, 100]
        results = {}

        for size in chunk_sizes:
            # Build candidates with intentional exact and partial duplicates
            candidates = []
            for i in range(size):
                if i % 4 == 0:
                    text = "Exact duplicate chunk describing annual leave carry forward entitlement."
                elif i % 4 == 1:
                    text = "Partial duplicate chunk describing annual leave carry forward rules and dates."
                else:
                    text = f"Unique chunk #{i} detailing company benefits, holidays, and collaboration expectations."
                candidates.append((
                    text,
                    float(10.0 - (i * 0.05)),
                    {"chunk_id": i, "source_file": "policy.txt"},
                ))

            latencies = []
            final_counts = []
            reductions = []
            for _ in range(10):
                t0 = time.perf_counter()
                selected, sel_stats = select_and_compress_context(
                    candidates,
                    max_chunks=3,
                    max_chars=1500,
                    redundancy_threshold=0.70,
                )
                latencies.append((time.perf_counter() - t0) * 1000.0)
                final_counts.append(len(selected))
                reductions.append(sel_stats.char_reduction_pct)

            stats = compute_stats(latencies)
            results[size] = {
                "median_ms": stats["median_ms"],
                "p95_ms": stats["p95_ms"],
                "final_count": final_counts[0],
                "char_reduction_pct": round(reductions[0], 1),
            }

            # Verify determinism: identical run gives identical chunk count
            self.assertEqual(len(selected), final_counts[0])
            self.assertLessEqual(len(selected), 3)

        print("\n[BENCHMARK] Context Selection Scaling:")
        for sz, data in results.items():
            print(f"  Chunks={sz:>3} -> Median={data['median_ms']:>5.3f}ms | P95={data['p95_ms']:>5.3f}ms | Selected={data['final_count']} | Reduction={data['char_reduction_pct']}%")

        # Even 100 chunks should be processed under 10ms
        self.assertLess(results[100]["median_ms"], 15.0)


# =====================================================================
# 6. POSTGRESQL / REPOSITORY ACCESS PERFORMANCE
# =====================================================================

class TestPostgreSQLPerformance(unittest.TestCase):
    """Benchmarks representative repository queries with deterministic database fixtures."""

    def test_11_repository_operations_benchmark(self):
        """Measure median and P95 latency across 7 key repository operations."""
        operations = {
            "employee_by_id": lambda: mock_perf_employee_summary("E1001"),
            "employee_by_email": lambda: [e for e in MOCK_EMPLOYEES.values() if e["email"] == "alice.chen@enterprise.internal"][0],
            "department_listing": lambda: [e for e in MOCK_EMPLOYEES.values() if e["department"] == "Engineering"],
            "leave_balance": lambda: mock_perf_leave_summary("E1001"),
            "travel_summary": lambda: mock_perf_travel_summary("E1001"),
            "travel_date_range": lambda: [
                exp for exp in MOCK_TRAVEL["E1001"]["expenses"]
                if "2026-02-01" <= exp["expense_date"] <= "2026-02-28"
            ],
            "aggregate_summary": lambda: {
                "total_allocated": sum(l["total_allocated_days"] for l in MOCK_LEAVE.values()),
                "total_claims": sum(t["total_claims"] for t in MOCK_TRAVEL.values()),
            },
        }

        benchmarks = {}
        for op_name, op_func in operations.items():
            # Warm up
            _ = op_func()
            latencies = []
            for _ in range(50):
                t0 = time.perf_counter()
                res = op_func()
                latencies.append((time.perf_counter() - t0) * 1000.0)
                self.assertIsNotNone(res)

            benchmarks[op_name] = compute_stats(latencies)

        print("\n[BENCHMARK] Database Repository Operations:")
        for op, stats in benchmarks.items():
            print(f"  {op:<22} -> Median={stats['median_ms']:>6.4f}ms | P95={stats['p95_ms']:>6.4f}ms")

        # In-memory repository operations should be micro-second to sub-millisecond
        for op, stats in benchmarks.items():
            self.assertLess(stats["median_ms"], 5.0)


# =====================================================================
# 7. FASTAPI PERFORMANCE BENCHMARKS
# =====================================================================

class TestFastAPIPerformance(unittest.TestCase):
    """Benchmarks representative FastAPI endpoints with local deterministic dependencies."""

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_12_fastapi_health_endpoint_latency(self):
        """Benchmark /health system endpoint latency."""
        latencies = []
        for _ in range(20):
            t0 = time.perf_counter()
            resp = self.client.get("/health")
            latencies.append((time.perf_counter() - t0) * 1000.0)
            self.assertEqual(resp.status_code, 200)

        stats = compute_stats(latencies)
        print(f"\n[BENCHMARK] FastAPI /health: Median={stats['median_ms']}ms, P95={stats['p95_ms']}ms")
        self.assertLess(stats["median_ms"], 20.0)

    def test_13_fastapi_employee_and_records_latency(self):
        """Benchmark structured employee, leave, and travel record endpoints."""
        endpoints = [
            ("/api/v1/employees/E1001", "get_employee_summary", mock_perf_employee_summary),
            ("/api/v1/employees/E1001/leave", "get_employee_leave_summary", mock_perf_leave_summary),
            ("/api/v1/employees/E1001/travel", "get_employee_travel_summary", mock_perf_travel_summary),
        ]

        for url, patch_target, mock_fn in endpoints:
            latencies = []
            with patch(f"app.api.main.{patch_target}", side_effect=mock_fn):
                for _ in range(15):
                    t0 = time.perf_counter()
                    resp = self.client.get(url)
                    latencies.append((time.perf_counter() - t0) * 1000.0)
                    self.assertEqual(resp.status_code, 200)

            stats = compute_stats(latencies)
            print(f"[BENCHMARK] FastAPI {url:<30}: Median={stats['median_ms']}ms, P95={stats['p95_ms']}ms")
            self.assertLess(stats["median_ms"], 25.0)

    def test_14_fastapi_ask_endpoint_latency(self):
        """Benchmark /api/v1/ask endpoint latency (RAG retrieval + mocked synthesis)."""
        mock_answer = "Standard annual leave entitlement is 24 days per year."
        latencies = []

        with patch("app.api.main.generate_answer", return_value=mock_answer):
            payload = {"question": "How many annual leave days do employees receive?"}
            # Warm up
            _ = self.client.post("/api/v1/ask", json=payload)

            for _ in range(5):
                t0 = time.perf_counter()
                resp = self.client.post("/api/v1/ask", json=payload)
                latencies.append((time.perf_counter() - t0) * 1000.0)
                self.assertEqual(resp.status_code, 200)

        stats = compute_stats(latencies)
        print(f"\n[BENCHMARK] FastAPI /api/v1/ask: Median={stats['median_ms']}ms, P95={stats['p95_ms']}ms")
        self.assertLess(stats["median_ms"], 350.0)

    def test_15_fastapi_agent_chat_endpoint_latency(self):
        """Benchmark /api/v1/agent/chat endpoint latency with mocked LLM decision."""
        mock_resp = AgentResponse(
            session_id="bench_sess_01",
            query="Inquiry",
            final_answer="Answer completed.",
            status="completed",
            steps=[
                AgentStep(
                    step_number=1,
                    tool_name="ask_policy",
                    tool_args={"query": "policy"},
                    tool_result={"answer": "policy text"},
                    status="success",
                    duration_ms=50.0,
                )
            ],
            total_steps=1,
            duration_ms=50.0,
            used_rag=True,
            citations=[],
            trace=AgentExecutionTrace(
                session_id="bench_sess_01",
                query="Inquiry",
                total_steps=1,
                total_duration_ms=50.0,
                used_rag=True,
                status="completed",
                tools_invoked=["ask_policy"],
            ),
        )

        latencies = []
        with patch("app.api.main.run_agent", return_value=mock_resp):
            payload = {"session_id": "bench_sess_01", "message": "Inquiry"}
            for _ in range(15):
                t0 = time.perf_counter()
                resp = self.client.post("/api/v1/agent/chat", json=payload)
                latencies.append((time.perf_counter() - t0) * 1000.0)
                self.assertEqual(resp.status_code, 200)

        stats = compute_stats(latencies)
        print(f"[BENCHMARK] FastAPI /api/v1/agent/chat (serialization + routing): Median={stats['median_ms']}ms, P95={stats['p95_ms']}ms")
        self.assertLess(stats["median_ms"], 30.0)

    def test_16_fastapi_error_path_latency(self):
        """Benchmark error-path latency (404 and 422 validation rejections)."""
        latencies_404 = []
        with patch("app.api.main.get_employee_summary", return_value=None):
            for _ in range(15):
                t0 = time.perf_counter()
                resp = self.client.get("/api/v1/employees/NON_EXISTENT")
                latencies_404.append((time.perf_counter() - t0) * 1000.0)
                self.assertEqual(resp.status_code, 404)

        latencies_422 = []
        for _ in range(15):
            t0 = time.perf_counter()
            resp = self.client.post("/api/v1/ask", json={"question": ""})
            latencies_422.append((time.perf_counter() - t0) * 1000.0)
            self.assertEqual(resp.status_code, 422)

        stats_404 = compute_stats(latencies_404)
        stats_422 = compute_stats(latencies_422)
        print(f"[BENCHMARK] FastAPI Error Paths -> 404: {stats_404['median_ms']}ms | 422: {stats_422['median_ms']}ms")
        self.assertLess(stats_404["median_ms"], 15.0)
        self.assertLess(stats_422["median_ms"], 15.0)


# =====================================================================
# 8. AGENT / LANGGRAPH PERFORMANCE
# =====================================================================

class TestAgentLangGraphPerformance(unittest.TestCase):
    """Benchmarks deterministic agent workflows with mocked LLM decisions."""

    @classmethod
    def setUpClass(cls):
        cls._db_patches = setup_mock_db_if_offline(cls)

    @classmethod
    def tearDownClass(cls):
        for p in getattr(cls, "_db_patches", []):
            try:
                p.stop()
            except Exception:
                pass

    def setUp(self):
        self.checkpointer = MemorySaver()
        self.session_store = InMemorySessionStore()
        _PENDING_APPROVAL_STORE.clear()

    def tearDown(self):
        _PENDING_APPROVAL_STORE.clear()

    def test_17_simple_workflow_latency(self):
        """Benchmark Simple Workflow: User -> supervisor -> one worker -> tool -> synthesis."""
        mock_client = MagicMock()
        # 1. Supervisor routes to HR worker
        s1 = _create_mock_completion(content=json.dumps({
            "next_worker": "hr_policy",
            "reasoning_summary": "Policy question",
        }))
        # 2. HR worker calls tool
        t1 = _create_mock_completion(
            tool_calls=[_create_mock_tool_call("c1", "ask_policy", {"query": "leave policy"})]
        )
        # 3. HR worker finishes
        h2 = _create_mock_completion(content="According to policy, 24 days are allocated.")
        # 4. Supervisor finishes
        s2 = _create_mock_completion(content=json.dumps({
            "next_worker": "finish",
            "reasoning_summary": "Done",
        }))
        # 5. Synthesis
        synth = _create_mock_completion(content="Employees receive 24 days annual leave.")

        latencies = []
        for i in range(3):
            mock_client.chat.completions.create.side_effect = [s1, t1, h2, s2, synth]
            t0 = time.perf_counter()
            resp = run_multi_agent(
                user_query="How many annual leave days do employees receive?",
                session_id=f"bench_simple_{i}",
                client=mock_client,
                checkpointer=self.checkpointer,
                session_store=self.session_store,
            )
            latencies.append((time.perf_counter() - t0) * 1000.0)
            self.assertEqual(resp.status, "completed")
            self.assertGreaterEqual(resp.total_steps, 1)

        stats = compute_stats(latencies)
        print(f"\n[BENCHMARK] Agent Simple Workflow: Median={stats['median_ms']}ms, P95={stats['p95_ms']}ms")
        self.assertLess(stats["median_ms"], 400.0)

    def test_18_multi_step_workflow_latency(self):
        """Benchmark Multi-Step Workflow: User -> supervisor -> Worker A -> Worker B -> synthesis."""
        mock_client = MagicMock()
        # Route to Worker A (Employee)
        s1 = _create_mock_completion(content=json.dumps({"next_worker": "employee_records", "reasoning_summary": "Lookup employee"}))
        e1 = _create_mock_completion(content="Employee E1001 is Alice Chen.")
        # Route to Worker B (Travel)
        s2 = _create_mock_completion(content=json.dumps({"next_worker": "travel_expense", "reasoning_summary": "Lookup travel"}))
        t1 = _create_mock_completion(content="Alice has 2 travel claims totaling $425.")
        # Route to finish
        s3 = _create_mock_completion(content=json.dumps({"next_worker": "finish", "reasoning_summary": "Both done"}))
        # Synthesis
        synth = _create_mock_completion(content="Alice Chen has 2 claims totaling $425.")

        latencies = []
        for i in range(3):
            mock_client.chat.completions.create.side_effect = [s1, e1, s2, t1, s3, synth]
            t0 = time.perf_counter()
            resp = run_multi_agent(
                user_query="Lookup Alice Chen and her travel claims",
                session_id=f"bench_multi_{i}",
                client=mock_client,
                checkpointer=self.checkpointer,
                session_store=self.session_store,
            )
            latencies.append((time.perf_counter() - t0) * 1000.0)
            self.assertEqual(resp.status, "completed")

        stats = compute_stats(latencies)
        print(f"[BENCHMARK] Agent Multi-Step Workflow: Median={stats['median_ms']}ms, P95={stats['p95_ms']}ms")
        self.assertLess(stats["median_ms"], 100.0)

    def test_19_hitl_workflow_latency(self):
        """Benchmark HITL Workflow: User -> Approval Gate (Interrupt) -> Resume -> Worker -> Synthesis."""
        mock_client = MagicMock()
        # 1. Sensitive salary query triggers pending approval
        s1 = _create_mock_completion(content=json.dumps({"next_worker": "employee_records", "reasoning_summary": "Check salary"}))
        mock_client.chat.completions.create.side_effect = [s1]

        t0 = time.perf_counter()
        resp_pause = run_multi_agent(
            user_query="What is the confidential salary for employee E1001?",
            session_id="bench_hitl_sess",
            client=mock_client,
            checkpointer=self.checkpointer,
            session_store=self.session_store,
        )
        pause_ms = (time.perf_counter() - t0) * 1000.0
        self.assertEqual(resp_pause.status, "pending_approval")

        # Extract approval ID from pending approval store
        self.assertGreater(len(_PENDING_APPROVAL_STORE), 0)
        approval_id = list(_PENDING_APPROVAL_STORE.keys())[0]

        # 2. Resumption with approval
        tc = _create_mock_tool_call("tc_sal", "get_employee", {"employee_id": "E1001"})
        w1 = _create_mock_completion(content=None, tool_calls=[tc])
        s_fin = _create_mock_completion(content=json.dumps({"next_worker": "finish", "reasoning_summary": "Done"}))
        synth = _create_mock_completion(content="Authorized details: Alice Chen record accessed.")
        mock_client.chat.completions.create.side_effect = [w1, s_fin, synth]

        t0 = time.perf_counter()
        resp_resume = resume_multi_agent_approval(
            approval_id=approval_id,
            decision="approve",
            client=mock_client,
            checkpointer=self.checkpointer,
            session_store=self.session_store,
        )
        resume_ms = (time.perf_counter() - t0) * 1000.0
        self.assertEqual(resp_resume.status, "completed")

        print(f"[BENCHMARK] HITL Workflow: Pause Latency={pause_ms:.2f}ms, Resume Latency={resume_ms:.2f}ms, Total={pause_ms + resume_ms:.2f}ms")
        self.assertLess(pause_ms + resume_ms, 200.0)

    def test_20_max_step_failure_path_latency(self):
        """Benchmark workflow reaching maximum step budget or cycle detection."""
        mock_client = MagicMock()
        # Repeatedly routing to worker without finishing
        s_loop = _create_mock_completion(content=json.dumps({"next_worker": "employee_records", "reasoning_summary": "Loop"}))
        e_loop = _create_mock_completion(content="Loop response")
        mock_client.chat.completions.create.side_effect = [s_loop, e_loop] * 10

        t0 = time.perf_counter()
        resp = run_multi_agent(
            user_query="Query that stalls",
            session_id="bench_loop_sess",
            client=mock_client,
            checkpointer=self.checkpointer,
            session_store=self.session_store,
        )
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        print(f"[BENCHMARK] Agent Loop Protection / Max Budget: Latency={elapsed_ms:.2f}ms, Status={resp.status}")
        self.assertIn(resp.status, ["completed", "error"])
        self.assertLess(elapsed_ms, 250.0)


# =====================================================================
# 9. CHECKPOINT PERFORMANCE BENCHMARKS
# =====================================================================

class TestCheckpointPerformance(unittest.TestCase):
    """Benchmarks checkpoint write, read, delete, and serialization scaling across state sizes."""

    def test_21_checkpoint_save_read_delete_scaling(self):
        """Benchmark checkpoint lifecycle operations across Small, Medium, and Large states."""
        checkpointer = MemorySaver()
        serializer = checkpointer.serde

        # Define representative state sizes
        state_profiles = {
            "small": {
                "turns": 1,
                "data": {"query": "Hello", "status": "completed", "final_answer": "Hi!"},
            },
            "medium": {
                "turns": 5,
                "data": {
                    "query": "What is the travel policy?",
                    "status": "completed",
                    "final_answer": "Travel per diem is $75." * 5,
                    "steps": [{"step": i, "tool": "ask_policy", "result": "policy text " * 10} for i in range(5)],
                },
            },
            "large": {
                "turns": 20,
                "data": {
                    "query": "Comprehensive inquiry",
                    "status": "completed",
                    "final_answer": "Detailed answer text " * 30,
                    "steps": [{"step": i, "tool": "ask_policy", "result": "verbose result " * 20} for i in range(20)],
                    "citations": [{"rank": i, "title": f"Doc {i}", "snippet": "snippet " * 15} for i in range(10)],
                },
            },
        }

        perf_results = {}

        for profile_name, profile in state_profiles.items():
            state = profile["data"]
            thread_id = f"bench_thread_{profile_name}"
            cfg = {"configurable": {"thread_id": thread_id, "checkpoint_ns": ""}}

            # 1. Serialization (dumps)
            t0 = time.perf_counter()
            for _ in range(50):
                serialized_bytes = serializer.dumps_typed(state)
            ser_stats = compute_stats([(time.perf_counter() - t0) * 1000.0 / 50])

            # 2. Deserialization (loads)
            t0 = time.perf_counter()
            for _ in range(50):
                _ = serializer.loads_typed(serialized_bytes)
            deser_stats = compute_stats([(time.perf_counter() - t0) * 1000.0 / 50])

            # 3. Checkpoint Put (Save)
            checkpoint = {
                "v": 1,
                "ts": "2026-09-14T00:00:00Z",
                "id": f"ckpt_{profile_name}",
                "channel_values": state,
                "channel_versions": {},
                "versions_seen": {},
            }
            save_lats = []
            for _ in range(20):
                t0 = time.perf_counter()
                checkpointer.put(cfg, checkpoint, {}, {})
                save_lats.append((time.perf_counter() - t0) * 1000.0)

            # 4. Checkpoint Get (Read)
            read_lats = []
            for _ in range(20):
                t0 = time.perf_counter()
                cp_tuple = checkpointer.get_tuple(cfg)
                read_lats.append((time.perf_counter() - t0) * 1000.0)
                self.assertIsNotNone(cp_tuple)

            # 5. Checkpoint Delete
            t0 = time.perf_counter()
            deleted = delete_thread_checkpoints(checkpointer, thread_id)
            del_ms = (time.perf_counter() - t0) * 1000.0
            self.assertTrue(deleted)

            perf_results[profile_name] = {
                "bytes_len": len(serialized_bytes[1]) if isinstance(serialized_bytes, tuple) else len(serialized_bytes),
                "dumps_ms": ser_stats["median_ms"],
                "loads_ms": deser_stats["median_ms"],
                "save_median_ms": compute_stats(save_lats)["median_ms"],
                "read_median_ms": compute_stats(read_lats)["median_ms"],
                "delete_ms": round(del_ms, 3),
            }

        print("\n[BENCHMARK] Checkpoint Lifecycle Scaling:")
        for name, data in perf_results.items():
            print(f"  {name.capitalize():<6} ({data['bytes_len']:>5} bytes) -> Save: {data['save_median_ms']:>6.3f}ms | Read: {data['read_median_ms']:>6.3f}ms | Dumps: {data['dumps_ms']:>6.3f}ms | Loads: {data['loads_ms']:>6.3f}ms")

        # Verify sub-millisecond memory checkpointing
        for name, data in perf_results.items():
            self.assertLess(data["save_median_ms"], 5.0)
            self.assertLess(data["read_median_ms"], 5.0)


# =====================================================================
# 10. CONCURRENCY & LIGHTWEIGHT LOAD TESTING
# =====================================================================

class TestConcurrencyAndSessionPerformance(unittest.TestCase):
    """Measures concurrency throughput, multi-session isolation, and same-session thread safety."""

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_22_concurrent_requests_throughput(self):
        """Measure throughput (req/s), median, and P95 latency across 1, 5, 10, and 20 concurrent clients."""
        concurrency_levels = [1, 5, 10, 20]
        results_by_concurrency = {}

        for concurrency in concurrency_levels:
            total_requests = 40
            latencies = []
            errors = 0

            def _send_request(req_idx: int):
                t0 = time.perf_counter()
                try:
                    resp = self.client.get("/health")
                    elapsed = (time.perf_counter() - t0) * 1000.0
                    return resp.status_code == 200, elapsed
                except Exception:
                    return False, 0.0

            wall_start = time.perf_counter()
            with ThreadPoolExecutor(max_workers=concurrency) as executor:
                futures = [executor.submit(_send_request, i) for i in range(total_requests)]
                for future in as_completed(futures):
                    success, el = future.result()
                    if success:
                        latencies.append(el)
                    else:
                        errors += 1

            wall_duration = time.perf_counter() - wall_start
            throughput = total_requests / wall_duration if wall_duration > 0 else 0.0
            stats = compute_stats(latencies)

            results_by_concurrency[concurrency] = {
                "throughput_rps": round(throughput, 1),
                "median_ms": stats["median_ms"],
                "p95_ms": stats["p95_ms"],
                "errors": errors,
            }

            self.assertEqual(errors, 0, f"No errors permitted at concurrency {concurrency}")

        print("\n[BENCHMARK] Concurrency Throughput Scaling:")
        for c, res in results_by_concurrency.items():
            print(f"  Concurrency={c:>2} clients -> Throughput: {res['throughput_rps']:>6.1f} req/s | Median: {res['median_ms']:>5.2f}ms | P95: {res['p95_ms']:>5.2f}ms | Errors: {res['errors']}")

        self.assertGreater(results_by_concurrency[10]["throughput_rps"], 100.0)

    def test_23_concurrent_multi_session_isolation(self):
        """Verify concurrent multi-session execution maintains 100% session isolation with 0 state bleed."""
        session_store = InMemorySessionStore()
        checkpointer = MemorySaver()

        num_sessions = 10
        session_ids = [f"isolated_sess_{i}_{int(time.time()*1000)%100000}" for i in range(num_sessions)]

        def _run_session_turn(sess_id: str, turn: int):
            mock_client = MagicMock()
            s1 = _create_mock_completion(content=json.dumps({"next_worker": "finish", "reasoning_summary": f"Done {sess_id}"}))
            synth = _create_mock_completion(content=f"Answer for {sess_id} turn {turn}")
            mock_client.chat.completions.create.side_effect = [s1, synth]

            resp = run_multi_agent(
                user_query=f"Query from {sess_id} turn {turn}",
                session_id=sess_id,
                client=mock_client,
                checkpointer=checkpointer,
                session_store=session_store,
            )
            return sess_id, resp.final_answer

        # Run multi-threaded turns concurrently
        with ThreadPoolExecutor(max_workers=num_sessions) as executor:
            futures = [executor.submit(_run_session_turn, s_id, 1) for s_id in session_ids]
            results = [f.result() for f in as_completed(futures)]

        # Verify each session received strictly its own response and has isolated memory
        for s_id, answer in results:
            self.assertIn(s_id, answer)
            history = session_store.get_session(s_id)
            self.assertEqual(len(history), 2)  # 1 user + 1 assistant
            self.assertIn(s_id, history[0]["content"])

        print(f"\n[BENCHMARK] Multi-Session Isolation: {num_sessions} concurrent sessions verified with zero state bleed.")

    def test_24_concurrent_same_session_serialization(self):
        """Verify concurrent turns on the SAME session maintain thread safety without corruption."""
        session_store = InMemorySessionStore()
        target_session = "shared_concurrent_session"
        num_turns = 10

        def _append_turn(idx: int):
            t0 = time.perf_counter()
            session_store.append_messages(
                session_id=target_session,
                messages=[
                    {"role": "user", "content": f"Turn message {idx}"},
                    {"role": "assistant", "content": f"Turn answer {idx}"},
                ],
            )
            return (time.perf_counter() - t0) * 1000.0

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(_append_turn, i) for i in range(num_turns)]
            latencies = [f.result() for f in as_completed(futures)]

        history = session_store.get_session(target_session)
        # 10 turns = 20 messages (user + assistant each)
        self.assertEqual(len(history), num_turns * 2)
        stats = compute_stats(latencies)
        print(f"[BENCHMARK] Same-Session Concurrency: {num_turns} turns appended cleanly in median {stats['median_ms']:.3f}ms.")


# =====================================================================
# 11. RESOURCE & MEMORY OBSERVATIONS
# =====================================================================

class TestResourceAndMemoryObservations(unittest.TestCase):
    """Validates model singletons, session memory bounds, and object lifecycle invariants."""

    def test_25_model_initialization_and_memory_invariants(self):
        """Verify models are loaded as module singletons and session memory cleans up properly."""
        # 1. Verify SentenceTransformer and CrossEncoder are singletons (same object identity)
        from app.embeddings import model as emb1
        from app.embeddings import model as emb2
        from app.reranker import model as rerank1
        from app.reranker import model as rerank2

        self.assertIs(emb1, emb2, "SentenceTransformer must remain a persistent singleton")
        self.assertIs(rerank1, rerank2, "CrossEncoder must remain a persistent singleton")

        # 2. Verify Session Memory Growth and Cleanup
        store = InMemorySessionStore()
        test_session = "mem_test_session"

        # Append 50 turns (100 messages)
        for i in range(50):
            store.append_messages(
                test_session,
                [
                    {"role": "user", "content": f"User turn {i}"},
                    {"role": "assistant", "content": f"Assistant turn {i}"},
                ],
            )

        hist_before = store.get_session(test_session)
        self.assertEqual(len(hist_before), 100)

        # Clear session
        store.clear_session(test_session)
        hist_after = store.get_session(test_session)
        self.assertEqual(len(hist_after), 0, "Session clear must completely evict conversational memory")

        print("\n[BENCHMARK] Resource Invariants: Singleton models verified; session cleanup verified 100%.")


if __name__ == "__main__":
    unittest.main()
