"""
Interface for Task Repository.
Defines the contract that all task repositories must implement.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from datetime import datetime


class ITaskRepository(ABC):
    """Interface for task repository operations."""

    @abstractmethod
    async def create(self, data: Dict) -> str:
        """
        Create a new task record.

        Args:
            data: Dictionary containing task data

        Returns:
            str: ID of created task
        """
        pass

    @abstractmethod
    async def find_by_id(self, task_id: str) -> Optional[Dict]:
        """
        Find a task by ID.

        Args:
            task_id: ID of the task

        Returns:
            Optional[Dict]: Task data if found, None otherwise
        """
        pass

    @abstractmethod
    async def find_by_status(
        self, status: str, skip: int = 0, limit: int = 100
    ) -> List[Dict]:
        """
        Find tasks by status with pagination.

        Args:
            status: Task status to filter by
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List[Dict]: List of tasks
        """
        pass

    @abstractmethod
    async def update_status(
        self,
        task_id: str,
        status: str,
        result: Optional[Dict] = None,
        error: Optional[str] = None,
    ) -> bool:
        """
        Update task status.

        Args:
            task_id: ID of the task
            status: New status
            result: Optional result data
            error: Optional error message

        Returns:
            bool: True if update successful, False otherwise
        """
        pass

    @abstractmethod
    async def update(self, task_id: str, data: Dict) -> bool:
        """
        Update a task record.

        Args:
            task_id: ID of the task
            data: Dictionary containing update data

        Returns:
            bool: True if update successful, False otherwise
        """
        pass

    @abstractmethod
    async def delete(self, task_id: str) -> bool:
        """
        Delete a task.

        Args:
            task_id: ID of the task

        Returns:
            bool: True if deletion successful, False otherwise
        """
        pass

    @abstractmethod
    async def get_statistics(self) -> Dict:
        """
        Get statistics about tasks.

        Returns:
            Dict: Statistics data including counts by status
        """
        pass

    @abstractmethod
    async def count_by_status(self) -> Dict[str, int]:
        """
        Count tasks by status.

        Returns:
            Dict[str, int]: Dictionary mapping status to count
        """
        pass

    @abstractmethod
    async def find_pending_tasks(self, limit: int = 100) -> List[Dict]:
        """
        Find pending tasks for processing.

        Args:
            limit: Maximum number of tasks to return

        Returns:
            List[Dict]: List of pending tasks
        """
        pass
