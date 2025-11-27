# Architecture Design

## Target Architecture

```mermaid
graph TD
    Presentation[Presentation Layer\n(FastAPI, Pydantic)] --> Application[Application Core\n(Use Cases, Orchestrators)]
    Application --> Domain[Domain Services\n(Job, Chunk, Audio)]
    Application --> Pipeline[Pipeline Engines\n(STT, Diarization)]
    Domain --> Ports[Ports/Interfaces]
    Pipeline --> Ports
    Ports --> Infrastructure[Infrastructure Adapters\n(Mongo, MinIO, RabbitMQ, Whisper)]
    Ports --> External[External Services]
```

## Layer Responsibilities

| Layer | Responsibility | Proposed Modules |
|-------|----------------|------------------|
| **Presentation** | HTTP routes, request validation, translation to commands/events | `cmd/api`, `internal/api/routes`, `internal/api/schemas` |
| **Application** | Use cases orchestrating repositories + domain services; queue publish | `services/task_use_case.py`, `services/file_use_case.py`, orchestrator classes |
| **Domain** | Pure business logic, entities, policies (Job, Chunk, TranscriptionResult) | `domain/` (new) with dataclasses + domain services |
| **Pipeline Engines** | STT workflow, chunking, transcriber coordination (runs inside consumer) | `pipelines/stt/processor.py`, `pipelines/common/chunking.py` |
| **Ports** | Abstract interfaces for repositories, storage, messaging, model runner | `ports/repository.py`, `ports/storage.py`, `ports/messaging.py`, `ports/transcriber.py` |
| **Infrastructure** | Concrete adapters to Mongo/Motor, MinIO, RabbitMQ, Whisper.cpp | `adapters/mongo_task_repository.py`, `adapters/minio_storage.py`, `adapters/rabbitmq_queue.py`, `adapters/whisper_runner.py` |

## Refactor Game Plan

### Phase 0 – Foundations
1. **Introduce DI container** (`core/container.py`) with providers for settings, logger, repository interfaces, queue interfaces.
2. **Create `domain/` package**:
   - `entities.py` (Job, File, Chunk).
   - `value_objects.py` (JobId, FilePath).
   - `events.py` (JobQueued, JobCompleted).
3. **Define ports** in `ports/` with docstrings and typing.

### Phase 1 – Application Layer
4. Refactor `services/task_service.py` to `services/task_use_case.py` implementing `ITaskUseCase`.
5. Update Routers to use `FastAPI Depends(get_task_use_case)` for container resolution.
6. Convert `process_stt_job` logic to `pipelines/stt/use_cases/process_job.py` injecting ports.

### Phase 2 – Infrastructure Adapters
7. Split `repositories/task_repository.py`:
   - Interface `TaskRepositoryPort`.
   - Adapter `MongoTaskRepository` (in `adapters/mongo/task_repository.py`).
8. Repeat for storage, messaging, and transcriber.
9. Bind default adapters in Container (allow options for testing).

### Phase 3 – Worker Modularity
10. Restructure `worker/` → `pipelines/stt/` with submodules: `chunker`, `transcriber`, `merger`, `orchestrator`.
11. Create generic `pipelines/base.py` for reusability.
12. Update `internal/consumer/handlers/stt_handler.py` to convert message → `ProcessSttJobCommand` and call use case.

### Phase 4 – Cross-cutting & Testing
13. Add contract tests for ports.
14. Update `docs/ARCHITECTURE.md` and README.
15. Enable new features (GPU adapter, Streaming).
