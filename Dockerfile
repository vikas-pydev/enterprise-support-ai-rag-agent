# =====================================================================
# Enterprise Support AI Agent: FastAPI Backend Production Dockerfile
# Phase 11: ONNX Runtime CPU Inference & 512 MB Render Free Optimization
# =====================================================================

# ---------------------------------------------------------------------
# Stage 1: Build & Dependencies
# ---------------------------------------------------------------------
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MODEL_DIR=/build/data/models

WORKDIR /build

# Install minimal OS build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create dedicated virtual environment for clean isolation
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install lightweight runtime dependencies (onnxruntime + tokenizers, NO PyTorch)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Pre-download and package ONNX models and tokenizers during build for deterministic offline startup
COPY scripts/download_onnx_models.py ./scripts/
RUN python scripts/download_onnx_models.py

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
    MODEL_DIR=/app/data/models

WORKDIR /app

# Install minimal runtime tool for container healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create unprivileged system user for non-root security
RUN groupadd --system --gid 10001 appgroup && \
    useradd --system --uid 10001 --gid appgroup --shell /bin/bash --create-home appuser && \
    mkdir -p /app/data/chroma /app/data/models && \
    chown -R appuser:appgroup /app

# Copy optimized virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

# Copy pre-downloaded ONNX models from builder stage
COPY --from=builder --chown=appuser:appgroup /build/data/models /app/data/models

# Copy application source code, deterministic data, and database assets
COPY --chown=appuser:appgroup app/ ./app/
COPY --chown=appuser:appgroup data/ ./data/
COPY --chown=appuser:appgroup database/ ./database/

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
