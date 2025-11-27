# SMAP Speech-to-Text System

A high-performance Speech-to-Text (STT) system built with **FastAPI**, **RabbitMQ**, and **Whisper.cpp**. Designed for scalability, parallel processing, and asynchronous job handling.

---

## Key Features

### Core Capabilities
- **Asynchronous Processing** - Non-blocking job queue with RabbitMQ for high throughput
- **Parallel Transcription** - Multi-threaded chunk processing for **3.6x faster** transcription
- **High-Quality STT** - Powered by Whisper.cpp (medium model) with anti-hallucination filters
- **Auto-Chunking** - Intelligent audio segmentation with intro/outro silence removal
- **Multiple Languages** - Support for Vietnamese, English, and 90+ languages
- **Scalable Storage** - MinIO object storage for audio files and results
- **Production-Ready** - Comprehensive logging, error handling, and monitoring

### Performance Optimizations
- **Consumer-Level Singleton** - Transcriber initialized once at startup (50x faster job startup)
- **In-Memory Caching** - Model validation cached to eliminate redundant I/O
- **Parallel Chunk Processing** - ThreadPoolExecutor with shared instances (90% efficiency)
- **Batch Database Updates** - Reduced DB calls from N to ~4 per job
- **Model Pre-warming** - Models validated and loaded at consumer startup

### Architecture Highlights
- **Microservices Design** - Separate API and consumer services
- **Clean Architecture** - Repository pattern, service layer, dependency injection
- **Interface-Based** - All services implement interfaces for testability
- **Docker-Ready** - Full Docker Compose setup with health checks
- **MongoDB + MinIO** - Document database + object storage for optimal performance

---

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Technology Stack](#technology-stack)
- [Quick Start](#quick-start)
- [Installation](#installation)
  - [Local Development](#local-development)
  - [Docker Deployment](#docker-deployment)
- [API Documentation](#api-documentation)
- [Configuration](#configuration)
- [Performance](#performance)
- [Project Structure](#project-structure)
- [Development Guide](#development-guide)
- [Documentation](#documentation)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)

---

## Architecture Overview

### System Architecture

```
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│   Client     │─────▶│  API Service │─────▶│   RabbitMQ   │
│  (Upload)    │      │  (FastAPI)   │      │ (Message Bus)│
└──────────────┘      └──────────────┘      └──────────────┘
                              │                     │
                              ▼                     ▼
                      ┌──────────────┐      ┌──────────────┐
                      │    MinIO     │      │   Consumer   │
                      │   (Storage)  │◀────▶│   Service    │
                      └──────────────┘      └──────────────┘
                              │                     │
                              ▼                     ▼
                      ┌──────────────┐      ┌──────────────┐
                      │   MongoDB    │      │  Whisper.cpp │
                      │  (Database)  │      │     (STT)    │
                      └──────────────┘      └──────────────┘
```

### Core Services

#### 1. **API Service** (`cmd/api/main.py`)
- RESTful API with FastAPI
- File upload to MinIO
- Job creation and status tracking (`TaskUseCase`)
- Query transcription results
- Health checks and monitoring

#### 2. **Consumer Service** (`cmd/consumer/main.py`)
- RabbitMQ message consumer
- Audio preprocessing and chunking (`pipelines/stt/chunking.py`)
- Parallel transcription with Whisper.cpp (`adapters/whisper/engine.py`)
- Result aggregation and storage (`pipelines/stt/merger.py`)
- Singleton transcriber for optimal performance

#### 3. **Supporting Services**
- **MongoDB** - Job metadata and results storage
- **RabbitMQ** - Asynchronous message queue
- **MinIO** - Object storage for audio files
- **Whisper.cpp** - High-performance STT engine

---

## Technology Stack

### Backend
| Technology | Version | Purpose |
|------------|---------|---------|
| **FastAPI** | 0.104+ | Web framework |
| **Pydantic** | 2.5+ | Data validation |
| **Motor** | 3.3+ | Async MongoDB driver |
| **aio-pika** | 9.3+ | Async RabbitMQ client |
| **Whisper.cpp** | Latest | Speech-to-text engine |

### Audio Processing
| Library | Purpose |
|---------|---------|
| **pydub** | Audio manipulation |
| **librosa** | Audio analysis |
| **soundfile** | Audio I/O |
| **FFmpeg** | Audio format conversion |

### Infrastructure
| Service | Purpose |
|---------|---------|
| **MongoDB** | Document database |
| **RabbitMQ** | Message broker |
| **MinIO** | Object storage (S3-compatible) |
| **Docker** | Containerization |
| **Docker Compose** | Multi-container orchestration |

---

## Quick Start

### Prerequisites
- **Python 3.10+**
- **Docker & Docker Compose** (for containerized deployment)
- **FFmpeg** (for audio processing)
- **Whisper.cpp** (compiled binary)

### 1. Clone Repository
```bash
git clone <repository-url>
cd smap-speech-to-text
```

### 2. Environment Setup
```bash
cp .env.example .env
# Edit .env with your configuration
```

### 3. Install Dependencies
```bash
# Create virtual environment
python -m venv myenv
source myenv/bin/activate  # Linux/Mac
# or
myenv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

### 4. Start Services

#### Option A: Docker (Recommended)
```bash
# Start all services
make docker-up

# View logs
make docker-logs

# Stop services
make docker-down
```

#### Option B: Local Development
```bash
# Terminal 1: Start API
make run-api

# Terminal 2: Start Consumer
make run-consumer
```

### 5. Test the System
```bash
# Upload audio file
curl -X POST http://localhost:8000/files/upload \
  -F "file=@audio.mp3"

# Create STT task (use file_id from upload response)
curl -X POST http://localhost:8000/api/v1/tasks/create \
  -F "file_id=<file_id>" \
  -F "language=vi"

# Check job status
curl http://localhost:8000/api/v1/tasks/<job_id>

# Get transcription result
curl http://localhost:8000/api/v1/tasks/<job_id>/result
```

---

## Installation

### Local Development

#### 1. System Dependencies
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y ffmpeg python3-dev build-essential

# macOS
brew install ffmpeg

# Verify installation
ffmpeg -version
```

#### 2. Whisper.cpp Setup
```bash
# Clone and build Whisper.cpp
git clone https://github.com/ggerganov/whisper.cpp
cd whisper.cpp
make

# Copy binary to project
mkdir -p whisper/bin
cp main whisper/bin/whisper-cli

# Download models
bash scripts/setup_whisper.sh
```

#### 3. MongoDB Setup
```bash
# Install MongoDB Community Edition
# https://docs.mongodb.com/manual/installation/

# Or use Docker
docker run -d -p 27017:27017 --name mongodb mongo:latest
```

#### 4. RabbitMQ Setup
```bash
# Install RabbitMQ
# https://www.rabbitmq.com/download.html

# Or use Docker
docker run -d -p 5672:5672 -p 15672:15672 --name rabbitmq rabbitmq:3-management
```

#### 5. MinIO Setup
```bash
# Use Docker
docker run -d \
  -p 9000:9000 \
  -p 9001:9001 \
  --name minio \
  -e "MINIO_ROOT_USER=minioadmin" \
  -e "MINIO_ROOT_PASSWORD=minioadmin" \
  minio/minio server /data --console-address ":9001"
```

#### 6. Python Environment
```bash
# Create virtual environment
python3 -m venv myenv
source myenv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Verify installation
python -c "import fastapi; print('FastAPI installed successfully')"
```

### Docker Deployment

#### 1. Build Images
```bash
make docker-build
```

#### 2. Start Services
```bash
# Start all services
make docker-up

# Check service status
docker-compose ps

# View logs
docker-compose logs -f api
docker-compose logs -f consumer
```

#### 3. Scale Consumers
```bash
# Scale to 3 consumer instances
docker-compose up -d --scale consumer=3
```

#### 4. Stop Services
```bash
# Stop all services
make docker-down

# Stop and remove volumes (clean slate)
make docker-clean
```

---

## API Documentation

### Base URL
```
http://localhost:8000
```

### API Endpoints

#### 1. Health Check
```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "services": {
    "api": "ok",
    "mongodb": "ok",
    "rabbitmq": "ok",
    "minio": "ok"
  },
  "timestamp": "2025-11-02T12:00:00Z"
}
```

#### 2. Upload Audio File
```http
POST /files/upload
Content-Type: multipart/form-data

file: <audio_file>
```

**Supported Formats:**
- Audio: MP3, WAV, M4A, AAC, OGG, FLAC, WMA
- Video: MP4, WEBM, MKV, AVI, MOV (audio extracted)

**Response:**
```json
{
  "status": "success",
  "file_id": "69073cc61dc7aa422463d537",
  "message": "File uploaded successfully",
  "details": {
    "filename": "audio.mp3",
    "size_mb": 5.2,
    "minio_path": "uploads/xxx-xxx-xxx.mp3"
  }
}
```

#### 3. Create STT Task
```http
POST /api/v1/tasks/create
Content-Type: application/x-www-form-urlencoded

file_id: <file_id>
language: vi (optional, defaults to 'vi')
```

**Response:**
```json
{
  "status": "success",
  "job_id": "69073cc61dc7aa422463d538",
  "id": "69073cc61dc7aa422463d538",
  "message": "Task created and queued for processing",
  "details": {
    "file_id": "69073cc61dc7aa422463d537",
    "filename": "audio.mp3",
    "language": "vi",
    "model": "medium",
    "status": "QUEUED"
  }
}
```

#### 4. Get Job Status
```http
GET /api/v1/tasks/{job_id}
```

**Response:**
```json
{
  "status": "success",
  "job": {
    "job_id": "69073cc61dc7aa422463d538",
    "status": "PROCESSING",
    "progress": {
      "chunks_total": 60,
      "chunks_completed": 30,
      "percentage": 50.0
    },
    "file_info": {
      "filename": "audio.mp3",
      "size_mb": 5.2,
      "duration_seconds": 1800
    },
    "created_at": "2025-11-02T12:00:00Z",
    "started_at": "2025-11-02T12:00:05Z"
  }
}
```

**Job Statuses:**
- `QUEUED` - Job in queue, waiting for consumer
- `PROCESSING` - Currently being processed
- `COMPLETED` - Transcription complete
- `FAILED` - Processing failed (see error_message)

#### 5. Get Transcription Result
```http
GET /api/v1/tasks/{job_id}/result
```

**Response:**
```json
{
  "status": "success",
  "job_id": "69073cc61dc7aa422463d538",
  "transcription": "Đây là nội dung được chuyển đổi từ giọng nói sang văn bản...",
  "metadata": {
    "language": "vi",
    "model": "medium",
    "chunks_processed": 60,
    "total_duration": 1800,
    "processing_time": 165.3
  }
}
```

#### 6. Download Result File
```http
GET /api/v1/tasks/{job_id}/download
```

**Response:**
- Content-Type: `text/plain; charset=utf-8`
- Downloads transcription as `.txt` file

### Interactive API Documentation

Once the API is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## Configuration

### Environment Variables

Key configuration options in `.env`:

#### Application Settings
```bash
APP_NAME=SMAP Speech-to-Text
ENVIRONMENT=production
DEBUG=false
```

#### API Service
```bash
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4
MAX_UPLOAD_SIZE_MB=500
```

#### MongoDB
```bash
MONGODB_URL=mongodb://localhost:27017
MONGODB_DATABASE=stt_system
MONGODB_MAX_POOL_SIZE=10
```

#### RabbitMQ
```bash
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
RABBITMQ_USER=guest
RABBITMQ_PASSWORD=guest
RABBITMQ_QUEUE_NAME=stt_jobs_queue
```

#### MinIO
```bash
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=stt-audio-files
```

#### Whisper Settings
```bash
WHISPER_EXECUTABLE=./whisper/bin/whisper-cli
WHISPER_MODELS_DIR=./whisper/models
DEFAULT_WHISPER_MODEL=medium
```

#### Parallel Processing
```bash
# Enable parallel transcription (recommended)
USE_PARALLEL_TRANSCRIPTION=true

# Number of parallel workers (set to CPU core count)
MAX_PARALLEL_WORKERS=4

# Number of concurrent jobs per consumer
MAX_CONCURRENT_JOBS=1
```

#### Audio Processing
```bash
# Chunk duration in seconds
CHUNK_DURATION=30

# Minimum chunk duration (filter out short chunks)
MIN_CHUNK_DURATION=1.0

# Intro/outro silence filtering
INTRO_DURATION=2.0
OUTRO_DURATION=2.0

# Transcription timeout per chunk
CHUNK_TIMEOUT=120
```

#### Anti-Hallucination Settings
```bash
# Whisper quality parameters (anti-hallucination)
WHISPER_MAX_CONTEXT=0              # Disable context reuse (prevents repetition)
WHISPER_NO_SPEECH_THOLD=0.7        # Higher = less false positives
WHISPER_ENTROPY_THOLD=2.6          # Higher = less hallucination
WHISPER_LOGPROB_THOLD=-0.8         # Filter low-quality predictions
WHISPER_NO_FALLBACK=true           # Consistent output quality
```

### Performance Tuning

#### Recommended Configurations

**Development Laptop (4 cores, 8GB RAM)**
```bash
MAX_PARALLEL_WORKERS=2
MAX_CONCURRENT_JOBS=1
DEFAULT_WHISPER_MODEL=small
```

**Production Server (8 cores, 16GB RAM)**
```bash
MAX_PARALLEL_WORKERS=6
MAX_CONCURRENT_JOBS=2
DEFAULT_WHISPER_MODEL=medium
```

**High-Performance Server (16+ cores, 32GB RAM)**
```bash
MAX_PARALLEL_WORKERS=8
MAX_CONCURRENT_JOBS=4
DEFAULT_WHISPER_MODEL=medium
```

For detailed configuration guide, see: [`docs/CONFIGURATION_GUIDE.md`](docs/CONFIGURATION_GUIDE.md)

---

## Performance

### Benchmarks

**Test Setup:** 30-minute audio file, Whisper medium model, 4 CPU cores

| Mode | Time | Speedup | Efficiency |
|------|------|---------|-----------|
| Sequential | 600s (10 min) | 1x | 25% CPU |
| Parallel (2 workers) | 310s (5.2 min) | 1.9x | 50% CPU |
| **Parallel (4 workers)** | **165s (2.8 min)** | **3.6x** | **90% CPU** |
| Parallel (8 workers) | 105s (1.8 min) | 5.7x | 100% CPU |

### Performance Optimizations

#### Three-Level Optimization Architecture

**Level 1: Chunk-Level Sharing (V2)**
- Transcriber shared across chunks within a job
- Eliminated per-chunk initialization overhead
- **Result:** 60x reduction in per-chunk overhead

**Level 2: In-Memory Caching (V2)**
- Model validation cached in memory
- Avoids redundant file I/O operations
- **Result:** Instant cache hits after first validation

**Level 3: Consumer-Level Singleton (V3)**
- Transcriber initialized once at consumer startup
- Shared across all jobs in consumer process
- **Result:** 50x faster job startup (<1ms vs 50ms)

### Performance Metrics

**Job Processing Overhead:**
- **Before optimization:** 50ms per job + 10.8s per 60 chunks = 11.3s overhead
- **After optimization:** <1ms per job + 0.18s per 60 chunks = 0.18s overhead
- **Reduction:** 60x faster (11.3s → 0.18s)

**Scalability:**
- **Parallel efficiency:** 90% with 4 workers
- **Throughput:** ~2.5x real-time (30-min audio in 12 minutes with 4 consumers)
- **Resource usage:** ~1.5GB RAM per worker (medium model)

For detailed performance analysis, see:
- [`docs/PARALLEL_OPTIMIZATION_V2.md`](docs/PARALLEL_OPTIMIZATION_V2.md) - Chunk-level optimization
- [`docs/PARALLEL_OPTIMIZATION_V3.md`](docs/PARALLEL_OPTIMIZATION_V3.md) - Consumer-level optimization

---

## Project Structure

```
smap-speech-to-text/
├── cmd/                              # Service entry points
│   ├── api/
│   │   ├── main.py                   # API service (FastAPI)
│   │   └── Dockerfile
│   └── consumer/
│       ├── main.py                   # Consumer service (RabbitMQ)
│       └── Dockerfile
│
├── core/                             # Shared utilities & DI
│   ├── container.py                  # Dependency Injection
│   ├── config.py                     # Configuration
│   ├── database.py                   # MongoDB connection
│   ├── messaging.py                  # RabbitMQ client
│   ├── storage.py                    # MinIO client
│   ├── logger.py                     # Logging utilities
│   └── errors.py                     # System errors
│
├── domain/                           # Domain Layer (Business Logic)
│   ├── entities.py                   # Domain Entities (Job, Chunk)
│   ├── value_objects.py              # Value Objects
│   └── events.py                     # Domain Events
│
├── ports/                            # Ports Layer (Interfaces)
│   ├── repository.py                 # Repository Port
│   ├── storage.py                    # Storage Port
│   ├── messaging.py                  # Messaging Port
│   └── transcriber.py                # Transcriber Port
│
├── adapters/                         # Adapters Layer (Infrastructure)
│   ├── mongo/                        # MongoDB Adapter
│   ├── minio/                        # MinIO Adapter
│   ├── rabbitmq/                     # RabbitMQ Adapter
│   └── whisper/                      # Whisper.cpp Adapter
│
├── services/                         # Application Layer (API Use Cases)
│   └── task_use_case.py              # Task Management Use Case
│
├── pipelines/                        # Application Layer (Worker Pipelines)
│   └── stt/
│       ├── use_cases/
│       │   └── process_job.py        # STT Job Processing Use Case
│       ├── chunking.py               # Audio Chunking Logic
│       └── merger.py                 # Result Merging Logic
│
├── internal/                         # Internal Implementation
│   ├── api/                          # API Implementation
│   │   ├── routes/                   # HTTP Routes
│   │   └── dependencies/             # DI Dependencies
│   └── consumer/                     # Consumer Implementation
│       └── handlers/                 # Message Handlers
│
├── docs/                             # Documentation
│   ├── ARCHITECTURE.md               # Architecture Design
│   └── ...
│
├── whisper/                          # Whisper.cpp Resources
│   ├── bin/                          # Executables (whisper-cli)
│   └── models/                       # Model files (.bin)
│
├── scripts/                          # Utility scripts
├── docker-compose.yml                # Orchestration
├── Makefile                          # Build commands
├── requirements.txt                  # Dependencies
└── README.md                         # This file
```

---

## Development Guide

### Adding New Features

#### 1. Add New API Endpoint

Create route in `internal/api/routes/`:
```python
# internal/api/routes/custom_routes.py
from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/custom", tags=["Custom"])

@router.get("/endpoint")
async def custom_endpoint():
    return {"message": "Custom endpoint"}
```

Register in `cmd/api/main.py`:
```python
from internal.api.routes import custom_routes

app.include_router(custom_routes.router)
```

#### 2. Add New Service

Create service in `services/`:
```python
# services/custom_service.py
class CustomService:
    def __init__(self, repo):
        self.repo = repo

    async def process(self, data):
        # Business logic here
        return result

def get_custom_service():
    return CustomService(get_custom_repository())
```

#### 3. Add New Repository

Create repository in `repositories/`:
```python
# repositories/custom_repository.py
from repositories.base_repository import BaseRepository

class CustomRepository(BaseRepository):
    def __init__(self):
        super().__init__("custom_collection")

    async def custom_query(self, filter):
        return await self.find_one(filter)

def get_custom_repository():
    return CustomRepository()
```

### Testing

#### Unit Tests
```bash
# Run all tests
make test

# Run specific test file
pytest tests/test_processor.py -v

# Run with coverage
pytest --cov=worker --cov=services --cov-report=html
```

#### Integration Tests
```bash
# Test file upload
python scripts/test_upload.py

# Test full pipeline
curl -X POST http://localhost:8000/files/upload -F "file=@test.mp3"
```

### Code Quality

#### Format Code
```bash
make format
```

#### Lint Code
```bash
make lint
```

#### Type Checking
```bash
mypy core/ repositories/ services/
```

---

## Documentation

### Complete Documentation

- **[START_HERE.md](docs/START_HERE.md)** - Getting started guide
- **[CONFIGURATION_GUIDE.md](docs/CONFIGURATION_GUIDE.md)** - Complete configuration reference
- **[DOCKER_SETUP.md](docs/DOCKER_SETUP.md)** - Docker deployment guide
- **[MODEL_DOWNLOAD_GUIDE.md](docs/MODEL_DOWNLOAD_GUIDE.md)** - Model setup and management

### Performance Optimization

- **[PARALLEL_PROCESSING.md](docs/PARALLEL_PROCESSING.md)** - Parallel transcription overview
- **[QUICK_START_PARALLEL.md](docs/QUICK_START_PARALLEL.md)** - Quick parallel setup
- **[PARALLEL_OPTIMIZATION_V2.md](docs/PARALLEL_OPTIMIZATION_V2.md)** - Chunk-level optimization
- **[PARALLEL_OPTIMIZATION_V3.md](docs/PARALLEL_OPTIMIZATION_V3.md)** - Consumer-level optimization

### Implementation Details

- **[MIGRATION_COMPLETE.md](docs/MIGRATION_COMPLETE.md)** - RabbitMQ migration details
- **[IMPLEMENTATION_GUIDE.md](docs/IMPLEMENTATION_GUIDE.md)** - Implementation reference

---

## Troubleshooting

### Common Issues

#### 1. Consumer Not Processing Jobs
```bash
# Check RabbitMQ connection
docker-compose logs rabbitmq

# Check consumer logs
docker-compose logs consumer

# Verify queue exists
# Visit: http://localhost:15672 (RabbitMQ Management UI)
```

#### 2. Transcription Timeout
```bash
# Increase timeout in .env
CHUNK_TIMEOUT=180

# Or use smaller model
DEFAULT_WHISPER_MODEL=small
```

#### 3. Out of Memory
```bash
# Reduce parallel workers
MAX_PARALLEL_WORKERS=2

# Or use smaller model
DEFAULT_WHISPER_MODEL=small
```

#### 4. Model Not Found
```bash
# Download models manually
bash scripts/setup_whisper.sh

# Or configure custom model path
WHISPER_MODELS_DIR=/path/to/models
```

#### 5. FFmpeg Not Found
```bash
# Ubuntu/Debian
sudo apt-get install ffmpeg

# macOS
brew install ffmpeg

# Verify
ffmpeg -version
```

### Log Locations

- **API Logs:** `logs/app.log`
- **Consumer Logs:** `logs/app.log`
- **Docker Logs:** `docker-compose logs -f <service>`

### Debug Mode

Enable debug logging in `.env`:
```bash
DEBUG=true
LOG_LEVEL=DEBUG
```

---

## Contributing

### Development Workflow

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **Commit** your changes (`git commit -m 'Add amazing feature'`)
4. **Push** to the branch (`git push origin feature/amazing-feature`)
5. **Open** a Pull Request

### Code Style

- Follow **PEP 8** guidelines
- Use **type hints** for function signatures
- Write **docstrings** for all public functions
- Add **unit tests** for new features
- Run **linters** before committing

### Commit Messages

```
feat: Add new feature
fix: Fix bug in processor
docs: Update README
refactor: Refactor chunking logic
test: Add unit tests for transcriber
perf: Optimize parallel processing
```

---

## Acknowledgments

- **[Whisper.cpp](https://github.com/ggerganov/whisper.cpp)** - High-performance speech recognition
- **[FastAPI](https://fastapi.tiangolo.com/)** - Modern Python web framework
- **[RabbitMQ](https://www.rabbitmq.com/)** - Reliable message broker
- **[MinIO](https://min.io/)** - High-performance object storage

---

## Support

For issues and questions:
- **Issues:** [GitHub Issues](https://github.com/your-repo/issues)
- **Discussions:** [GitHub Discussions](https://github.com/your-repo/discussions)
- **Documentation:** [docs/](docs/)

---

## Roadmap

### Planned Features

- [ ] **GPU Acceleration** - CUDA support for faster transcription
- [ ] **Real-time Streaming** - WebSocket for live transcription
- [ ] **Speaker Diarization** - Multi-speaker identification
- [ ] **Language Auto-detection** - Automatic language detection
- [ ] **Custom Vocabulary** - Domain-specific vocabulary support
- [ ] **REST API v2** - Enhanced API with more features
- [ ] **Web UI** - Browser-based upload and monitoring
- [ ] **Kubernetes** - K8s deployment manifests

---

**Version:** 1.0.0
**Last Updated:** November 2025
**Maintained by:** SMAP Team
