"""Master Test Runner for Enterprise Support AI Agent.

Consolidates and executes test suites across four clearly defined tiers:
- Tier A: Fast Deterministic Tests (Pure logic, unit tests, mock API, security)
- Tier B: Local Integration Tests (FastAPI contracts, DB hardening, checkpoints, HITL)
- Tier C: AI/LLM-Dependent Tests (Real Groq calls for live grounding & RAG evaluation)
- Tier D: Performance Benchmarks (P95 latency, throughput, context scaling)
"""

import argparse
import os
import sys
import subprocess
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


# =====================================================================
# TIER DEFINITIONS
# =====================================================================

# Tier A: 100% deterministic, 0 network, 0 Groq tokens
TIER_A_MODULES = [
    "tests.test_document_loader",
    "tests.test_multi_doc_loader",
    "tests.test_chunker",
    "tests.test_chunk_embeddings",
    "tests.test_embeddings",
    "tests.test_reranker",
    "tests.test_retrieval_filtering",
    "tests.test_retrieval_cases",
    "tests.test_hybrid_search",
    "tests.test_hybrid_evaluation",
    "tests.test_context_selection",
    "tests.test_top_k_benchmark",
    "tests.test_rag",
    "tests.test_rag_evaluation",
    "tests.test_langchain_tools",
    "tests.test_agent",
    "tests.test_agent_memory",
    "tests.test_agent_reliability",
    "tests.test_agent_reliability_hardening",
    "tests.test_agent_graph",
    "tests.test_multi_agent",
    "tests.test_security_adversarial",
    "tests.test_onnx_parity",
]

# Tier B: Local integration (local DB, ChromaDB, FastAPI contracts, checkpointers)
TIER_B_MODULES = [
    "tests.test_ingestion",
    "tests.test_vector_store",
    "tests.test_retriever",
    "tests.test_fastapi_contract_integration",
    "tests.test_api_integration_hardening",
    "tests.test_api",
    "tests.test_multi_agent_workflows",
    "tests.test_human_in_loop",
    "tests.test_checkpointing",
    "tests.test_hitl_checkpoint_hardening",
    "tests.test_database",
]

# Tier C: AI/LLM-dependent suites making real external Groq API calls
TIER_C_MODULES = [
    "tests.test_grounding",
    "tests.test_ui_integration",
]

# Tier D: Performance and scalability benchmarks
TIER_D_MODULES = [
    "tests.test_performance",
]


def get_default_env() -> dict:
    """Configures deterministic, offline environment variables."""
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["HF_HUB_OFFLINE"] = "1"
    env["TRANSFORMERS_OFFLINE"] = "1"
    env["ANONYMIZED_TELEMETRY"] = "False"
    env["TESTING"] = "1"
    if not env.get("LLM_API_KEY") and not env.get("GROQ_API_KEY"):
        env["LLM_API_KEY"] = "mock-ci-key-testing"
    return env



def run_tier(tier_name: str, modules: list[str], env: dict) -> tuple[int, list[str], float]:
    """Executes a list of test modules sequentially, capturing results and elapsed time."""
    print(f"\n{'=' * 75}")
    print(f"EXECUTING {tier_name.upper()} ({len(modules)} SUITES)")
    print(f"{'=' * 75}")

    passed = 0
    failed = []
    tier_start = time.perf_counter()

    for module in modules:
        mod_start = time.perf_counter()
        print(f"\n>> Executing: {sys.executable} -m {module}")
        res = subprocess.run([sys.executable, "-m", module], env=env)
        elapsed = time.perf_counter() - mod_start

        if res.returncode == 0:
            print(f"   --> {module}: PASSED ({elapsed:.2f}s)")
            passed += 1
        else:
            print(f"   --> {module}: FAILED (exit code {res.returncode}, {elapsed:.2f}s)")
            failed.append(module)

    tier_duration = time.perf_counter() - tier_start
    return passed, failed, tier_duration


def main():
    parser = argparse.ArgumentParser(description="Enterprise Support AI Agent Master Test Runner")
    parser.add_argument("--tier-a", action="store_true", help="Run only Tier A fast deterministic tests")
    parser.add_argument("--tier-b", action="store_true", help="Run only Tier B integration tests")
    parser.add_argument("--tier-c", action="store_true", help="Run only Tier C live LLM tests")
    parser.add_argument("--tier-d", action="store_true", help="Run only Tier D performance benchmarks")
    parser.add_argument("--all", action="store_true", help="Run Tier A, Tier B, Tier C, and Tier D")
    parser.add_argument("--inventory", action="store_true", help="Print categorized test inventory")

    args = parser.parse_args()

    if args.inventory:
        print("\n" + "=" * 75)
        print("ENTERPRISE SUPPORT AI AGENT - CATEGORIZED TEST INVENTORY")
        print("=" * 75)
        print(f"Tier A (Fast Deterministic): {len(TIER_A_MODULES)} suites")
        for m in TIER_A_MODULES:
            print(f"  - {m}")
        print(f"\nTier B (Local Integration):  {len(TIER_B_MODULES)} suites")
        for m in TIER_B_MODULES:
            print(f"  - {m}")
        print(f"\nTier C (Live LLM Eval):      {len(TIER_C_MODULES)} suites")
        for m in TIER_C_MODULES:
            print(f"  - {m}")
        print(f"\nTier D (Performance):        {len(TIER_D_MODULES)} suites")
        for m in TIER_D_MODULES:
            print(f"  - {m}")
        total = len(TIER_A_MODULES) + len(TIER_B_MODULES) + len(TIER_C_MODULES) + len(TIER_D_MODULES)
        print(f"\nTotal Backend Test Suites:   {total}")
        print("=" * 75)
        return

    env = get_default_env()
    total_passed = 0
    all_failed = []
    start_time = time.perf_counter()

    tiers_to_run = []
    if args.tier_a:
        tiers_to_run.append(("Tier A - Fast Deterministic Tests", TIER_A_MODULES))
    elif args.tier_b:
        tiers_to_run.append(("Tier B - Local Integration Tests", TIER_B_MODULES))
    elif args.tier_c:
        tiers_to_run.append(("Tier C - AI/LLM-Dependent Tests", TIER_C_MODULES))
    elif args.tier_d:
        tiers_to_run.append(("Tier D - Performance Benchmarks", TIER_D_MODULES))
    elif args.all:
        tiers_to_run.append(("Tier A - Fast Deterministic Tests", TIER_A_MODULES))
        tiers_to_run.append(("Tier B - Local Integration Tests", TIER_B_MODULES))
        tiers_to_run.append(("Tier C - AI/LLM-Dependent Tests", TIER_C_MODULES))
        tiers_to_run.append(("Tier D - Performance Benchmarks", TIER_D_MODULES))
    else:
        # Default regression: Tier A + Tier B (Pure correctness & local integration, 0 Groq tokens)
        tiers_to_run.append(("Tier A - Fast Deterministic Tests", TIER_A_MODULES))
        tiers_to_run.append(("Tier B - Local Integration Tests", TIER_B_MODULES))

    print("\n" + "=" * 75)
    print("MASTER REGRESSION RUNNER - ENTERPRISE SUPPORT AI AGENT")
    print("=" * 75)

    for tier_name, modules in tiers_to_run:
        if not modules:
            print(f"\n[INFO] {tier_name}: No suites configured or enabled.")
            continue
        p, f, d = run_tier(tier_name, modules, env)
        total_passed += p
        all_failed.extend(f)

    total_duration = time.perf_counter() - start_time
    total_suites = sum(len(mods) for _, mods in tiers_to_run)

    print("\n" + "=" * 75)
    print("FINAL REGRESSION SUMMARY REPORT")
    print("=" * 75)
    print(f"Total Suites Executed: {total_suites}")
    print(f"Passed:                 {total_passed}")
    print(f"Failed:                 {len(all_failed)}")
    print(f"Total Wall Time:        {total_duration:.2f}s")

    if all_failed:
        print("\nFailed Suites:")
        for failed in all_failed:
            print(f"  [FAIL] {failed}")
        print("=" * 75)
        sys.exit(1)
    else:
        print(f"\n[SUCCESS] All {total_passed} test suites completed successfully!")
        print("=" * 75)


if __name__ == "__main__":
    main()
