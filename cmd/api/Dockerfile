# API Service Dockerfile
# Optimized: Only includes source code, no whisper models or unnecessary files
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install minimal system dependencies
# Only gcc for building some Python packages (if needed)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for better Docker layer caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy only essential application code (no docs, tests, logs, IDE files)
# Using .dockerignore to exclude unnecessary files
COPY core/ ./core/
COPY repositories/ ./repositories/
COPY services/ ./services/
COPY internal/ ./internal/
COPY cmd/ ./cmd/

# Create logs directory (empty, logs are written at runtime)
RUN mkdir -p logs

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["python", "-m", "uvicorn", "cmd.api.main:app", "--host", "0.0.0.0", "--port", "8000"]

