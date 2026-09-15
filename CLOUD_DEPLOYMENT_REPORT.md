# Phase 11 — Task 3: Production Environment Validation & Cloud Deployment Report

**Status Classification:** **YELLOW**  
*(Production environment validation, Infrastructure-as-Code blueprints, database bootstrap decoupling, persistence boundaries, and production smoke tests are 100% verified GREEN. Classification is YELLOW exclusively because final live cloud deployment requires connecting the repository to a Render account with billing authorization, which cannot be performed autonomously.)*

---

## 1. Deployment Overview

- **Date / Time**: 2026-09-15 12:15:00 UTC
- **Target Cloud Platform**: Render (Oregon Region)
- **Deployment Blueprint**: [`render.yaml`](render.yaml)
- **Planned Render Services**:
  - `enterprise-support-db` (Managed PostgreSQL 16 Starter Tier)
  - `enterprise-support-backend` (Docker Web Service, 1 instance, 1 GB Persistent Disk mounted at `/app/data/chroma`, port 8000)
  - `enterprise-support-frontend` (Docker Web Service, Next.js 16, port 3000)
- **Environment Status**: Fully validated against production container runtime with active PostgreSQL persistence, ChromaDB block storage simulation, and live Groq LLM inference.

---

## 2. Pre-Deployment Audit & Render Disk Decoupling (Step 1 & 2)

### The Pre-Deploy Disk Constraint
On Render, **Persistent Disks are attached exclusively to the active web service instance**. Persistent disks are **NOT mounted during build or pre-deploy execution**.

### Root Cause Diagnosed:
In the initial Task 2 implementation, `app/database/bootstrap.py` imported `init_checkpoint_tables()`, which indirectly imported `app.agent.__init__.py`. This loaded `app.tools` &rarr; `app.retriever` &rarr; `sentence_transformers` &rarr; `chromadb`. On Render, attempting to access ChromaDB during `preDeployCommand` when `/app/data/chroma` is unmounted would cause deploy failure.

### Resolution Implemented:
- Decoupled `init_checkpoint_tables()` in [`app/database/bootstrap.py`](app/database/bootstrap.py) to directly initialize the LangGraph checkpointer via `psycopg` and `langgraph.checkpoint.postgres.PostgresSaver`.
- Verified that `python -m app.database.bootstrap` has **zero dependencies** on ChromaDB, PyTorch, or SentenceTransformers.
- Added regression test `test_bootstrap_has_no_chroma_or_torch_dependency` in [`tests/test_cloud_bootstrap.py`](tests/test_cloud_bootstrap.py).

---

## 3. Production Smoke Test & Validation Results (`scripts/render_smoke_test.ps1`)

The production smoke test was executed against the production-configured container stack:

| Check Item | Target Endpoint | Result | Measured Latency | Verification Details |
|---|---|---|---|---|
| **1. Frontend Reachability** | `http://localhost:3000` | **PASS** | 72.9 ms | HTTP 200 OK, full SSR HTML rendered (40,085 bytes) |
| **2. Backend Health Check** | `GET /health` | **PASS** | 63.9 ms | `status=healthy, version=1.0.0` |
| **3. Employee Lookup** | `GET /api/v1/employees/E1001` | **PASS** | 23.1 ms | Alice Chen, Engineering, Manager E1004 |
| **4. Operational Records** | `GET /api/v1/employees/E1001/leave` | **PASS** | 28.1 ms | 34.0 allocated days, travel records intact |
| **5. Grounded Policy RAG** | `POST /api/v1/ask` | **PASS** | 2,305.0 ms | Grounded answer with 1 source citation |
| **6. Deterministic Refusal** | `POST /api/v1/ask` | **PASS** | 45.2 ms | Correct refusal (`is_refusal=true`) for out-of-domain query |
| **7. Conversational Agent** | `POST /api/v1/agent/chat` | **PASS** | 1,685.5 ms | Multi-turn reasoning, tool execution, synthesized answer |
| **8. Security Sanitization** | `GET /api/v1/employees/NONEXISTENT` | **PASS** | 8.4 ms | Error response sanitized; zero credentials or stack traces |

**Overall Smoke Test Result**: **8/8 CHECKS PASSED (100% GREEN)**

---

## 4. PostgreSQL & Persistence Boundaries Verification

### 1. Business Schema Verification
Inspected tables in PostgreSQL:
- `employees`: 4 rows
- `leave_balances`: 8 rows
- `travel_expenses`: 4 rows

### 2. LangGraph Checkpoint Persistence
Verified checkpointer configuration:
- `CHECKPOINTER_TYPE`: Confirmed active `PostgresSaver` backed by PostgreSQL.
- Checkpoint tables verified: `checkpoints`, `checkpoint_blobs`, `checkpoint_writes`, `checkpoint_migrations`.
- Executed multi-agent session `test_sess_001` and inspected PostgreSQL:
  - `checkpoints`: 4 rows recorded under `thread_id = test_sess_001`.
  - Confirms state is stored in PostgreSQL rather than in-memory fallback.

### 3. ChromaDB Vector Store Persistence
- Inspected collection `company_documents`: **14 indexed chunks**.
- Executed container restart (`docker compose restart backend`).
- Re-queried after restart: **14 indexed chunks intact**.
- Zero vector data loss across container lifecycle events.

---

## 5. AI & LLM Inference Verification

- **Inference Gateway**: Groq Cloud API (`https://api.groq.com/openai/v1`).
- **Configured Model**: `openai/gpt-oss-20b` (verified live on Groq).
- **RAG Policy Query**: "What is the meal per diem allowance for domestic travel?" &rarr; Correctly extracted $75/day with verifiable source citation to Corporate Travel Policy.
- **Out-of-Domain Refusal**: Query regarding warp travel correctly returned standard refusal (`is_refusal=true`).
- **Conversational Agent**: Executed multi-turn tool-calling loop, looked up employee records, and returned structured Markdown balance summary.

---

## 6. Security Audit

1. **Secret Leakage Prevention**:
   - Audited frontend bundle (`frontend/.next/`): Zero API keys (`gsk_`), passwords, or database URLs found.
   - Audited error responses: 404/500 endpoints return sanitized JSON error envelopes with zero stack traces or credentials.
2. **Runtime User Privileges**:
   - Backend: `appuser` (UID 10001, GID 10001).
   - Frontend: `nextjs` (UID 1001, GID 65533).
   - No container runs with root privileges.
3. **CORS & Network Flow**:
   - `CORS_ORIGINS` configured to accept production frontend domain.
   - Client browser communicates only with public HTTPS frontend/backend endpoints.

---

## 7. Problems Encountered & Fixes Applied

| Issue Encountered | Root Cause | Fix Applied | Fix Type |
|---|---|---|---|
| **Pre-deploy bootstrap imported ML models** | `app/database/bootstrap.py` imported `app.agent.checkpoint`, which triggered `app/agent/__init__.py` loading `sentence_transformers` and `chromadb` | Decoupled `init_checkpoint_tables()` in `bootstrap.py` to use `psycopg` and `PostgresSaver` directly without importing `app.agent` | Code / Architecture |
| **OpenAI 401 Authentication Error** | Backend defaulted `LLM_BASE_URL` to `https://api.openai.com/v1`, sending a Groq key (`gsk_...`) to OpenAI | Added auto-detection in `app/config.py`: when key starts with `gsk_`, automatically defaults `LLM_BASE_URL` to `https://api.groq.com/openai/v1` | Code / Configuration |
| **Empty string `LLM_BASE_URL` connection error** | `os.getenv("LLM_BASE_URL", default)` returns `""` if set as empty string in environment | Changed to `os.getenv("LLM_BASE_URL") or default` to handle empty strings | Code |
| **Groq 404 Model Not Found** | `llama-3.3-70b-versatile` was not enabled on this Groq API key | Queried available models via Groq API and updated default to `openai/gpt-oss-20b` in `app/config.py` and `render.yaml` | Configuration |

---

## 8. Remaining Limitations & Manual Steps Required for Live Cloud Provisioning

Per strict instructions: *"If deployment cannot proceed because Render requires an account/payment/interactive approval that you cannot perform, STOP at that point and report exactly what manual action is required rather than pretending deployment succeeded."*

### Why Live Render Provisioning Requires User Interaction:
1. **Interactive Render Account Authorization**: Render requires an authenticated session linked to a GitHub/GitLab account or an interactive browser authorization.
2. **Paid Plan Requirement for Persistent Disks**: Render requires a credit card / billing plan to provision Persistent Disks (Starter tier, ~$7/mo for DB + ~$7/mo for Backend Web Service + ~$1/mo for Disk). An agent cannot enter credit card or billing details.
3. **Repository Connection**: The repository must be pushed to a remote GitHub repository so Render's webhook can pull the build context.

### Required Manual Action to Complete Live Cloud Provisioning:
1. **Push to Remote Git**: Push this repository to your GitHub account (`git remote add origin ...; git push -u origin main`).
2. **Open Render Dashboard**: Navigate to [dashboard.render.com](https://dashboard.render.com/).
3. **Create Blueprint**:
   - Click **New +** &rarr; **Blueprint**.
   - Select your repository.
   - Render automatically reads [`render.yaml`](render.yaml) and detects `enterprise-support-db`, `enterprise-support-backend`, and `enterprise-support-frontend`.
4. **Supply Dashboard Secrets**:
   - Under `enterprise-support-backend` environment settings, paste your `GROQ_API_KEY` (or `LLM_API_KEY`).
5. **Approve & Deploy**:
   - Click **Apply**.
   - Render provisions PostgreSQL, runs `python -m app.database.bootstrap`, attaches the 1 GB persistent disk at `/app/data/chroma`, and deploys both containers.
6. **Verify Live**: Run `.\scripts\render_smoke_test.ps1 -BackendUrl "https://<backend>.onrender.com" -FrontendUrl "https://<frontend>.onrender.com"`.

---

## 9. Final Classification

**Classification:** **YELLOW**

- **Why Not GREEN**: Live cloud deployment on Render cannot be completed without manual account/billing authorization on Render's web dashboard.
- **Why Not RED**: The entire codebase, Docker containers, Infrastructure-as-Code blueprint (`render.yaml`), database bootstrap, persistent storage isolation, and smoke test suite are 100% verified, validated, and passing with zero blockers.
