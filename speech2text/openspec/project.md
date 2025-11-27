# Project Context

## Purpose
Provide a production-ready, asynchronous speech-to-text (STT) platform that ingests large media files, orchestrates transcription jobs via RabbitMQ, persists metadata in MongoDB, stores binaries in MinIO, and delivers Whisper.cpp transcripts through a FastAPI interface.

## Tech Stack
- Python 3.10+
- FastAPI + Pydantic for HTTP services
- aio-pika + RabbitMQ for messaging
- Motor (async MongoDB driver)
- MinIO / boto3-compatible client for object storage
- Whisper.cpp binaries for transcription engine
- FFmpeg/librosa/pydub for audio preprocessing

## Project Conventions

### Code Style
- Follow PEP8 with type hints on public functions.
- Prefer descriptive module/class names that mirror their Clean Architecture role (e.g., `task_use_case`, `mongo_task_repository`).
- Use Conventional Commit prefixes (`feat`, `fix`, `docs`, `refactor`, etc.) as suggested in README.
- Keep logging structured with contextual identifiers (job_id, file_id) to aid observability.

### Architecture Patterns
- Clean Architecture layering: presentation (FastAPI routers), application/services, domain/pipelines, infrastructure adapters (Mongo/MinIO/RabbitMQ/Whisper).
- Microservices split: API service for ingestion/monitoring, Consumer service for heavy processing.
- Repository and service interfaces to decouple business logic from persistence/messaging drivers.
- Queue-driven processing with singleton Whisper transcriber inside consumers for performance.

### Testing Strategy
- Pytest for unit/integration tests; prioritize domain/pipeline logic and repository adapters.
- Use in-memory or Dockerized Mongo/Rabbit/MinIO for integration flows.
- `make test` runs full suite; coverage focused on services, worker pipelines, and error handling paths.
- Smoke tests available via `scripts/test_upload.py` for end-to-end validation.

### Git Workflow
- Develop on short-lived feature branches named `feat/<scope>` or `fix/<scope>`; merge via PRs.
- Require proposal approval (OpenSpec) before implementing architectural or capability changes.
- Use Conventional Commits and keep PRs focused on a single change-set aligned with an OpenSpec change ID.

## Domain Context
- Primary workflow: client uploads audio → API stores metadata/files → RabbitMQ queues job → consumer downloads from MinIO, chunks audio, transcribes via Whisper.cpp, merges output, persists transcript/metrics.
- Jobs tracked via MongoDB documents (`JobModel`) storing chunk progress, retry counts, MinIO paths.
- Anti-hallucination settings and parallel chunking are key differentiators; ensure new work preserves configurable thresholds (chunk duration, retries, language defaults).

## Important Constraints
- Large uploads (up to ~500 MB) require streaming-safe handlers and MinIO storage limits.
- Processing is CPU-bound; design for horizontal scaling via multiple consumers while keeping singleton transcriber per process.
- Whisper models must exist locally (managed by `scripts/setup_whisper.sh`); consumer startup validates dependencies (ffmpeg, models).
- API responses standardize on success/error payload helpers; avoid throwing raw HTTP errors without wrapper.

## External Dependencies
- MongoDB (job metadata, chunk status).
- RabbitMQ (STT job queue, prioritization).
- MinIO (S3-compatible object storage for audio/result artifacts).
- Whisper.cpp binaries (transcription engine) plus model files.
- FFmpeg/librosa/pydub for media manipulation.
