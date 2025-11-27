## ADDED Requirements

### Requirement: STT Swagger Exposure
The system SHALL expose the Speech-to-Text API documentation at `domain/swagger/index.html`, backed by the latest OpenAPI definition (`/openapi.json`) and bundled assets (JS/CSS) so internal teams can self-serve integration details.

#### Scenario: Serve swagger UI
- **WHEN** an authenticated internal client performs `GET domain/swagger/index.html`
- **THEN** the service SHALL return HTTP 200 with the swagger HTML shell
- **AND** the page SHALL load the API spec from `/openapi.json`
- **AND** referenced JS/CSS assets SHALL be served under `/swagger/`.

#### Scenario: Keep FastAPI native docs available
- **WHEN** engineers hit `/docs` or `/redoc`
- **THEN** the service SHALL continue serving the default FastAPI interactive docs to avoid breaking existing tooling.

### Requirement: Presigned URL Transcription API
The system SHALL expose a POST `/transcribe` endpoint that accepts a JSON payload with `media_url` (MinIO presigned URL) and optional `language` hint, secured by an internal API key header, and returns transcription metadata.

#### Scenario: Successful transcription
- **WHEN** the crawler sends a POST request with a valid API key header and JSON body containing `media_url` and `language`
- **THEN** the service SHALL stream-download the media without storing it permanently
- **AND** it SHALL transcribe the audio (detected or extracted via ffmpeg) using the configured Whisper backend
- **AND** it SHALL respond with HTTP 200 and JSON fields `status`, `transcription`, `duration`, `confidence`, `processing_time`.

#### Scenario: Enforce authentication
- **WHEN** the request is missing the internal API key or provides an invalid key
- **THEN** the service SHALL return HTTP 401 with an error payload and skip any media download or inference work.

#### Scenario: Enforce inference timeout
- **WHEN** inference exceeds the configured timeout threshold (default 30 seconds)
- **THEN** the service SHALL abort processing, clean up temporary files, and return HTTP 504 (or HTTP 200 with `status=timeout` per response contract) so the crawler can retry gracefully.

#### Scenario: Handle invalid media URL
- **WHEN** the provided `media_url` cannot be fetched (4xx/5xx) or is not reachable within network/timeouts
- **THEN** the service SHALL return an error payload describing the fetch failure and SHALL not attempt transcription.

