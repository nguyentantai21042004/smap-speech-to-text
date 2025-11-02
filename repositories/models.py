"""
MongoDB document models using Pydantic.
Includes validation, logging, and error handling.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum

from core.logger import logger


class JobStatus(str, Enum):
    """Job status enumeration."""

    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ChunkModel(BaseModel):
    """Model for audio chunk."""

    chunk_index: int = Field(..., description="Index of the chunk in sequence")
    start_time: float = Field(..., description="Start time in seconds")
    end_time: float = Field(..., description="End time in seconds")
    file_path: Optional[str] = Field(None, description="Path to chunk audio file")
    transcription: Optional[str] = Field(None, description="Transcribed text")
    status: JobStatus = Field(
        default=JobStatus.PENDING, description="Chunk processing status"
    )
    error_message: Optional[str] = Field(None, description="Error message if failed")
    processed_at: Optional[datetime] = Field(
        None, description="When chunk was processed"
    )

    class Config:
        """Pydantic config."""

        json_encoders = {datetime: lambda v: v.isoformat() if v else None}


class JobModel(BaseModel):
    """Model for STT job (MongoDB document)."""

    # IDs
    job_id: str = Field(..., description="Unique job identifier")

    # Status
    status: JobStatus = Field(
        default=JobStatus.PENDING, description="Current job status"
    )
    language: str = Field(..., description="Language code (en, vi, etc.)")

    # File information (MinIO paths)
    original_filename: str = Field(..., description="Original uploaded filename")
    minio_audio_path: str = Field(..., description="Path to audio file in MinIO")
    minio_result_path: Optional[str] = Field(
        None, description="Path to result file in MinIO"
    )
    file_size_mb: float = Field(..., description="File size in MB")
    audio_duration_seconds: Optional[float] = Field(
        None, description="Audio duration in seconds"
    )

    # Processing information
    worker_id: Optional[str] = Field(
        None, description="ID of worker processing the job"
    )
    retry_count: int = Field(default=0, description="Number of retry attempts")
    chunks_total: Optional[int] = Field(None, description="Total number of chunks")
    chunks_completed: int = Field(default=0, description="Number of completed chunks")
    chunks: List[ChunkModel] = Field(
        default_factory=list, description="List of audio chunks"
    )

    # Results
    transcription_text: Optional[str] = Field(
        None, description="Final transcription result"
    )
    error_message: Optional[str] = Field(
        None, description="Error message if job failed"
    )

    # Metadata
    model_used: str = Field(default="medium", description="Whisper model used")
    chunk_strategy: str = Field(
        default="silence_based", description="Chunking strategy"
    )

    # Timestamps
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Job creation time"
    )
    started_at: Optional[datetime] = Field(None, description="Job start time")
    completed_at: Optional[datetime] = Field(None, description="Job completion time")
    updated_at: datetime = Field(
        default_factory=datetime.utcnow, description="Last update time"
    )

    class Config:
        """Pydantic config."""

        json_encoders = {datetime: lambda v: v.isoformat() if v else None}

    def to_dict(self) -> dict:
        """
        Convert to dictionary for MongoDB.

        Returns:
            Dictionary representation

        Raises:
            Exception: If conversion fails
        """
        try:
            data = self.dict()
            logger.debug(f"✅ Converted JobModel to dict: job_id={self.job_id}")
            return data

        except Exception as e:
            logger.error(f"❌ Failed to convert JobModel to dict: {e}")
            logger.exception("Model to dict conversion error:")
            raise

    @classmethod
    def from_dict(cls, data: dict) -> "JobModel":
        """
        Create from MongoDB document.

        Args:
            data: MongoDB document dictionary

        Returns:
            JobModel instance

        Raises:
            Exception: If creation fails
        """
        try:
            # Remove MongoDB _id field if present
            if "_id" in data:
                data.pop("_id")

            job = cls(**data)
            logger.debug(f"✅ Created JobModel from dict: job_id={job.job_id}")
            return job

        except Exception as e:
            logger.error(f"❌ Failed to create JobModel from dict: {e}")
            logger.exception("Model creation error:")
            raise


class JobCreate(BaseModel):
    """Model for creating a new job."""

    language: str = Field(default="vi", description="Language code")
    original_filename: str = Field(..., description="Original filename")
    minio_audio_path: str = Field(..., description="MinIO audio path")
    file_size_mb: float = Field(..., description="File size in MB")
    model_used: str = Field(default="medium", description="Whisper model to use")
    chunk_strategy: str = Field(
        default="silence_based", description="Chunking strategy"
    )


class JobUpdate(BaseModel):
    """Model for updating a job."""

    status: Optional[JobStatus] = None
    worker_id: Optional[str] = None
    chunks_total: Optional[int] = None
    chunks_completed: Optional[int] = None
    chunks: Optional[List[ChunkModel]] = None
    transcription_text: Optional[str] = None
    error_message: Optional[str] = None
    minio_result_path: Optional[str] = None
    audio_duration_seconds: Optional[float] = None
    retry_count: Optional[int] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# MongoDB collection names
JOBS_COLLECTION = "stt_jobs"

logger.info("✅ MongoDB models defined")
