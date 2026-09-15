# Zero-Cost ($0) Free Tier Deployment Guide

## Enterprise Support AI Agent: Portfolio & Demo Deployment

This guide outlines the most practical, reliable, and **100% free ($0 mandatory cost)** deployment strategy for hosting the Enterprise Support AI Agent as a public portfolio/demo showcase.

---

## 1. Selected Platform Architecture

To achieve a true **$0/month** deployment without sacrificing architecture integrity, relational PostgreSQL, LangGraph state checkpoints, or RAG embeddings, the application is deployed across complementary, permanently free developer tiers:

```
+-------------------------------------------------------------------------+
|                              USER BROWSER                               |
+-------------------------------------------------------------------------+
                                    |
            +-----------------------+-----------------------+
            | (Public HTTPS)                                | (REST API HTTPS)
            v                                               v
+-----------------------+                       +-----------------------+
|    VERCEL (Frontend)  |                       |  RENDER / KOYEB / HF  |
|  - Next.js App Router |                       |  (FastAPI Backend)    |
|  - 100% Free Forever  |                       |  - Docker Container   |
|  - Instant CDN Cache  |                       |  - PyTorch + MiniLM   |
|  - Zero Cold Starts   |                       |  - ChromaDB (Baked)   |
|  - $0 / month         |                       |  - Free Web Service   |
+-----------------------+                       +-----------------------+
                                                            |
                                    +-----------------------+
                                    | (SSL Connection Pool)
                                    v
                        +-----------------------+
                        |  NEON SERVERLESS PG   |
                        |  - PostgreSQL 16+     |
                        |  - 0.5 GiB Free ACID  |
                        |  - Business Tables    |
                        |  - LangGraph Checks   |
                        |  - $0 / month         |
                        +-----------------------+
```

### Component Breakdown & Provider Selection

| Layer | Provider | Free Tier Offering | Why Selected |
| :--- | :--- | :--- | :--- |
| **Relational Database & State** | **Neon Serverless PostgreSQL** | 0.5 GiB storage, compute included, permanent free tier (no 30-day expiration). | Standard PostgreSQL on Render Free expires after 30 days and deletes data. Neon provides permanent free PostgreSQL with full ACID transactions and SSL, fully compatible with both the application schema and LangGraph `PostgresSaver`. |
| **Vector Store (ChromaDB)** | **Baked Container Index** (Docker) | Local container storage (475 KB SQLite + HNSW index). | Cloud persistent block volumes on Render/Fly.io require paid subscriptions ($7+/mo). By baking the pre-ingested Chroma index into the Docker container or auto-seeding on boot, ChromaDB functions 100% locally with zero paid volume mounts. |
| **FastAPI Backend** | **Render Free Web Service** *(or Hugging Face Spaces)* | 512 MB RAM, 0.1 vCPU, 750 free instance hrs/mo. | Native Dockerfile deployment with custom non-root runtime, automatic HTTPS, and environment variable management. *(Alternative: HF Spaces provides 16GB RAM free if PyTorch encounters memory pressure).* |
| **Next.js Frontend** | **Vercel Hobby Tier** *(or Render Static/Web)* | Unlimited deployments, 100 GB bandwidth, free SSL, zero sleep. | Running Next.js on Render free tier consumes a second instance (hitting free hour quotas and suffering 50s cold starts). Vercel hosts Next.js at the edge with zero cold starts for free. |
| **LLM Inference** | **Groq Cloud API** | Free tier (30 requests/min, 14,400 requests/day on LLaMA 3.3 70B). | Ultra-fast token generation (~300 tokens/sec) within free community rate limits. |

---

## 2. Free-Tier Limitations & Trade-Offs

When running on $0 infrastructure, the following operational characteristics must be expected:

1. **Backend Inactivity Sleep (Cold Starts)**:
   - Render Free spins down web services after 15 minutes of zero traffic.
   - The initial request after inactivity takes **40 to 50 seconds** to wake up the container.
   - *Mitigation*: The frontend includes visual connection health indicators (`BackendStatusBadge`) to notify users when the backend is warming up.
2. **RAM Ceiling (512 MB on Render Free)**:
   - PyTorch CPU + `SentenceTransformer` (`all-MiniLM-L6-v2`) + `CrossEncoder` (`ms-marco-MiniLM-L-6-v2`) consume ~450–550 MB RAM under load.
   - *If Render Free triggers an OOM (Out Of Memory) event*, deploy the backend Docker container to **Hugging Face Spaces (CPU Basic)**, which provides **16 GB RAM and 2 vCPUs for $0**.
3. **Database Volume Quota (Neon Free)**:
   - Neon provides 0.5 GiB of storage. The application business schema and LangGraph checkpoints use < 5 MB for demo workloads (well under 1% of the free quota).
4. **Bandwidth & Compute Pooling**:
   - Render provides 750 free compute hours/month per account (sufficient to run 1 single web service 24/7 all month, or 2 services for 15 days). Placing the frontend on Vercel preserves 100% of Render hours for the backend.

---

## 3. ChromaDB Persistence Strategy on Free Ephemeral Disks

Because free cloud containers do not provide free mounted persistent block disks, the project utilizes a **deterministic dual-stage ChromaDB strategy**:

1. **Container Baking**:
   - The policy documents in `data/documents/` are small text/markdown files.
   - During local or CI container builds, `python -m app.ingest` compiles the vector embeddings into `data/chroma/`.
   - The Dockerfile copies `data/` into the production container image:
     ```dockerfile
     COPY data/ ./data/
     ```
2. **Startup Self-Healing**:
   - If the container starts up and `data/chroma` is missing or unpopulated, the application or pre-deploy hook executes:
     ```bash
     python -m app.ingest
     ```
     This process takes only **4.8 seconds** and rebuilds the SQLite table and HNSW binary graphs automatically.

---

## 4. Step-by-Step Deployment Instructions

### Step 1: Provision Free PostgreSQL on Neon
1. Navigate to [neon.tech](https://neon.tech) and create a free account.
2. Click **Create Project** -> Name it `enterprise-support-db`.
3. Copy the supplied **Connection String** (PostgreSQL URI):
   ```text
   postgresql://<user>:<password>@<ep-xyz>.us-east-2.aws.neon.tech/neondb?sslmode=require
   ```
4. In Neon's SQL Editor, you can optionally run `database/schema.sql` and `database/seed.sql` (or let the backend auto-bootstrap them on startup).

---

### Step 2: Deploy Backend on Render (or Hugging Face Spaces)

#### Option 2A: Render Web Service
1. Log in to [dashboard.render.com](https://dashboard.render.com).
2. Click **New +** -> **Web Service**.
3. Connect your GitHub repository: `vikas-pydev/enterprise-support-ai-rag-agent`.
4. Configure service settings:
   - **Name**: `enterprise-support-backend`
   - **Region**: Oregon (US West) or Frankfurt (EU)
   - **Branch**: `main` (or approved deployment branch)
   - **Runtime**: `Docker`
   - **Dockerfile Path**: `Dockerfile`
   - **Instance Type**: `Free` ($0/mo)
5. Add **Environment Variables** (see Section 5 below).
6. Under **Advanced** -> **Pre-Deploy Command**:
   ```bash
   python -m app.database.bootstrap --seed-demo
   ```
7. Click **Deploy Web Service**.
8. Note your public backend URL: `https://enterprise-support-backend.onrender.com`.

---

### Step 3: Deploy Frontend on Vercel
1. Log in to [vercel.com](https://vercel.com).
2. Click **Add New...** -> **Project**.
3. Import your GitHub repository: `vikas-pydev/enterprise-support-ai-rag-agent`.
4. Configure project settings:
   - **Root Directory**: Select `frontend`.
   - **Framework Preset**: `Next.js`.
5. Under **Environment Variables**, add:
   ```text
   NEXT_PUBLIC_API_BASE_URL=https://enterprise-support-backend.onrender.com
   ```
6. Click **Deploy**.
7. Vercel will build and deploy the Next.js application to a global CDN URL (e.g., `https://enterprise-support-ai-agent.vercel.app`).

---

### Step 4: Update Backend CORS
Return to Render -> `enterprise-support-backend` -> **Environment**:
Update `CORS_ORIGINS` to include your Vercel URL:
```text
CORS_ORIGINS=https://enterprise-support-ai-agent.vercel.app,http://localhost:3000
```
Trigger a redeploy so the backend permits cross-origin requests from your frontend.

---

## 5. Required Environment Variables

### Backend Service (Render / Container Environment)

| Variable | Required | Secret? | Free Tier Value / Recommendation |
| :--- | :--- | :--- | :--- |
| `DATABASE_URL` | **Yes** | **YES** | Your Neon PostgreSQL connection string (`postgresql://...sslmode=require`) |
| `CHECKPOINT_DB_URL` | No | **YES** | Optional dedicated connection. Defaults to `DATABASE_URL` if omitted. |
| `LLM_API_KEY` | **Yes** | **YES** | Groq API key (`gsk_...`) or OpenAI API key |
| `LLM_BASE_URL` | **Yes** | No | `https://api.groq.com/openai/v1` |
| `LLM_MODEL` | **Yes** | No | `llama-3.3-70b-versatile` |
| `USE_POSTGRES_CHECKPOINT`| **Yes** | No | `1` (Enables PostgreSQL LangGraph state persistence) |
| `CHROMA_PATH` | **Yes** | No | `/app/data/chroma` |
| `CORS_ORIGINS` | **Yes** | No | `https://your-frontend.vercel.app,http://localhost:3000` |
| `DB_SSLMODE` | **Yes** | No | `require` |
| `SEED_DEMO_DATA` | Optional | No | `1` on initial boot, then `0` |
| `PORT` | **Yes** | No | `8000` |

### Frontend Service (Vercel)

| Variable | Required | Secret? | Free Tier Value / Recommendation |
| :--- | :--- | :--- | :--- |
| `NEXT_PUBLIC_API_BASE_URL`| **Yes** | No | `https://enterprise-support-backend.onrender.com` |

> [!CAUTION]
> Never put private database passwords or API keys in `NEXT_PUBLIC_*` variables. Those are embedded into the client browser bundle.

---

## 6. How to Decommission / Delete Services to Prevent Charges

To cleanly spin down or delete services without leaving orphaned resources:
1. **Neon PostgreSQL**: Log into Neon -> Project Settings -> **Delete Project**. All data is completely wiped; $0 charges.
2. **Render Web Service**: Log into Render -> Service -> Settings -> **Delete Web Service**. Suspends and removes the container; $0 charges.
3. **Vercel Project**: Log into Vercel -> Project -> Settings -> **Delete Project**. Removes frontend deployment; $0 charges.
