# SMAP Speech-to-Text (Async) - Microservices Architecture

A scalable, CPU-friendly Speech-to-Text (STT) system for asynchronous processing. Built with FastAPI, RabbitMQ, and worker consumers. No third‑party paid APIs required.

## Architecture Overview

This project implements a **microservices architecture** with clear separation between business logic, ML models, and support services.

### Core Services

1. **API Gateway** (`cmd/api/`) - FastAPI REST API
   - Upload audio, create STT jobs, query job status/results
   - Push jobs to message queue for async processing
   - Routes organized in `internal/api/`

2. **Worker/Consumer** (`cmd/consumer/`) - Background Processor
   - Consumes jobs from RabbitMQ
   - Performs audio preprocessing, chunking, transcription via an STT engine (e.g., whisper.cpp)
   - Aggregates chunk results and stores final text

3. **Scheduler** (`cmd/scheduler/`) - Optional maintenance
   - Periodic cleanup, metrics, health checks

## Project Structure

```
smap-speech-to-text/
├── cmd/                              # Service entry points
│   ├── api/
│   │   ├── main.py                   # Original API entry point
│   │   ├── main.py        # Refactored with clean architecture
│   │   └── Dockerfile
│   ├── consumer/
│   │   └── main.py                   # Consumer service entry point
│   └── scheduler/
│       ├── main.py
│       └── Dockerfile
│
├── internal/                         # Internal implementation (not public API)
│   ├── api/                          # API implementation
│   │   ├── routes/                   # HTTP route handlers
│   │   │   ├── keyword_routes.py
│   │   │   ├── task_routes.py
│   │   │   ├── health_routes.py
│   │   ├── schemas/                  # Request/Response models
│   │   │   ├── keyword_schemas.py
│   │   │   ├── task_schemas.py
│   │   │   └── common_schemas.py
│   │   └── dependencies/             # Dependency injection
│   │
│   └── consumer/                     # Consumer implementation
│       └── handlers/                 # Message handlers
│           └── keyword_handler.py
│
├── services/                         # Business logic layer (public API)
│   ├── interfaces/                   # Service interfaces
│   ├── keyword_service.py            # Example (kept for structure)
│   ├── task_service.py               # Async job tracking
│   └── sentiment_service.py          # Stub (no LLM bundled)
│
├── repositories/                     # Data access layer (public API)
│   ├── interfaces/                   # Repository interfaces
│   │   ├── keyword_repository_interface.py
│   │   └── task_repository_interface.py
│   ├── base_repository.py
│   ├── keyword_repository.py
│   └── task_repository.py
│
├── core/                             # Core utilities (public API)
│   ├── config.py                     # Configuration management
│   ├── database.py                   # MongoDB connection (optional)
│   ├── messaging.py                  # RabbitMQ messaging
│   └── logger.py                     # Logging utilities
│
├── llm-models/                       # LLM Models module
│   ├── base/                         # Base classes and interfaces
│   │   └── model_interface.py
│   ├── utils/                        # Shared utilities
│   ├── preprocessors/                # Text preprocessing
│   │   └── vncorenlp_client.py       # HTTP client for VnCoreNLP
│   ├── sentiment/                    # Sentiment analysis
│   │   ├── phobert_sentiment.py
│   │   └── config.py
│   └── term/                         # Term extraction
│
├── packages/                         # External microservices
│   └── vncorenlp/                    # VnCoreNLP service (optional)
│       └── Dockerfile
│
├── docs/                             # Documentation
│   ├── ARCHITECTURE.md               # System architecture
│   ├── DEVELOPER_GUIDE.md            # How to add features
│   ├── ML_INTEGRATION_GUIDE.md       # How to integrate ML models
│   └── QUICKSTART.md                 # Quick start guide
│
├── docker-compose.yml                # Multi-service orchestration
├── Makefile                          # Build and run commands
└── requirements.txt                  # Python dependencies
```

## Design Patterns & Principles

- **Microservices Architecture** - Services communicate via HTTP/RabbitMQ
- **Interface-Based Design** - All services and repositories implement interfaces
- **Single Responsibility Principle** - Each module has one clear responsibility
- **Producer-Consumer Pattern** - RabbitMQ for asynchronous message processing
- **Service Layer Pattern** - Business logic separated from data access
- **Repository Pattern** - Data access abstraction
- **Factory Pattern** - Route creation with dependency injection
- **Separation of Internal/Public** - Clear boundaries between public API and internal implementation

## Technology Stack

### Backend
- **FastAPI** - Modern Python web framework
- **Pydantic** - Data validation and settings management
- **Motor** - Async MongoDB driver
- **aio-pika** - Async RabbitMQ client
- **APScheduler** - Job scheduling

### Infrastructure
- **MongoDB** - Document database
- **RabbitMQ** - Message broker
- **Docker** - Containerization
- **Docker Compose** - Multi-container orchestration

---

**Version**: 1.0.0  
**Last Updated**: 2024
