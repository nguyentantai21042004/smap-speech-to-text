## Change: Add dedicated STT swagger endpoint and presigned transcription API

## Why
- Ops team needs a discoverable swagger UI hosted at `domain/stt/swagger/index.html` to expose all STT API methods under a consistent path.
- Crawler team requires a lightweight transcription API that accepts MinIO presigned URLs instead of binary uploads to reduce bandwidth and memory pressure.

## What Changes
- Host generated OpenAPI/Swagger assets under `/swagger/index.html` (and supporting files) served by the API service behind the domain.
- Define and expose a POST `/transcribe` endpoint that accepts `media_url` + `language` hints and returns transcription metadata (`status`, `transcription`, `duration`, `confidence`, `processing_time`).
- Implement streaming download, optional ffmpeg audio extraction, whisper inference with timeout guard, and cleanup lifecycle for temporary assets.
- **CRITICAL - Placeholder Removal**: Replace all placeholder implementations with production code:
  - Implement ffmpeg-based audio loading (convert any format → 16kHz mono PCM float32)
  - Implement actual `whisper_full()` C library calls with proper ctypes bindings
  - Extract transcript segments using `whisper_full_get_segment_text()`
  - Calculate confidence scores from segment probabilities
  - Ensure all valid audio inputs return non-empty transcripts (no placeholders in production)
- Secure the endpoint with an internal API key header (with future option for mTLS).

## Impact
- Specs: `stt-api`
- Code: 
  - `cmd/api/main.py` - Swagger static file mounting
  - `internal/api/routes/transcribe_routes.py` - New `/transcribe` endpoint with auth
  - `internal/api/dependencies/auth.py` - API key authentication
  - `internal/api/schemas/` - Request/response models
  - `services/transcription.py` - Timeout handling and service orchestration
  - `adapters/whisper/library_adapter.py` - **CRITICAL**: Audio loading + whisper_full implementation (replace placeholders)
  - `core/config.py` - New config fields (API key, timeout, language)
  - `tests/test_api_transcribe_v2.py` - Comprehensive test coverage
  - `cmd/api/swagger_static/index.html` - Swagger UI hosting

