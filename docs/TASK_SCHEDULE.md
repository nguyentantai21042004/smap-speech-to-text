# 📋 Complete Task Schedule - STT System Implementation

## 🎯 Your Requirements

**Database:** MongoDB (not SQLite/PostgreSQL)
**Logging:** Detailed logs in all logic
**Error Handling:** Try-catch everywhere to catch bugs

---

## 📊 Task Overview

| # | Task | Files | Est. Time | Priority |
|---|------|-------|-----------|----------|
| 1 | Setup MongoDB connection | `core/database.py` | 15 min | 🔴 High |
| 2 | Create MongoDB models | `repositories/models.py` | 20 min | 🔴 High |
| 3 | Update repositories | `repositories/task_repository.py` | 30 min | 🔴 High |
| 4 | Create audio chunking module | `worker/chunking.py` | 45 min | 🔴 High |
| 5 | Create Whisper transcriber | `worker/transcriber.py` | 30 min | 🔴 High |
| 6 | Create result merger | `worker/merger.py` | 30 min | 🟡 Medium |
| 7 | Create STT processor | `worker/processor.py` | 60 min | 🔴 High |
| 8 | Update API routes | `internal/api/routes/task_routes.py` | 45 min | 🔴 High |
| 9 | Create consumer handler | `internal/consumer/handlers/stt_handler.py` | 30 min | 🔴 High |
| 10 | Create test scripts | `scripts/test_upload.py` | 20 min | 🟢 Low |

**Total Estimated Time:** ~5-6 hours

---

## Detailed Task Breakdown

### **TASK 1: Setup MongoDB Connection** ⏱️ 15 min

**File:** `core/database.py`

**Requirements:**
- Use Motor (async MongoDB driver)
- Connection pooling
- Detailed logging (connection success/failure)
- Try-catch for all operations

**Code:**

```python
"""
MongoDB connection using Motor (async driver).
Includes detailed logging and error handling.
"""
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from typing import Optional
import asyncio

from core.config import get_settings
from core.logger import get_logger

settings = get_settings()
logger = get_logger(__name__)


class MongoDB:
    """MongoDB connection manager with async support."""

    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.db: Optional[AsyncIOMotorDatabase] = None

    async def connect(self) -> None:
        """Establish connection to MongoDB."""
        try:
            logger.info(f"Connecting to MongoDB: {settings.mongodb_url}")

            self.client = AsyncIOMotorClient(
                settings.mongodb_url,
                maxPoolSize=settings.mongodb_max_pool_size,
                minPoolSize=settings.mongodb_min_pool_size,
                serverSelectionTimeoutMS=5000
            )

            # Test connection
            await self.client.admin.command('ping')

            self.db = self.client[settings.mongodb_database]

            logger.info(f"Connected to MongoDB database: {settings.mongodb_database}")
            logger.debug(f"Connection pool: min={settings.mongodb_min_pool_size}, max={settings.mongodb_max_pool_size}")

        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            logger.exception("MongoDB connection error details:")
            raise

    async def disconnect(self) -> None:
        """Close MongoDB connection."""
        try:
            if self.client:
                logger.info("Disconnecting from MongoDB...")
                self.client.close()
                logger.info("Disconnected from MongoDB")
        except Exception as e:
            logger.error(f"Error disconnecting from MongoDB: {e}")
            logger.exception("MongoDB disconnection error details:")

    async def get_collection(self, collection_name: str):
        """Get a MongoDB collection."""
        try:
            if not self.db:
                raise RuntimeError("Database not connected. Call connect() first.")

            collection = self.db[collection_name]
            logger.debug(f"Accessed collection: {collection_name}")
            return collection

        except Exception as e:
            logger.error(f"Failed to access collection {collection_name}: {e}")
            raise

    async def health_check(self) -> bool:
        """Check if MongoDB connection is healthy."""
        try:
            if not self.client:
                logger.warning("MongoDB client not initialized")
                return False

            await self.client.admin.command('ping')
            logger.debug("MongoDB health check passed")
            return True

        except Exception as e:
            logger.error(f"MongoDB health check failed: {e}")
            return False


# Global instance
_mongodb: Optional[MongoDB] = None


async def get_database() -> MongoDB:
    """Get or create global MongoDB instance."""
    global _mongodb

    try:
        if _mongodb is None:
            logger.info("Initializing MongoDB connection...")
            _mongodb = MongoDB()
            await _mongodb.connect()

        return _mongodb

    except Exception as e:
        logger.error(f"Failed to get MongoDB instance: {e}")
        logger.exception("Database initialization error:")
        raise


async def close_database() -> None:
    """Close global MongoDB connection."""
    global _mongodb

    try:
        if _mongodb:
            await _mongodb.disconnect()
            _mongodb = None
    except Exception as e:
        logger.error(f"Error closing database: {e}")
```

**Testing:**
```python
# Test in Python REPL or script
import asyncio
from core.database import get_database

async def test_connection():
    db = await get_database()
    is_healthy = await db.health_check()
    print(f"MongoDB healthy: {is_healthy}")

asyncio.run(test_connection())
```

---

### **TASK 2: Create MongoDB Models** ⏱️ 20 min

**File:** `repositories/models.py`

**Requirements:**
- Pydantic models for validation
- MongoDB document schemas
- Logging for model operations

**Code:**

```python
"""
MongoDB document models using Pydantic.
Includes validation and logging.
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum

from core.logger import get_logger

logger = get_logger(__name__)


class JobStatus(str, Enum):
    """Job status enumeration."""
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ChunkModel(BaseModel):
    """Model for audio chunk."""
    chunk_index: int
    start_time: float
    end_time: float
    transcription: Optional[str] = None
    status: JobStatus = JobStatus.PENDING
    error_message: Optional[str] = None
    processed_at: Optional[datetime] = None


class JobModel(BaseModel):
    """Model for STT job (MongoDB document)."""

    # IDs
    job_id: str = Field(..., description="Unique job identifier")

    # Status
    status: JobStatus = JobStatus.PENDING
    language: str = Field(..., description="Language code (en, vi)")

    # File information (MinIO paths)
    original_filename: str
    minio_audio_path: str
    minio_result_path: Optional[str] = None
    file_size_mb: float
    audio_duration_seconds: Optional[float] = None

    # Processing information
    worker_id: Optional[str] = None
    retry_count: int = 0
    chunks_total: Optional[int] = None
    chunks_completed: int = 0
    chunks: List[ChunkModel] = []

    # Results
    transcription_text: Optional[str] = None
    error_message: Optional[str] = None

    # Metadata
    model_used: str = "medium"
    chunk_strategy: str = "silence_based"

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        """Pydantic config."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

    def to_dict(self) -> dict:
        """Convert to dictionary for MongoDB."""
        try:
            data = self.dict()
            logger.debug(f"Converted JobModel to dict: job_id={self.job_id}")
            return data
        except Exception as e:
            logger.error(f"Failed to convert JobModel to dict: {e}")
            raise

    @classmethod
    def from_dict(cls, data: dict) -> "JobModel":
        """Create from MongoDB document."""
        try:
            job = cls(**data)
            logger.debug(f"Created JobModel from dict: job_id={job.job_id}")
            return job
        except Exception as e:
            logger.error(f"Failed to create JobModel from dict: {e}")
            logger.exception("Model creation error:")
            raise


class JobCreate(BaseModel):
    """Model for creating a new job."""
    language: str = "vi"
    original_filename: str
    minio_audio_path: str
    file_size_mb: float
    model_used: str = "medium"


class JobUpdate(BaseModel):
    """Model for updating a job."""
    status: Optional[JobStatus] = None
    worker_id: Optional[str] = None
    chunks_total: Optional[int] = None
    chunks_completed: Optional[int] = None
    transcription_text: Optional[str] = None
    error_message: Optional[str] = None
    minio_result_path: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# MongoDB collection names
JOBS_COLLECTION = "stt_jobs"
CHUNKS_COLLECTION = "stt_chunks"

logger.info("MongoDB models defined")
```

---

### **TASK 3: Update Task Repository** ⏱️ 30 min

**File:** `repositories/task_repository.py`

**Requirements:**
- CRUD operations with MongoDB
- Detailed logging for every operation
- Try-catch for all database operations

**Code:**

```python
"""
Task repository for MongoDB operations.
Includes comprehensive logging and error handling.
"""
from typing import Optional, List
from datetime import datetime

from core.database import get_database
from repositories.models import (
    JobModel, JobCreate, JobUpdate, JobStatus,
    JOBS_COLLECTION
)
from core.logger import get_logger

logger = get_logger(__name__)


class TaskRepository:
    """Repository for STT job database operations."""

    def __init__(self):
        self.collection_name = JOBS_COLLECTION

    async def create_job(self, job_data: JobCreate) -> JobModel:
        """
        Create a new STT job.

        Args:
            job_data: Job creation data

        Returns:
            Created JobModel
        """
        try:
            logger.info(f"Creating new job: {job_data.original_filename}")

            # Generate job ID
            import uuid
            job_id = str(uuid.uuid4())

            # Create job model
            job = JobModel(
                job_id=job_id,
                **job_data.dict()
            )

            # Insert into MongoDB
            db = await get_database()
            collection = await db.get_collection(self.collection_name)

            result = await collection.insert_one(job.to_dict())

            logger.info(f"Job created successfully: job_id={job_id}, inserted_id={result.inserted_id}")
            logger.debug(f"Job details: {job.dict()}")

            return job

        except Exception as e:
            logger.error(f"Failed to create job: {e}")
            logger.exception("Job creation error details:")
            raise

    async def get_job(self, job_id: str) -> Optional[JobModel]:
        """
        Get job by ID.

        Args:
            job_id: Job identifier

        Returns:
            JobModel or None if not found
        """
        try:
            logger.debug(f"🔍 Fetching job: job_id={job_id}")

            db = await get_database()
            collection = await db.get_collection(self.collection_name)

            doc = await collection.find_one({"job_id": job_id})

            if doc:
                logger.info(f"Job found: job_id={job_id}, status={doc.get('status')}")
                return JobModel.from_dict(doc)
            else:
                logger.warning(f"Job not found: job_id={job_id}")
                return None

        except Exception as e:
            logger.error(f"Failed to get job {job_id}: {e}")
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
        """
        try:
            logger.info(f"Updating job: job_id={job_id}")
            logger.debug(f"Update data: {update_data.dict(exclude_unset=True)}")

            db = await get_database()
            collection = await db.get_collection(self.collection_name)

            # Build update document
            update_dict = {
                k: v for k, v in update_data.dict(exclude_unset=True).items()
                if v is not None
            }
            update_dict["updated_at"] = datetime.utcnow()

            result = await collection.update_one(
                {"job_id": job_id},
                {"$set": update_dict}
            )

            if result.modified_count > 0:
                logger.info(f"Job updated: job_id={job_id}, modified={result.modified_count}")
                return True
            else:
                logger.warning(f"Job not updated (not found or no changes): job_id={job_id}")
                return False

        except Exception as e:
            logger.error(f"Failed to update job {job_id}: {e}")
            logger.exception("Update job error details:")
            raise

    async def update_status(
        self,
        job_id: str,
        status: JobStatus,
        error_message: Optional[str] = None
    ) -> bool:
        """
        Update job status.

        Args:
            job_id: Job identifier
            status: New status
            error_message: Optional error message

        Returns:
            True if updated
        """
        try:
            logger.info(f"🔄 Updating job status: job_id={job_id}, status={status}")

            update_data = JobUpdate(
                status=status,
                error_message=error_message
            )

            # Set timestamps based on status
            if status == JobStatus.PROCESSING:
                update_data.started_at = datetime.utcnow()
            elif status in [JobStatus.COMPLETED, JobStatus.FAILED]:
                update_data.completed_at = datetime.utcnow()

            return await self.update_job(job_id, update_data)

        except Exception as e:
            logger.error(f"Failed to update status for job {job_id}: {e}")
            raise

    async def get_pending_jobs(self, limit: int = 10) -> List[JobModel]:
        """Get pending jobs."""
        try:
            logger.debug(f"🔍 Fetching pending jobs (limit={limit})")

            db = await get_database()
            collection = await db.get_collection(self.collection_name)

            cursor = collection.find(
                {"status": JobStatus.PENDING}
            ).sort("created_at", 1).limit(limit)

            jobs = []
            async for doc in cursor:
                jobs.append(JobModel.from_dict(doc))

            logger.info(f"Found {len(jobs)} pending jobs")
            return jobs

        except Exception as e:
            logger.error(f"Failed to get pending jobs: {e}")
            raise

    async def delete_job(self, job_id: str) -> bool:
        """Delete job (use with caution)."""
        try:
            logger.warning(f"🗑️ Deleting job: job_id={job_id}")

            db = await get_database()
            collection = await db.get_collection(self.collection_name)

            result = await collection.delete_one({"job_id": job_id})

            if result.deleted_count > 0:
                logger.info(f"Job deleted: job_id={job_id}")
                return True
            else:
                logger.warning(f"Job not found for deletion: job_id={job_id}")
                return False

        except Exception as e:
            logger.error(f"Failed to delete job {job_id}: {e}")
            raise


# Singleton instance
_task_repository: Optional[TaskRepository] = None


def get_task_repository() -> TaskRepository:
    """Get task repository instance."""
    global _task_repository
    if _task_repository is None:
        _task_repository = TaskRepository()
        logger.debug("TaskRepository initialized")
    return _task_repository
```

---

## 📌 Remaining Tasks (4-10)

Due to length constraints, I'll create separate detailed files for each remaining task. Let me create:

1. A quick reference checklist
2. Detailed code for worker modules (Tasks 4-7)
3. API and consumer code (Tasks 8-9)
4. Test scripts (Task 10)

Would you like me to:
1. **Create all worker modules now** (chunking, transcriber, merger, processor)
2. **Create API routes and consumer handler**
3. **Create test scripts**

Or should I prioritize specific tasks first?

---

## 🎯 Quick Task Checklist

```
TASK 1: MongoDB connection (core/database.py)
TASK 2: MongoDB models (repositories/models.py)
TASK 3: Task repository (repositories/task_repository.py)
⏳ TASK 4: Audio chunking (worker/chunking.py) - NEXT
⏳ TASK 5: Whisper transcriber (worker/transcriber.py)
⏳ TASK 6: Result merger (worker/merger.py)
⏳ TASK 7: STT processor (worker/processor.py)
⏳ TASK 8: API routes (internal/api/routes/task_routes.py)
⏳ TASK 9: Consumer handler (internal/consumer/handlers/stt_handler.py)
⏳ TASK 10: Test scripts (scripts/test_upload.py)
```

**Priority Order:** 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10
