# Project Context

## Purpose
Provide a production-ready, stateless speech-to-text (STT) API that transcribes audio from URLs using Whisper.cpp, delivering high-quality transcripts through a FastAPI interface with minimal infrastructure dependencies.

## Tech Stack
- **Python 3.12+** with uv for dependency management
- **FastAPI + Pydantic** for HTTP services and data validation
- **Whisper.cpp** (shared library integration) for transcription engine
- **httpx** for async HTTP client (audio download)
- **FFmpeg** for audio format conversion
- **Docker** for containerized deployment

## Project Conventions

### Code Style
- Follow PEP8 with type hints on public functions
- Prefer descriptive module/class names that mirror their Clean Architecture role (e.g., `TranscribeService`, `WhisperLibraryAdapter`)
- Use Conventional Commit prefixes (`feat`, `fix`, `docs`, `refactor`, etc.)
- Keep logging structured with contextual identifiers to aid observability

### Architecture Patterns
- **Stateless Design**: Each request is independent, no session state or background jobs
- **Clean Architecture**: Presentation (FastAPI routers) → Application (services) → Infrastructure (adapters)
- **Singleton Pattern**: Whisper transcriber initialized once at startup for performance
- **Direct Library Integration**: Whisper.cpp loaded as shared library (.so) instead of CLI subprocess
- **Interface-Based**: Services implement interfaces for testability and flexibility

### Testing Strategy
- **Pytest** for unit/integration tests
- **Coverage Focus**: Services, adapters, and error handling paths
- **Test Commands**:
  - `make test` - Run full test suite
  - `uv run pytest` - Direct pytest execution
  - `make -f Makefile.dev dev-test` - Run tests in dev container

### Git Workflow
- Develop on short-lived feature branches: `feat/<scope>` or `fix/<scope>`
- Require OpenSpec proposal approval before architectural changes
- Use Conventional Commits
- Keep PRs focused on single change-set aligned with OpenSpec change ID

## Domain Context

### Primary Workflow
1. **Client Request**: POST to `/transcribe` with `audio_url`
2. **Audio Download**: Service downloads audio from URL (with size validation)
3. **Transcription**: Direct call to Whisper.cpp library (no subprocess)
4. **Response**: Return transcribed text immediately

### Key Features
- **Direct Transcription**: Synchronous request-response (no queues)
- **Dynamic Model Loading**: Switch between small/medium models via ENV variable
- **Auto-Download**: Whisper artifacts downloaded from MinIO on first run
- **Anti-Hallucination**: Configurable thresholds (entropy, logprob, no-speech)

## Important Constraints

### Performance
- **Model Loading**: Models loaded once at startup (~500MB for small, ~2GB for medium)
- **Concurrent Requests**: Singleton transcriber handles requests sequentially
- **File Size Limits**: Configurable max upload size (default: 500MB)
- **Temporary Storage**: Files cleaned up after transcription

### Platform Requirements
- **Linux Only**: Shared libraries (.so) compiled for Linux x86_64/Xeon
- **macOS Development**: Use Docker dev container (`docker-compose.dev.yml`)
- **CPU Requirements**: AVX2 and FMA support for optimal performance

### API Standards
- **Response Format**: Standardized `{error_code, message, data}` structure
- **Error Handling**: Proper HTTP status codes with detailed error messages
- **Health Checks**: `/health` endpoint for monitoring

## External Dependencies

### Runtime Dependencies
- **Whisper.cpp Libraries**: `libwhisper.so`, `libggml*.so` (Linux shared libraries)
- **Whisper Models**: `ggml-small-q5_1.bin` or `ggml-medium-q5_1.bin`
- **FFmpeg**: Audio format conversion
- **libgomp1**: OpenMP runtime for parallel processing

### Development Dependencies
- **MinIO**: Artifact storage (for downloading Whisper models)
- **boto3**: MinIO client for artifact downloads
- **Docker**: Development container for macOS compatibility

## Project Structure

```
speech2text/
├── adapters/           # Infrastructure adapters
│   └── whisper/        # Whisper.cpp integration
│       ├── engine.py   # Legacy CLI wrapper (fallback)
│       └── library_adapter.py  # Direct C library integration
├── cmd/                # Application entry points
│   └── api/            # API service
│       ├── Dockerfile  # Production Docker image
│       └── main.py     # FastAPI application
├── core/               # Core configuration and utilities
│   ├── config.py       # Settings management (Pydantic)
│   ├── logger.py       # Logging setup
│   ├── errors.py       # Custom exceptions
│   └── container.py    # Dependency injection
├── internal/           # Internal API implementation
│   └── api/
│       ├── routes/     # API endpoints
│       ├── schemas/    # Request/response models
│       └── utils.py    # API utilities
├── services/           # Business logic
│   └── transcription.py  # Transcription service
├── scripts/            # Utility scripts
│   ├── dev-startup.sh  # Dev container startup
│   ├── download_whisper_artifacts.py  # MinIO downloader
│   └── entrypoint.sh   # Production entrypoint
├── tests/              # Test suite
├── openspec/           # OpenSpec specifications
├── docker-compose.yml  # Production compose
├── docker-compose.dev.yml  # Development compose
└── pyproject.toml      # Project dependencies (uv)
```

## Development Workflow

### Local Development (macOS)
```bash
# Use dev container (required for .so libraries)
make -f Makefile.dev dev-up
make -f Makefile.dev dev-logs
```

### Production Build
```bash
# Build Docker image
docker build -t smap-stt:latest -f cmd/api/Dockerfile .

# Run with model selection
docker run -e WHISPER_MODEL_SIZE=small -p 8000:8000 smap-stt:latest
```

### Model Switching
```bash
# Switch to medium model (no rebuild required)
WHISPER_MODEL_SIZE=medium docker-compose up
```

## Migration History

This project was migrated from a stateful architecture (MongoDB + RabbitMQ + MinIO + Consumer service) to a stateless API design. See archived OpenSpec changes:
- `2025-11-27-stateless-migration` - Core stateless refactor
- `2025-11-27-dynamic-model-loading` - Shared library integration
