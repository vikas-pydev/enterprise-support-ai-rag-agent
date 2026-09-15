# Docker Developer Workflow & Command Reference

This document provides a concise, developer-friendly guide to building, running, inspecting, troubleshooting, and safely resetting the containerized Enterprise Support AI Agent stack.

---

## 1. Quick Start (Zero to Running in 4 Commands)

```bash
# 1. Copy template environment variables
cp .env.example .env

# 2. Add your LLM API key in .env (e.g. GROQ_API_KEY or LLM_API_KEY)
# (All other variables have working defaults for Docker Compose)

# 3. Build container images
docker compose build

# 4. Start all services in detached mode
docker compose up -d
```

Once running, access the services:
- **Frontend Web UI**: [http://localhost:3000](http://localhost:3000)
- **FastAPI REST API**: [http://localhost:8000](http://localhost:8000)
- **API Documentation (Swagger UI)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Backend Health Check**: [http://localhost:8000/health](http://localhost:8000/health)
- **PostgreSQL Database**: `localhost:5432` (`enterprise_support` database)

---

## 2. Command Reference

All commands run from the repository root.

### Configuration Validation

Validate that syntax, variable interpolation, and service topologies in `docker-compose.yml` are correct:

```bash
docker compose config
```

To run silently and only check for errors:

```bash
docker compose config --quiet
```

### Building Images

Build or rebuild container images defined in `docker-compose.yml`:

```bash
# Standard build using layer cache
docker compose build

# Rebuild from scratch ignoring cached layers
docker compose build --no-cache

# Build a specific service only
docker compose build backend
docker compose build frontend
```

### Starting Services

Start containers in the background (detached mode):

```bash
# Start all services
docker compose up -d

# Build and start in a single step
docker compose up --build -d

# Start a specific service (and its dependencies)
docker compose up -d backend
```

### Inspecting Status & Health

Check the state and healthcheck status of all managed containers:

```bash
docker compose ps
```

Expected output when fully healthy:
```text
NAME                          IMAGE                                  STATUS                    PORTS
enterprise_support_backend    enterprise-support-ai-agent-backend    Up (healthy)              0.0.0.0:8000->8000/tcp
enterprise_support_frontend   enterprise-support-ai-agent-frontend   Up (healthy)              0.0.0.0:3000->3000/tcp
enterprise_support_postgres   postgres:16-alpine                     Up (healthy)              0.0.0.0:5432->5432/tcp
```

### Inspecting Container Logs

Stream logs to diagnose service activity:

```bash
# Follow logs from all services simultaneously
docker compose logs -f

# Follow logs from a specific service
docker compose logs -f backend
docker compose logs -f frontend
docker compose logs -f postgres

# View the last 50 log lines without streaming
docker compose logs --tail=50 backend
```

### Restarting Services

Restart containers without recreating them or losing state:

```bash
# Restart all services
docker compose restart

# Restart only backend (useful when updating server logic)
docker compose restart backend

# Restart frontend
docker compose restart frontend
```

### Stopping Services (Safe Shutdown)

Stop and remove container instances while **preserving all persistent data**:

```bash
docker compose down
```

> [!NOTE]
> `docker compose down` removes the container instances and internal network, but **leaves all named volumes (`postgres_data` and `chroma_data`) intact**. When you run `docker compose up -d` again, your PostgreSQL tables, seeded data, and ChromaDB vector embeddings are completely preserved.

---

## 3. Data Persistence Architecture

Understanding the storage layer ensures you avoid accidental data loss:

| Component | Storage Mechanism | Location | Lifetime & Behavior |
|---|---|---|---|
| **PostgreSQL Database** | Named Docker Volume (`enterprise_support_postgres_data`) | `/var/lib/postgresql/data` | **Persistent across restarts and `docker compose down`**. Holds relational tables (`employees`, `leave_balances`, `travel_expenses`) and LangGraph checkpointer checkpoints. |
| **ChromaDB Vector Store** | Named Docker Volume (`enterprise_support_chroma_data`) | `/app/data/chroma` | **Persistent across restarts and `docker compose down`**. Holds ingested document chunks and dense embeddings. |
| **Model Weight Cache** | **Baked into Docker Image Layer** | `/home/appuser/.cache/huggingface` | **Static image content** (~176 MB). Pre-cached during image build for `all-MiniLM-L6-v2` and `ms-marco-MiniLM-L-6-v2`. Enables <3s cold-starts and 100% offline startup. **Not a volume**. |

> [!IMPORTANT]
> **Model Cache vs. Vector Database**:
> - The **model cache** contains static neural network weights pre-baked into the image layer so the backend starts instantly without external internet downloads.
> - The **ChromaDB vector store** is your dynamic knowledge base stored in a named Docker volume so indexed documents survive container recreation.

---

## 4. Reset Workflows: Safe vs. Destructive

### Safe Restart / Recreate (Data Preserved)
To stop the stack and recreate containers without losing database records or vector indices:

```bash
docker compose down
docker compose up -d
```

### DESTRUCTIVE Reset (Complete Data Wipe)

> [!CAUTION]
> **DESTRUCTIVE — removes persistent PostgreSQL and ChromaDB volumes.**
> The `-v` (or `--volumes`) flag will permanently delete `enterprise_support_postgres_data` and `enterprise_support_chroma_data`. All dynamic database records, employee balance updates, expense submissions, and indexed vector embeddings will be destroyed.

```bash
# 1. Stop containers and DESTROY persistent volumes
docker compose down -v

# 2. Start stack with fresh, empty volumes
docker compose up -d
```

When started with a fresh volume, the `postgres` service automatically re-runs `database/schema.sql` and `database/seed.sql` via its `/docker-entrypoint-initdb.d/` trigger, restoring default baseline employee and balance records.

---

## 5. Security & Isolation Model

- **Non-Root Runtime Users**:
  - `backend`: Runs as unprivileged system user `appuser` (`UID 10001`, `GID 10001`).
  - `frontend`: Runs as unprivileged system user `nextjs` (`UID 1001`, `GID 65533`).
- **Secrets Management**:
  - No secrets or API keys are baked into Dockerfile image layers.
  - `.dockerignore` excludes `.env`, `.env.local`, `.git`, and private keys from build contexts.
  - Secrets (`LLM_API_KEY`, `DB_PASSWORD`) are supplied at runtime via environment variables or `.env`.
- **Isolated Network**:
  - Containers communicate on a dedicated bridge network (`enterprise_support_network`).
  - The backend references PostgreSQL via container hostname `postgres:5432`.
  - Host ports (`3000`, `8000`, `5432`) are mapped for local developer access.

---

## 6. Automated Smoke Test Script

To quickly verify that your Docker deployment is running and healthy, run the automated smoke test:

**PowerShell (Windows)**:
```powershell
.\scripts\docker_smoke_test.ps1
```

This non-destructive script verifies:
1. Docker and Docker Compose availability
2. `docker compose config` syntax validity
3. Health status of `postgres`, `backend`, and `frontend`
4. Backend `GET /health` endpoint
5. Frontend HTTP reachability (port 3000)
6. Sample employee, leave, and travel REST API endpoints
7. Non-root user security checks
8. Persistence integrity of PostgreSQL records and ChromaDB chunk counts
