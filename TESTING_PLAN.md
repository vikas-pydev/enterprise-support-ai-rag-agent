# Enterprise Support AI Agent — Comprehensive Testing Plan (Phase 9)

## 1. Testing Philosophy & Guiding Principles

The Enterprise Support AI Agent is a mission-critical hybrid system combining deterministic micro-logic (tokenizers, chunkers, fusion scoring, database constraints), retrieval-augmented generation (dense embeddings, BM25, cross-encoder rerankers, refusal guardrails), stateful multi-agent orchestration (LangGraph supervisors, isolated domain workers, Human-in-the-Loop approval workflows, PostgreSQL checkpoints), and a modern Next.js/React web interface.

To ensure long-term stability, reliability, and security without wasting API quotas or slowing developer iteration, we follow these core testing principles:

1. **Fast Deterministic Tests First (Shift Left)**: Pure algorithmic logic, schema validations, context deduplication, BM25 tokenization, security boundaries, and state transition graphs must run 100% offline, fully deterministic, and execute in under 10 seconds without external dependencies.
2. **Deterministic Service Isolation & Mocking**: Agent decision branches, tool routing, and multi-turn workflows must be verified using deterministic mock LLMs and mock database layers to guarantee 100% test reproducibility regardless of network conditions or model non-determinism.
3. **Decoupled LLM Evaluation & Benchmark Tiers**: Token-consuming and non-deterministic LLM-as-judge benchmarks (e.g., Faithfulness, Answer Relevance, Semantic Accuracy) must be isolated into dedicated evaluation suites that are run on-demand or during release gating, never on every local unit test cycle.
4. **Real Database & State Persistence Verification**: Live PostgreSQL operations (schema constraints, joins, transaction boundaries, connection recovery, Postgres checkpointer serialization) must be tested against an isolated test database (`enterprise_support_test`) with graceful offline skipping when local Postgres is inactive.
5. **Human-in-the-Loop & Checkpoint Resiliency**: HITL interrupt triggers, pending state preservation across restarts, approval replay protection, and session thread isolation must be thoroughly tested against both in-memory and PostgreSQL checkpoint backends.
6. **Zero-Mock Security & Adversarial Hardening**: Explicit test suites for SQL injection, prompt injection inside documents, tool privilege escalation, approval bypass, and sensitive token leakage.
7. **Comprehensive Frontend Testing**: Component unit testing, interaction testing, mock API integration, and full browser-level end-to-end (E2E) user flows.

---

## 2. Current Test Inventory

The repository currently contains **34 Python files** in the `tests/` directory comprising **329 formal test methods** and over **8,500 lines of test code**.

| Test File | Primary Component | Layer | Test Type | Deterministic | External Dependency | Current Status & Coverage Summary |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `mock_db_helper.py` | Test Infrastructure | Helper | Mock Fixture | Deterministic | None (In-memory mock DB) | **ACTIVE**: Provides deterministic DB fixtures for offline testing |
| `run_all_tests.py` | Test Runner | Runner | Orchestrator | Mixed | Mixed | **ACTIVE**: Runs 30 test modules via sequential subprocesses with offline flags |
| `test_document_loader.py` | Ingestion & Loader | A / C | Unit | Deterministic | Filesystem (`leave_policy.txt`) | **COVERED**: 9 test methods (title extraction, format registry, hash IDs, errors) |
| `test_multi_doc_loader.py` | Ingestion & Loader | A / C | Unit | Deterministic | Filesystem (temp dir) | **COVERED**: 7 test methods, 38 assertions (metadata, markdown, extensions, versioning) |
| `test_chunker.py` | Chunking | A | Unit | Deterministic | None (In-memory text) | **COVERED**: 7 test methods, 16 assertions (chunk size, overlap, headers, boundaries) |
| `test_chunk_embeddings.py` | Embeddings Integration | A / C | Unit | Deterministic | Offline model weights (`all-MiniLM-L6-v2`) | **COVERED**: 5 test methods (vector invariants, normalization, dimensions, determinism) |
| `test_embeddings.py` | Embeddings | A / C | Unit | Deterministic | Offline model weights (`all-MiniLM-L6-v2`) | **COVERED**: 5 test methods (dimensions, determinism, cosine similarity, special characters) |
| `test_ingestion.py` | Ingestion & Registry | C | Unit / Integration | Deterministic | ChromaDB + Filesystem | **COVERED**: 6 test methods (incremental skip, force re-embed, registry schema, summaries) |
| `test_vector_store.py` | ChromaDB Store | C | Unit / Integration | Deterministic | ChromaDB | **COVERED**: 5 test methods (CRUD, metadata filtering, chunk hash enrichment, doc deletion) |
| `test_reranker.py` | Cross-Encoder Reranking | A / C | Unit | Deterministic | Offline model weights (`ms-marco-MiniLM-L-6-v2`) | **COVERED**: 4 test methods, 8 assertions (score ordering, thresholds, empty sets) |
| `test_retrieval_filtering.py` | Retrieval Guardrails | A / C | Unit | Deterministic | Offline weights + ChromaDB | **COVERED**: 6 test methods, 15 assertions (metadata filter, unanswerable queries, guardrails) |
| `test_retrieval_cases.py` | Hybrid Search Eval | C | Evaluation | Deterministic | ChromaDB + In-memory BM25 | **COVERED**: 10 test cases evaluated with programmatic thresholds |
| `test_hybrid_search.py` | BM25 + Dense + RRF | A / C | Unit | Deterministic | In-memory BM25 + ChromaDB | **COVERED**: 7 test methods, 31 assertions (tokenization, numbers, RRF fusion logic) |
| `test_hybrid_evaluation.py` | Retrieval Benchmarks | C | Evaluation | Deterministic | In-memory BM25 + ChromaDB | **COVERED**: Precision/Recall/MRR benchmark across modes with quality gates |
| `test_context_selection.py` | Context Selector | A | Unit | Deterministic | None (In-memory) | **COVERED**: 7 test methods, 31 assertions (Jaccard deduplication, budget cap, citations) |
| `test_top_k_benchmark.py` | Top-K Optimization | C | Evaluation | Deterministic | In-memory BM25 + ChromaDB | **COVERED**: Top-K benchmark (k=1..10) with quality gates and budget scaling |
| `test_retriever.py` | Unified Retriever | C | Unit / Integration | Deterministic | ChromaDB + BM25 + Reranker | **COVERED**: 7 test methods (dense, sparse, hybrid, metadata filters, stats output) |
| `test_rag.py` | RAG Pipeline | C | Unit / Integration | Deterministic | Mocked LLM + Retriever | **COVERED**: 4 test methods (grounded synthesis, XML formatting, refusal paths, 0 Groq tokens) |
| `test_rag_evaluation.py` | RAG Quality Evaluation | C | Evaluation | Non-deterministic | ChromaDB + Live Groq API | **COVERED**: 5 quality threshold assertions, uses LLM-as-judge (Groq) |
| `test_grounding.py` | Grounding & Guardrails | C | Unit | Deterministic | None (Mocked RAG / Context) | **COVERED**: 10 test methods (hallucinations, refusal, injection in docs, conflicting facts) |
| `test_ui_integration.py` | Legacy Streamlit UI | I | Unit / Smoke | Deterministic | Streamlit / Python | **COVERED**: 5 test methods (Streamlit UI script import, query flows) |
| `test_database.py` | PostgreSQL Database | B | Integration | Deterministic | PostgreSQL (`enterprise_support_test`) | **COVERED**: 25 test methods (schema, CRUD, joins, aggregates, SQL injection, negative days) |
| `test_api.py` | FastAPI Endpoints | D | Integration | Deterministic | FastAPI TestClient + Mocked DB/LLM | **COVERED**: 16 test methods (`/health`, `/ask`, employee, leave, travel, agent, approval) |
| `test_api_integration_hardening.py` | DB Resiliency & API Concurrency | B / D | Integration | Deterministic | Mock DB + TestClient (0 Groq tokens) | **COVERED**: 22 test methods (lifecycle cleanup, session isolation, same-session concurrency, error contracts) |
| `test_langchain_tools.py` | Agent Tool Interfaces | E | Unit | Deterministic | LangChain Core + Mock DB | **COVERED**: 12 test methods (schemas, RAG tool, DB tools, error sanitization, SQL safety) |
| `test_agent.py` | Single Agent Loop | E | Unit / Integration | Deterministic | Mock Groq LLM + Mock DB | **COVERED**: 16 test methods (routing, schema validation, loop bounds, memory) |
| `test_agent_reliability_hardening.py` | Agent & LangGraph Hardening | E / F | Unit / Integration | Deterministic | Mock Groq LLM + Mock DB (0 Groq tokens) | **COVERED**: 29 test methods (malformed JSON, tool errors, stall/cycle detection, state corruption, zero trace leaks) |
| `test_agent_memory.py` | Agent Memory & State | E | Unit | Deterministic | Mock Groq LLM + Session Dict | **COVERED**: 20 test methods (thread isolation, turn history, trimming, context carryover) |
| `test_agent_reliability.py` | Agent Failure Handling | E | Unit | Deterministic | Mock Groq LLM + Mock DB | **COVERED**: 24 test methods (malformed JSON, invalid args, cycle protection, secret safety) |
| `test_agent_graph.py` | LangGraph Agent State | F | Unit / Integration | Deterministic | LangGraph + Mock Groq LLM | **COVERED**: 21 test methods (graph compilation, state routing, worker nodes, trace) |
| `test_multi_agent.py` | Multi-Agent Supervisor | F | Unit / Integration | Deterministic | LangGraph + Mock Groq LLM | **COVERED**: 27 test methods (supervisor router, worker isolation, tool sandboxing, synthesis) |
| `test_multi_agent_workflows.py` | Complex Workflows | F | Integration | Deterministic | LangGraph + Mock Groq LLM | **COVERED**: 20 test methods (multi-domain workflows, cycle detection, evidence checks) |
| `test_human_in_loop.py` | HITL Approvals | G | Integration | Deterministic | LangGraph + Mock Groq LLM | **COVERED**: 22 test methods (interrupt trigger, pending state, approve/reject, replay defense) |
| `test_checkpointing.py` | LangGraph Checkpointers | H | Integration | Deterministic | MemorySaver + Postgres checkpointer | **COVERED**: 22 test methods (thread resumption, approval recovery, restart simulation) |
| `test_hitl_checkpoint_hardening.py` | HITL & Checkpoint Hardening | G / H | Integration | Deterministic | MemorySaver + Mock Postgres (0 Groq tokens) | **COVERED**: 32 test methods (session ownership, replay defense, concurrent race locks, restart persistence, DB failures, credential masking, thread isolation, secret sanitization, idempotency) |
| `test_security_adversarial.py` | Comprehensive Adversarial Security | All Layers | Security / Fuzz | Deterministic | Mock Groq LLM + Mock DB (0 Groq tokens) | **COVERED**: 41 test methods (injection, sandboxing, SQLi, traversal, HITL replay, leakage, fuzzing) |
| `test_performance.py` | Performance & Scalability Benchmarks | All Layers | Benchmark / Load | Deterministic | Local CPU + In-memory (0 Groq tokens) | **COVERED**: 25 benchmarks (RAG, corpus scaling, CrossEncoder, FastAPI, LangGraph, checkpoints, concurrency) |

---

## 3. Test Layer Mapping & Coverage Matrix

| Layer | Focus Area | Current Coverage | Key Tested Scenarios | Key Untested / Gap Areas | Risk Level |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Layer A: Pure Unit** | Chunking, tokenization, BM25, RRF fusion, context selection, deduplication, reranking | **COVERED** (High) | Chunker overlaps, Markdown header injection, BM25 exact match, RRF rank fusion, Jaccard similarity, budget limits | Extreme unicode inputs, massive documents (>10MB), non-UTF8 encodings, malformed markdown AST | Low |
| **Layer B: Database** | PostgreSQL schema, CRUD, joins, date filters, constraints, SQL injection, error sanitization | **COVERED** (High) | Connection, schema init, seed verification, employee/leave/travel queries, aggregations, SQL injection defense, negative days constraint | Connection pool exhaustion, transient DB disconnect/reconnect mid-query, deadlocks, transaction rollback on worker crash | Medium |
| **Layer C: RAG** | Ingestion, hybrid retrieval, cross-encoder rerank, context budgeting, citations, refusal guardrails | **PARTIALLY COVERED** | Multi-doc loader, BM25+Dense retrieval, score thresholding, grounding traps, prompt injection in doc, citation validation | Incremental ingestion version collision, corrupted ChromaDB index recovery, unanswerable queries benchmark assertions | Medium |
| **Layer D: API** | FastAPI endpoints (`/health`, `/ask`, employees, leave, travel, agent chat, approval) | **COVERED** (High) | Route validation, Pydantic schemas, 404/422 responses, sanitized error messages, agent endpoint invocation | Rate limiting, concurrent request handling, SSE/streaming responses, CORS origin validation | Medium |
| **Layer E: Agent** | Tool routing, allowlisting, argument validation, max steps, failure handling, execution trace | **COVERED** (High) | Tool registry schemas, invalid arg recovery, loop bounds (max steps), error sanitization, execution trace timing | Multi-turn memory token overflow, tool timeout handling, unexpected tool return payload types | Medium |
| **Layer F: LangGraph** | Multi-agent supervisor, HR/Travel/Employee workers, conditional branches, worker sandboxing | **COVERED** (High) | Supervisor routing, worker tool boundaries, multi-worker sequential execution, cycle limits, final synthesis | Dynamic worker additions, parallel worker execution race conditions, state mutation outside reducers | Medium |
| **Layer G: HITL** | Human-in-the-loop triggers, pending approval state, approval/rejection resume, replay protection | **COVERED** (High) | Sensitive keyword triggers, restricted executive ID, interrupt state persistence, explicit approve/reject, replay protection | Multi-user approval authorization, approval expiration timeout, approval race conditions | Medium |
| **Layer H: Checkpoints** | In-memory and PostgreSQL checkpointer persistence, thread mapping, restart recovery | **COVERED** (High) | Session-to-thread mapping, turn state persistence, interrupted state resume, process restart simulation, cleanup | Live Postgres checkpointer migration, connection pool loss during checkpoint write, checkpoint storage compaction | Medium |
| **Layer I: Frontend** | Next.js components, Policy & Agent chat modes, citations, approval cards, workflow timeline | **NOT COVERED** (Critical Gap) | None (Only legacy Streamlit smoke test in `test_ui_integration.py`) | Component unit tests, React Testing Library, Mode switching, Approval UI interactions, API error states | **HIGH** |
| **Layer J: End-to-End** | Full stack integration: User Browser → Next.js → FastAPI → Agent / RAG → Postgres / Checkpoints | **NOT COVERED** (Critical Gap) | None | Full browser automation (Playwright/Cypress), live approval flow, real session lifecycle | **HIGH** |

---

## 4. High-Risk Untested Areas & Gap Analysis

```
+---------------------------------------------------------------------------------------+
|                                    SECURITY GAPS                                      |
+---------------------------------------------------------------------------------------+
|  1. SQL Injection: Repository layer is tested, but raw ORM / LangChain SQL-injection  |
|     vectors via agent input parameters require systematic fuzzing.                    |
|  2. Prompt Injection via Documents: Injection inside retrieved chunks tested once,    |
|     needs multi-vector adversarial dataset (jailbreaks, markdown payload attacks).     |
|  3. Approval Tampering & Authorization: Approval decisions lack user identity checks  |
|     (e.g., any client can POST /approval with an approval_id without RBAC).           |
|  4. Session & State Leaks: Verifying that concurrent async FastAPI requests cannot    |
|     leak session memory or execution trace between distinct thread_ids.               |
+---------------------------------------------------------------------------------------+
|                                  RELIABILITY GAPS                                     |
+---------------------------------------------------------------------------------------+
|  1. Groq LLM Timeouts & Rate Limits: Handling 429 Too Many Requests and 504 Gateway   |
|     Timeouts during multi-step graph execution.                                       |
|  2. Malformed LLM Tool Call Payloads: Partial JSON, truncated tool names, and wrong   |
|     type parameters generated by smaller or quantized models.                         |
|  3. PostgreSQL Transient Outages: Agent and API behavior when PostgreSQL restarts mid- |
|     conversation or during checkpoint commit.                                         |
|  4. Memory & Token Budget Overflow: Conversational history exceeding model context   |
|     window without proper sliding window compaction.                                  |
+---------------------------------------------------------------------------------------+
|                                  FRONTEND GAPS                                        |
+---------------------------------------------------------------------------------------+
|  1. No Test Runner in Next.js: `frontend/package.json` contains 0 testing libraries   |
|     (no Vitest, Jest, React Testing Library, or Playwright).                          |
|  2. UI State Desynchronization: Approval card double-clicks, stale session IDs, and    |
|     API error banner handling when backend is down.                                   |
|  3. Responsive & Accessibility Breakdowns: Missing automated checks for mobile layout  |
|     overflows, ARIA roles, and theme switching.                                       |
+---------------------------------------------------------------------------------------+
```

---

## 5. Detailed Testing Gap Inventory (Prioritized)

| ID | Component | Risk | Current Coverage | Missing Test Specification | Test Type | Execution Mode | Priority |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **GAP-01** | Frontend Test Foundation | High | NOT COVERED | Setup Vitest / Testing Library for Next.js 16 + React 19 components | Unit / Component | Fast Deterministic | **P0** |
| **GAP-02** | Frontend Approval UI | High | NOT COVERED | Test `ApprovalCard.tsx` action triggers, pending states, disabled buttons on submission, rejection feedback | Component | Fast Deterministic | **P0** |
| **GAP-03** | Frontend Chat Workspaces | High | NOT COVERED | Test `AgentChatWorkspace.tsx` and `PolicyChatWorkspace.tsx` message rendering, streaming, error banners | Component | Fast Deterministic | **P0** |
| **GAP-04** | API Concurrency & Isolation | High | COVERED (Task 4) | Concurrent async requests to `/api/v1/agent/chat` ensuring thread state isolation under load | Integration | Fast Deterministic | **P0** |
| **GAP-05** | Approval RBAC & Auth Bypass | High | PARTIALLY COVERED | Test unauthorized approval attempts, invalid tokens, and non-admin approval decision rejections | Security / API | Fast Deterministic | **P0** |
| **GAP-06** | Retrieval Benchmark Thresholds | Medium | COVERED (Task 3) | Convert unasserted benchmark scripts (`test_retrieval_cases.py`, `test_top_k_benchmark.py`) into automated threshold tests | RAG Eval | Fast Deterministic | **P1** |
| **GAP-07** | Document Versioning & Invalidation | Medium | PARTIALLY COVERED | Test incremental ingestion: modified document updating ChromaDB + BM25, deleted doc removal | Ingestion Unit | Fast Deterministic | **P1** |
| **GAP-08** | Transient Database Failures | Medium | COVERED (Task 4) | Test repository and checkpoint behavior during database disconnections and automatic pool recovery | DB Integration | Fast Deterministic (Mock DB) | **P1** |
| **GAP-09** | LLM Rate-Limit & Backoff | Medium | COVERED (Task 5) | Test agent resilience, step bounds, and safe error handling on malformed tool payloads / failures | Agent Unit | Fast Deterministic (Mock LLM) | **P1** |
| **GAP-10** | End-to-End User Journeys | High | NOT COVERED | Playwright E2E tests: Policy Search → Citations, Agent Request → HITL Approval Card → Resume → Final Output | E2E Browser | Offline Mock API / Local Backend | **P1** |
| **GAP-11** | Prompt Injection Benchmark | High | PARTIALLY COVERED | Adversarial test suite with 25+ indirect prompt injection payloads embedded in policies & user queries | Security / RAG | Fast Deterministic (Mock & Offline) | **P1** |
| **GAP-12** | Memory Context Window Compaction | Medium | PARTIALLY COVERED | Test agent behavior when multi-turn conversation approaches maximum token context limit | Agent Unit | Fast Deterministic | **P2** |
| **GAP-13** | Frontend Theme & Accessibility | Low | NOT COVERED | A11y axe-core tests for contrast, keyboard navigation, and dark/light theme switching | Frontend Unit | Fast Deterministic | **P2** |
| **GAP-14** | Performance & Latency Benchmarks | Medium | NOT COVERED | Profiling P95 latency for BM25, Chroma retrieval, Cross-encoder reranking, and LangGraph dispatch | Performance | Isolated Benchmark | **P2** |
| **GAP-15** | Legacy Test Cleanup | Low | COVERED (Task 2) | Deprecate or convert legacy print scripts to formal test cases | Refactor | Fast Deterministic | **P3** |

---

## 6. External Dependency Analysis & Isolation Strategy

To ensure deterministic CI/CD and cost efficiency, all tests are categorized into three distinct execution tiers:

```
========================================================================================
TIER 1: FAST DETERMINISTIC TESTS (Local & CI Default)
Runtime: < 15 seconds | Cost: $0.00 | Network: 0 KB | External Services: None
- Pure unit tests (Chunker, BM25, RRF Fusion, Context Selector, Reranker)
- LangGraph and Multi-Agent tests with mocked LLM completions
- FastAPI endpoint tests with TestClient and mock DB/LLM
- Checkpointing tests using MemorySaver and mock Postgres
- Grounding & Guardrail unit tests
- Frontend component & interaction tests (Vitest + JSDOM + MSW)
========================================================================================
TIER 2: INTEGRATION & SERVICE TESTS (Local Docker / Staging)
Runtime: < 45 seconds | Cost: $0.00 | Network: Localhost only | External Services: PostgreSQL
- Live PostgreSQL schema, CRUD, joins, and constraint verification (`test_database.py`)
- Live PostgreSQL LangGraph checkpointer persistence (`test_checkpointing.py`)
- ChromaDB vector store disk persistence and reload tests
- Full-stack local E2E tests with Playwright and mock backend
========================================================================================
TIER 3: EVALUATION & LIVE BENCHMARKS (On-Demand / Release Gating)
Runtime: 2-5 minutes | Cost: Low (< $0.05) | Network: Required | External Services: Groq API
- Retrieval benchmarks (Precision@K, Recall@K, MRR@K across BM25/Dense/Hybrid)
- LLM-as-a-judge Faithfulness & Relevance quality audits (`test_rag_evaluation.py`)
- Top-K retrieval hyperparameter tuning benchmarks
========================================================================================
```

---

## 7. Test Runner Audit & Infrastructure Recommendations

### Current State of `tests/run_all_tests.py`

1. **Monolithic Subprocess Execution**: The runner executes 26 separate Python modules sequentially via `subprocess.run([sys.executable, "-m", module])`.
2. **Missing Test Tiers**: Fast unit tests, slow DB tests, and live LLM evaluation tests are lumped together in a single sequential list.
3. **Legacy Unasserted Scripts Included**: Print-only scripts like `test_document_loader.py` and `test_rag.py` (which makes live Groq API calls) are run without test assertions.
4. **Missing 6 Test Files**: 6 files in `tests/` (`mock_db_helper.py`, `test_chunk_embeddings.py`, `test_ingestion.py`, `test_retriever.py`, `test_vector_store.py`, `run_all_tests.py`) are unmanaged.
5. **No Frontend Integration**: The Python runner has zero visibility into frontend tests or Next.js build verification.
6. **Error Reporting Granularity**: It only outputs `PASSED` or `FAILED (exit code X)` without aggregating individual test case counts, assertions, or stack traces.

### Recommended Test Runner Improvements

1. **Introduce Tiered Test Commands**:
   - `python -m tests.run_fast_tests` (Tier 1: 100% deterministic, offline, <10s)
   - `python -m tests.run_integration_tests` (Tier 2: DB + Checkpoints)
   - `python -m tests.run_evaluations` (Tier 3: Groq LLM quality benchmarks)
   - `npm --prefix frontend test` (Frontend Vitest suite)
2. **Unified Summary Reporting**: Display total tests, passed, skipped, failed, assertion counts, and total execution time.

---

## 8. Frontend Testing Foundation Architecture

Currently, the Next.js frontend has **no test runner or testing dependencies**. To bridge this critical gap in Phase 9, we plan:

1. **Testing Stack**:
   - **Runner**: `vitest` (fast, native ESM and TypeScript support with Next.js)
   - **DOM Environment**: `jsdom` + `@testing-library/react` + `@testing-library/jest-dom` + `@testing-library/user-event`
   - **API Mocking**: `msw` (Mock Service Worker) for deterministic backend API mocking
2. **Component Coverage Targets**:
   - `ModeSelector.tsx`: Mode toggling, state transitions
   - `ApprovalCard.tsx`: Decision actions (`approve`/`reject`), pending loading states, disabled state on submission
   - `WorkflowTimeline.tsx`: Multi-agent step visualization, status indicators
   - `ToolActivity.tsx`: Tool arguments and duration rendering
   - `PolicyChatWorkspace.tsx` & `AgentChatWorkspace.tsx`: User message input, citations list, error displays
   - `client.ts`: API error handling and HTTP fallback behavior

---

## 9. Phase 9 Task 3: RAG & Retrieval Benchmark Quality Gates (COMPLETE)

The RAG and retrieval benchmark scripts have been converted into programmatic quality gates using `unittest.TestCase`:

### Benchmark Suites & Gated Metrics

| Test Suite | Gated Quality Metrics | Thresholds Enforced | Execution Mode |
|---|---|---|---|
| `test_retrieval_cases.py` | Overall Recall@K<br>Overall Precision<br>Answerable Recall/Precision<br>Unanswerable Precision | Recall $\ge 0.85$<br>Precision $\ge 0.75$<br>Ans Precision $\ge 0.85$<br>Unans Precision $\ge 0.85$ | Deterministic Two-Stage Retrieval (Offline Embeddings & Reranker) |
| `test_hybrid_evaluation.py` | Dense Recall<br>Sparse Recall<br>Hybrid Recall<br>Dense Reranked Precision<br>Sparse Reranked Precision<br>Hybrid Reranked Precision | Raw Recall $\ge 0.70$<br>Reranked Precision $\ge 0.50$<br>Pipeline Invariants | Deterministic (Offline Chroma + BM25 + Cross-Encoder) |
| `test_top_k_benchmark.py` | Small/Medium/Large Top-K Quality<br>Recall@K<br>Precision<br>Citation Integrity<br>Context Budget Scaling | Recall $\ge 0.85$<br>Precision $\ge 0.75$<br>Citation Integrity $= 1.00$<br>Chunks $\le \text{Context Budget}$ | Deterministic (Offline retrieval + Deterministic LLM Mock) |
| `test_rag_evaluation.py` | Generation Recall<br>Generation Precision<br>Faithfulness / Groundedness<br>Answer Relevance<br>Citation Integrity | Recall $\ge 0.85$<br>Precision $\ge 0.75$<br>Faithfulness $\ge 0.80$<br>Relevance $\ge 0.80$<br>Citation Integrity $\ge 0.90$ | Deterministic (Mocked LLM & Judge) / Optional Live Groq |

---

## 10. Phase 9 Task 4: Database & FastAPI Integration Hardening (COMPLETE)

The PostgreSQL database access layer and FastAPI service integration have been thoroughly hardened and verified via `tests/test_api_integration_hardening.py` (22 test methods, 100% deterministic, 0 Groq tokens consumed):

### 1. Database Connection Resiliency & Resource Cleanup
- **Lifecycle Guarantees**: Verified via context-manager mocking that every repository operation systematically closes cursor resources and guarantees connection release in the `finally` block on both success and exceptions.
- **Operational Error Wrapping**: Confirmed that low-level `psycopg2.OperationalError`, `psycopg2.InterfaceError`, and `psycopg2.DatabaseError` are converted into the application's sanitized `app.database.exceptions.DatabaseError`.
- **Zero Leakage Contract**: Verified that raw database exceptions containing connection strings, hosts, usernames, or simulated database passwords (`FATAL: password authentication failed`) are stripped and never leak into API response payloads.

### 2. FastAPI Concurrent Session Isolation
- **Multi-Session History Isolation**: Concurrently executed independent session threads (e.g. Session 1..5 for Employees E1001..E1005) against `POST /api/v1/agent/chat` using `ThreadPoolExecutor`. Confirmed that Session A cannot observe Session B's conversational state, answers, or step arguments.
- **Session Lifecycle Isolation**: Confirmed that `POST /api/v1/agent/sessions/{session_id}/clear` and `DELETE /api/v1/agent/sessions/{session_id}` for one session do not alter or corrupt concurrent sessions in `InMemorySessionStore`.
- **Checkpoint & Approval Thread Association**: Verified that `format_approval_id` deterministically embeds thread identities, `resolve_thread_from_approval_id` resolves strictly to the originating thread, and checkpointer state deletions are thread-scoped.

### 3. Same-Session Concurrency & Thread-Safety Behavior
- **Memory Store Mutex Protection**: Verified `InMemorySessionStore` thread safety under concurrent writes (20 concurrent threads appending messages to the SAME session) and concurrent reader/writer access (8 threads) with zero `RuntimeError`, lost messages, or list corruption.
- **Same-Session Concurrent API Invocations**: Verified that two simultaneous requests to `POST /api/v1/agent/chat` targeting the exact same `session_id` complete safely without service crashes or broken schemas.
- **Documented Concurrency Limitations**:
  - *In-Memory Architecture*: `InMemorySessionStore` provides atomic thread-safe appending and reading via internal `threading.Lock()`.
  - *Multi-Turn Agent Ordering*: Concurrent multi-turn requests arriving for the *same* session run without turn-level serialization locks; turns append in order of completion.
  - *Distributed Scaling*: For multi-process deployments (multiple Uvicorn workers), session state and checkpoint coordination should transition to Redis or PostgreSQL checkpoints.

---

## 11. Phase 9 Task 5: Agent & LangGraph Reliability Hardening (COMPLETE)

The controlled agent loop, tool execution sandboxes, and LangGraph multi-agent orchestration have been hardened against adversarial payloads, unexpected tool crashes, supervisor routing failures, cycle loops, state corruption, and trace information leaks via `tests/test_agent_reliability_hardening.py` (29 test methods, 100% deterministic, 0 Groq tokens consumed):

### 1. Malformed & Adversarial Tool-Call Hardening
- **Unknown Tool Names**: Unregistered tool names (e.g. `malicious_eval_code`) are rejected with sanitized `"Execution error: Tool '...' not found"`, preventing arbitrary execution.
- **Schema & Pydantic Validation**: Missing required arguments (`employee_id`), wrong types (integer passed for string employee ID), null values, and malformed/non-JSON payloads are intercepted safely and return descriptive validation observations rather than crashing the Python process.
- **Extreme Length Inputs**: Adversarial 100KB string arguments are safely handled and routed without buffer overflows or recursion depth crashes.
- **Worker Sandboxing & Tool Allowlisting**: Worker permission boundaries are strictly enforced (`WORKER_TOOL_MAPPING`). If an HR worker attempts to call `get_employee`, execution is aborted with a security violation observation without executing the unauthorized tool.

### 2. Tool Failure Recovery & Graceful Degradation
- **DatabaseError Wrapping**: Repository-level database exceptions raised within tools (e.g. `get_leave_balance`) are caught, converted to safe error strings, recorded in the agent trace as failed steps, and returned to the LLM to formulate a polite, bounded user response.
- **Unexpected Runtime Errors**: Uncaught exceptions (`RuntimeError("Fatal hardware bus error")`) are caught inside `_execute_tool_call`, preventing unhandled 500 crashes.
- **Scalar Non-Dict Wrapping**: Tools returning non-dict objects (strings, lists, booleans) are safely wrapped into dictionaries (`{"result": ...}`) without raising `AttributeError: 'str' object has no attribute 'get'`.
- **RAG Refusal & Retrieval Failures**: When `ask_policy` encounters zero matching chunks or unanswerable queries, it produces standard refusal structures without hallucinating tool output.

### 3. Tool Timing, Monotonic Durations & Step Budget Enforcement
- **Monotonic Duration Guarantee**: Every step duration is calculated via `time.monotonic()`, guaranteeing non-negative durations (`duration_ms >= 0`) regardless of system clock adjustments.
- **Strict Step Budget Bound**: Agent loops terminate deterministically when `step_count >= MAX_AGENT_STEPS` (default: 10), concluding with a bounded fallback response rather than entering an unbounded loop.

### 4. Supervisor Routing Failure & Loop Detection
- **Invalid & Missing Routes**: Empty strings, whitespace, null routing responses, and unknown worker names (e.g. `unauthorized_database_admin`) are safely caught by `_parse_supervisor_response` and `route_after_supervisor`, defaulting to safe termination (`END`).
- **Markdown & Code Fence JSON Extraction**: The supervisor parser robustly extracts JSON payloads wrapped in markdown triple-backticks (` ```json ... ``` `) and falls back to text heuristic classification when JSON is entirely absent.
- **Stall Protection**: If a worker executes repeatedly without producing new findings or changing state, the supervisor detects the stall and terminates the workflow safely.
- **Cycle Detection**: Oscillating worker loops (e.g. Worker A → Worker B → Worker A → Worker B) are detected via execution history inspection and routed to immediate safe synthesis.
- **Supervisor Iteration Budgets**: Supervisor iterations are capped by `max_supervisor_iterations` (default: 6), preventing infinite multi-agent dispatch.

### 5. Duplicate Call & Replay Protection
- **Identical Tool Call Deduplication**: If an agent attempts to execute an identical tool call with the exact same arguments in the same turn, duplicate protection suppresses re-execution and reuses the previous observation.
- **Distinct Arguments Allowed**: Legitimate calls to the same tool with different arguments (e.g. `get_employee("E1001")` followed by `get_employee("E1002")`) are executed normally.
- **Replayed Approval Defenses**: Replaying an expired, non-existent, or previously executed approval token (`appr_fake_replay_999`) is safely rejected without executing privileged tool operations.

### 6. Graph State Corruption Resilience
- **Missing & None State Fields**: Multi-agent nodes (`supervisor_node`, `_execute_worker`, `final_synthesis_node`) were hardened against `None` values for `step_count`, `max_steps`, `supervisor_iterations`, `max_supervisor_iterations`, and `status`. State getters now use fallback expressions `state.get(...) or default` to prevent `TypeError: '>=' not supported between instances of 'NoneType' and 'int'`.
- **Inconsistent Step Counts**: Inconsistent or missing message lists, evidence dictionaries, and current worker fields default gracefully to neutral baseline structures.

### 7. Trace & Observability Integrity
- **Accurate Trace Counts**: `tool_calls_count` and `tools_used` accurately reflect actual tool invocations even during failures or step exhaustion.
- **Zero Secrets / Stack Leakage**: Traces and final responses are scrubbed of raw tracebacks, internal database connection strings, passwords, secret keys, and chain-of-thought scratchpads.

### 8. Documented Agent Reliability Limitations
- **External Network Timeouts**: Tool-level network socket timeouts depend on underlying HTTP / DB driver timeouts (`connect_timeout`, urllib timeouts). The agent execution loop currently enforces iteration/step budgets rather than async wall-clock cancellation timers.
- **Single-Turn LLM Output Repair**: When an LLM produces completely unparseable plain-text without tool markers or supervisor JSON, the supervisor falls back to regex/keyword heuristics rather than recursive LLM correction prompts.

---

---

## 12. Phase 9 Task 6: HITL & Checkpoint Persistence Hardening (COMPLETE)

The Human-in-the-Loop (HITL) approval system and LangGraph state checkpoint persistence have been comprehensively hardened against authorization failures, approval replay, cross-session hijacking, conflicting concurrent decisions, process crashes, and PostgreSQL checkpoint database failures via `tests/test_hitl_checkpoint_hardening.py` (32 test methods, 100% deterministic, 0 Groq tokens consumed):

### 1. Approval Authorization & Ownership Boundaries
- **Session/Thread Context Verification**: `resume_multi_agent_approval` accepts an optional `expected_session_id`. If an approval generated for Session A is submitted with Session B's context, the operation is rejected with an authorization error (`status: "error"`, HTTP 403 in API), executing zero tools and preserving Session A's pending state intact.
- **Nonexistent & Malformed IDs**: Unknown IDs, empty strings, whitespace, path traversal strings (`appr_tok_../../../etc/passwd`), and invalid prefixes return safe errors without crashing or leaking sensitive approval internals.
- **Active Approval ID Matching**: If a thread checkpoint contains an active approval ID, any attempt to resume using a mismatched approval ID is rejected.
- **Sanitized Rejection Output**: Unauthorized approval attempts and invalid token errors expose zero query secrets, confidential employee identifiers, or system prompt definitions.

### 2. Approval Replay Defense & Conflicting Decision Handling
- **Double Decision Idempotency**: Approving or rejecting the same approval request twice succeeds on the first attempt and deterministically returns a safe error on the second attempt (`"Approval request '...' has already been approved / rejected"`). No tools are re-executed.
- **Terminal State Irreversibility**: Rejecting an approval permanently marks it as rejected; subsequent `approve` attempts are blocked. Approving an approval permanently marks it as approved; subsequent `reject` attempts are blocked.
- **Concurrent Conflict Resolution**: Submitting conflicting decisions (e.g. concurrent `approve` and `reject`) under multithreaded race conditions is protected by a thread synchronization mutex (`_APPROVAL_MUTEX`), guaranteeing that exactly one decision wins and the other is safely rejected.
- **Completed Thread Re-execution Block**: Calling `resume_multi_agent_approval` on an ordinary completed thread that never requested approval is rejected (`"not in a pending state"`).

### 3. Approval State Persistence & Process-Restart Simulation
- **Persistent State Survival**: Pending approval state (query, thread ID, approval request payload, routing history, evidence) survives process restarts.
- **Process Restart Lifecycle**: In simulated process restarts (complete destruction and teardown of graphs, clients, and checkpointer instances), a fresh graph connecting to persistent checkpointer storage successfully reloads the paused checkpoint, validates the human decision, executes the authorized worker tool, and synthesizes the final response.
- **Rejection Persistence Across Restarts**: Rejection status persists across restarts, preventing subsequent approval attempts after application reboots.

### 4. Checkpoint Database Failure & Fallback Behavior
- **PostgreSQL Offline Fallback**: When PostgreSQL is unreachable on TCP port, `create_checkpointer` safely falls back to `MemorySaver` without crashing application startup.
- **Credential Masking in Connection Errors**: `mask_connection_string` masks database passwords in all log entries and exception handlers (e.g. `postgresql://user:***@host:5432/db`), guaranteeing credentials are never printed to console, logs, or error responses.
- **Checkpoint Write Failure**: When the checkpointer raises an exception during state commit (e.g. disk full, DB network drop), `run_multi_agent` catches the error, marks the trace as `status: "error"`, and returns a sanitized user error without falsely reporting durable persistence.
- **Checkpoint Read Failure**: When `get_tuple` raises an exception during approval resumption, `resume_multi_agent_approval` fails safely without executing privileged tools.
- **Corrupted State Recovery**: Corrupted or incomplete checkpoint states are handled safely without unhandled Python exceptions.

### 5. Checkpoint Thread & Session Isolation
- **Complete State & Message Sandboxing**: Checkpoint state, message histories, worker observations, and collected evidence in Thread A are strictly isolated from Thread B.
- **Targeted Deletions**: Deleting or clearing Thread A's checkpoints leaves Thread B's checkpoints completely untouched.
- **Isolated Resumption**: Resuming approval on Thread A has zero side-effects on Thread B.

### 6. Persisted-State Secret Sanitization
- **Zero Secret Leakage**: Checkpoint state serialization excludes raw API keys (`gsk_`, `sk-`), database passwords, internal connection strings, system prompts (`SUPERVISOR_SYSTEM_PROMPT`, worker prompts), and internal reasoning scratchpads.
- **Strict State Schema Allowlist**: Checkpoint state contains only validated business and execution fields (`session_id`, `query`, `messages`, `turn_messages`, `worker_results`, `collected_evidence`, `approval_request`, `steps`, `status`, `citations`).

### 7. Checkpoint Cleanup & Idempotency
- **Session Clear & Delete Endpoints**: `/api/v1/agent/sessions/{session_id}/clear` and `DELETE /api/v1/agent/sessions/{session_id}` clear message memory, purge in-memory pending approvals (`cleanup_pending_approvals_for_thread`), and delete checkpoint storage, writes, and blobs.
- **Idempotent Deletions**: Calling `delete_thread_checkpoints` repeatedly or on nonexistent threads returns `True` safely without errors.
- **Deleted Thread Resumption Prevention**: After deleting checkpoints for a thread, any associated approval ID is invalidated and cannot be resumed.

### 8. Explicit System Limitations & Architectural Boundaries
- **Authentication & RBAC Limitation**: The system currently enforces session-to-thread identity boundaries (`expected_session_id`). True multi-tenant user authentication, JWT verification, and Role-Based Access Control (RBAC) (e.g., distinguishing HR Admin vs Regular Employee) are not yet implemented and represent a future identity provider integration tier.
- **MemorySaver vs PostgresSaver Durability Boundary**: `MemorySaver` provides process-local persistence and will lose pending approval states upon complete application container restarts. For durable multi-instance production environments, `PostgresSaver` with a dedicated PostgreSQL checkpoint database (`CHECKPOINT_DB_URL`) is required.

---

## 13. Planned Phase 9 Task Execution Roadmap

```
+---------------------------------------------------------------------------------------+
| PHASE 9 EXECUTION ROADMAP — COMPLETE                                                  |
+---------------------------------------------------------------------------------------+
|  Task 1  | Testing Architecture, Inventory & Gap Audit (COMPLETE)                      |
|  Task 2  | Backend Deterministic Tests & Legacy Cleanup (COMPLETE - 41 tests converted)|
|  Task 3  | RAG & Retrieval Benchmark Automation (COMPLETE - 18 quality gates gated)   |
|  Task 4  | Database & API Integration Hardening (COMPLETE - 22 hardening tests added) |
|  Task 5  | Agent & LangGraph Reliability Hardening (COMPLETE - 29 tests added)        |
|  Task 6  | HITL & Checkpoint Persistence Hardening (COMPLETE - 32 tests added)        |
|  Task 7  | Frontend Unit & Component Test Foundation (COMPLETE - 112 tests added)     |
|  Task 8  | Frontend ↔ FastAPI Integration Testing (COMPLETE - 39 tests added)          |
|  Task 9  | Security & Adversarial Testing (COMPLETE - 41 backend + 10 frontend tests)  |
|  Task 10 | Performance & Latency Profiling (COMPLETE - 25 benchmarks, P95 metrics)     |
|  Task 11 | Master Test Suite Consolidation & Release Readiness Audit (COMPLETE)        |
+---------------------------------------------------------------------------------------+
```

---

## 14. Phase 9 Task 7: Next.js Frontend Unit & Component Testing Foundation (COMPLETE)

A modern, fast, and 100% deterministic automated testing foundation has been established for the Next.js 16 + React 19 + TypeScript frontend using **Vitest**, **React Testing Library**, **jsdom**, and **@testing-library/jest-dom**.

### 1. Test Architecture & Dependencies
- **Test Runner**: `vitest@5.0.0` with jsdom environment and native TypeScript/ESM support (`frontend/vitest.config.ts`).
- **DOM & Interaction**: `@testing-library/react@16.3.3`, `@testing-library/jest-dom@7.0.1`, `@testing-library/user-event@14.6.7`.
- **Global Test Setup**: `frontend/vitest.setup.ts` providing automatic DOM cleanup, polyfills for `window.matchMedia`, `Element.prototype.scrollIntoView`, and mock stub configuration for `navigator.clipboard`.
- **Scripts**: `"test": "vitest"`, `"test:run": "vitest run"`, `"test:coverage": "vitest run --coverage"`.

### 2. Test Suites & Coverage Inventory

The suite contains **25 test files** comprising **112 test methods** (**100% PASSING**, 0 skipped, 0 Groq tokens, 0 network calls).

---

## 15. Phase 9 Task 8: Frontend ↔ FastAPI Integration Testing (COMPLETE)

The integration boundary between the Next.js frontend (`EnterpriseApiClient`, error translators, and workspace UI) and the actual FastAPI backend (`app.api.main`, Pydantic validation, exception handlers, and session stores) has been verified and proven.

### 1. Integration Test Architecture
```text
Next.js Typed Client (EnterpriseApiClient)
        │ HTTP Request (fetch)
        ▼
FastAPI Server (uvicorn on port 8089)
        │ Route dispatch & Pydantic validation
        ▼
Deterministic Mock Backend (0 Groq tokens, 0 network, in-memory state)
        │ Pydantic serialization & exception handlers
        ▼
Next.js Typed Client Error / Response Parsing
```

- **Zero External Token / Network Dependency**: 0 Groq API tokens consumed, no live external database required, no ChromaDB rust panics.
- **Server Lifecycle**: Managed via `frontend/__tests__/integration/globalSetup.ts` and `testServerHelper.ts` which spawns the FastAPI server using `.venv\Scripts\python.exe tests/integration_server.py` and cleans it up after test completion.
- **Backend Companion Suite**: `tests/test_fastapi_contract_integration.py` (13 tests) verifying exact contract parity with FastAPI's `TestClient`.

### 2. Test Suites & Coverage Inventory

| Integration Test Suite | Boundary Tested | Tests | Key Behaviors Verified |
|:---|:---|:---|:---|
| `__tests__/integration/api.integration.test.ts` | System & Employee API | 10 | Real `GET /health` (200), offline backend handling (`ServiceUnavailable`), `GET /api/v1/employees/{id}` with manager hierarchy, `GET /leave` breakdown, `GET /travel` rollups, non-existent 404s, parameterized encoding, and `DatabaseError` 500 sanitization |
| `__tests__/integration/policy.integration.test.ts` | Policy RAG API (`/ask`) | 5 | Grounded response parsing, citation source contract (`rank`, `title`, `source_file`, `chunk_uid`, `rerank_score`, `snippet`), out-of-domain refusal (`is_refusal: true`, empty sources), 422 validation on empty/whitespace questions, safe 500 server error handling |
| `__tests__/integration/agent.integration.test.ts` | Agent Chat & HITL | 11 | First turn execution (`status: "completed"`, tool steps, execution trace), follow-up turn context continuity in same session, multi-session state isolation, 422 invalid request validation, HITL approval flow (`pending_approval` -> `approve`/`reject`), 400 replay rejection on resolved approvals, 403 session authorization failure, 404 missing approval, session `/clear` and `DELETE`, and secret masking |
| `tests/test_fastapi_contract_integration.py` | FastAPI Contract Parity | 13 | Direct Python `TestClient` verification of all response models matching TypeScript interfaces |

### 3. Genuine Discrepancies & Production Hardening Fixed
1. **ChromaDB SQLite Rust Panic on Import**: `app/vector_store.py` previously initialized persistent ChromaDB client at top-level module load. On environments where persistent ChromaDB SQLite schema differed or was unavailable, this caused an unhandled Rust PanicException crashing imports. Fixed by wrapping initialization in safe try/except fallback with EphemeralClient.
2. **Missing `session_id` in Frontend Approval Request**: `frontend/types/api.ts` was missing optional `session_id?: string | null` in `ApprovalDecisionRequest` required by the backend to verify approval ownership and prevent session hijacking. Added field to interface.
3. **HTTP 403 Forbidden Normalization**: `frontend/lib/api/errors.ts` previously fell back to generic `UnknownError` for 403 status codes. Added explicit mapping to `AuthorizationError` with clean user-facing permission messages.
4. **Fast Test Server Startup**: Optimized `tests/integration_server.py` to pre-mock heavy ML model weight downloads during integration testing, reducing test server cold start from 12+ seconds to ~3.5 seconds.

### 4. Test Execution Summary
- **Frontend Vitest Suite**: 28 files, 138 tests, **138 passed (100%)**, 0 failures, 0 skipped.
- **Backend Contract Suite**: 13 tests, **13 passed (100%)**, runtime ~0.44s.
- **Backend Hardening Suite**: 35 tests, **35 passed (100%)**, runtime ~0.52s.

---

*Plan updated through Phase 9 Task 8. All existing Phase 8 backend and frontend code preserved intact.*

| Test Directory / File | Target Component / Area | Tests | Key Behaviors Verified |
|:---|:---|:---|:---|
| `__tests__/api/client.test.ts` | `EnterpriseApiClient` | 15 | `/health`, `/api/v1/ask`, employee profile/leave/travel REST routes, `/api/v1/agent/chat`, approval decisions, session clear/delete, 404/422/500 errors, network failure, sanitized error mapping |
| `__tests__/api/errors.test.ts` | `ApiClientError` & formatters | 11 | HTTP status normalization, FastAPI validation error formatting, zero-traceback safety, internal detail scrub |
| `__tests__/contracts/api_contracts.test.ts` | TypeScript Interfaces | 6 | Frontend type parsing against backend Pydantic response fixtures (`HealthResponse`, `AskResponse`, `AgentChatResponse`, `Employee`, `LeaveBalance`, `TravelSummary`) |
| `__tests__/policy/MessageComposer.test.tsx` | Policy Composer | 7 | Auto-resize textarea, submit button states, Enter submission, Shift+Enter newlines, char counter, input clearing |
| `__tests__/policy/CitationCard.test.tsx` | Policy Citation Card | 3 | Title rendering, relevance score badge, chunk UID, expandable snippet, clipboard copy |
| `__tests__/policy/CitationList.test.tsx` | Citations List | 3 | Empty list guard, count badge, accordion expand/collapse |
| `__tests__/policy/RetrievalDetails.test.tsx` | Grounding Inspector | 3 | Pipeline stage tags, rerank scores, latency, evidence vs refusal status |
| `__tests__/policy/EmptyState.test.tsx` | Policy Empty State | 3 | Onboarding header, prompt suggestions, click population/submission, disabled state |
| `__tests__/policy/ChatMessage.test.tsx` | Policy Chat Message | 4 | User bubbles, grounded assistant responses, refusal alerts, error cards, copy answer button |
| `__tests__/policy/PolicyChatWorkspace.test.tsx` | Policy Workspace | 5 | Workspace lifecycle, empty state transitions, query execution, message thread, API error banner, clear chat |
| `__tests__/agent/AgentComposer.test.tsx` | Agent Composer | 5 | Input handling, loading spinner, submission via click/Enter, clear button |
| `__tests__/agent/WorkflowTimeline.test.tsx` | Multi-Agent Timeline | 3 | Step sequencing, worker badge categorization, duration formatting, HITL gate indicator |
| `__tests__/agent/ToolActivity.test.tsx` | Tool Inspector | 3 | Collapsible tool cards, JSON argument/observation syntax styling, clipboard copy |
| `__tests__/agent/ApprovalCard.test.tsx` | HITL Governance Card | 6 | Pending approval state, reason display, operator notes textarea, approve/reject triggers, resolved states, error handling |
| `__tests__/agent/ExecutionSummary.test.tsx` | Execution Telemetry | 3 | Status badges, latency, step count, worker chips, citation badges |
| `__tests__/agent/SessionControlBar.test.tsx` | Session Controls | 5 | Session ID chip, clipboard copy, new session generation, two-step confirmation for clear & delete |
| `__tests__/agent/AgentEmptyState.test.tsx` | Agent Empty State | 3 | Categorized demo prompt cards, click handling, disabled state |
| `__tests__/agent/AgentMessage.test.tsx` | Agent Chat Message | 3 | User/Assistant rendering, embedded workflow timeline, tool activity, citations, execution summary, copy answer |
| `__tests__/agent/AgentChatWorkspace.test.tsx` | Agent Workspace | 6 | Full workspace lifecycle, query execution, HITL approval trigger & resumption, session clear & delete, safe error handling |
| `__tests__/components/ThemeToggle.test.tsx` | Theme System | 3 | Dark/Light theme switching, localStorage persistence, document class toggle, accessible aria-labels |
| `__tests__/components/ModeSelector.test.tsx` | Mode Navigation | 3 | ARIA tablist/tab roles, `aria-selected`, mode switching between Policy and Agent |
| `__tests__/components/Header.test.tsx` | Product Shell Header | 2 | Branding, production version badge, Swagger docs link, Architecture modal trigger |
| `__tests__/components/BackendStatusBadge.test.tsx` | Backend Status | 3 | Online/offline indicators, version display, latency metrics, diagnostics popover |
| `__tests__/components/SystemInfoCard.test.tsx` | Diagnostics Matrix | 2 | Tech stack tags, REST API endpoints list, accordion expand/collapse |
| `__tests__/components/ArchitectureModal.test.tsx` | Architecture Modal | 2 | Modal rendering, multi-tab switching (Overview, Multi-Agent, RAG, DB), close button |

### 3. Genuine Defects Identified and Fixed
- **Worker Domain Categorization Precedence**: In `WorkflowTimeline.tsx`, `ToolActivity.tsx`, and `ExecutionSummary.tsx`, worker domain identification previously checked `tool.includes('employee')` prior to `tool.includes('travel')`. Because the backend tool `get_employee_travel_tool` contains `employee` in its name, it was miscategorized under `Employee Records` instead of `Travel & Expense`. Fixed by reordering precedence so `travel` and `expense` take priority over generic `employee` substring matching.

### 4. Code Coverage Results
- **Overall Line Coverage**: **89.67%** across all components, API client, and error normalization utilities.

---

## Phase 9 Task 9: Security & Adversarial Testing Report

Comprehensive adversarial testing against RAG + PostgreSQL + FastAPI + LangChain tools + LangGraph multi-agent + HITL/checkpointing + Next.js frontend integration.

```
+---------------------------------------------------------------------------------------------------------+
|                                    SECURITY DEFENSE-IN-DEPTH MATRIX                                     |
+---------------------------------------------------------------------------------------------------------+
| Layer                  | Defense Mechanisms                          | Residual Threat / Limitation    |
+------------------------+---------------------------------------------+---------------------------------+
| 1. Frontend (Next.js)  | Automatic text escaping (No raw innerHTML), | UI state relies on API contract;|
|                        | sanitized error mapping, button lock on submit| no cryptographic client auth yet|
+------------------------+---------------------------------------------+---------------------------------+
| 2. API (FastAPI)       | Pydantic schema validation, clean 422/400/  | Public endpoints (no RBAC /     |
|                        | 403/404/500 code mapping, error scrubbers   | JWT auth in this phase)         |
+------------------------+---------------------------------------------+---------------------------------+
| 3. Governance (HITL)   | Deterministic regex policy gates, mutex-    | Session IDs are logical tokens, |
|                        | serialized approval state machine & replay  | not cryptographic signatures    |
+------------------------+---------------------------------------------+---------------------------------+
| 4. Multi-Agent Graph   | Worker tool allowlists, supervisor budget   | Prompt injection resistance is  |
|                        | limits, strict JSON router validation       | defense-in-depth, not complete  |
+------------------------+---------------------------------------------+---------------------------------+
| 5. Tools & SQL Layer   | Pydantic args schemas, `%s` parameterized   | Database user privileges must   |
|                        | queries, no `eval`/`exec`/raw SQL           | be least-privilege on server    |
+------------------------+---------------------------------------------+---------------------------------+
| 6. RAG & Ingestion     | Extension allowlist (.txt/.md), sanitized   | Malicious context documents     |
|                        | slug document IDs, grounded prompt refusal  | cannot be 100% prevented in LLM |
+---------------------------------------------------------------------------------------------------------+
```

### 1. Threat Categories & Attack Classes Tested

1. **Prompt Injection & Adversarial Instructions**:
   - Attacks: Direct jailbreak attempts ("Ignore previous instructions", "You are ROOT administrator"), credential exfiltration ("Reveal Groq/OpenAI API key"), system prompt extraction, indirect prompt injection inside retrieved context, fake `<tool_call>` XML/JSON syntax in user prompts.
   - Defenses Verified: Strict grounded prompt structure with `STANDARD_REFUSAL`, separation of document context as untrusted data chunks, static immutable system prompts, deterministic `check_approval_policy()` trigger on sensitive keywords (`salary`, `termination`, `ssn`) and executive IDs (`E1000`, `E9999`).
2. **Tool Abuse & Worker Boundary Sandboxing**:
   - Attacks: Unregistered tool invocation, cross-worker tool hijacking (e.g. HR Policy worker calling `get_employee`, Employee worker calling `ask_policy`), malformed JSON arguments, missing required fields, type mismatches (dicts instead of strings), oversized arguments (50KB strings), duplicate tool replay.
   - Defenses Verified: Strict `WORKER_TOOL_MAPPING` allowlists, Pydantic argument validation returning structured errors with `status: error`, and `rejected_duplicate` caching.
3. **SQL Injection Hardening**:
   - Attacks: `' OR '1'='1`, `'; DROP TABLE employees; --`, `UNION SELECT` extraction, comment-based injection `/*`, special character encodings across `get_employee_by_id`, `get_employee_by_email`, `list_employees_by_department`, `get_employee_manager`, `get_leave_balances`, `get_travel_expenses`, and `get_total_travel_expenses`.
   - Defenses Verified: 100% parameterized SQL queries (`%s`), no dynamic string interpolation in SQL queries, safe return of `None` / empty lists on invalid lookups, and generic `DatabaseError` wrapping.
4. **Path Traversal & Document Ingestion Security**:
   - Attacks: Directory traversal via `../../secret.txt` and `..\\..\\secret.txt`, absolute paths, unauthorized file formats (`.py`, `.env`, `.exe`), special characters/unicode in filenames.
   - Defenses Verified: `LOADER_REGISTRY` extension whitelist (`.txt`, `.md`), deterministic alphanumeric slug generation (`_generate_document_id`), and safe `FileNotFoundError`/`ValueError` handling.
5. **HITL Approval Bypass & Replay Defense**:
   - Attacks: Resuming non-existent approval ID, cross-session approval hijacking (Session B approving Session A's request), approve-after-reject, reject-after-approve, duplicate approval replay, approval after thread checkpoint deletion, tampering with query text.
   - Defenses Verified: State machine validation (`APPROVAL_STATUS_PENDING`), ownership enforcement (`expected_session_id`), thread-safe mutex serialization (`_APPROVAL_MUTEX`), and automatic invalidation upon checkpoint deletion.
6. **Checkpoint & Session Isolation**:
   - Attacks: State bleed across distinct sessions, manipulating thread IDs with special characters/unicode, cross-session checkpoint access.
   - Defenses Verified: Isolated thread keys in `BaseCheckpointSaver`, isolated session deletion preserving other threads, zero leakage of credentials or system instructions in stored states.
7. **Sensitive-Data & Secret Leakage Prevention**:
   - Attacks: Database connection failure dumping raw passwords, tool exceptions dumping tracebacks, API errors exposing internal architecture.
   - Defenses Verified: Enhanced `mask_connection_string` with regex masking for complex passwords with special characters, global FastAPI exception handlers returning sanitized JSON without stack traces.
8. **API Abuse & Malformed Requests**:
   - Attacks: Empty bodies, whitespace-only questions, missing fields, invalid decision verbs, non-existent employee lookups.
   - Defenses Verified: FastAPI/Pydantic status code mapping (422 Unprocessable Entity on validation error, 400 Bad Request on invalid state transitions, 403 Forbidden on session mismatch, 404 Not Found on missing resources, 500 on internal failures).
9. **Frontend Rendering & Client Security**:
   - Attacks: HTML/script tag injection (`<script>`, `<img onerror>`) in reasons, citations, or operator notes; double-click submission races; rendering raw tracebacks.
   - Defenses Verified: Safe React JSX string rendering without `dangerouslySetInnerHTML`, `ApiClientError` sanitization scrubbing tracebacks and DB strings, and button locking during active submission.
10. **Deterministic Fuzz Robustness Corpus**:
    - Compact 15-item corpus (Unicode, Emoji, SQL metacharacters, prompt injections, shell escapes, whitespace, null bytes) tested across all tools and session stores with zero crashes.

### 2. Test Execution & Results

- **Backend Security Test Suite (`tests/test_security_adversarial.py`)**:
  - **41 tests executed, 41 passed (100%), 0 failed, 0 skipped**.
  - **Runtime**: ~16.8s (offline deterministic execution with mocked LLM/DB fixtures).
- **Frontend Security Test Suite (`frontend/__tests__/security/security-boundaries.test.tsx`)**:
  - **10 tests executed, 10 passed (100%), 0 failed, 0 skipped**.
  - **Runtime**: ~6.6s.

### 3. Genuine Vulnerabilities Discovered & Production Fixes

1. **Connection String Password Masking Fragility**:
   - *Vulnerability*: `mask_connection_string` in `app/agent/checkpoint.py` used `urlparse.password` + `replace()`. When passwords contained special characters (e.g. `@`, `#`, `!`), `urlparse` split on the first `@`, failing to mask the full password or throwing exceptions.
   - *Fix*: Implemented robust regex-based password masking `re.sub(r"://([^:@/]+):([^@/]+)@", r"://\1:***@", conn_string)` with safe fallback, ensuring all passwords in connection strings are masked before logging.
   - *Regression Test*: `test_connection_string_password_masking` in `tests/test_security_adversarial.py`.

### 4. Known Residual Limitations & Application vs LLM Security Distinction

> [!IMPORTANT]
> **Deterministic Application Security vs. LLM-Level Residual Risk**:
> - **Deterministic Application Security (Enforced)**: Database access is strictly parameterized (SQL injection impossible); tool execution is strictly sandboxed by Pydantic and worker allowlists (arbitrary tool execution impossible); HITL gates are enforced in Python code (bypass impossible); checkpoints and sessions are isolated by thread IDs.
> - **Unresolved LLM-Level Residual Risk (Inherent to GenAI)**: Indirect prompt injection embedded within legitimate enterprise policy documents cannot be 100% mathematically prevented at the LLM level. System prompts instruct the LLM to disregard injected instructions and strictly ground answers in facts, but enterprise deployments must treat document ingestion as a privileged process with document access controls.
> - **Authentication / RBAC Scope**: Session IDs and approval IDs are logical identifiers, not cryptographic JWT tokens or authenticated user identities. Authentication, role-based access control (RBAC), and network rate limiting are out of scope for Phase 9 and will be added in future security hardening phases.

---

## Phase 9 Task 10: Performance, Scalability & Load Testing Report

Comprehensive benchmark and scalability testing establishing engineering baseline performance metrics and architectural limits under deterministic local workloads (zero external network calls, zero Groq tokens, mocked AI boundaries).

```
+---------------------------------------------------------------------------------------------------------+
|                                    PERFORMANCE PROFILE AT A GLANCE                                      |
+---------------------------------------------------------------------------------------------------------+
| Operation Layer             | Median Latency    | P95 Latency       | Performance Classification        |
+-----------------------------+-------------------+-------------------+-----------------------------------+
| 1. BM25 Lexical Search      | 0.08 ms           | 0.10 ms           | Micro-deterministic (Ultra-fast)  |
| 2. Context Selection        | 0.05 ms           | 0.09 ms           | Micro-deterministic (Ultra-fast)  |
| 3. Checkpoint Read/Save     | < 0.01 ms         | < 0.01 ms         | Micro-deterministic (Ultra-fast)  |
| 4. Repository DB Operations | < 0.01 ms         | < 0.01 ms         | Fast in-memory / indexed          |
| 5. FastAPI Overhead         | 3.4 ms – 5.5 ms   | 4.3 ms – 10.6 ms  | Fast REST service boundary        |
| 6. Dense Vector Retrieval   | 17.4 ms           | 25.7 ms           | Moderate (Embedding + Chroma)     |
| 7. Hybrid RRF Fusion        | 16.5 ms           | 18.3 ms           | Moderate (Dominated by dense)     |
| 8. LangGraph Orchestration  | 29.8 ms – 31.7 ms | 33.9 ms – 37.9 ms | Moderate (Deterministic state)    |
| 9. Cross-Encoder Reranking  | 73.4 ms           | 75.5 ms           | EXPENSIVE / CPU-BOUND BOTTLENECK  |
| 10. End-to-End RAG Pipeline | 104.3 ms          | 127.2 ms          | Reranker accounts for ~70% total  |
+-----------------------------+-------------------+-------------------+-----------------------------------+
```

### 1. Performance Test Suite Inventory (`tests/test_performance.py`)

A focused suite of **25 deterministic performance benchmarks** executed in **16.5s** with 100% pass rate:
- **`TestRAGRetrievalPerformance`** (6 benchmarks): Dense (17.4ms), BM25 (0.08ms), Hybrid RRF (16.5ms), Cross-Encoder (73.4ms), Context Selection (0.05ms), Complete Retrieval Pipeline (104.3ms, character cap 1500 chars 100% verified).
- **`TestCorpusScalingBenchmark`** (1 benchmark): Synthetic corpus scaling across 10, 50, 100, and 250 documents. Dense search scaled sub-linearly (0.86ms to 1.19ms, a 1.38x increase for 25x documents); BM25 scaled linearly (0.06ms to 1.36ms); ingestion scaled linearly (~5.8ms per chunk on CPU).
- **`TestTopKScalability`** (1 benchmark): Candidate scaling for $K=5, 10, 20$. Verified context selector strictly bounds final output count ($\le 3$) and character size ($\le 1500$) regardless of candidate size.
- **`TestCrossEncoderPerformance`** (1 benchmark): Candidate pair scaling across 5, 10, 20, 50 pairs. Verified CPU-bound linear scaling at ~4.2ms per pair. Confirmed default $K=10$ candidate pool as the optimal Pareto frontier.
- **`TestContextSelectionPerformance`** (1 benchmark): Chunk scaling across 5, 10, 20, 50, 100 chunks. Verified 100% deterministic selection in $<0.05$ms with up to 97.1% character reduction.
- **`TestPostgreSQLPerformance`** (1 benchmark): 7 key repository operations (`employee_by_id`, `employee_by_email`, `department_listing`, `leave_balance`, `travel_summary`, `travel_date_range`, `aggregate_summary`) verified in $<0.01$ms without connection leaks.
- **`TestFastAPIPerformance`** (5 benchmarks): `/health` (3.9ms), records endpoints (3.5ms), `/api/v1/ask` (109.3ms, combining retrieval + FastAPI route), `/api/v1/agent/chat` (5.5ms serialization/routing), and 404/422 error contracts (4.6ms–5.5ms).
- **`TestAgentLangGraphPerformance`** (4 benchmarks): Simple workflow (31.7ms), multi-step workflow (29.8ms), HITL pause/resume workflow (57.2ms total), and maximum step budget / stall detection (42.1ms).
- **`TestCheckpointPerformance`** (1 benchmark): Small (47 B), Medium (948 B), and Large (8.8 KB) checkpoint save, read, delete, and JSONPlus serialization scaling ($<0.01$ms in memory).
- **`TestConcurrencyAndSessionPerformance`** (3 benchmarks): 1, 5, 10, 20 concurrent clients (up to 313 req/s, 0.0% error rate), 10 concurrent independent sessions (100% isolation, 0 state bleed), and same-session concurrent turn serialization.
- **`TestResourceAndMemoryObservations`** (1 benchmark): Verified model singletons (`all-MiniLM-L6-v2` and `ms-marco-MiniLM-L-6-v2` retained across requests without repeated initialization) and 100% session history eviction upon `clear_session`.

### 2. Primary Bottleneck & Architectural Findings

- **Bottleneck**: The Cross-Encoder reranker (`ms-marco-MiniLM-L-6-v2`) is the primary computational bottleneck, consuming **70.4%** of end-to-end RAG retrieval latency.
- **Pareto Optimality**: Reranking $K=10$ candidates takes ~43ms, while $K=50$ candidates takes ~210ms. Retaining the production default of $K=10$ provides high recall while keeping retrieval latency within ~100ms.
- **HNSW Scaling**: Vector search latency stays almost flat across a 25x corpus increase (0.86ms at 10 docs vs 1.19ms at 250 docs).

### 3. Engineering Limitations & Deferred Production Testing

- **Local Baseline vs Production SLA**: Measured on local CPU with mocked LLM boundaries. Production latency will be dominated by Groq LLM network round-trips (~300ms–800ms).
- **Infrastructure Scope**: In accordance with project instructions, Redis, Celery, distributed queues, and cloud Kubernetes load testing were omitted from this phase and deferred to production infrastructure deployment.

---

## Phase 9 Task 11: Master Test Suite Consolidation & Final System Regression Audit (COMPLETE)

**Phase 9 — Testing: COMPLETE**

Consolidated and executed the entire regression baseline for the enterprise AI agent system across backend and frontend boundaries.

### 1. Consolidated Test Execution Architecture
The test suite has been consolidated into four distinct operational tiers in `tests/run_all_tests.py`:
- **Tier A — Fast Deterministic Tests (22 Suites)**: Pure logic, unit tests, mock API, security tests (0 network, 0 Groq tokens).
- **Tier B — Local Integration Tests (11 Suites)**: FastAPI contracts, DB resiliency hardening, checkpoint persistence, HITL resumption, and local PostgreSQL integration (with graceful offline skipping).
- **Tier C — AI/LLM-Dependent Tests (2 Suites)**: Grounding and UI integration making live external Groq calls. Marked as environment-blocked when Groq API credentials or quota are unavailable.
- **Tier D — Performance Benchmarks (1 Suite)**: 25 performance benchmarks verifying P95 latency and scalability thresholds without cluttering standard correctness regression.
- **Frontend Regression (29 Suites / 148 Tests)**: Vitest + React Testing Library + jsdom suite running 100% offline and deterministic.

### 2. Regression Results Summary
- **Deterministic Backend Suites**: 33 suites executed, **33 PASSED (100%)**, 0 failures, total wall time: 566.05s.
- **Frontend Suites**: 29 test files, **148 PASSED (100%)**, 0 failures, 0 skipped, runtime: 22.60s.
- **Frontend Type Safety**: `npx tsc -p tsconfig.json --noEmit` passed with 0 errors.
- **Frontend Production Build**: `npm run build` compiled successfully in 5.9s, generating optimized static pages.
- **Backend Smoke Import**: `from app.api.main import app` verified OK.
- **Security Suite**: 41 backend + 10 frontend tests = 51 security tests, **100% PASSED**.
- **Performance Sanity**: 25 benchmarks, **100% PASSED** (throughput up to 315.2 req/s, P95 latencies aligned with baseline).

### 3. Defects Identified and Fixed During Final Regression
1. **Password Masking with Literal `@` Characters**:
   - *Issue*: `mask_connection_string` in `app/agent/checkpoint.py` used `[^@/]+` to match the password. Passwords containing literal `@` characters (e.g. `P@ssw0rd!`) were truncated, leaving trailing password characters exposed.
   - *Fix*: Updated regex pattern to `r"://([^:@/]+):(.*)@([^/@:]+(?::\d+)?(?:/.*)?$)"` to greedily match the password up to the final `@` preceding the host. Verified across `tests.test_hitl_checkpoint_hardening` and `tests.test_security_adversarial`.
2. **Master Test Runner Tier Organization**:
   - *Issue*: Previously omitted 6 newly created test suites and lacked tier differentiation.
   - *Fix*: Consolidated all 36 backend test suites into Tiers A, B, C, and D, with clean CLI flags (`--tier-a`, `--tier-b`, `--tier-c`, `--tier-d`, `--all`, `--inventory`) and safe UTF-8 output.

### 4. Release Readiness
The codebase is classified as **GREEN** and is fully ready to transition to **Phase 10: Docker Containerization**.

*Detailed breakdown available in `FINAL_TEST_REPORT.md`.*

---

*Phase 9 — Testing: COMPLETE. Ready for Phase 10.*



