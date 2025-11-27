## SMAP Speech-to-Text – Architecture Refactor Proposal

### 1. Context & Goals
- **Business driver**: hệ thống cần scale xử lý STT song song, dễ bảo trì và mở rộng thêm tính năng (speaker diarization, streaming, GPU variants).
- **Mục tiêu kỹ thuật**  
  - Chuẩn hoá Clean Architecture giúp domain độc lập hạ tầng.  
  - Tách rõ trách nhiệm API (ingest), Orchestrator/Worker (process) và Core Infrastructure.  
  - Nâng cao testability thông qua interface + dependency injection.  
  - Chuẩn bị cho multi-pipeline (STT, summarization, diarization) dùng chung nền tảng queue/storage.

### 2. Current Architecture Snapshot
```
cmd/api → internal/api → services → repositories → core (DB, MQ, storage)
cmd/consumer → internal/consumer → worker (processor/chunk/transcriber) → repositories/core
```

**Điểm mạnh**
- Đã tách API & consumer entrypoint.
- Có service layer và repository pattern cơ bản.
- Worker pipeline rõ ràng (download → chunk → transcribe → merge → persist).

**Khoảng trống**
- `services/interfaces` chưa được implement, DI chủ yếu thông qua singleton getter nên khó mock/test.
- Worker domain phụ thuộc trực tiếp `repositories` (Mongo schemas) và `core` factories → ngược chiều nguyên tắc Clean Architecture.
- Adapter (`internal/api/routes`) phải tự tạo service ngay trong handler => khó kiểm soát lifecycle, retry policy, metrics.
- Thiếu chuẩn module cho các pipeline mới (ví dụ diarization) vì `worker` đang gắn chặt vào STT.

### 3. Target Architecture Overview
```
                            ┌──────────────┐
                            │ Presentation │ (FastAPI routers, Pydantic I/O)
                            └──────┬───────┘
                                   │
                                   ▼
                          ┌──────────────────┐
                          │ Application Core │
                          │ - TaskUseCases   │
                          │ - Orchestrators  │
                          └──────┬───────────┘
                                   │
                    ┌──────────────┴──────────────┐
                    ▼                             ▼
        ┌──────────────────┐           ┌──────────────────┐
        │ Domain Services  │           │ Pipeline Engines │
        │ (Job, Chunk,     │           │ (STT, future     │
        │  Audio entities) │           │  diarization…)   │
        └────────┬─────────┘           └────────┬─────────┘
                 │                              │
                 ▼                              ▼
        ┌──────────────┐               ┌──────────────────┐
        │ Ports/Interfaces (Repository, Storage, MQ, Model APIs) │
        └──────────────┘               └──────────────────┘
                 │                              │
                 ▼                              ▼
        ┌──────────────┐               ┌──────────────────┐
        │ Infrastructure│              │ External Services │
        │ (Mongo, MinIO,│              │ (Whisper, Rabbit) │
        │ RabbitMQ…)    │              └──────────────────┘
        └──────────────┘
```

### 4. Layer Responsibilities & Module Mapping
| Layer | Responsibility | Proposed Modules |
|-------|----------------|------------------|
| Presentation | HTTP routes, request validation, translation to commands/events | `cmd/api`, `internal/api/routes`, `internal/api/schemas` |
| Application | Use cases orchestrating repositories + domain services; queue publish | `services/task_use_case.py`, `services/file_use_case.py`, orchestrator classes |
| Domain | Pure business logic, entities, policies (Job, Chunk, TranscriptionResult) | `domain/` (new) with dataclasses + domain services |
| Pipeline Engines | STT workflow, chunking, transcriber coordination (runs inside consumer) | `pipelines/stt/processor.py`, `pipelines/common/chunking.py` |
| Ports | Abstract interfaces for repositories, storage, messaging, model runner | `ports/repository.py`, `ports/storage.py`, `ports/messaging.py`, `ports/transcriber.py` |
| Infrastructure | Concrete adapters to Mongo/Motor, MinIO, RabbitMQ, Whisper.cpp | `adapters/mongo_task_repository.py`, `adapters/minio_storage.py`, `adapters/rabbitmq_queue.py`, `adapters/whisper_runner.py` |

### 5. Refactor Game Plan
#### Phase 0 – Foundations
1. **Introduce DI container** (ví dụ `core/container.py`) với provider cho settings, logger, repository interface, queue interface.  
2. **Create `domain/` package** chứa:  
   - `entities.py` (Job, File, Chunk).  
   - `value_objects.py` (JobId, FilePath).  
   - `events.py` (JobQueued, JobCompleted).
3. **Define ports** trong `ports/` và cập nhật docstring + typing.

#### Phase 1 – Application Layer
4. Refactor `services/task_service.py` thành `services/task_use_case.py` implement interface `ITaskUseCase`.  
5. Routers sử dụng FastAPI `Depends(get_task_use_case)` -> container resolve.  
6. Chuyển logic `process_stt_job` thành `pipelines/stt/use_cases/process_job.py` nhận vào các port thay vì gọi `get_task_repository` trực tiếp.

#### Phase 2 – Infrastructure Adapters
7. Tách `repositories/task_repository.py` thành hai phần:  
   - Interface `TaskRepositoryPort`.  
   - Adapter `MongoTaskRepository` (trong `adapters/mongo/task_repository.py`).  
8. Làm tương tự với storage, messaging, transcriber.  
9. Container bind default adapters nhưng mở options (ví dụ testing: InMemoryTaskRepository).

#### Phase 3 – Worker Modularity
10. Restructure `worker/` → `pipelines/stt/` với submodules:  
    - `chunker`, `transcriber`, `merger`, `orchestrator`.  
    - Generic `pipelines/base.py` để tái dùng cho pipeline mới.
11. Handler `internal/consumer/handlers/stt_handler.py` chỉ convert message → `ProcessSttJobCommand` và gọi use case.

#### Phase 4 – Cross-cutting & Testing
12. Thêm contract tests cho ports (ví dụ pytest fixtures kiểm tra repository conform).  
13. Document build trong `docs/ARCHITECTURE.md` + update README architecture section.  
14. Mở đường cho features:  
    - GPU transcriber adapter implement `TranscriberPort`.  
    - Streaming service = thêm presentation adapter (WebSocket) reuse application core.

### 6. Migration Strategy
| Step | Action | Risk Mitigation |
|------|--------|-----------------|
| 0 | Add container + ports (no behavior change). | Feature flag to switch back to direct `get_*`. |
| 1 | Move services to use cases & inject ports. | Add unit tests covering `create_stt_task_from_file_id`. |
| 2 | Refactor worker pipeline with new ports. | Keep old `worker/processor.py` until new orchestrator stable; run dual path behind env var `USE_NEW_PIPELINE`. |
| 3 | Remove legacy factories once consumer/API proven. | Observability: compare metrics (processing time, failure rate). |

### 7. Expected Outcomes
- **Testability**: 80%+ core logic testable bằng in-memory adapters, không cần Rabbit/Mongo thật.  
- **Extensibility**: Dễ thêm pipeline mới bằng cách implement port + orchestrator.  
- **Operational clarity**: Container + modules giúp log/tracing theo layer, giảm coupling.  
- **Team onboarding**: Docs chuẩn + cấu trúc rõ ràng → dev mới nắm flow nhanh hơn.

### 8. Next Steps
1. Approve proposal & prioritize refactor phases.  
2. Tạo tickets chi tiết cho từng bước (container, ports, worker restructure).  
3. Thiết lập CI gates (lint, tests) để đảm bảo refactor không phá vỡ pipeline hiện tại.  
4. Sau khi hoàn thành, cập nhật tài liệu (README, diagrams) và tổ chức walkthrough cho team.

