# Configuration Guide

This document explains all configuration fields used in the SMAP Speech-to-Text system.

## Environment File

Copy `.env.example` to `.env` and configure the values according to your environment:

```bash
cp .env.example .env
```

---

## Configuration Fields

### Application Settings

| Field | Required | Default | Description | Used In |
|-------|----------|---------|-------------|---------|
| `APP_NAME` | No | `SMAP Speech-to-Text` | Application name displayed in logs and API docs | API, Worker, Scheduler |
| `APP_VERSION` | No | `1.0.0` | Application version | API docs, Health endpoints |
| `ENVIRONMENT` | No | `development` | Environment name (development, staging, production) | All services, worker naming |
| `DEBUG` | No | `True` | Enable debug mode (more verbose logging) | Logger, API server log level |

**Usage:**
- These fields are used across all services for identification and logging
- `DEBUG=True` enables DEBUG level logs, `False` uses INFO level
- `ENVIRONMENT` is used to name workers and distinguish environments

---

### API Service Settings

| Field | Required | Default | Description | Used In |
|-------|----------|---------|-------------|---------|
| `API_HOST` | No | `0.0.0.0` | API server host address | cmd/api/main.py |
| `API_PORT` | No | `8000` | API server port | cmd/api/main.py |
| `API_RELOAD` | No | `True` | Enable auto-reload in development | cmd/api/main.py |
| `API_WORKERS` | No | `4` | Number of Uvicorn workers (production) | cmd/api/main.py |
| `MAX_UPLOAD_SIZE_MB` | No | `500` | Maximum audio file size in MB | ⚠️ **Defined but NOT currently used** |

**Usage:**
- Use `0.0.0.0` for host to accept connections from any network interface
- Set `API_RELOAD=False` in production
- `API_WORKERS` should match CPU cores in production

**Note:** `MAX_UPLOAD_SIZE_MB` is defined in config but not currently enforced. File size validation is hardcoded in `services/task_service.py:52` (500MB limit).

---

### MongoDB Settings (Primary Database)

| Field | Required | Default | Description | Used In |
|-------|----------|---------|-------------|---------|
| `MONGODB_URL` | Yes | `mongodb://localhost:27017` | MongoDB connection URL | core/database.py |
| `MONGODB_DATABASE` | Yes | `stt_system` | Database name | core/database.py |
| `MONGODB_MAX_POOL_SIZE` | No | `10` | Maximum connection pool size | core/database.py |
| `MONGODB_MIN_POOL_SIZE` | No | `1` | Minimum connection pool size | core/database.py |

**Usage:**
- MongoDB stores job metadata, status, and transcription results
- Collections: `jobs` (STT jobs and their chunks)
- Connection pooling optimizes performance for concurrent requests

**Example URLs:**
```bash
# Local MongoDB
MONGODB_URL=mongodb://localhost:27017

# MongoDB with authentication
MONGODB_URL=mongodb://username:password@localhost:27017

# MongoDB Atlas
MONGODB_URL=mongodb+srv://username:password@cluster.mongodb.net/?retryWrites=true&w=majority
```

---

### RabbitMQ Settings (Message Queue)

| Field | Required | Default | Description | Used In |
|-------|----------|---------|-------------|---------|
| `RABBITMQ_HOST` | Yes | `localhost` | RabbitMQ server hostname | core/messaging.py |
| `RABBITMQ_PORT` | No | `5672` | RabbitMQ server port | core/messaging.py |
| `RABBITMQ_USER` | Yes | `guest` | RabbitMQ username | core/messaging.py |
| `RABBITMQ_PASSWORD` | Yes | `guest` | RabbitMQ password | core/messaging.py |
| `RABBITMQ_VHOST` | No | `/` | RabbitMQ virtual host | core/messaging.py |
| `RABBITMQ_QUEUE_NAME` | No | `stt_jobs_queue` | Queue name for STT jobs | core/messaging.py |
| `RABBITMQ_EXCHANGE_NAME` | No | `stt_exchange` | Exchange name | core/messaging.py |
| `RABBITMQ_ROUTING_KEY` | No | `stt.job` | Routing key for job messages | core/messaging.py |

**Usage:**
- RabbitMQ handles asynchronous job processing
- Jobs are queued when uploaded and processed by workers
- Supports job persistence and retry logic

**Installation:**
```bash
# Using Docker
docker run -d --name rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:3-management

# Access management UI
http://localhost:15672 (guest/guest)
```

---

### MinIO Settings (Object Storage)

| Field | Required | Default | Description | Used In |
|-------|----------|---------|-------------|---------|
| `MINIO_ENDPOINT` | Yes | `localhost:9000` | MinIO server endpoint | core/storage.py |
| `MINIO_ACCESS_KEY` | Yes | `minioadmin` | MinIO access key | core/storage.py |
| `MINIO_SECRET_KEY` | Yes | `minioadmin` | MinIO secret key | core/storage.py |
| `MINIO_BUCKET` | Yes | `stt-audio-files` | Bucket name for audio storage | core/storage.py |
| `MINIO_USE_SSL` | No | `False` | Enable SSL/TLS | core/storage.py |

**Usage:**
- MinIO stores uploaded audio files and transcription results
- Bucket structure: `uploads/`, `results/`, `chunks/`
- Supports presigned URLs for secure file download

**Installation:**
```bash
# Using Docker
docker run -d --name minio -p 9000:9000 -p 9001:9001 \
  -e "MINIO_ROOT_USER=minioadmin" \
  -e "MINIO_ROOT_PASSWORD=minioadmin" \
  quay.io/minio/minio server /data --console-address ":9001"

# Access console UI
http://localhost:9001 (minioadmin/minioadmin)
```

---

### Whisper Settings (Speech Recognition)

| Field | Required | Default | Description | Used In |
|-------|----------|---------|-------------|---------|
| `WHISPER_EXECUTABLE` | Yes | `./whisper/whisper.cpp/main` | Path to Whisper.cpp executable | worker/transcriber.py |
| `WHISPER_MODELS_DIR` | Yes | `./whisper/whisper.cpp/models` | Directory containing Whisper models | worker/transcriber.py |
| `DEFAULT_MODEL` | No | `medium` | Default Whisper model | ⚠️ **Defined but NOT enforced** |
| `DEFAULT_LANGUAGE` | No | `vi` | Default language code | ⚠️ **Defined but NOT enforced** |

**Usage:**
- Whisper.cpp performs the actual speech-to-text transcription
- Models: `tiny`, `base`, `small`, `medium`, `large` (larger = more accurate but slower)
- Models must be downloaded separately to `WHISPER_MODELS_DIR`

**Model Download:**
```bash
cd whisper/whisper.cpp
./models/download-ggml-model.sh medium
./models/download-ggml-model.sh large
```

**Note:** `DEFAULT_MODEL` and `DEFAULT_LANGUAGE` are defined but model selection comes from API request parameters, not these defaults.

---

### Audio Chunking Settings

| Field | Required | Default | Description | Used In |
|-------|----------|---------|-------------|---------|
| `CHUNK_STRATEGY` | No | `silence_based` | Chunking strategy (silence_based or fixed_duration) | ⚠️ **Defined but NOT used** |
| `CHUNK_DURATION` | No | `30` | Chunk duration in seconds | worker/chunking.py, worker/processor.py |
| `CHUNK_OVERLAP` | No | `3` | Overlap between chunks in seconds | ⚠️ **Defined but NOT used** |
| `SILENCE_THRESHOLD` | No | `-40` | Silence detection threshold in dB | worker/processor.py |
| `MIN_SILENCE_DURATION` | No | `1.0` | Minimum silence duration in seconds | worker/processor.py |

**Usage:**
- Long audio files are split into chunks for parallel processing
- Silence-based chunking splits at natural pauses
- Fixed-duration chunking uses `CHUNK_DURATION` as fallback

**Note:** `CHUNK_STRATEGY` and `CHUNK_OVERLAP` are defined but not currently used in the implementation.

---

### Processing Settings

| Field | Required | Default | Description | Used In |
|-------|----------|---------|-------------|---------|
| `MAX_RETRIES` | No | `3` | Maximum retry attempts for failed chunks | worker/processor.py |
| `RETRY_DELAY` | No | `2` | Delay between retries in seconds | ⚠️ **Defined but NOT used** |
| `JOB_TIMEOUT` | No | `3600` | Job timeout in seconds (1 hour) | core/messaging.py |
| `CHUNK_TIMEOUT` | No | `300` | Single chunk timeout in seconds (5 min) | worker/transcriber.py |
| `MAX_CONCURRENT_JOBS` | No | `4` | Maximum concurrent jobs per worker | cmd/consumer/main.py |

**Usage:**
- Retry logic handles transient errors (network issues, temporary failures)
- Timeouts prevent hung jobs from blocking the queue
- `MAX_CONCURRENT_JOBS` should match server capacity

**Note:** `RETRY_DELAY` is defined but retry logic doesn't currently use configurable delays.

---

### Storage Settings

| Field | Required | Default | Description | Used In |
|-------|----------|---------|-------------|---------|
| `TEMP_DIR` | No | `/tmp/stt_processing` | Temporary directory for processing | worker/processor.py (likely) |

**Usage:**
- Temporary storage for downloaded audio chunks during processing
- Cleaned up after job completion
- Ensure sufficient disk space (audio files can be large)

---

### Logging Settings

| Field | Required | Default | Description | Used In |
|-------|----------|---------|-------------|---------|
| `LOG_LEVEL` | No | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) | ⚠️ **Defined but NOT used** |
| `LOG_FILE` | No | `logs/stt.log` | Log file path | ⚠️ **Defined but NOT used** |

**Usage:**
- Logging is currently controlled by `DEBUG` setting
- `DEBUG=True` → DEBUG level, `DEBUG=False` → INFO level
- Logs output to console (stdout/stderr)

**Note:** `LOG_LEVEL` and `LOG_FILE` are defined but the logger in `core/logger.py` doesn't use them. Logging configuration is hardcoded.

---

### Scheduler Settings

| Field | Required | Default | Description | Used In |
|-------|----------|---------|-------------|---------|
| `SCHEDULER_TIMEZONE` | No | `Asia/Ho_Chi_Minh` | Timezone for scheduled tasks | cmd/scheduler/main.py |

**Usage:**
- Used by APScheduler for scheduled cleanup tasks
- Ensures timestamps are in correct timezone

---

## Summary of Unused Fields

The following fields are **defined in core/config.py** but are **NOT currently used** in the code:

| Field | Status | Recommendation |
|-------|--------|----------------|
| `MAX_UPLOAD_SIZE_MB` | Defined but not enforced | **Keep** - Should be used for validation |
| `DEFAULT_MODEL` | Defined but not enforced | ❌ **Remove** - Model comes from API request |
| `DEFAULT_LANGUAGE` | Defined but not enforced | ❌ **Remove** - Language comes from API request |
| `CHUNK_STRATEGY` | Defined but not used | ❌ **Remove** - Strategy is hardcoded |
| `CHUNK_OVERLAP` | Defined but not used | ❌ **Remove** - Not implemented |
| `RETRY_DELAY` | Defined but not used | ❌ **Remove** - Retry delay not configurable |
| `LOG_LEVEL` | Defined but not used | **Keep** - Should be used instead of DEBUG |
| `LOG_FILE` | Defined but not used | **Keep** - Should be used for file logging |

---

## Missing Required Fields

The following field is **used in code** but **NOT defined in core/config.py**:

| Field | Used In | Recommendation |
|-------|---------|----------------|
| `API_WORKERS` | cmd/api/main.py:234 | **Add to config.py** |

---

## Quick Start Configuration

Minimal `.env` file for local development:

```bash
# Application
APP_NAME=SMAP Speech-to-Text
ENVIRONMENT=development
DEBUG=True

# API
API_HOST=0.0.0.0
API_PORT=8000
API_RELOAD=True

# MongoDB
MONGODB_URL=mongodb://localhost:27017
MONGODB_DATABASE=stt_system

# RabbitMQ
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
RABBITMQ_USER=guest
RABBITMQ_PASSWORD=guest

# MinIO
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=stt-audio-files
MINIO_USE_SSL=False

# Whisper
WHISPER_EXECUTABLE=./whisper/whisper.cpp/main
WHISPER_MODELS_DIR=./whisper/whisper.cpp/models

# Processing
MAX_CONCURRENT_JOBS=4
JOB_TIMEOUT=3600
CHUNK_TIMEOUT=300
```

---

## Production Configuration Tips

1. **Security:**
   - Change default credentials for MongoDB, RabbitMQ, and MinIO
   - Use strong passwords
   - Enable SSL/TLS for all connections
   - Set `DEBUG=False`

2. **Performance:**
   - Adjust `MAX_CONCURRENT_JOBS` based on CPU cores
   - Tune MongoDB pool sizes for concurrent load
   - Use larger Whisper models for better accuracy (at cost of speed)

3. **Reliability:**
   - Set appropriate timeouts based on expected audio lengths
   - Configure `MAX_RETRIES` for transient errors
   - Monitor disk space for `TEMP_DIR`

4. **Monitoring:**
   - Enable file logging (once `LOG_FILE` is implemented)
   - Set up health check monitoring on `/api/v1/tasks/health`
   - Monitor RabbitMQ queue lengths

---

## Troubleshooting

### Connection Errors

**MongoDB connection failed:**
```bash
# Check MongoDB is running
docker ps | grep mongo
# Test connection
mongosh mongodb://localhost:27017
```

**RabbitMQ connection failed:**
```bash
# Check RabbitMQ is running
docker ps | grep rabbitmq
# Check management UI
curl http://localhost:15672
```

**MinIO connection failed:**
```bash
# Check MinIO is running
docker ps | grep minio
# Check console
curl http://localhost:9001
```

### Whisper Errors

**Executable not found:**
```bash
# Verify path
ls -la ./whisper/whisper.cpp/main
# Make executable
chmod +x ./whisper/whisper.cpp/main
```

**Model not found:**
```bash
# List models
ls -la ./whisper/whisper.cpp/models/
# Download missing model
cd whisper/whisper.cpp && ./models/download-ggml-model.sh medium
```

---

## Environment-Specific Configs

### Development (`.env.development`)
```bash
DEBUG=True
API_RELOAD=True
MAX_CONCURRENT_JOBS=2
```

### Production (`.env.production`)
```bash
DEBUG=False
API_RELOAD=False
API_WORKERS=8
MAX_CONCURRENT_JOBS=8
MINIO_USE_SSL=True
```

Load with:
```bash
cp .env.development .env  # Development
cp .env.production .env   # Production
```
