# 🚀 Updated STT Implementation Guide (RabbitMQ + MinIO)

## ✅ Architecture Clarifications

### **1. Project Structure (Parallel Design)**

```
API Side:                              Consumer Side:
├── cmd/api/main.py                    ├── cmd/consumer/main.py
│   └── Entry point for API            │   └── Entry point for Consumer
│                                       │
├── internal/api/                      ├── internal/consumer/
│   ├── routes/                        │   └── handlers/
│   │   └── task_routes.py             │       └── stt_handler.py
│   └── schemas/                       │           (Message processing)
│       └── task_schemas.py            │
│   (HTTP request handling)            │
│                                       │
└── services/                          └── worker/
    └── task_service.py                    ├── chunking.py
        (Business logic for API)           ├── transcriber.py
                                           ├── merger.py
                                           └── processor.py
                                               (Business logic for Consumer)

Shared:
├── core/
│   ├── config.py       (Configuration)
│   ├── database.py     (SQLAlchemy)
│   ├── messaging.py    (RabbitMQ)
│   ├── storage.py      (MinIO)
│   └── logger.py       (Logging)
│
└── repositories/
    ├── models.py       (Job, Chunk models)
    └── task_repository.py
```

**Key Points:**
- ✅ `worker/` = Business logic for consumer (like `services/` for API)
- ✅ `cmd/consumer/main.py` = Entry point (starts RabbitMQ consumer)
- ✅ `internal/consumer/handlers/` = Message handlers (calls worker logic)

---

### **2. Message Queue: RabbitMQ (Not Redis)**

✅ **Using:** RabbitMQ with `aio-pika`
❌ **Removed:** Redis Queue (RQ)

**Why RabbitMQ?**
- ✅ You already have RabbitMQ infrastructure
- ✅ Async message handling with `aio-pika`
- ✅ Supports priority queues, dead letter queues
- ✅ Better for microservices architecture

---

### **3. Storage: MinIO (Not Local Filesystem)**

✅ **Using:** MinIO for object storage
❌ **Removed:** Local file storage

**MinIO Configuration:**
```bash
# .env file
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=stt-audio-files
MINIO_USE_SSL=False
```

**Start MinIO (Docker):**
```bash
docker run -d \
  -p 9000:9000 \
  -p 9001:9001 \
  --name minio \
  -e "MINIO_ROOT_USER=minioadmin" \
  -e "MINIO_ROOT_PASSWORD=minioadmin" \
  -v minio_data:/data \
  minio/minio server /data --console-address ":9001"
```

---

### **4. Chunking Strategy: Consumer Side (After Download)**

**✅ CORRECT Workflow:**

```
1. Client → API: Upload large audio file
2. API: Validate file (size, format)
3. API → MinIO: Upload original file
   └─ Path: "uploads/{job_id}/{original_filename}"
4. API → RabbitMQ: Send message
   └─ Message: {
        "job_id": "abc123",
        "minio_path": "uploads/abc123/audio.mp3",
        "language": "vi",
        "model": "medium"
      }
5. API → Client: Return job_id immediately (HTTP 200)
6. API → Database: Insert job (status=PENDING)

--- API is done, Consumer takes over ---

7. Consumer ← RabbitMQ: Receive message
8. Consumer → Database: Update job (status=PROCESSING)
9. Consumer ← MinIO: Download file to /tmp
10. Consumer: Chunk audio HERE! (chunking.py)
    └─ Chunks saved to: /tmp/stt_processing/{job_id}/chunk_*.wav
11. Consumer: Process each chunk with Whisper (transcriber.py)
12. Consumer: Merge results (merger.py)
13. Consumer → MinIO: Upload result file
    └─ Path: "results/{job_id}/transcription.json"
14. Consumer → Database: Update job (status=COMPLETED)
```

**Why chunk on consumer side?**
- ✅ API responds immediately (fast UX)
- ✅ Consumer handles heavy processing
- ✅ Can retry chunking without re-uploading
- ✅ Parallel processing of multiple jobs

---

## 📋 Step-by-Step Implementation

### **Step 1: Install Dependencies**

```bash
# Activate virtual environment
source myenv/bin/activate

# Install Python packages
pip install -r requirements.txt

# Install system dependencies
# macOS:
brew install ffmpeg

# Ubuntu:
# sudo apt-get install -y ffmpeg libopenblas-dev
```

---

### **Step 2: Start Infrastructure Services**

```bash
# Terminal 1: Start RabbitMQ (if not running)
docker run -d \
  -p 5672:5672 \
  -p 15672:15672 \
  --name rabbitmq \
  -e RABBITMQ_DEFAULT_USER=guest \
  -e RABBITMQ_DEFAULT_PASS=guest \
  rabbitmq:3-management

# Terminal 2: Start MinIO
docker run -d \
  -p 9000:9000 \
  -p 9001:9001 \
  --name minio \
  -e "MINIO_ROOT_USER=minioadmin" \
  -e "MINIO_ROOT_PASSWORD=minioadmin" \
  -v minio_data:/data \
  minio/minio server /data --console-address ":9001"

# Verify services
curl http://localhost:15672  # RabbitMQ UI
curl http://localhost:9001   # MinIO UI
```

---

### **Step 3: Initialize Database**

```bash
# Create storage directory
mkdir -p storage

# Initialize database tables
python -c "from core.database import init_db; init_db()"
```

---

### **Step 4: Update Core Modules**

#### **4.1 Update `core/database.py`**

Replace MongoDB with SQLAlchemy:

```python
"""Database connection using SQLAlchemy."""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from typing import Generator

from core.config import get_settings
from core.logger import get_logger

settings = get_settings()
logger = get_logger(__name__)

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
    pool_pre_ping=True,
    echo=settings.debug
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for database session."""
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
    import repositories.models  # Import models
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialized")

def drop_db():
    """Drop all tables."""
    Base.metadata.drop_all(bind=engine)
```

#### **4.2 ✅ `core/messaging.py` - Already Good!**

Your existing `core/messaging.py` already has RabbitMQ with `aio-pika`. No changes needed!

#### **4.3 ✅ `core/storage.py` - Already Created!**

MinIO client is ready at `core/storage.py`.

---

### **Step 5: Create Repository Models**

Create `repositories/models.py`:

```python
"""Database models for STT system."""
from sqlalchemy import Column, String, Float, Integer, DateTime, Text, Enum as SQLEnum
from sqlalchemy.sql import func
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
    status = Column(SQLEnum(JobStatusEnum), default=JobStatusEnum.PENDING)
    language = Column(String, nullable=False)

    # File information (MinIO paths)
    original_filename = Column(String)
    minio_audio_path = Column(Text)  # Path in MinIO: uploads/{job_id}/file.mp3
    minio_result_path = Column(Text)  # Path in MinIO: results/{job_id}/result.json
    file_size_mb = Column(Float)
    audio_duration_seconds = Column(Float)

    # Processing information
    worker_id = Column(String)
    retry_count = Column(Integer, default=0)
    chunks_total = Column(Integer)
    chunks_completed = Column(Integer, default=0)

    # Results
    transcription_text = Column(Text)
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
    job_id = Column(String, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    start_time = Column(Float)
    end_time = Column(Float)
    transcription = Column(Text)
    status = Column(SQLEnum(JobStatusEnum), default=JobStatusEnum.PENDING)
    error_message = Column(Text)
    processed_at = Column(DateTime(timezone=True))
```

---

### **Step 6: Create Worker Modules**

Now implement the business logic in `worker/` folder (consumer's "services" layer).

#### **6.1 ✅ Already Created:**
- `worker/errors.py` - Error definitions
- `worker/constants.py` - Constants

#### **6.2 Create Worker Modules:**

Copy code from `docs/Implementation.md` for these files:

**`worker/chunking.py`** - Audio chunking logic
- Lines 467-613 in Implementation.md
- Use this AFTER downloading from MinIO

**`worker/transcriber.py`** - Whisper.cpp interface
- Lines 617-751 in Implementation.md

**`worker/merger.py`** - Result merging
- Lines 755-874 in Implementation.md

**`worker/processor.py`** - Main STT processor
- Lines 879-1076 in Implementation.md
- Update to use MinIO instead of local filesystem

---

### **Step 7: Update API Routes**

Update `internal/api/routes/task_routes.py` for STT:

```python
"""STT API routes."""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from sqlalchemy.orm import Session
import uuid
from pathlib import Path
import io

from core.database import get_db
from core.storage import get_minio_client
from core.messaging import MessageBroker
from core.logger import get_logger
from repositories.models import Job, JobStatusEnum

router = APIRouter(prefix="/api/stt", tags=["stt"])
logger = get_logger(__name__)


@router.post("/upload")
async def upload_audio(
    file: UploadFile = File(...),
    language: str = Form("vi"),
    model: str = Form("medium"),
    db: Session = Depends(get_db)
):
    """Upload audio file for transcription."""

    # 1. Validate file
    if not file.filename.endswith(('.mp3', '.wav', '.m4a', '.mp4')):
        raise HTTPException(400, "Unsupported file format")

    # 2. Generate job ID
    job_id = str(uuid.uuid4())

    # 3. Upload to MinIO
    minio_client = get_minio_client()
    file_content = await file.read()
    file_size_mb = len(file_content) / (1024 * 1024)

    minio_path = f"uploads/{job_id}/{file.filename}"
    minio_client.upload_file(
        file_data=io.BytesIO(file_content),
        object_name=minio_path,
        content_type=file.content_type
    )

    logger.info(f"Uploaded to MinIO: {minio_path} ({file_size_mb:.2f} MB)")

    # 4. Create database record
    db_job = Job(
        id=job_id,
        job_id=job_id,
        status=JobStatusEnum.PENDING,
        language=language,
        original_filename=file.filename,
        minio_audio_path=minio_path,
        file_size_mb=file_size_mb
    )
    db.add(db_job)
    db.commit()

    # 5. Send message to RabbitMQ
    message_broker = MessageBroker()
    await message_broker.connect()
    await message_broker.publish({
        "job_id": job_id,
        "minio_path": minio_path,
        "language": language,
        "model": model
    })
    await message_broker.disconnect()

    logger.info(f"Job {job_id} queued for processing")

    # 6. Return job ID
    return {
        "job_id": job_id,
        "status": "PENDING",
        "message": "File uploaded successfully. Processing started."
    }


@router.get("/status/{job_id}")
async def get_status(job_id: str, db: Session = Depends(get_db)):
    """Get job processing status."""
    job = db.query(Job).filter(Job.job_id == job_id).first()

    if not job:
        raise HTTPException(404, "Job not found")

    return {
        "job_id": job.job_id,
        "status": job.status.value,
        "progress": (job.chunks_completed / job.chunks_total * 100) if job.chunks_total else 0,
        "created_at": job.created_at,
        "error_message": job.error_message
    }


@router.get("/result/{job_id}")
async def get_result(job_id: str, db: Session = Depends(get_db)):
    """Get transcription result."""
    job = db.query(Job).filter(Job.job_id == job_id).first()

    if not job:
        raise HTTPException(404, "Job not found")

    if job.status != JobStatusEnum.COMPLETED:
        raise HTTPException(400, f"Job not completed. Status: {job.status.value}")

    return {
        "job_id": job.job_id,
        "status": job.status.value,
        "text": job.transcription_text,
        "minio_result_path": job.minio_result_path,
        "completed_at": job.completed_at
    }
```

---

### **Step 8: Update Consumer**

Update `cmd/consumer/main.py`:

```python
"""Consumer entry point - consumes messages from RabbitMQ."""
import asyncio
from core.messaging import MessageBroker
from core.logger import get_logger
from internal.consumer.handlers.stt_handler import handle_stt_job

logger = get_logger(__name__)


async def main():
    """Start consuming messages from RabbitMQ."""
    logger.info("Starting STT Consumer...")

    message_broker = MessageBroker()
    await message_broker.connect()

    # Start consuming
    await message_broker.consume(
        callback=handle_stt_job,
        shutdown_event=None  # Run forever
    )


if __name__ == "__main__":
    asyncio.run(main())
```

Create `internal/consumer/handlers/stt_handler.py`:

```python
"""STT job message handler."""
from typing import Dict, Any
from core.logger import get_logger
from worker.processor import STTProcessor

logger = get_logger(__name__)


async def handle_stt_job(message: Dict[str, Any]):
    """
    Handle STT job message from RabbitMQ.

    Message format:
    {
        "job_id": "abc123",
        "minio_path": "uploads/abc123/audio.mp3",
        "language": "vi",
        "model": "medium"
    }
    """
    logger.info(f"Received STT job: {message}")

    job_id = message.get("job_id")
    minio_path = message.get("minio_path")
    language = message.get("language", "vi")
    model = message.get("model", "medium")

    # Process job using worker logic
    processor = STTProcessor()
    result = processor.process_job(
        job_id=job_id,
        minio_audio_path=minio_path,
        language=language,
        model=model
    )

    logger.info(f"Job {job_id} processed: {result['status']}")
```

---

## 🚀 Running the System

### **Terminal 1: Start API**
```bash
source myenv/bin/activate
python cmd/api/main.py
```

### **Terminal 2: Start Consumer**
```bash
source myenv/bin/activate
python cmd/consumer/main.py
```

### **Terminal 3: Test Upload**
```bash
curl -X POST \
  -F "file=@test.mp3" \
  -F "language=vi" \
  -F "model=medium" \
  http://localhost:8000/api/stt/upload
```

---

## 📊 Summary

### **✅ What's Updated:**
1. ✅ **RabbitMQ** instead of Redis (using existing `core/messaging.py`)
2. ✅ **MinIO** for object storage (created `core/storage.py`)
3. ✅ **Chunking on consumer side** (after downloading from MinIO)
4. ✅ **Clear structure**: `worker/` = consumer's business logic

### **📁 File Structure:**
```
✅ requirements.txt - RabbitMQ + MinIO dependencies
✅ core/config.py - RabbitMQ + MinIO settings
✅ core/storage.py - MinIO client (NEW)
✅ core/messaging.py - RabbitMQ (EXISTING)
✅ core/database.py - SQLAlchemy (UPDATE)
✅ .env - RabbitMQ + MinIO config

📝 repositories/models.py - Job/Chunk models (CREATE)
📝 worker/*.py - Chunking, Transcriber, Merger, Processor (CREATE)
📝 internal/api/routes/task_routes.py - STT routes (UPDATE)
📝 internal/consumer/handlers/stt_handler.py - Message handler (CREATE)
```

### **Next Steps:**
1. Copy worker modules from `docs/Implementation.md`
2. Update `worker/processor.py` to use MinIO
3. Test end-to-end workflow

**Status:** Infrastructure ready, worker modules pending implementation.
