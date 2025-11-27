# Stateless Migration

## Why
The current architecture is overly complex for the core requirement of converting audio URL to text. It relies on stateful components (MongoDB, RabbitMQ) and heavy infrastructure (MinIO) which introduces:
- **Operational Overhead**: Managing DB, Queue, and Storage credentials and connections.
- **Code Complexity**: ~60-70% of code is boilerplate for infrastructure management.
- **Scaling Issues**: Stateful workers are harder to scale than stateless APIs.

## What Changes
We will migrate the service to a **Stateless Architecture**:
1.  **Input**: HTTP POST request with `audio_url` instead of RabbitMQ messages.
2.  **Processing**: Synchronous (or async-waiting) download and transcription.
3.  **Output**: JSON response with transcription text instead of writing to MongoDB.
4.  **Cleanup**: Remove MongoDB, RabbitMQ, and MinIO adapters and dependencies.
5.  **Configuration**: Reduce environment variables from ~40 to ~10.

## Verification Plan
1.  **Unit Tests**: Update service tests to mock HTTP download instead of MinIO.
2.  **Integration Tests**: Test the new `/transcribe` endpoint with a sample audio URL.
3.  **Manual Verification**: Deploy and verify memory usage and response time.
