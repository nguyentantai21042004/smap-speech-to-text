"""
Domain entities for Speech-to-Text system.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from enum import Enum


class JobStatus(str, Enum):
    """Job status enumeration."""

    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass
class Chunk:
    """Audio chunk entity."""

    index: int
    start_time: float
    end_time: float
    file_path: Optional[str] = None
    transcription: Optional[str] = None
    status: JobStatus = JobStatus.PENDING
    error_message: Optional[str] = None
    processed_at: Optional[datetime] = None


@dataclass
class Job:
    """STT Job entity."""

    id: str
    original_filename: str
    minio_audio_path: str
    file_size_mb: float
    language: str = "vi"
    status: JobStatus = JobStatus.PENDING

    # Processing details
    worker_id: Optional[str] = None
    retry_count: int = 0
    chunks: List[Chunk] = field(default_factory=list)
    chunks_total: Optional[int] = None
    chunks_completed: int = 0

    # Results
    transcription_text: Optional[str] = None
    minio_result_path: Optional[str] = None
    audio_duration_seconds: Optional[float] = None
    error_message: Optional[str] = None

    # Metadata
    model_used: str = "medium"
    chunk_strategy: str = "silence_based"

    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def add_chunk(self, chunk: Chunk):
        """Add a chunk to the job."""
        self.chunks.append(chunk)
        if self.chunks_total is not None:
            self.chunks_total = len(self.chunks)

    def update_progress(self, chunks_completed: int):
        """Update progress."""
        self.chunks_completed = chunks_completed
        self.updated_at = datetime.utcnow()

    def complete(self, transcription: str, result_path: str):
        """Mark job as completed."""
        self.status = JobStatus.COMPLETED
        self.transcription_text = transcription
        self.minio_result_path = result_path
        self.completed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def fail(self, error: str):
        """Mark job as failed."""
        self.status = JobStatus.FAILED
        self.error_message = error
        self.completed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
