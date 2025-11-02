"""
Redis Queue management for asynchronous job processing.
Includes detailed logging and comprehensive error handling.
"""

import redis
from rq import Queue
from rq.job import Job
from typing import Optional, Any, Dict, Callable
from datetime import datetime

from core.config import get_settings
from core.logger import logger

settings = get_settings()


class RedisQueueManager:
    """Manages Redis Queue connections and operations with detailed logging."""

    def __init__(self):
        """Initialize Redis connection and queues."""
        try:
            logger.info("📝 Initializing Redis Queue Manager...")

            # Build Redis connection string
            redis_password_part = (
                f":{settings.redis_password}@" if settings.redis_password else ""
            )
            redis_url = f"redis://{redis_password_part}{settings.redis_host}:{settings.redis_port}/{settings.redis_db}"

            # Mask password for logging
            masked_url = (
                redis_url.replace(f":{settings.redis_password}@", ":****@")
                if settings.redis_password
                else redis_url
            )
            logger.debug(f"Connecting to Redis: {masked_url}")

            # Create Redis connection
            self.redis_conn = redis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                db=settings.redis_db,
                password=settings.redis_password,
                decode_responses=False,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
            )

            # Test connection
            self.redis_conn.ping()
            logger.info(
                f"✅ Connected to Redis at {settings.redis_host}:{settings.redis_port}"
            )

            # Define queue priorities
            self.queue_high = Queue("stt_jobs_high", connection=self.redis_conn)
            self.queue_normal = Queue("stt_jobs", connection=self.redis_conn)
            self.queue_low = Queue("stt_jobs_low", connection=self.redis_conn)

            logger.info("✅ Redis Queue Manager initialized")
            logger.debug(
                f"Queues created: high={self.queue_high.name}, normal={self.queue_normal.name}, low={self.queue_low.name}"
            )

        except redis.ConnectionError as e:
            logger.error(f"❌ Redis connection error: {e}")
            logger.exception("Redis connection error details:")
            raise

        except redis.TimeoutError as e:
            logger.error(f"❌ Redis connection timeout: {e}")
            logger.exception("Redis timeout error details:")
            raise

        except Exception as e:
            logger.error(f"❌ Failed to initialize Redis Queue Manager: {e}")
            logger.exception("Redis initialization error details:")
            raise

    def enqueue_job(
        self,
        func: Callable,
        args: tuple = (),
        kwargs: Optional[Dict[str, Any]] = None,
        priority: str = "normal",
        job_id: Optional[str] = None,
        job_timeout: Optional[int] = None,
        result_ttl: int = 86400,
        failure_ttl: int = 604800,
    ) -> Job:
        """
        Enqueue a job for processing.

        Args:
            func: Function to execute (can be function object or string path)
            args: Positional arguments for the function
            kwargs: Keyword arguments for the function
            priority: Job priority ('high', 'normal', 'low')
            job_id: Optional custom job ID
            job_timeout: Maximum execution time in seconds
            result_ttl: How long to keep successful results (seconds)
            failure_ttl: How long to keep failed job info (seconds)

        Returns:
            RQ Job object

        Raises:
            Exception: If job enqueue fails
        """
        try:
            kwargs = kwargs or {}
            job_timeout = job_timeout or settings.job_timeout

            logger.info(
                f"📝 Enqueueing job: func={func}, priority={priority}, job_id={job_id}"
            )
            logger.debug(f"Job args: {args}, kwargs: {kwargs}")

            # Select queue based on priority
            if priority == "high":
                queue = self.queue_high
            elif priority == "low":
                queue = self.queue_low
            else:
                queue = self.queue_normal

            logger.debug(f"Selected queue: {queue.name}")

            # Enqueue the job
            job = queue.enqueue(
                func,
                args=args,
                kwargs=kwargs,
                job_id=job_id,
                job_timeout=job_timeout,
                result_ttl=result_ttl,
                failure_ttl=failure_ttl,
            )

            logger.info(
                f"✅ Job enqueued successfully: job_id={job.id}, queue={queue.name}"
            )
            logger.debug(
                f"Job timeout: {job_timeout}s, result_ttl: {result_ttl}s, failure_ttl: {failure_ttl}s"
            )

            return job

        except redis.ConnectionError as e:
            logger.error(f"❌ Redis connection error while enqueueing job: {e}")
            logger.exception("Connection error details:")
            raise

        except Exception as e:
            logger.error(f"❌ Failed to enqueue job: {e}")
            logger.exception("Job enqueue error details:")
            raise

    def get_job(self, job_id: str) -> Optional[Job]:
        """
        Get job by ID.

        Args:
            job_id: Job ID

        Returns:
            Job object or None if not found
        """
        try:
            logger.debug(f"🔍 Fetching job: job_id={job_id}")

            job = Job.fetch(job_id, connection=self.redis_conn)

            if job:
                logger.debug(
                    f"✅ Job found: job_id={job_id}, status={job.get_status()}"
                )
            else:
                logger.warning(f"⚠️ Job not found: job_id={job_id}")

            return job

        except Exception as e:
            logger.error(f"❌ Failed to fetch job {job_id}: {e}")
            logger.exception("Job fetch error details:")
            return None

    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get status of a job.

        Args:
            job_id: Job ID

        Returns:
            Job status dictionary or None if not found
        """
        try:
            logger.debug(f"🔍 Getting status for job: job_id={job_id}")

            job = Job.fetch(job_id, connection=self.redis_conn)

            status_info = {
                "job_id": job.id,
                "status": job.get_status(),
                "result": job.result,
                "exc_info": job.exc_info,
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "ended_at": job.ended_at.isoformat() if job.ended_at else None,
                "meta": job.meta,
            }

            logger.debug(
                f"✅ Job status retrieved: job_id={job_id}, status={status_info['status']}"
            )

            return status_info

        except Exception as e:
            logger.error(f"❌ Failed to get job status for {job_id}: {e}")
            logger.exception("Job status retrieval error details:")
            return None

    def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a pending or started job.

        Args:
            job_id: Job ID

        Returns:
            True if cancelled successfully
        """
        try:
            logger.info(f"📝 Cancelling job: job_id={job_id}")

            job = Job.fetch(job_id, connection=self.redis_conn)
            job.cancel()

            logger.info(f"✅ Job cancelled: job_id={job_id}")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to cancel job {job_id}: {e}")
            logger.exception("Job cancellation error details:")
            return False

    def delete_job(self, job_id: str) -> bool:
        """
        Delete a job from Redis.

        Args:
            job_id: Job ID

        Returns:
            True if deleted successfully
        """
        try:
            logger.info(f"📝 Deleting job: job_id={job_id}")

            job = Job.fetch(job_id, connection=self.redis_conn)
            job.delete()

            logger.info(f"✅ Job deleted: job_id={job_id}")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to delete job {job_id}: {e}")
            logger.exception("Job deletion error details:")
            return False

    def get_queue_stats(self) -> Dict[str, Any]:
        """
        Get statistics about all queues.

        Returns:
            Dictionary with queue statistics
        """
        try:
            logger.debug("🔍 Fetching queue statistics...")

            stats = {
                "high_priority": {
                    "name": self.queue_high.name,
                    "pending": len(self.queue_high),
                    "started": self.queue_high.started_job_registry.count,
                    "finished": self.queue_high.finished_job_registry.count,
                    "failed": self.queue_high.failed_job_registry.count,
                    "workers": len(self.queue_high.workers),
                },
                "normal": {
                    "name": self.queue_normal.name,
                    "pending": len(self.queue_normal),
                    "started": self.queue_normal.started_job_registry.count,
                    "finished": self.queue_normal.finished_job_registry.count,
                    "failed": self.queue_normal.failed_job_registry.count,
                    "workers": len(self.queue_normal.workers),
                },
                "low_priority": {
                    "name": self.queue_low.name,
                    "pending": len(self.queue_low),
                    "started": self.queue_low.started_job_registry.count,
                    "finished": self.queue_low.finished_job_registry.count,
                    "failed": self.queue_low.failed_job_registry.count,
                    "workers": len(self.queue_low.workers),
                },
            }

            logger.debug(f"✅ Queue stats retrieved: {stats}")

            return stats

        except Exception as e:
            logger.error(f"❌ Failed to get queue stats: {e}")
            logger.exception("Queue stats error details:")
            return {}

    def health_check(self) -> bool:
        """
        Check if Redis connection is healthy.

        Returns:
            True if healthy, False otherwise
        """
        try:
            logger.debug("🔍 Performing Redis health check...")

            self.redis_conn.ping()

            logger.debug("✅ Redis health check passed")
            return True

        except Exception as e:
            logger.error(f"❌ Redis health check failed: {e}")
            logger.exception("Health check error details:")
            return False

    def close(self):
        """Close Redis connection."""
        try:
            logger.info("📝 Closing Redis connection...")

            if self.redis_conn:
                self.redis_conn.close()
                logger.info("✅ Redis connection closed")

        except Exception as e:
            logger.error(f"❌ Error closing Redis connection: {e}")
            logger.exception("Redis close error details:")


# Global instance
_queue_manager: Optional[RedisQueueManager] = None


def get_queue_manager() -> RedisQueueManager:
    """
    Get or create global queue manager instance.

    Returns:
        RedisQueueManager instance

    Raises:
        Exception: If queue manager initialization fails
    """
    global _queue_manager

    try:
        if _queue_manager is None:
            logger.info("📝 Creating global Redis Queue Manager...")
            _queue_manager = RedisQueueManager()

        return _queue_manager

    except Exception as e:
        logger.error(f"❌ Failed to get queue manager: {e}")
        logger.exception("Queue manager initialization error:")
        raise


def close_queue_manager():
    """Close global queue manager."""
    global _queue_manager

    try:
        if _queue_manager:
            logger.info("📝 Closing global queue manager...")
            _queue_manager.close()
            _queue_manager = None
            logger.info("✅ Global queue manager closed")

    except Exception as e:
        logger.error(f"❌ Error closing queue manager: {e}")
        logger.exception("Queue manager close error details:")
