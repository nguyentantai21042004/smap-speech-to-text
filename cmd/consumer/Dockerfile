# ===================================
# Stage 1: Builder Stage
# ===================================
FROM python:3.11-slim AS builder

# Set working directory
WORKDIR /app

# Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    make \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt

# ===================================
# Stage 2: Runtime Stage
# ===================================
FROM python:3.11-slim AS runtime

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    # Whisper configuration
    WHISPER_EXECUTABLE=/app/whisper/bin/whisper-cli \
    WHISPER_MODELS_DIR=/app/whisper/models \
    # Model configuration
    SKIP_MODEL_DOWNLOAD=false \
    MODEL_TO_DOWNLOAD=medium \
    DEFAULT_WHISPER_MODEL=medium

# Install only runtime dependencies (no build tools)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    # Audio processing libraries (REQUIRED for STT)
    ffmpeg \
    libsndfile1 \
    # Basic utilities
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /tmp/* \
    && rm -rf /var/tmp/*

# Copy wheels from builder and install
COPY --from=builder /app/wheels /wheels
RUN pip install --no-cache /wheels/* \
    && rm -rf /wheels

# Create necessary directories with proper permissions
RUN mkdir -p \
    whisper/models \
    whisper/bin \
    logs \
    /tmp/stt_processing \
    && chmod 755 whisper/models logs /tmp/stt_processing

# Copy application code in a single layer
COPY --chown=app:app . /app/

# Set executable permissions for scripts
RUN find /app/scripts -type f -name "*.sh" -exec chmod +x {} \; 2>/dev/null || true && \
    find /app/scripts -type f -name "*.py" -exec chmod +x {} \; 2>/dev/null || true && \
    chmod +x /app/whisper/bin/* 2>/dev/null || true && \
    chmod +x /app/whisper/run_whisper.sh 2>/dev/null || true && \
    chmod +x /docker-entrypoint.sh 2>/dev/null || true

# Create non-root user for security
RUN groupadd -r app && \
    useradd -r -g app -d /app -s /sbin/nologin app && \
    chown -R app:app /app

# Switch to non-root user
USER app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=3 \
    CMD pgrep -f "python.*cmd.consumer.main" || exit 1

# Entrypoint
ENTRYPOINT ["/docker-entrypoint.sh"]

# Default command
CMD ["python", "-m", "cmd.consumer.main"]