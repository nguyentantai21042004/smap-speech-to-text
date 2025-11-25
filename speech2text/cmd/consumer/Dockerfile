# syntax=docker/dockerfile:1

# ==============================================================================
# STAGE 1: BUILDER (Use uv for lightning-fast builds)
# ==============================================================================
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

# Optimize for uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install build dependencies (needed for compiling packages like numpy, scipy, librosa)
# Note: Using Python 3.12 instead of 3.13 to use pre-built wheels for pydantic-core
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    make \
    && rm -rf /var/lib/apt/lists/*

# 1. Install dependencies (This layer changes infrequently, can be cached)
# Use bind mount so we don't need to copy files into image, keeps layers clean
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
# STAGE 2: RUNTIME (Python Slim - Needs shell, FFmpeg, and system packages)
# ==============================================================================
FROM python:3.12-slim AS runtime

# Standard OCI Metadata
LABEL org.opencontainers.image.title="SMAP Speech2Text Consumer Service" \
      org.opencontainers.image.description="Fast STT Consumer with Whisper.cpp, FFmpeg, and UV" \
      org.opencontainers.image.source="https://github.com/smap/speech2text" \
      org.opencontainers.image.licenses="MIT"

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    # Whisper configuration
    WHISPER_EXECUTABLE=/app/whisper/bin/whisper-cli \
    WHISPER_MODELS_DIR=/app/whisper/models \
    # Model configuration
    SKIP_MODEL_DOWNLOAD=false \
    MODEL_TO_DOWNLOAD=medium \
    DEFAULT_WHISPER_MODEL=medium

WORKDIR /app

# Install runtime dependencies (ONLY what's needed, minimize image size)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    # Audio processing (REQUIRED for STT)
    ffmpeg \
    libsndfile1 \
    # Process management (for healthcheck pgrep)
    procps \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* /var/cache/apt/archives/*

# Copy virtual environment from Builder (only .venv, don't copy entire /app)
COPY --from=builder /app/.venv /app/.venv

# Copy source code (all required modules)
COPY --from=builder /app/cmd /app/cmd
COPY --from=builder /app/core /app/core
COPY --from=builder /app/internal /app/internal
COPY --from=builder /app/repositories /app/repositories
COPY --from=builder /app/services /app/services
COPY --from=builder /app/worker /app/worker

# Copy whisper directory (bin and models)
COPY --from=builder /app/whisper /app/whisper

# Copy scripts (including entrypoint)
COPY --from=builder /app/scripts /app/scripts

# Create necessary directories with proper permissions
RUN mkdir -p \
    whisper/models \
    whisper/bin \
    logs \
    /tmp/stt_processing \
    && chmod 755 whisper/models logs /tmp/stt_processing

# Create non-root user for security
RUN groupadd -r app && \
    useradd -r -g app -d /app -s /sbin/nologin app

# Set executable permissions for scripts
RUN chmod +x /app/scripts/docker-entrypoint.sh && \
    find /app/scripts -type f -name "*.sh" -exec chmod +x {} \; 2>/dev/null || true && \
    find /app/scripts -type f -name "*.py" -exec chmod +x {} \; 2>/dev/null || true && \
    chmod +x /app/whisper/bin/* 2>/dev/null || true

# Set ownership to app user
RUN chown -R app:app /app

# Switch to non-root user
USER app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=3 \
    CMD pgrep -f "python.*cmd.consumer.main" || exit 1

# Entrypoint (downloads models from MinIO if needed)
ENTRYPOINT ["/app/scripts/docker-entrypoint.sh"]

# Default command
CMD ["python", "-m", "cmd.consumer.main"]