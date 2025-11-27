## Change: Add dedicated STT swagger endpoint and presigned transcription API

## Why
- Ops team needs a discoverable swagger UI hosted at `domain/stt/swagger/index.html` to expose all STT API methods under a consistent path.
- Crawler team requires a lightweight transcription API that accepts MinIO presigned URLs instead of binary uploads to reduce bandwidth and memory pressure.

## What Changes
- Host generated OpenAPI/Swagger assets under `/swagger/index.html` (and supporting files) served by the API service behind the domain.
- Define and expose a POST `/transcribe` endpoint that accepts `media_url` + `language` hints and returns transcription metadata (`status`, `transcription`, `duration`, `confidence`, `processing_time`).
- Implement streaming download, optional ffmpeg audio extraction, whisper inference with timeout guard, and cleanup lifecycle for temporary assets.
- Secure the endpoint with an internal API key header (with future option for mTLS).

## Impact
- Specs: `stt-api`
- Code: `cmd/api/main.py`, `internal/api/routes/transcribe_routes.py`, `internal/api/schemas`, `services/transcription.py`, `scripts/` (ffmpeg helpers), swagger static hosting config.

