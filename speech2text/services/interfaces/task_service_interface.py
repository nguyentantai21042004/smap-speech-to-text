"""
Interface for Task Service.
Defines the contract that all task services must implement.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional


class ITaskService(ABC):
    """Interface for task service operations."""

    @abstractmethod
    async def create_task(
        self, task_type: str, payload: Dict, priority: int = 0
    ) -> Dict:
        """
        Create a new task.

        Args:
            task_type: Type of task
            payload: Task payload data
            priority: Task priority (higher = more important)

        Returns:
            Dict: Created task information
        """
        pass

    @abstractmethod
    async def get_task(self, task_id: str) -> Optional[Dict]:
        """
        Get task by ID.

        Args:
            task_id: ID of the task

        Returns:
            Optional[Dict]: Task data if found, None otherwise
        """
        pass

    @abstractmethod
    async def get_tasks_by_status(
        self, status: str, skip: int = 0, limit: int = 100
    ) -> List[Dict]:
        """
        Get tasks by status with pagination.

        Args:
            status: Task status to filter by
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List[Dict]: List of tasks
        """
        pass

    @abstractmethod
    async def update_task_status(
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
    async def get_statistics(self) -> Dict:
        """
        Get task statistics.

        Returns:
            Dict: Statistics data including counts by status
        """
        pass

    @abstractmethod
    async def get_pending_tasks(self, limit: int = 100) -> List[Dict]:
        """
        Get pending tasks for processing.

        Args:
            limit: Maximum number of tasks to return

        Returns:
            List[Dict]: List of pending tasks
        """
        pass
