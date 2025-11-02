"""
Task service for STT job management.
Includes comprehensive logging and error handling.
"""
from typing import Optional, BinaryIO
import uuid
from pathlib import Path

from core.logger import logger
from core.storage import get_minio_client
from core.messaging import get_queue_manager
from repositories.task_repository import get_task_repository
from repositories.models import JobCreate, JobModel
from worker.processor import process_stt_job


class TaskService:
    """Service for managing STT tasks with detailed logging."""

    def __init__(self):
        """Initialize task service."""
        logger.debug("TaskService initialized")

    async def create_stt_task(
        self,
        audio_file: BinaryIO,
        filename: str,
        file_size_mb: float,
        language: str = "vi",
        model: str = "medium"
    ) -> dict:
        """
        Create a new STT task.

        Args:
            audio_file: Audio file data
            filename: Original filename
            file_size_mb: File size in MB
            language: Language code
            model: Whisper model to use

        Returns:
            Task information dictionary

        Raises:
            Exception: If task creation fails
        """
        try:
            logger.info(f"Creating STT task: filename={filename}, size={file_size_mb:.2f}MB, language={language}")

            # Validate file size
            if file_size_mb > 500:
                error_msg = f"File too large: {file_size_mb:.2f}MB (max 500MB)"
                logger.error(f"❌ {error_msg}")
                raise ValueError(error_msg)

            # Generate job ID
            job_id = str(uuid.uuid4())
            logger.debug(f"Generated job_id: {job_id}")

            # Upload to MinIO
            logger.info(f"Uploading audio to MinIO...")
            minio_path = await self._upload_to_minio(audio_file, filename, job_id)
            logger.info(f"Audio uploaded: {minio_path}")

            # Create job in database
            logger.info(f"Creating job in database...")
            repo = get_task_repository()
            job_data = JobCreate(
                language=language,
                original_filename=filename,
                minio_audio_path=minio_path,
                file_size_mb=file_size_mb,
                model_used=model,
                chunk_strategy="silence_based"
            )

            job = await repo.create_job(job_data)
            logger.info(f"Job created in database: job_id={job.job_id}")

            # Publish job to RabbitMQ queue
            logger.info(f"Publishing job to RabbitMQ queue...")
            queue_manager = get_queue_manager()

            # Publish the job to RabbitMQ
            await queue_manager.publish_job(
                job_id=job.job_id,
                job_data={
                    "language": language,
                    "model": model,
                    "filename": filename
                },
                priority=5  # Normal priority (0-10 scale)
            )
            logger.info(f"Job published to RabbitMQ: job_id={job.job_id}")

            logger.info(f"STT task created successfully: job_id={job.job_id}")

            return {
                "status": "success",
                "job_id": job.job_id,
                "message": "Task created and queued for processing",
                "details": {
                    "filename": filename,
                    "size_mb": file_size_mb,
                    "language": language,
                    "model": model,
                    "minio_path": minio_path
                }
            }

        except ValueError as e:
            logger.error(f"❌ Validation error: {e}")
            raise

        except Exception as e:
            logger.error(f"❌ Failed to create STT task: {e}")
            logger.exception("Task creation error details:")
            raise

    async def _upload_to_minio(
        self,
        file_data: BinaryIO,
        filename: str,
        job_id: str
    ) -> str:
        """
        Upload audio file to MinIO.

        Args:
            file_data: File data
            filename: Original filename
            job_id: Job ID

        Returns:
            MinIO object path

        Raises:
            Exception: If upload fails
        """
        try:
            logger.debug(f"🔍 Uploading to MinIO: filename={filename}, job_id={job_id}")

            # Create MinIO path
            file_extension = Path(filename).suffix
            minio_filename = f"{job_id}{file_extension}"
            minio_path = f"uploads/{minio_filename}"

            # Get MinIO client
            minio_client = get_minio_client()

            # Upload file
            minio_client.upload_file(
                file_data=file_data,
                object_name=minio_path,
                content_type="audio/mpeg"
            )

            logger.debug(f"File uploaded to MinIO: {minio_path}")

            return minio_path

        except Exception as e:
            logger.error(f"❌ MinIO upload failed: {e}")
            logger.exception("MinIO upload error details:")
            raise

    async def get_task_status(self, job_id: str) -> Optional[dict]:
        """
        Get task status.

        Args:
            job_id: Job ID

        Returns:
            Task status dictionary or None if not found

        Raises:
            Exception: If status retrieval fails
        """
        try:
            logger.info(f"Getting task status: job_id={job_id}")

            # Get job from database
            repo = get_task_repository()
            job = await repo.get_job(job_id)

            if not job:
                logger.warning(f"⚠️ Job not found: job_id={job_id}")
                return None

            logger.info(f"Job status retrieved: job_id={job_id}, status={job.status}")

            # Calculate progress
            progress = 0
            if job.chunks_total and job.chunks_total > 0:
                progress = (job.chunks_completed / job.chunks_total) * 100

            return {
                "job_id": job.job_id,
                "status": job.status.value,
                "filename": job.original_filename,
                "language": job.language,
                "model": job.model_used,
                "progress": round(progress, 2),
                "chunks_total": job.chunks_total,
                "chunks_completed": job.chunks_completed,
                "error_message": job.error_message,
                "created_at": job.created_at.isoformat(),
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            }

        except Exception as e:
            logger.error(f"❌ Failed to get task status for {job_id}: {e}")
            logger.exception("Status retrieval error details:")
            raise

    async def get_task_result(self, job_id: str) -> Optional[dict]:
        """
        Get task result.

        Args:
            job_id: Job ID

        Returns:
            Task result dictionary or None if not found

        Raises:
            Exception: If result retrieval fails
        """
        try:
            logger.info(f"Getting task result: job_id={job_id}")

            # Get job from database
            repo = get_task_repository()
            job = await repo.get_job(job_id)

            if not job:
                logger.warning(f"⚠️ Job not found: job_id={job_id}")
                return None

            if job.status.value != "COMPLETED":
                logger.warning(f"⚠️ Job not completed: job_id={job_id}, status={job.status}")
                return {
                    "job_id": job_id,
                    "status": job.status.value,
                    "message": "Job not yet completed",
                    "transcription": None
                }

            logger.info(f"Job result retrieved: job_id={job_id}, text_length={len(job.transcription_text or '')}")

            # Generate presigned URL if result file exists
            download_url = None
            if job.minio_result_path:
                try:
                    minio_client = get_minio_client()
                    download_url = minio_client.generate_presigned_url(
                        job.minio_result_path,
                        expiry_seconds=3600  # 1 hour
                    )
                    logger.debug(f"Generated download URL for result file")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to generate download URL: {e}")

            return {
                "job_id": job.job_id,
                "status": job.status.value,
                "filename": job.original_filename,
                "language": job.language,
                "transcription": job.transcription_text,
                "download_url": download_url,
                "duration_seconds": job.audio_duration_seconds,
                "processing_time_seconds": (
                    (job.completed_at - job.started_at).total_seconds()
                    if job.started_at and job.completed_at
                    else None
                ),
                "created_at": job.created_at.isoformat(),
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            }

        except Exception as e:
            logger.error(f"❌ Failed to get task result for {job_id}: {e}")
            logger.exception("Result retrieval error details:")
            raise

    async def list_tasks(self, limit: int = 10, status: Optional[str] = None) -> list:
        """
        List tasks.

        Args:
            limit: Maximum number of tasks to return
            status: Filter by status (optional)

        Returns:
            List of task dictionaries

        Raises:
            Exception: If listing fails
        """
        try:
            logger.info(f"Listing tasks: limit={limit}, status={status}")

            repo = get_task_repository()

            if status:
                from repositories.models import JobStatus
                jobs = await repo.get_jobs_by_status(JobStatus(status), limit)
            else:
                # Get all recent jobs (you may want to add this method to repo)
                jobs = []

            logger.info(f"Retrieved {len(jobs)} tasks")

            return [
                {
                    "job_id": job.job_id,
                    "filename": job.original_filename,
                    "status": job.status.value,
                    "language": job.language,
                    "created_at": job.created_at.isoformat(),
                    "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                }
                for job in jobs
            ]

        except Exception as e:
            logger.error(f"❌ Failed to list tasks: {e}")
            logger.exception("Task listing error details:")
            raise


# Singleton instance
_task_service: Optional[TaskService] = None


def get_task_service() -> TaskService:
    """
    Get task service instance (singleton).

    Returns:
        TaskService instance
    """
    global _task_service

    try:
        if _task_service is None:
            logger.debug("Creating new TaskService instance")
            _task_service = TaskService()

        return _task_service

    except Exception as e:
        logger.error(f"❌ Failed to get task service: {e}")
        logger.exception("Task service initialization error:")
        raise
