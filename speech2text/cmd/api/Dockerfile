# syntax=docker/dockerfile:1

# ==============================================================================
# STAGE 1: BUILDER (Use uv for ultra-fast builds)
# ==============================================================================
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder

# Optimize for uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1

WORKDIR /app

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
# STAGE 2: RUNTIME (Distroless - Maximum Security & Minimal Size)
# ==============================================================================
FROM gcr.io/distroless/python3-debian12:nonroot AS runtime

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
    WORKERS=2

WORKDIR /app

# Copy virtual environment from Builder
COPY --from=builder --chown=nonroot:nonroot /app/.venv /app/.venv

# Copy source code (all required modules)
COPY --from=builder --chown=nonroot:nonroot /app/cmd /app/cmd
COPY --from=builder --chown=nonroot:nonroot /app/core /app/core
COPY --from=builder --chown=nonroot:nonroot /app/internal /app/internal
COPY --from=builder --chown=nonroot:nonroot /app/repositories /app/repositories
COPY --from=builder --chown=nonroot:nonroot /app/services /app/services
COPY --from=builder --chown=nonroot:nonroot /app/worker /app/worker

# Native Healthcheck - Use Python http.client (no curl/wget needed)
# Distroless has no shell, so must run python command directly
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD ["/usr/bin/python3", "-c", "import http.client, os, sys; conn = http.client.HTTPConnection('127.0.0.1', int(os.getenv('PORT', 8000))); conn.request('GET', '/health'); r = conn.getresponse(); sys.exit(0 if r.status == 200 else 1)"]

# Expose port
EXPOSE 8000

# Run API service with uvicorn
# Default distroless python3 entrypoint is /usr/bin/python3
ENTRYPOINT ["/usr/bin/python3", "-m", "uvicorn", "cmd.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
