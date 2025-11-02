"""
Repository layer for data access.
Implements Repository Pattern and follows Single Responsibility Principle.
"""

from .base_repository import BaseRepository
from .task_repository import TaskRepository

__all__ = [
    "BaseRepository",
    "TaskRepository",
]

