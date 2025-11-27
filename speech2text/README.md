# SMAP Speech-to-Text System

A high-performance **stateless** Speech-to-Text (STT) API built with **FastAPI** and **Whisper.cpp**. Designed for simplicity, direct transcription, and minimal infrastructure dependencies.

---

## Key Features

### Core Capabilities
- **Direct Transcription** - Transcribe audio from URL with a single API call
- **Stateless Architecture** - No database, no message queue, no object storage
- **High-Quality STT** - Powered by Whisper.cpp with anti-hallucination filters
- **Multiple Languages** - Support for Vietnamese, English, and 90+ languages
- **Production-Ready** - Comprehensive logging, error handling, and health monitoring

### NEW: Dynamic Model Loading
- **Runtime Model Switching** - Change between small/medium models via environment variable
- **90% Faster** - Direct C library integration eliminates subprocess overhead
- **No Rebuild Required** - Single Docker image for all environments
- **Auto-Download** - Artifacts automatically downloaded from MinIO if missing
- **Memory Efficient** - Model loaded once at startup, reused for all requests

### Performance Optimizations
- **Direct Library Integration** - C library calls instead of subprocess spawning
- **Model Preloading** - Whisper model loaded once and reused (90% latency reduction)
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
- [Dynamic Model Loading](#dynamic-model-loading-new)
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
# Start service with small model (default)
docker-compose up -d

# OR switch to medium model (no rebuild required!)
WHISPER_MODEL_SIZE=medium docker-compose up -d

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

## Dynamic Model Loading (NEW!)

### Overview

The system now supports **dynamic model loading** with direct C library integration, providing **60-90% performance improvement** over the previous CLI-based approach.

### Key Benefits

| Feature | Benefit |
|---------|---------|
| **Runtime Switching** | Change models via `WHISPER_MODEL_SIZE=small\|medium` without Docker rebuild |
| **90% Faster** | Direct C library calls eliminate subprocess overhead (2-3s → 0.1-0.3s) |
| **Single Image** | One Docker image works for all environments (dev/staging/prod) |
| **Auto-Download** | Artifacts automatically downloaded from MinIO if missing |
| **Memory Efficient** | Model loaded once at startup, reused for all requests |

### Quick Start

#### Local Development

```bash
# Download model artifacts
make setup-artifacts-small    # Download small model (181MB, ~500MB RAM)
make setup-artifacts-medium   # Download medium model (1.5GB, ~2GB RAM)

# Run tests
make test-library             # Test library adapter
make test-integration         # Test model switching

# Run API
make run-api
```

#### Docker Deployment

```bash
# Run with small model (default)
docker-compose up

# Switch to medium model (no rebuild!)
WHISPER_MODEL_SIZE=medium docker-compose up

# Or edit docker-compose.yml:
# WHISPER_MODEL_SIZE: medium
```

### Model Specifications

| Model | Size | RAM | Use Case |
|-------|------|-----|----------|
| **small** | 181 MB | ~500 MB | Development, fast transcription |
| **medium** | 1.5 GB | ~2 GB | Production, high accuracy |

### Performance Comparison

| Metric | Before (CLI) | After (Library) | Improvement |
|--------|-------------|-----------------|-------------|
| First request | 2-3s | 0.5-1s | **60-75%** |
| Subsequent requests | 2-3s | 0.1-0.3s | **90%** |
| Memory (small) | ~200MB/req | ~500MB total | Constant |
| Model loads | Every request | Once at startup | (Very large improvement) |

### Documentation

- [User Guide](docs/DYNAMIC_MODEL_LOADING_GUIDE.md)
- [Implementation Summary](IMPLEMENTATION_SUMMARY.md)
- [Change Log](CHANGES.md)

### Makefile Commands

```bash
make help                     # Show all available commands
make setup-artifacts-small    # Download small model
make setup-artifacts-medium   # Download medium model
make test-library             # Test library adapter
make test-integration         # Test model switching
make clean-old                # Remove old/unused files
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

# Whisper Library (Dynamic Model Loading)
WHISPER_MODEL_SIZE="small"       # or "medium"
WHISPER_ARTIFACTS_DIR="."

# MinIO (for artifact download)
MINIO_ENDPOINT="http://172.16.19.115:9000"
MINIO_ACCESS_KEY="smap"
MINIO_SECRET_KEY="hcmut2025"

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
│       ├── engine.py         # Legacy CLI transcriber
│       ├── library_adapter.py # NEW Direct C library integration
│       └── model_downloader.py
├── cmd/
│   └── api/                  # API service entry point
│       ├── Dockerfile        # Production Docker image
│       └── main.py           # FastAPI application
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
├── scripts/                  # NEW Utility scripts
│   ├── entrypoint.sh         # NEW Smart entrypoint for Docker
│   ├── dev-startup.sh        # Dev container startup
│   └── download_whisper_artifacts.py # Download from MinIO
├── services/
│   └── transcription.py      # Transcription service
├── tests/                    # Test suite
│   ├── test_whisper_library.py  # Library adapter tests
│   └── test_model_switching.py  # Integration tests
├── whisper/                  # Whisper models and binaries
├── docker-compose.yml
├── docker-compose.dev.yml    # NEW Development compose
├── pyproject.toml
└── README.md
```

---

## Development Guide

### Running Tests
```bash
# Run all tests
make test

# Run library adapter tests
make test-library

# Run model switching tests
make test-integration

# Run with specific model
make test-small
make test-medium

# Run with coverage
uv run pytest --cov=. --cov-report=html
```

### Code Quality
```bash
# Format code
make format

# Lint code
make lint

# Clean up
make clean
make clean-old  # Remove old/unused files
```

### Docker Development
```bash
# Build image
make docker-build

# Start service with small model
make docker-up

# Start with medium model (no rebuild!)
WHISPER_MODEL_SIZE=medium docker-compose up -d

# View logs
make docker-logs

# Restart service
docker-compose restart api

# Stop service
make docker-down
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

#### 5. Model artifacts not found (Dynamic Loading)
```bash
# Download artifacts manually
make setup-artifacts-small
make setup-artifacts-medium

# Or let entrypoint download automatically
docker-compose up
```

#### 6. Library loading error
```bash
# Check LD_LIBRARY_PATH is set correctly
export LD_LIBRARY_PATH=/app/whisper_small_xeon:$LD_LIBRARY_PATH

# Verify artifacts exist
ls -la whisper_small_xeon/

# Re-download if corrupted
rm -rf whisper_small_xeon
make setup-artifacts-small
```

### Logs
```bash
# View application logs
tail -f logs/stt.log

# Docker logs
docker-compose logs -f api
```

---

## Contact

- **Email**: nguyentantai.dev@gmail.com
- **Team**: SMAP Team
