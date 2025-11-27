"""
Task Use Case.
"""

from abc import ABC, abstractmethod
from typing import Optional, BinaryIO, List, Dict
import uuid
from pathlib import Path

from domain.entities import Job, JobStatus
from ports.repository import TaskRepositoryPort
from ports.storage import StoragePort
from ports.messaging import MessagingPort
from core.logger import logger


class ITaskUseCase(ABC):
    """Interface for Task Use Case."""

    @abstractmethod
    async def create_stt_task(
        self,
        audio_file: BinaryIO,
        filename: str,
        file_size_mb: float,
        language: str = "vi",
        model: str = "medium",
    ) -> Job:
        pass

    @abstractmethod
    async def create_job_from_existing_file(
        self,
        filename: str,
        minio_path: str,
        file_size_mb: float,
        language: str = "vi",
        model: str = "medium",
    ) -> Job:
        pass

    @abstractmethod
    async def get_task_status(self, job_id: str) -> Optional[Job]:
        pass

    @abstractmethod
    async def get_task_result(self, job_id: str) -> Optional[Dict]:
        pass

    @abstractmethod
    async def list_tasks(
        self, limit: int = 10, status: Optional[str] = None
    ) -> List[Job]:
        pass


class TaskUseCase(ITaskUseCase):
    """
    Application Use Case for managing STT Tasks.
    """

    def __init__(
        self,
        repository: TaskRepositoryPort,
        storage: StoragePort,
        messaging: MessagingPort,
    ):
        self.repository = repository
        self.storage = storage
        self.messaging = messaging

    async def create_stt_task(
        self,
        audio_file: BinaryIO,
        filename: str,
        file_size_mb: float,
        language: str = "vi",
        model: str = "medium",
    ) -> Job:
        logger.info(f"Creating STT task: filename={filename}, size={file_size_mb}MB")

        # 1. Upload to Storage
        job_id_for_object_name = str(
            uuid.uuid4()
        )  # This ID is for the object name, not the job itself
        file_ext = Path(filename).suffix
        object_name = f"uploads/{job_id_for_object_name}{file_ext}"

        minio_path = await self.storage.upload_file(
            file_data=audio_file,
            object_name=object_name,
            content_type="audio/mpeg",  # Simplified
        )

        return await self.create_job_from_existing_file(
            filename=filename,
            minio_path=minio_path,
            file_size_mb=file_size_mb,
            language=language,
            model=model,
        )

    async def create_job_from_existing_file(
        self,
        filename: str,
        minio_path: str,
        file_size_mb: float,
        language: str = "vi",
        model: str = "medium",
    ) -> Job:
        logger.info(f"Creating Job from existing file: {filename}")

        # Create Job Entity
        job = Job(
            id=str(uuid.uuid4()),  # A new UUID for the job entity
            original_filename=filename,
            minio_audio_path=minio_path,
            file_size_mb=file_size_mb,
            language=language,
            model_used=model,
        )

        # Save to Repository
        saved_job = await self.repository.create_job(job)

        # Publish to Queue
        await self.messaging.publish(
            queue_name="stt_tasks",
            message={
                "job_id": saved_job.id,
                "language": language,
                "model": model,
                "filename": filename,
            },
        )

        return saved_job

    async def get_task_status(self, job_id: str) -> Optional[Job]:
        return await self.repository.get_job(job_id)

    async def get_task_result(self, job_id: str) -> Optional[Dict]:
        job = await self.repository.get_job(job_id)
        if not job:
            return None

        download_url = None
        if job.status == JobStatus.COMPLETED and job.minio_result_path:
            download_url = await self.storage.get_file_url(job.minio_result_path)

        return {"job": job, "download_url": download_url}

    async def list_tasks(
        self, limit: int = 10, status: Optional[str] = None
    ) -> List[Job]:
        return await self.repository.list_jobs(limit=limit, status=status)
