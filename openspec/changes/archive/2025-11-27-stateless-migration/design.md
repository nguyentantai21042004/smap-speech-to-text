# Design: Stateless Migration

## Architecture Shift

| Feature | Legacy (Stateful) | Target (Stateless) |
| :--- | :--- | :--- |
| **Pattern** | Async Worker (Consumer) | Sync/Async API |
| **Input** | RabbitMQ Message | HTTP POST `{"audio_url": "..."}` |
| **Data Access** | MinIO Client + Credentials | HTTP GET (Presigned URL) |
| **Persistence** | MongoDB | None (Response only) |
| **Scaling** | Queue Depth | CPU Utilization (HPA) |

## New Workflow

1.  **Client** sends `POST /transcribe` with `audio_url`.
2.  **API Service**:
    *   Validates URL.
    *   Downloads file to `/tmp` (streamed).
    *   Checks size limit (500MB).
3.  **Whisper Engine**:
    *   Reads file from `/tmp`.
    *   Performs inference.
4.  **Cleanup**: Deletes temporary file.
5.  **Response**: Returns JSON `{ "text": "...", "duration": ... }`.

## Component Cleanup

We will **DELETE** the following directories and files:
-   `adapters/mongo/`
-   `adapters/rabbitmq/`
-   `adapters/minio/`
-   `core/database.py`
-   `core/messaging.py`
-   `core/storage.py`
-   `cmd/consumer/` (Entire consumer service)

We will **KEEP** and **REFACTOR**:
-   `adapters/whisper/` (Engine logic)
-   `cmd/api/` (Main entry point)
-   `core/config.py` (Simplified)

## Configuration Changes

**Keep**:
-   `APP_NAME`, `ENVIRONMENT`, `LOG_LEVEL`
-   `API_PORT`, `API_WORKERS`, `MAX_UPLOAD_SIZE_MB`
-   `WHISPER_MODEL`, `WHISPER_LANGUAGE`, `TEMP_DIR`

**Remove**:
-   `MONGODB_*`
-   `RABBITMQ_*`
-   `MINIO_*`
