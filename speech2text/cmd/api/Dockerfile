# syntax=docker/dockerfile:1

# ==============================================================================
# STAGE 1: BUILDER (Use uv for ultra-fast builds)
# ==============================================================================
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

# Optimize for uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install build dependencies (needed for compiling packages like numpy, scipy)
# Note: Using Python 3.12 instead of 3.13 to use pre-built wheels for pydantic-core
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    make \
    && rm -rf /var/lib/apt/lists/*

# 1. Install dependencies (This layer changes infrequently, can be cached)
# Use bind mount to avoid copying files into the image, keep layers clean
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

# 2. Copy source code and install project
COPY . .

# 3. Final sync to install actual source code into venv
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# ==============================================================================
# STAGE 2: RUNTIME (Python Slim - Includes FFmpeg)
# ==============================================================================
FROM python:3.12-slim-bookworm AS runtime

# Install runtime dependencies (FFmpeg for chunking, wget for downloads, libgomp1 for Whisper.cpp threading)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ffmpeg \
    ffprobe \
    wget \
    curl \
    libgomp1 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Standard OCI Metadata
LABEL org.opencontainers.image.title="SMAP Speech2Text API Service" \
      org.opencontainers.image.description="Secure, Fast Speech2Text API with UV and Distroless" \
      org.opencontainers.image.source="https://github.com/smap/speech2text" \
      org.opencontainers.image.licenses="MIT"

# Set optimal environment variables for Python Runtime
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0 \
    PORT=8000 \
    WORKERS=2 \
    # Whisper Model Configuration (base = default, balanced performance)
    WHISPER_MODEL_SIZE=base \
    WHISPER_LANGUAGE=en \
    WHISPER_N_THREADS=0 \
    # Chunking Configuration (NEW - Production Ready)
    WHISPER_CHUNK_ENABLED=true \
    WHISPER_CHUNK_DURATION=30 \
    WHISPER_CHUNK_OVERLAP=1 \
    # MinIO Configuration (Override in production with secrets)
    MINIO_ENDPOINT=http://172.16.19.115:9000 \
    MINIO_ACCESS_KEY=smap \
    MINIO_SECRET_KEY=hcmut2025 \
    # Timeout Configuration
    TRANSCRIBE_TIMEOUT_SECONDS=90

WORKDIR /app

# Copy virtual environment from Builder
COPY --from=builder /app/.venv /app/.venv

# Copy source code (all required modules)
COPY cmd /app/cmd
COPY core /app/core
COPY internal /app/internal
COPY services /app/services
COPY adapters /app/adapters
COPY whisper /app/whisper
COPY scripts /app/scripts

# Make scripts executable
RUN chmod +x /app/scripts/download_whisper_artifacts.py || true

# Copy and setup entrypoint
COPY scripts/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Native Healthcheck (Optimized for Kubernetes liveness/readiness probes)
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD ["python3", "-c", "import http.client, os, sys; conn = http.client.HTTPConnection('127.0.0.1', int(os.getenv('PORT', 8000))); conn.request('GET', '/health'); r = conn.getresponse(); sys.exit(0 if r.status == 200 else 1)"]

# Expose port
EXPOSE 8000

# Use entrypoint for dynamic model loading
ENTRYPOINT ["/entrypoint.sh"]
CMD ["python3", "-m", "uvicorn", "cmd.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
