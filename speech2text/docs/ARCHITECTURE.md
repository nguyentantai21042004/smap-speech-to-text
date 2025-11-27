# System Architecture

This document describes the architecture of the SMAP Speech-to-Text system, following Clean Architecture principles.

## Overview

The system is designed to be modular, testable, and maintainable by separating concerns into distinct layers.

## Layers

### 1. Domain Layer (`domain/`)
The core of the application. It contains business logic and rules independent of external frameworks.
- **Entities**: `Job`, `Chunk` (Mutable business objects)
- **Value Objects**: `JobId`, `FilePath` (Immutable attributes)
- **Events**: `JobCreated`, `JobCompleted` (Domain events)

### 2. Ports Layer (`ports/`)
Defines the interfaces (contracts) that the application uses to interact with the outside world.
- **Repositories**: `TaskRepositoryPort` (Data access)
- **Storage**: `StoragePort` (File storage)
- **Messaging**: `MessagingPort` (Message queue)
- **Transcriber**: `TranscriberPort` (Speech-to-text engine)

### 3. Application Layer (`services/`, `pipelines/`)
Contains Use Cases that orchestrate the domain logic and ports.
- **TaskUseCase**: Handles API requests for creating and retrieving tasks.
- **ProcessJobUseCase**: Handles the background processing pipeline (Download -> Chunk -> Transcribe -> Merge -> Upload).

### 4. Adapters Layer (`adapters/`)
Implements the interfaces defined in the Ports layer.
- **Mongo**: `MongoTaskRepository` (MongoDB implementation)
- **MinIO**: `MinioStorageAdapter` (MinIO implementation)
- **RabbitMQ**: `RabbitMQAdapter` (RabbitMQ implementation)
- **Whisper**: `WhisperAdapter` (Whisper.cpp implementation)

### 5. Infrastructure/Entry Points (`cmd/`, `internal/`)
The entry points that wire everything together.
- **API**: `cmd/api/main.py` (FastAPI)
- **Consumer**: `cmd/consumer/main.py` (RabbitMQ Consumer)
- **DI Container**: `core/container.py` (Wires ports to adapters)

## Data Flow

1. **User** uploads file via API.
2. **API** calls `TaskUseCase.create_stt_task`.
3. **TaskUseCase**:
   - Uploads file via `StoragePort`.
   - Creates `Job` entity.
   - Saves `Job` via `TaskRepositoryPort`.
   - Publishes event via `MessagingPort`.
4. **Consumer** receives event.
5. **Consumer** calls `ProcessJobUseCase.execute`.
6. **ProcessJobUseCase**:
   - Fetches `Job` via `TaskRepositoryPort`.
   - Downloads audio via `StoragePort`.
   - Chunks audio (Domain logic).
   - Transcribes chunks via `TranscriberPort`.
   - Merges results (Domain logic).
   - Uploads result via `StoragePort`.
   - Updates `Job` status via `TaskRepositoryPort`.

## Dependency Injection

The system uses a Dependency Injection (DI) container to manage dependencies.
- **Bootstrap**: The container is initialized at application startup (`bootstrap_container`).
- **Resolution**: Use Cases resolve their dependencies from the container (`Container.resolve`).

## Future Improvements

- **Contract Tests**: Verify that adapters correctly implement ports.
- **Event-Driven Architecture**: Fully decouple components using domain events.
- **Scalability**: The modular design allows scaling individual components (e.g., multiple consumers).
