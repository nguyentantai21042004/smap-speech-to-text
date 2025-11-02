# Speech-to-Text Implementation Guide

This guide provides step-by-step instructions to complete the STT system implementation following the existing project structure.

## Prerequisites

**Completed Steps:**
- Step 1: Project initialization (already done)
- Step 2: Whisper.cpp built and models downloaded in `whisper/` directory

## Current Status

Your project structure is ready with:
- Microservices architecture (API, Worker/Consumer, Scheduler)
- Updated `requirements.txt` with STT dependencies
- Updated `core/config.py` for Redis + SQLite/PostgreSQL
- Updated `.env` file with STT configuration
- ⏳ Need to implement: Worker modules, API routes, Services, Repositories

---

## Step 3: Install Dependencies

Run this inside your virtual environment (`myenv`):

```bash
# Activate virtual environment
source myenv/bin/activate

# Install updated dependencies
pip install -r requirements.txt

# Install system dependencies for audio processing (if not already installed)
# macOS:
brew install ffmpeg

# Ubuntu/Debian:
# sudo apt-get install -y ffmpeg libopenblas-dev
```

---

## Step 4: Update Database Layer

### 4.1 Update `core/database.py`

Replace the MongoDB connection with SQLAlchemy:

```python
"""
Database connection and session management using SQLAlchemy.
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from typing import Generator

from core.config import get_settings
from core.logger import get_logger

settings = get_settings()
logger = get_logger(__name__)

# Create SQLAlchemy engine
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
    pool_pre_ping=True,
    echo=settings.debug
)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    Dependency for FastAPI routes to get database session.

    Yields:
        Database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context():
    """
    Context manager for database session (for use outside FastAPI).

    Usage:
        with get_db_context() as db:
            # use db session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database - create all tables."""
    from repositories.models import Job, Chunk  # Import models
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialized successfully")


def drop_db():
    """Drop all tables - use with caution!"""
    Base.metadata.drop_all(bind=engine)
    logger.warning("All database tables dropped")
```

### 4.2 Update `core/messaging.py`

Replace RabbitMQ with Redis Queue:

```python
"""
Redis Queue management for asynchronous job processing.
"""
import redis
from rq import Queue
from typing import Optional, Any, Dict
from core.config import get_settings
from core.logger import get_logger

settings = get_settings()
logger = get_logger(__name__)


class RedisQueueManager:
    """Manages Redis Queue connections and operations."""

    def __init__(self):
        """Initialize Redis connection."""
        self.redis_conn = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            password=settings.redis_password,
            decode_responses=False
        )

        # Define queue priorities
        self.queue_high = Queue('stt_jobs_high', connection=self.redis_conn)
        self.queue_normal = Queue('stt_jobs', connection=self.redis_conn)
        self.queue_low = Queue('stt_jobs_low', connection=self.redis_conn)

        logger.info("Redis Queue Manager initialized")

    def enqueue_job(
        self,
        func_name: str,
        args: tuple = (),
        kwargs: Optional[Dict[str, Any]] = None,
        priority: str = "normal",
        job_timeout: Optional[int] = None,
        result_ttl: int = 86400,
        failure_ttl: int = 604800
    ):
        """
        Enqueue a job for processing.

        Args:
            func_name: Function to execute (e.g., 'worker.processor.process_stt_job')
            args: Positional arguments for the function
            kwargs: Keyword arguments for the function
            priority: Job priority ('high', 'normal', 'low')
            job_timeout: Maximum execution time in seconds
            result_ttl: How long to keep successful results (seconds)
            failure_ttl: How long to keep failed job info (seconds)

        Returns:
            RQ Job object
        """
        kwargs = kwargs or {}
        job_timeout = job_timeout or settings.job_timeout

        # Select queue based on priority
        if priority == "high":
            queue = self.queue_high
        elif priority == "low":
            queue = self.queue_low
        else:
            queue = self.queue_normal

        job = queue.enqueue(
            func_name,
            args=args,
            kwargs=kwargs,
            job_timeout=job_timeout,
            result_ttl=result_ttl,
            failure_ttl=failure_ttl
        )

        logger.info(f"Job {job.id} enqueued in {queue.name}")
        return job

    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get status of a job.

        Args:
            job_id: Job ID

        Returns:
            Job status dictionary or None if not found
        """
        from rq.job import Job

        try:
            job = Job.fetch(job_id, connection=self.redis_conn)
            return {
                "job_id": job.id,
                "status": job.get_status(),
                "result": job.result,
                "exc_info": job.exc_info,
                "created_at": job.created_at,
                "started_at": job.started_at,
                "ended_at": job.ended_at
            }
        except Exception as e:
            logger.error(f"Failed to fetch job {job_id}: {e}")
            return None

    def get_queue_stats(self) -> Dict[str, Any]:
        """Get statistics about all queues."""
        return {
            "high_priority": {
                "name": self.queue_high.name,
                "pending": len(self.queue_high),
                "workers": len(self.queue_high.workers)
            },
            "normal": {
                "name": self.queue_normal.name,
                "pending": len(self.queue_normal),
                "workers": len(self.queue_normal.workers)
            },
            "low_priority": {
                "name": self.queue_low.name,
                "pending": len(self.queue_low),
                "workers": len(self.queue_low.workers)
            }
        }

    def close(self):
        """Close Redis connection."""
        self.redis_conn.close()
        logger.info("Redis connection closed")


# Global instance
_queue_manager: Optional[RedisQueueManager] = None


def get_queue_manager() -> RedisQueueManager:
    """Get or create global queue manager instance."""
    global _queue_manager
    if _queue_manager is None:
        _queue_manager = RedisQueueManager()
    return _queue_manager
```

---

## Step 5: Create Worker Modules

Create the worker package structure:

```bash
mkdir -p worker
touch worker/__init__.py
```

### 5.1 Create `worker/errors.py`

```python
"""Error definitions for STT processing."""


class STTError(Exception):
    """Base STT Error."""
    pass


class TransientError(STTError):
    """Errors that can be retried."""
    def __init__(self, message, retry_count=0):
        self.message = message
        self.retry_count = retry_count
        super().__init__(self.message)


class PermanentError(STTError):
    """Errors that should not be retried."""
    pass


# Transient errors
class OutOfMemoryError(TransientError):
    pass


class TimeoutError(TransientError):
    pass


class WhisperCrashError(TransientError):
    pass


class NetworkError(TransientError):
    pass


# Permanent errors
class InvalidAudioFormatError(PermanentError):
    pass


class UnsupportedLanguageError(PermanentError):
    pass


class FileTooLargeError(PermanentError):
    pass


class FileNotFoundError(PermanentError):
    pass


class CorruptedFileError(PermanentError):
    pass
```

### 5.2 Create `worker/constants.py`

```python
"""Constants for STT worker."""
from enum import Enum


class JobStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class Language(str, Enum):
    ENGLISH = "en"
    VIETNAMESE = "vi"


# Supported audio formats
SUPPORTED_FORMATS = [
    '.mp3', '.wav', '.m4a', '.mp4',
    '.aac', '.ogg', '.flac', '.wma',
    '.webm', '.mkv', '.avi', '.mov'
]

# Queue names
QUEUE_HIGH_PRIORITY = "stt_jobs_high"
QUEUE_NORMAL = "stt_jobs"
QUEUE_LOW_PRIORITY = "stt_jobs_low"
QUEUE_DEAD_LETTER = "stt_jobs_dlq"

# Processing constants
MAX_CHUNK_SIZE_SECONDS = 60
MIN_CHUNK_SIZE_SECONDS = 5
DEFAULT_SAMPLE_RATE = 16000
```

### 5.3 Create Remaining Worker Files

Due to message length limits, I'll provide the continuation in the next message. The remaining files to create are:

- `worker/chunking.py` - Audio chunking logic
- `worker/transcriber.py` - Whisper.cpp interface
- `worker/merger.py` - Result merging
- `worker/processor.py` - Main STT processor

Would you like me to continue with these implementations?

---

## Step 6-10: Summary (To Be Continued)

The remaining steps are:

**Step 6:** Create Repository Models and Interfaces
**Step 7:** Update Services Layer
**Step 8:** Update API Routes
**Step 9:** Update Worker/Consumer Entry Point
**Step 10:** Testing and Deployment

### Quick Start Commands (After Implementation)

```bash
# 1. Activate virtual environment
source myenv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create storage directories
mkdir -p storage/uploads storage/results logs

# 4. Initialize database
python -c "from core.database import init_db; init_db()"

# 5. Start Redis (in separate terminal)
redis-server

# 6. Start API server
python cmd/api/main.py

# 7. Start Worker (in separate terminal)
python cmd/consumer/main.py

# 8. Test the system
python scripts/test_upload.py sample_audio.mp3
```

---

**Status:** Configuration complete. Next: Implement worker modules.

Continue to next message for remaining implementation files.
