"""
Pydantic schemas for Task Management API.
"""

from pydantic import BaseModel, Field
from typing import Dict, List, Optional


class TaskCreateRequest(BaseModel):
    """Request model for task creation."""

    task_type: str = Field(..., description="Type of task")
    payload: Dict = Field(..., description="Task payload")
    priority: int = Field(default=0, ge=0, le=10, description="Task priority (0-10)")

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "task_type": "stt_transcription",
                    "payload": {
                        "filename": "audio.mp3",
                        "file_url": "https://minio.tantai.dev/audio/test.mp3",
                        "language": "vi",
                        "model": "medium",
                    },
                    "priority": 5,
                },
            ]
        }


class TaskResponse(BaseModel):
    """Response model for task."""

    status: str
    data: Optional[Dict] = None

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "status": "success",
                    "data": {
                        "id": "task_abc123xyz",
                        "task_type": "stt_transcription",
                        "status": "pending",
                        "priority": 5,
                        "created_at": "2025-10-30T10:30:00Z",
                    },
                }
            ]
        }


class TaskDetail(BaseModel):
    """Model for detailed task information."""

    id: str
    task_type: str
    status: str
    payload: Dict
    priority: int
    result: Optional[Dict] = None
    error: Optional[str] = None
    created_at: str
    updated_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class TaskStatistics(BaseModel):
    """Model for task statistics."""

    total_tasks: int
    pending: int
    processing: int
    completed: int
    failed: int
    by_type: Dict[str, int]
