"""
Repository for task management.
Follows Single Responsibility Principle - only handles task data access.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from .base_repository import BaseRepository
from .interfaces import ITaskRepository


class TaskRepository(BaseRepository, ITaskRepository):
    """Repository for managing background tasks."""

    def __init__(self):
        super().__init__("tasks")

    async def create_task(
        self,
        task_type: str,
        payload: Dict[str, Any],
        status: str = "pending",
        priority: int = 0,
    ) -> str:
        """
        Create a new task.
        
        Args:
            task_type: Type of task
            payload: Task payload
            status: Task status (pending, processing, completed, failed)
            priority: Task priority (higher = more important)
            
        Returns:
            ID of created task
        """
        document = {
            "task_type": task_type,
            "payload": payload,
            "status": status,
            "priority": priority,
            "result": None,
            "error": None,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "started_at": None,
            "completed_at": None,
        }
        return await self.create(document)

    async def update_task_status(
        self,
        task_id: str,
        status: str,
        result: Optional[Any] = None,
        error: Optional[str] = None,
    ) -> bool:
        """
        Update task status and result.
        
        Args:
            task_id: Task ID
            status: New status
            result: Task result if completed
            error: Error message if failed
            
        Returns:
            True if updated
        """
        update_data = {
            "status": status,
            "updated_at": datetime.utcnow(),
        }
        
        if status == "processing":
            update_data["started_at"] = datetime.utcnow()
        elif status in ["completed", "failed"]:
            update_data["completed_at"] = datetime.utcnow()
        
        if result is not None:
            update_data["result"] = result
        
        if error:
            update_data["error"] = error
        
        return await self.update_by_id(task_id, update_data)

    async def find_pending_tasks(
        self,
        limit: int = 10,
        task_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Find pending tasks ordered by priority.
        
        Args:
            limit: Maximum number of tasks
            task_type: Optional task type filter
            
        Returns:
            List of pending tasks
        """
        filter_dict = {"status": "pending"}
        if task_type:
            filter_dict["task_type"] = task_type
        
        return await self.find_many(
            filter_dict,
            limit=limit,
            sort=[("priority", -1), ("created_at", 1)],
        )

    async def find_tasks_by_status(
        self,
        status: str,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Find tasks by status.
        
        Args:
            status: Task status
            skip: Number of tasks to skip
            limit: Maximum number of tasks
            
        Returns:
            List of tasks
        """
        return await self.find_many(
            {"status": status},
            skip=skip,
            limit=limit,
            sort=[("created_at", -1)],
        )

    async def get_task_statistics(self) -> Dict[str, Any]:
        """
        Get task statistics.
        
        Returns:
            Statistics dictionary
        """
        pipeline = [
            {
                "$group": {
                    "_id": {
                        "status": "$status",
                        "task_type": "$task_type",
                    },
                    "count": {"$sum": 1},
                }
            }
        ]
        
        cursor = self.collection.aggregate(pipeline)
        results = await cursor.to_list(length=None)
        
        return {
            "total_tasks": await self.count(),
            "by_status_and_type": results,
        }

    async def cleanup_old_tasks(self, days: int = 30) -> int:
        """
        Delete completed tasks older than specified days.
        
        Args:
            days: Number of days to keep
            
        Returns:
            Number of tasks deleted
        """
        from datetime import timedelta
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        return await self.delete_many({
            "status": {"$in": ["completed", "failed"]},
            "completed_at": {"$lt": cutoff_date},
        })

    # Implement interface methods
    async def find_by_status(
        self,
        status: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Find tasks by status."""
        return await self.find_tasks_by_status(status, skip, limit)

    async def update_status(
        self,
        task_id: str,
        status: str,
        result: Optional[Any] = None,
        error: Optional[str] = None
    ) -> bool:
        """Update task status."""
        return await self.update_task_status(task_id, status, result, error)

    async def update(self, task_id: str, data: Dict[str, Any]) -> bool:
        """Update a task record."""
        return await self.update_by_id(task_id, data)

    async def delete(self, task_id: str) -> bool:
        """Delete a task."""
        return await self.delete_by_id(task_id)

    async def count_by_status(self) -> Dict[str, int]:
        """Count tasks by status."""
        pipeline = [
            {
                "$group": {
                    "_id": "$status",
                    "count": {"$sum": 1},
                }
            }
        ]
        
        cursor = self.collection.aggregate(pipeline)
        results = await cursor.to_list(length=None)
        
        return {item["_id"]: item["count"] for item in results}

    async def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about tasks (interface requirement)."""
        return await self.get_task_statistics()

