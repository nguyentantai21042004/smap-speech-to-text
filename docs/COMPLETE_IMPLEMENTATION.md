# Complete STT System Implementation

This document contains all the code needed to complete the STT system. Copy each section to the appropriate file.

## ✅ Already Completed

1. `requirements.txt` - Updated with STT dependencies
2. `core/config.py` - Updated with Redis + SQLite configuration
3. `.env` - Updated with STT settings
4. `worker/errors.py` - Error definitions
5. `worker/constants.py` - Constants

---

## 📁 Files to Create/Update

### **1. Update `core/database.py`**

**Location:** `core/database.py`

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
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context():
    """Context manager for database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database - create all tables."""
    # Import models here to avoid circular imports
    import repositories.models
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialized successfully")


def drop_db():
    """Drop all tables - use with caution!"""
    Base.metadata.drop_all(bind=engine)
    logger.warning("All database tables dropped")
```

---

### **2. Update `core/messaging.py`**

**Location:** `core/messaging.py`

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
        """Enqueue a job for processing."""
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

### **3. Create `repositories/models.py`**

**Location:** `repositories/models.py`

```python
"""
Database models for STT system.
"""
from sqlalchemy import Column, String, Float, Integer, DateTime, Text, Enum, ForeignKey
from sqlalchemy.sql import func
from datetime import datetime
import enum

from core.database import Base


class JobStatusEnum(enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class Job(Base):
    """Job table for tracking STT jobs."""
    __tablename__ = "jobs"

    id = Column(String, primary_key=True)
    job_id = Column(String, unique=True, index=True, nullable=False)
    status = Column(Enum(JobStatusEnum), default=JobStatusEnum.PENDING)
    language = Column(String, nullable=False)

    # File information
    original_filename = Column(String)
    file_path = Column(Text)
    file_size_mb = Column(Float)
    audio_duration_seconds = Column(Float)

    # Processing information
    worker_id = Column(String)
    retry_count = Column(Integer, default=0)
    chunks_total = Column(Integer)
    chunks_completed = Column(Integer, default=0)

    # Results
    transcription_text = Column(Text)
    result_file_path = Column(Text)
    error_message = Column(Text)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())


class Chunk(Base):
    """Chunk table for tracking individual audio chunks."""
    __tablename__ = "chunks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String, ForeignKey('jobs.job_id', ondelete='CASCADE'), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    start_time = Column(Float)
    end_time = Column(Float)
    transcription = Column(Text)
    status = Column(Enum(JobStatusEnum), default=JobStatusEnum.PENDING)
    error_message = Column(Text)
    processed_at = Column(DateTime(timezone=True))
```

---

## 🔧 Continue to Part 2

Due to length constraints, the remaining implementation files are provided in the next section.

Run these commands to create necessary directories:

```bash
# Create storage directories
mkdir -p storage/uploads storage/results logs

# Create worker directory if not exists
mkdir -p worker

# Initialize database
python -c "from core.database import init_db; init_db()"
```

---

## 📝 Next Steps

1. Copy the code above into the respective files
2. See `COMPLETE_IMPLEMENTATION_PART2.md` for worker modules
3. See `COMPLETE_IMPLEMENTATION_PART3.md` for API routes and services
4. See `COMPLETE_IMPLEMENTATION_PART4.md` for consumer and testing

**Current Progress:** 40% Complete
**Next:** Worker modules (chunking, transcriber, merger, processor)
