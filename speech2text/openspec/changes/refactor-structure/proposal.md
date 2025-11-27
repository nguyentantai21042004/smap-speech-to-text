# Refactor Structure to Clean Architecture

## Summary
Refactor the Speech-to-Text system to follow Clean Architecture principles, decoupling the domain from infrastructure, separating API and Worker responsibilities clearly, and introducing a Dependency Injection container. This prepares the system for future scalability (multi-pipeline, streaming).

## Motivation
The current architecture has tight coupling between the worker domain and repositories/core factories, making testing difficult (singleton getters). New features (like diarization) lack a standard module structure.
**Goals:**
- Standardize on Clean Architecture to make the domain independent of infrastructure.
- Improve testability via interfaces and dependency injection.
- Prepare for multi-pipeline support (STT, summarization, diarization).

## Proposed Solution
The refactor will be executed in phases:
- **Phase 0 – Foundations**: Introduce a DI container and the Domain layer (Entities, Value Objects, Events).
- **Phase 1 – Application Layer**: Refactor Services into Use Cases and update Routers to use DI.
- **Phase 2 – Infrastructure Adapters**: Split repositories into Ports and Adapters (Mongo, MinIO, RabbitMQ).
- **Phase 3 – Worker Modularity**: Restructure the worker into pipelines (STT, etc.) with a generic base.
- **Phase 4 – Cross-cutting**: Add contract tests and update documentation.
