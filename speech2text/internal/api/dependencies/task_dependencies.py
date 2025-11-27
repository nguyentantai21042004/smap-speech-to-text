"""
Task Dependencies.
"""

from fastapi import Depends
from services.task_use_case import ITaskUseCase, TaskUseCase
from adapters.mongo.task_repository import MongoTaskRepository
from adapters.minio.storage import MinioStorageAdapter
from adapters.rabbitmq.messaging import RabbitMQAdapter


def get_task_use_case() -> ITaskUseCase:
    """Get Task Use Case instance."""
    from core.container import Container
    from ports.repository import TaskRepositoryPort
    from ports.storage import StoragePort
    from ports.messaging import MessagingPort

    repo = Container.resolve(TaskRepositoryPort)
    storage = Container.resolve(StoragePort)
    messaging = Container.resolve(MessagingPort)

    return TaskUseCase(repo, storage, messaging)
