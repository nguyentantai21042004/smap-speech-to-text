# Scheduler Service Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY core/ ./core/
COPY repositories/ ./repositories/
COPY services/ ./services/
COPY cmd/scheduler/ ./cmd/scheduler/

# Create logs directory
RUN mkdir -p logs

# Health check (check if process is running)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD ps aux | grep -v grep | grep "python" || exit 1

# Run the application
CMD ["python", "cmd/scheduler/main.py"]

