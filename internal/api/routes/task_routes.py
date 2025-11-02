"""
Task Management API Routes.
"""

from fastapi import APIRouter, HTTPException, Query, status
from typing import Dict, List

from internal.api.schemas import (
    TaskCreateRequest,
    TaskResponse,
)
from services.interfaces import ITaskService
from core import logger


router = APIRouter(prefix="/api/v1/tasks", tags=["Tasks"])


def create_task_routes(task_service: ITaskService) -> APIRouter:
    """
    Factory function to create task routes with dependency injection.

    Args:
        task_service: Implementation of ITaskService

    Returns:
        APIRouter: Configured router with all task endpoints
    """

    @router.post(
        "",
        response_model=TaskResponse,
        status_code=status.HTTP_201_CREATED,
        summary="Create Task",
        description="Create a new asynchronous task for background processing",
        responses={
            201: {
                "description": "Task created successfully",
                "content": {
                    "application/json": {
                        "example": {
                            "id": "task_789xyz",
                            "task_type": "keyword_extraction",
                            "status": "pending",
                            "priority": 5,
                            "created_at": "2025-10-30T10:30:00Z",
                        }
                    }
                },
            },
            500: {"description": "Internal server error"},
        },
    )
    async def create_task(request: TaskCreateRequest):
        """
        Create a new asynchronous task.

        Submit a background job for asynchronous processing. The task will be
        queued and processed by worker services.

        **Parameters:**
        - **task_type**: Type of task to execute (e.g., "keyword_extraction")
        - **payload**: Task-specific data and parameters
        - **priority**: Task priority (0-10, higher = more important)

        **Returns:**
        Task object with unique ID and initial status "pending".
        Use the task ID to check status and retrieve results.
        """
        try:
            result = await task_service.create_task(
                task_type=request.task_type,
                payload=request.payload,
                priority=request.priority,
            )
            return TaskResponse(**result)
        except Exception as e:
            logger.error(f"Error creating task: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error creating task: {str(e)}",
            )

    @router.get(
        "/{task_id}",
        response_model=Dict,
        summary="Get Task",
        description="Retrieve task details and status by ID",
        responses={
            200: {
                "description": "Task found",
                "content": {
                    "application/json": {
                        "example": {
                            "id": "task_789xyz",
                            "task_type": "keyword_extraction",
                            "status": "completed",
                            "result": {"keywords": ["python", "fastapi"]},
                            "created_at": "2025-10-30T10:30:00Z",
                            "completed_at": "2025-10-30T10:30:15Z",
                        }
                    }
                },
            },
            404: {"description": "Task not found"},
            500: {"description": "Internal server error"},
        },
    )
    async def get_task(task_id: str):
        """
        Get task details by ID.

        Retrieve complete information about a task including its current status,
        results (if completed), and timing information.

        **Parameters:**
        - **task_id**: Unique task identifier

        **Returns:**
        Task object with status, result, and metadata.

        **Task Status Values:**
        - `pending`: Waiting in queue
        - `processing`: Currently being processed
        - `completed`: Successfully finished
        - `failed`: Processing failed (check error field)
        """
        try:
            task = await task_service.get_task(task_id)
            if not task:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Task {task_id} not found",
                )
            return task
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting task: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error getting task: {str(e)}",
            )

    @router.get(
        "",
        response_model=List[Dict],
        summary="List Tasks",
        description="Retrieve tasks filtered by status with pagination",
        responses={
            200: {"description": "List of tasks"},
            500: {"description": "Internal server error"},
        },
    )
    async def get_tasks(
        status: str = Query(
            default="pending",
            description="Filter by task status (pending/processing/completed/failed)",
        ),
        skip: int = Query(
            default=0, ge=0, description="Number of tasks to skip (pagination)"
        ),
        limit: int = Query(
            default=100, ge=1, le=1000, description="Maximum number of tasks to return"
        ),
    ):
        """
        Get tasks filtered by status.

        Retrieve a paginated list of tasks matching the specified status.
        Useful for monitoring pending work, checking completed jobs, or
        investigating failures.

        **Query Parameters:**
        - **status**: Filter by status (pending/processing/completed/failed)
        - **skip**: Pagination offset (default: 0)
        - **limit**: Maximum results (1-1000, default: 100)

        **Returns:**
        Array of task objects sorted by creation time.
        """
        try:
            return await task_service.get_tasks_by_status(status, skip, limit)
        except Exception as e:
            logger.error(f"Error getting tasks: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error getting tasks: {str(e)}",
            )

    @router.get(
        "/stats/summary",
        response_model=Dict,
        summary="Get Task Statistics",
        description="Retrieve aggregate statistics about task processing",
        responses={
            200: {
                "description": "Statistics retrieved successfully",
                "content": {
                    "application/json": {
                        "example": {
                            "total_tasks": 5420,
                            "by_status": {
                                "pending": 45,
                                "processing": 12,
                                "completed": 5310,
                                "failed": 53,
                            },
                            "success_rate": 0.99,
                            "average_processing_time": 3.45,
                        }
                    }
                },
            },
            500: {"description": "Internal server error"},
        },
    )
    async def get_task_statistics():
        """
        Get task processing statistics.

        Provides aggregate metrics about task execution including:
        - Total number of tasks
        - Distribution by status
        - Success/failure rates
        - Average processing times

        **Returns:**
        Statistics object with various task-related metrics.
        """
        try:
            return await task_service.get_statistics()
        except Exception as e:
            logger.error(f"Error getting task statistics: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error getting statistics: {str(e)}",
            )

    return router
