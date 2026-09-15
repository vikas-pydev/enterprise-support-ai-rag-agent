# =====================================================================
# Enterprise Support AI Agent: FastAPI Backend Production Dockerfile
# Phase 10: Docker Containerization Foundation (Multi-Stage Build)
# =====================================================================

# ---------------------------------------------------------------------
# Stage 1: Build & Dependencies
# ---------------------------------------------------------------------
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/cache/huggingface

WORKDIR /build

# Install minimal OS build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create dedicated virtual environment for clean isolation
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install CPU-only PyTorch to eliminate >4GB of unused NVIDIA CUDA runtime bloat
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu

# Pre-download and cache model weights during build for deterministic offline startup
RUN python -c "from sentence_transformers import SentenceTransformer, CrossEncoder; SentenceTransformer('all-MiniLM-L6-v2'); CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')"

# ---------------------------------------------------------------------
# Stage 2: Production Minimal Runtime
# ---------------------------------------------------------------------
FROM python:3.11-slim AS runner

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PATH="/opt/venv/bin:$PATH" \
    PORT=8000 \
    CHROMA_PATH=/app/data/chroma \
    HF_HOME=/home/appuser/.cache/huggingface

WORKDIR /app

# Install minimal runtime tool for container healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create unprivileged system user for non-root security
RUN groupadd --system --gid 10001 appgroup && \
    useradd --system --uid 10001 --gid appgroup --shell /bin/bash --create-home appuser && \
    mkdir -p /home/appuser/.cache/huggingface /app/data/chroma && \
    chown -R appuser:appgroup /home/appuser /app

# Copy optimized virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

# Copy pre-downloaded model weights ensuring non-root ownership
COPY --from=builder --chown=appuser:appgroup /cache/huggingface /home/appuser/.cache/huggingface

# Copy application source code, deterministic data, and database assets
COPY app/ ./app/
COPY data/ ./data/
COPY database/ ./database/

# Ensure appropriate directory permissions
RUN chown -R appuser:appgroup /app

# Run as non-root user
USER appuser

# Expose FastAPI REST service port
EXPOSE 8000

# Container healthcheck using existing GET /health endpoint
HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start production FastAPI application with Uvicorn
CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
