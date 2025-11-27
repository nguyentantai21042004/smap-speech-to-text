# SMAP Speech-to-Text System

A high-performance **stateless** Speech-to-Text (STT) API built with **FastAPI** and **Whisper.cpp**. Designed for simplicity, direct transcription, and minimal infrastructure dependencies.

---

## Key Features

### Core Capabilities
- **Direct Transcription** - Transcribe audio from URL with a single API call
- **Stateless Architecture** - No database, no message queue, no object storage
- **High-Quality STT** - Powered by Whisper.cpp (medium model) with anti-hallucination filters
- **Multiple Languages** - Support for Vietnamese, English, and 90+ languages
- **Production-Ready** - Comprehensive logging, error handling, and health monitoring

### Performance Optimizations
- **Singleton Transcriber** - Whisper engine initialized once at startup
- **In-Memory Caching** - Model validation cached to eliminate redundant I/O
- **Efficient Downloads** - Streaming audio download with size validation
- **Automatic Cleanup** - Temporary files cleaned up after transcription

### Architecture Highlights
- **Stateless Design** - Each request is independent, no session state
- **Clean Architecture** - Service layer, dependency injection, interface-based design
- **Docker-Ready** - Minimal Docker setup with health checks
- **Simple Deployment** - Single service, no external dependencies

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
- [Project Structure](#project-structure)
- [Development Guide](#development-guide)
- [Troubleshooting](#troubleshooting)

---

## Architecture Overview

### System Architecture

```
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│   Client     │─────▶│  API Service │─────▶│  Whisper.cpp │
│  (Request)   │      │  (FastAPI)   │      │     (STT)    │
└──────────────┘      └──────────────┘      └──────────────┘
                              │
                              ▼
                      ┌──────────────┐
                      │  Audio URL   │
                      │  (Download)  │
                      └──────────────┘
```

### Core Service

#### **API Service** (`cmd/api/main.py`)
- RESTful API with FastAPI
- `/transcribe` endpoint for direct transcription
- Downloads audio from provided URL
- Transcribes using Whisper.cpp
- Returns result immediately
- Health checks and monitoring

---

## Technology Stack

### Backend
| Technology | Version | Purpose |
|------------|---------|---------|
| **FastAPI** | 0.104+ | Web framework |
| **Pydantic** | 2.5+ | Data validation |
| **httpx** | Latest | Async HTTP client |
| **Whisper.cpp** | Latest | Speech-to-text engine |

### Audio Processing
| Library | Purpose |
|---------|---------|
| **FFmpeg** | Audio format conversion |

### Infrastructure
| Service | Purpose |
|---------|---------|
| **Docker** | Containerization |
| **Docker Compose** | Container orchestration |

---

## Quick Start

### Prerequisites
- **Python 3.12+**
- **Docker & Docker Compose** (for containerized deployment)
- **FFmpeg** (for audio processing)
- **Whisper.cpp** (compiled binary)

### 1. Clone Repository
```bash
git clone <repository-url>
cd speech2text
```

### 2. Environment Setup
```bash
cp .env.example .env
# Edit .env with your configuration
```

### 3. Install Dependencies
```bash
# Using uv (recommended)
uv sync

# Or using pip
pip install -e .
```

### 4. Start Service

#### Option A: Docker (Recommended)
```bash
# Start service
docker-compose up -d

# View logs
docker-compose logs -f api

# Stop service
docker-compose down
```

#### Option B: Local Development
```bash
# Start API
uv run python cmd/api/main.py

# Or with uvicorn directly
uv run uvicorn cmd.api.main:app --host 0.0.0.0 --port 8000 --reload
```

### 5. Test the System
```bash
# Transcribe audio from URL
curl -X POST http://localhost:8000/transcribe \
  -H "Content-Type: application/json" \
  -d '{"audio_url": "http://example.com/audio.mp3"}'

# Check health
curl http://localhost:8000/health
```

---

## API Documentation

### Interactive Documentation
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Endpoints

#### POST `/transcribe`
Transcribe audio from URL.

**Request:**
```json
{
  "audio_url": "http://example.com/audio.mp3"
}
```

**Response:**
```json
{
  "error_code": 0,
  "message": "Transcription successful",
  "data": {
    "text": "Transcribed text content...",
    "duration": 1.5,
    "download_duration": 0.5,
    "file_size_mb": 1.0,
    "model": "small"
  }
}
```

**Error Responses:**
- `413` - File too large
- `400` - Invalid URL or download failed
- `500` - Internal server error

#### GET `/health`
Service health check.

**Response:**
```json
{
  "error_code": 0,
  "message": "Service is healthy",
  "data": {
    "status": "healthy",
    "service": "SMAP Speech-to-Text",
    "version": "1.0.0"
  }
}
```

#### GET `/`
Root endpoint with service information.

**Response:**
```json
{
  "error_code": 0,
  "message": "API service is running",
  "data": {
    "service": "SMAP Speech-to-Text",
    "version": "1.0.0",
    "status": "running"
  }
}
```

---

## Configuration

### Environment Variables

```bash
# Application
APP_NAME="SMAP Speech-to-Text"
APP_VERSION="1.0.0"
ENVIRONMENT="development"
DEBUG=true

# API Service
API_HOST="0.0.0.0"
API_PORT=8000
API_RELOAD=true
API_WORKERS=1
MAX_UPLOAD_SIZE_MB=500

# Storage
TEMP_DIR="/tmp/stt_processing"

# Whisper Settings
WHISPER_EXECUTABLE="./whisper/bin/whisper-cli"
WHISPER_MODELS_DIR="./whisper/models"
WHISPER_LANGUAGE="vi"
WHISPER_MODEL="small"

# Whisper Quality/Accuracy Flags
WHISPER_MAX_CONTEXT=0
WHISPER_NO_SPEECH_THOLD=0.7
WHISPER_ENTROPY_THOLD=2.6
WHISPER_LOGPROB_THOLD=-0.8
WHISPER_NO_FALLBACK=true

# Logging
LOG_LEVEL="INFO"
LOG_FILE="logs/stt.log"
```

### Supported Audio Formats
MP3, WAV, M4A, MP4, AAC, OGG, FLAC, WMA, WEBM, MKV, AVI, MOV

---

## Project Structure

```
speech2text/
├── adapters/
│   └── whisper/              # Whisper.cpp integration
│       ├── engine.py         # Whisper transcriber
│       └── model_downloader.py
├── cmd/
│   └── api/                  # API service entry point
│       ├── Dockerfile
│       └── main.py
├── core/                     # Core configuration and utilities
│   ├── config.py             # Settings management
│   ├── logger.py             # Logging setup
│   ├── errors.py             # Custom exceptions
│   ├── dependencies.py       # Dependency validation
│   └── container.py          # DI container
├── internal/
│   └── api/                  # API layer
│       ├── routes/           # API endpoints
│       │   ├── transcribe_routes.py
│       │   └── health_routes.py
│       ├── schemas/          # Request/response models
│       │   └── common_schemas.py
│       └── utils.py          # API utilities
├── services/
│   └── transcription.py      # Transcription service
├── tests/                    # Unit tests
├── whisper/                  # Whisper models and binaries
├── docker-compose.yml
├── pyproject.toml
└── README.md
```

---

## Development Guide

### Running Tests
```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=. --cov-report=html

# Run specific test
uv run pytest tests/test_transcription_service.py
```

### Code Quality
```bash
# Format code
uv run black .

# Lint code
uv run ruff check .

# Type checking
uv run mypy .
```

### Docker Development
```bash
# Build image
docker-compose build

# Start service
docker-compose up -d

# View logs
docker-compose logs -f api

# Restart service
docker-compose restart api

# Stop service
docker-compose down
```

---

## Troubleshooting

### Common Issues

#### 1. Whisper executable not found
```bash
# Check whisper path
ls -la whisper/bin/whisper-cli

# Update .env
WHISPER_EXECUTABLE="./whisper/bin/whisper-cli"
```

#### 2. FFmpeg not installed
```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt-get install ffmpeg

# Verify installation
ffmpeg -version
```

#### 3. Port already in use
```bash
# Change port in .env
API_PORT=8001

# Or kill process using port 8000
lsof -ti:8000 | xargs kill -9
```

#### 4. Audio download fails
- Verify URL is accessible
- Check firewall/proxy settings
- Ensure audio format is supported
- Verify file size is within limits

### Logs
```bash
# View application logs
tail -f logs/stt.log

# Docker logs
docker-compose logs -f api
```

---

## Migration from Stateful Architecture

This service was previously a stateful architecture with MongoDB, RabbitMQ, and MinIO. It has been migrated to a stateless API for simplicity and reduced infrastructure dependencies.

### Key Changes
- ❌ Removed MongoDB (job storage)
- ❌ Removed RabbitMQ (message queue)
- ❌ Removed MinIO (object storage)
- ❌ Removed consumer service
- ✅ Added direct `/transcribe` endpoint
- ✅ Simplified configuration
- ✅ Reduced infrastructure requirements

For migration details, see `docs/STATELESS_MIGRATION.md`.

---

## License

[Your License Here]

## Contact

- **Email**: nguyentantai.dev@gmail.com
- **Team**: SMAP Team
