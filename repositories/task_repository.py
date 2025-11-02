"""
Task repository for MongoDB operations.
Includes comprehensive logging and error handling for all CRUD operations.
"""

from typing import Optional, List
from datetime import datetime
import uuid

from core.database import get_database
from repositories.models import (
    JobModel,
    JobCreate,
    JobUpdate,
    JobStatus,
    JOBS_COLLECTION,
)
from core.logger import logger


class TaskRepository:
    """Repository for STT job database operations with detailed logging."""

    def __init__(self):
        """Initialize task repository."""
        self.collection_name = JOBS_COLLECTION
        logger.debug(
            f"TaskRepository initialized for collection: {self.collection_name}"
        )

    async def create_job(self, job_data: JobCreate) -> JobModel:
        """
        Create a new STT job.

        Args:
            job_data: Job creation data

        Returns:
            Created JobModel

        Raises:
            Exception: If job creation fails
        """
        try:
            logger.info(f"📝 Creating new job: filename={job_data.original_filename}")
            logger.debug(f"Job data: {job_data.dict()}")

            # Generate unique job ID
            job_id = str(uuid.uuid4())
            logger.debug(f"Generated job_id: {job_id}")

            # Create job model
            job = JobModel(job_id=job_id, **job_data.dict())

            # Get database collection
            db = await get_database()
            collection = await db.get_collection(self.collection_name)

            # Insert into MongoDB
            result = await collection.insert_one(job.to_dict())

            logger.info(
                f"✅ Job created successfully: job_id={job_id}, mongo_id={result.inserted_id}"
            )
            logger.debug(
                f"Job details: status={job.status}, language={job.language}, size={job.file_size_mb}MB"
            )

            return job

        except Exception as e:
            logger.error(f"❌ Failed to create job: {e}")
            logger.exception("Job creation error details:")
            raise

    async def get_job(self, job_id: str) -> Optional[JobModel]:
        """
        Get job by ID.

        Args:
            job_id: Job identifier

        Returns:
            JobModel or None if not found

        Raises:
            Exception: If database query fails
        """
        try:
            logger.debug(f"🔍 Fetching job: job_id={job_id}")

            # Get database collection
            db = await get_database()
            collection = await db.get_collection(self.collection_name)

            # Find job by job_id
            doc = await collection.find_one({"job_id": job_id})

            if doc:
                job = JobModel.from_dict(doc)
                logger.info(f"✅ Job found: job_id={job_id}, status={job.status}")
                logger.debug(
                    f"Job details: created_at={job.created_at}, chunks={job.chunks_total}"
                )
                return job
            else:
                logger.warning(f"⚠️ Job not found: job_id={job_id}")
                return None

        except Exception as e:
            logger.error(f"❌ Failed to get job {job_id}: {e}")
            logger.exception("Get job error details:")
            raise

    async def update_job(self, job_id: str, update_data: JobUpdate) -> bool:
        """
        Update job.

        Args:
            job_id: Job identifier
            update_data: Update data

        Returns:
            True if updated, False if not found

        Raises:
            Exception: If update fails
        """
        try:
            logger.info(f"📝 Updating job: job_id={job_id}")
            update_dict = update_data.dict(exclude_unset=True)
            logger.debug(f"Update data: {update_dict}")

            # Get database collection
            db = await get_database()
            collection = await db.get_collection(self.collection_name)

            # Build update document
            update_dict = {k: v for k, v in update_dict.items() if v is not None}
            update_dict["updated_at"] = datetime.utcnow()

            logger.debug(f"Final update document: {update_dict}")

            # Update in MongoDB
            result = await collection.update_one(
                {"job_id": job_id}, {"$set": update_dict}
            )

            if result.modified_count > 0:
                logger.info(
                    f"✅ Job updated: job_id={job_id}, modified_count={result.modified_count}"
                )
                return True
            elif result.matched_count > 0:
                logger.info(
                    f"⚠️ Job matched but not modified (no changes): job_id={job_id}"
                )
                return True
            else:
                logger.warning(f"⚠️ Job not found for update: job_id={job_id}")
                return False

        except Exception as e:
            logger.error(f"❌ Failed to update job {job_id}: {e}")
            logger.exception("Update job error details:")
            raise

    async def update_status(
        self, job_id: str, status: JobStatus, error_message: Optional[str] = None
    ) -> bool:
        """
        Update job status.

        Args:
            job_id: Job identifier
            status: New status
            error_message: Optional error message

        Returns:
            True if updated

        Raises:
            Exception: If status update fails
        """
        try:
            logger.info(f"📝 Updating job status: job_id={job_id}, status={status}")

            update_data = JobUpdate(status=status, error_message=error_message)

            # Set timestamps based on status
            if status == JobStatus.PROCESSING:
                update_data.started_at = datetime.utcnow()
                logger.debug(f"Setting started_at for job {job_id}")
            elif status in [JobStatus.COMPLETED, JobStatus.FAILED]:
                update_data.completed_at = datetime.utcnow()
                logger.debug(f"Setting completed_at for job {job_id}")

            result = await self.update_job(job_id, update_data)

            if result:
                logger.info(f"✅ Status updated: job_id={job_id}, new_status={status}")
            else:
                logger.warning(f"⚠️ Status update failed: job_id={job_id}")

            return result

        except Exception as e:
            logger.error(f"❌ Failed to update status for job {job_id}: {e}")
            logger.exception("Status update error details:")
            raise

    async def get_pending_jobs(self, limit: int = 10) -> List[JobModel]:
        """
        Get pending jobs ordered by creation time.

        Args:
            limit: Maximum number of jobs to return

        Returns:
            List of pending jobs

        Raises:
            Exception: If query fails
        """
        try:
            logger.debug(f"🔍 Fetching pending jobs (limit={limit})")

            # Get database collection
            db = await get_database()
            collection = await db.get_collection(self.collection_name)

            # Query pending jobs
            cursor = (
                collection.find({"status": JobStatus.PENDING})
                .sort("created_at", 1)
                .limit(limit)
            )

            jobs = []
            async for doc in cursor:
                try:
                    job = JobModel.from_dict(doc)
                    jobs.append(job)
                except Exception as e:
                    logger.error(f"❌ Failed to parse job document: {e}")
                    logger.exception("Job parsing error:")
                    # Continue with other jobs
                    continue

            logger.info(f"✅ Found {len(jobs)} pending jobs")
            if jobs:
                logger.debug(f"Pending job IDs: {[job.job_id for job in jobs]}")

            return jobs

        except Exception as e:
            logger.error(f"❌ Failed to get pending jobs: {e}")
            logger.exception("Pending jobs query error details:")
            raise

    async def get_jobs_by_status(
        self, status: JobStatus, limit: int = 100
    ) -> List[JobModel]:
        """
        Get jobs by status.

        Args:
            status: Job status to filter by
            limit: Maximum number of jobs to return

        Returns:
            List of jobs with specified status

        Raises:
            Exception: If query fails
        """
        try:
            logger.debug(f"🔍 Fetching jobs by status: status={status}, limit={limit}")

            # Get database collection
            db = await get_database()
            collection = await db.get_collection(self.collection_name)

            # Query jobs by status
            cursor = (
                collection.find({"status": status}).sort("created_at", -1).limit(limit)
            )

            jobs = []
            async for doc in cursor:
                try:
                    job = JobModel.from_dict(doc)
                    jobs.append(job)
                except Exception as e:
                    logger.error(f"❌ Failed to parse job document: {e}")
                    continue

            logger.info(f"✅ Found {len(jobs)} jobs with status {status}")

            return jobs

        except Exception as e:
            logger.error(f"❌ Failed to get jobs by status: {e}")
            logger.exception("Jobs query error details:")
            raise

    async def delete_job(self, job_id: str) -> bool:
        """
        Delete job (use with caution).

        Args:
            job_id: Job identifier

        Returns:
            True if deleted

        Raises:
            Exception: If deletion fails
        """
        try:
            logger.warning(f"🗑️ Deleting job: job_id={job_id}")

            # Get database collection
            db = await get_database()
            collection = await db.get_collection(self.collection_name)

            # Delete from MongoDB
            result = await collection.delete_one({"job_id": job_id})

            if result.deleted_count > 0:
                logger.info(f"✅ Job deleted: job_id={job_id}")
                return True
            else:
                logger.warning(f"⚠️ Job not found for deletion: job_id={job_id}")
                return False

        except Exception as e:
            logger.error(f"❌ Failed to delete job {job_id}: {e}")
            logger.exception("Job deletion error details:")
            raise

    async def update_chunks(self, job_id: str, chunks: List[dict]) -> bool:
        """
        Update job chunks.

        Args:
            job_id: Job identifier
            chunks: List of chunk dictionaries

        Returns:
            True if updated

        Raises:
            Exception: If update fails
        """
        try:
            logger.info(
                f"📝 Updating chunks for job: job_id={job_id}, chunk_count={len(chunks)}"
            )

            update_data = JobUpdate(chunks=chunks, chunks_total=len(chunks))

            result = await self.update_job(job_id, update_data)

            if result:
                logger.info(f"✅ Chunks updated: job_id={job_id}, total={len(chunks)}")

            return result

        except Exception as e:
            logger.error(f"❌ Failed to update chunks for job {job_id}: {e}")
            logger.exception("Chunks update error details:")
            raise

    async def increment_retry_count(self, job_id: str) -> bool:
        """
        Increment retry count for a job.

        Args:
            job_id: Job identifier

        Returns:
            True if updated

        Raises:
            Exception: If update fails
        """
        try:
            logger.info(f"📝 Incrementing retry count for job: job_id={job_id}")

            # Get database collection
            db = await get_database()
            collection = await db.get_collection(self.collection_name)

            # Increment retry_count
            result = await collection.update_one(
                {"job_id": job_id},
                {"$inc": {"retry_count": 1}, "$set": {"updated_at": datetime.utcnow()}},
            )

            if result.modified_count > 0:
                logger.info(f"✅ Retry count incremented: job_id={job_id}")
                return True
            else:
                logger.warning(f"⚠️ Failed to increment retry count: job_id={job_id}")
                return False

        except Exception as e:
            logger.error(f"❌ Failed to increment retry count for job {job_id}: {e}")
            logger.exception("Retry count increment error details:")
            raise


# Singleton instance
_task_repository: Optional[TaskRepository] = None


def get_task_repository() -> TaskRepository:
    """
    Get task repository instance (singleton).

    Returns:
        TaskRepository instance
    """
    global _task_repository

    try:
        if _task_repository is None:
            logger.debug("Creating new TaskRepository instance")
            _task_repository = TaskRepository()

        return _task_repository

    except Exception as e:
        logger.error(f"❌ Failed to get task repository: {e}")
        logger.exception("Task repository initialization error:")
        raise
