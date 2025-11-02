# Consumer Service Dockerfile (STT Worker with Whisper)
# Optimized: Downloads models from MinIO at runtime, keeps image lightweight
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    # Whisper configuration
    WHISPER_EXECUTABLE=/app/whisper/bin/whisper-cli \
    WHISPER_MODELS_DIR=/app/whisper/models

# Install system dependencies for audio processing and Whisper
# Note: ffmpeg is REQUIRED for audio processing (pydub dependency)
# - ffmpeg: Handles decoding/encoding of audio formats (mp3, wav, m4a, etc.)
# - libsndfile1: Required for audio file I/O operations
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    make \
    curl \
    # Audio processing libraries (REQUIRED for STT)
    ffmpeg \
    libsndfile1 \
    # Cleanup
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for better Docker layer caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy only essential application code (no docs, tests, logs, whisper/models)
# Using .dockerignore to exclude unnecessary files
COPY core/ ./core/
COPY repositories/ ./repositories/
COPY services/ ./services/
COPY worker/ ./worker/
COPY internal/ ./internal/
COPY cmd/consumer/ ./cmd/consumer/
COPY scripts/ ./scripts/

# Copy Whisper executable ONLY (models will be downloaded from MinIO)
# IMPORTANT: Do NOT copy whisper/models/ - they will be downloaded at runtime
COPY whisper/bin/ ./whisper/bin/
COPY whisper/run_whisper.sh ./whisper/ 2>/dev/null || true

# Create directories for models (empty), logs, and temp processing
# Models will be downloaded from MinIO at runtime via entrypoint script
RUN mkdir -p whisper/models logs /tmp/stt_processing && \
    chmod +x whisper/bin/* 2>/dev/null || true && \
    chmod +x whisper/run_whisper.sh 2>/dev/null || true && \
    chmod +x scripts/*.sh 2>/dev/null || true && \
    chmod +x scripts/*.py 2>/dev/null || true

# Set entrypoint to download models from MinIO before starting consumer
COPY scripts/docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Environment variables for model download from MinIO
# Set SKIP_MODEL_DOWNLOAD=true to skip downloading
# Set MODEL_TO_DOWNLOAD to specify which model (default: medium)
ENV SKIP_MODEL_DOWNLOAD=false \
    MODEL_TO_DOWNLOAD=medium \
    DEFAULT_WHISPER_MODEL=medium

# Health check (check if consumer process is running)
HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=3 \
    CMD pgrep -f "python.*cmd.consumer.main" || exit 1

# Use entrypoint to download models from MinIO before starting consumer
# Models are downloaded from private MinIO storage at container startup
ENTRYPOINT ["/docker-entrypoint.sh"]

# Default command: Start Consumer service
CMD ["python", "-m", "cmd.consumer.main"]

