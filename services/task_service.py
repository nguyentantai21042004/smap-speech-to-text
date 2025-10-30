"""
Service for task management business logic.
Implements Service Layer Pattern - orchestrates task processing.
Follows Single Responsibility Principle - only handles task business logic.
"""

from typing import Any, Dict, List, Optional

from core import MessageBroker, logger
from repositories import TaskRepository
from .interfaces import ITaskService


class TaskService(ITaskService):
    """
    Service handling task management business logic.
    Coordinates between task repository and message broker.
    """

    def __init__(self):
        self.repository = TaskRepository()
        self.message_broker = MessageBroker()

    async def create_task(
        self,
        task_type: str,
        payload: Dict[str, Any],
        priority: int = 0,
        publish_to_queue: bool = True,
    ) -> Dict[str, Any]:
        """
        Create a new task.
        
        Args:
            task_type: Type of task
            payload: Task payload
            priority: Task priority
            publish_to_queue: Whether to publish to message queue
            
        Returns:
            Created task information
        """
        try:
            # Create task in database
            task_id = await self.repository.create_task(
                task_type=task_type,
                payload=payload,
                priority=priority,
            )
            
            # Publish to queue if requested
            if publish_to_queue:
                message = {
                    "type": "task",
                    "task_id": task_id,
                    "task_type": task_type,
                    "payload": payload,
                }
                await self.message_broker.publish(message)
                logger.info(f"Published task {task_id} to queue")
            
            task = await self.repository.find_by_id(task_id)
            
            return {
                "status": "created",
                "data": task,
            }
        except Exception as e:
            logger.error(f"Error in create_task: {e}")
            raise

    async def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get task by ID.
        
        Args:
            task_id: Task ID
            
        Returns:
            Task if found
        """
        try:
            task = await self.repository.find_by_id(task_id)
            return task
        except Exception as e:
            logger.error(f"Error in get_task: {e}")
            raise

    async def update_task_status(
        self,
        task_id: str,
        status: str,
        result: Optional[Any] = None,
        error: Optional[str] = None,
    ) -> bool:
        """
        Update task status.
        
        Args:
            task_id: Task ID
            status: New status
            result: Task result
            error: Error message if failed
            
        Returns:
            True if updated
        """
        try:
            updated = await self.repository.update_task_status(
                task_id, status, result, error
            )
            
            if updated:
                logger.info(f"Updated task {task_id} status to {status}")
            
            return updated
        except Exception as e:
            logger.error(f"Error in update_task_status: {e}")
            raise

    async def get_pending_tasks(
        self,
        limit: int = 10,
        task_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get pending tasks.
        
        Args:
            limit: Maximum number of tasks
            task_type: Optional task type filter
            
        Returns:
            List of pending tasks
        """
        try:
            tasks = await self.repository.find_pending_tasks(limit, task_type)
            return tasks
        except Exception as e:
            logger.error(f"Error in get_pending_tasks: {e}")
            raise

    async def get_tasks_by_status(
        self,
        status: str,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Get tasks by status.
        
        Args:
            status: Task status
            skip: Number of tasks to skip
            limit: Maximum number of tasks
            
        Returns:
            List of tasks
        """
        try:
            tasks = await self.repository.find_tasks_by_status(status, skip, limit)
            return tasks
        except Exception as e:
            logger.error(f"Error in get_tasks_by_status: {e}")
            raise

    async def get_statistics(self) -> Dict[str, Any]:
        """
        Get task statistics.
        
        Returns:
            Statistics dictionary
        """
        try:
            stats = await self.repository.get_task_statistics()
            return stats
        except Exception as e:
            logger.error(f"Error in get_statistics: {e}")
            raise

    async def cleanup_old_tasks(self, days: int = 30) -> Dict[str, Any]:
        """
        Cleanup old completed/failed tasks.
        
        Args:
            days: Number of days to keep
            
        Returns:
            Cleanup result
        """
        try:
            deleted_count = await self.repository.cleanup_old_tasks(days)
            
            logger.info(f"Cleaned up {deleted_count} old tasks")
            
            return {
                "status": "success",
                "deleted_count": deleted_count,
            }
        except Exception as e:
            logger.error(f"Error in cleanup_old_tasks: {e}")
            raise

    async def process_task(self, task_data: Dict[str, Any]) -> None:
        """
        Process a task received from the queue.
        This method is called by the queue consumer.
        
        Args:
            task_data: Task data from queue
        """
        task_id = task_data.get("task_id")
        task_type = task_data.get("task_type")
        payload = task_data.get("payload", {})
        
        try:
            logger.info(f"Processing task {task_id} of type {task_type}")
            
            # Update status to processing
            await self.update_task_status(task_id, "processing")
            
            # Process based on task type
            result = await self._execute_task(task_type, payload)
            
            # Update status to completed
            await self.update_task_status(task_id, "completed", result=result)
            
            logger.info(f"Completed task {task_id}")
        except Exception as e:
            logger.error(f"Failed to process task {task_id}: {e}")
            await self.update_task_status(task_id, "failed", error=str(e))

    async def _execute_task(
        self,
        task_type: str,
        payload: Dict[str, Any],
    ) -> Any:
        """
        Execute task based on type.
        
        Args:
            task_type: Type of task
            payload: Task payload
            
        Returns:
            Task result
        """
        # Implement task execution logic based on task_type
        # This is a placeholder
        
        if task_type == "keyword_extraction":
            # Handle keyword extraction task
            text = payload.get("text", "")
            method = payload.get("method", "default")
            num_keywords = payload.get("num_keywords", 10)
            
            # Import here to avoid circular dependency
            from services.keyword_service import KeywordService
            
            keyword_service = KeywordService()
            result = await keyword_service.extract_keywords_sync(
                text, method, num_keywords
            )
            return result
        
        # Default: return payload
        return {"processed": True, "payload": payload}

