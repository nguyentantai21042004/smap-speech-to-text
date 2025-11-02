# 🚀 STT System - Quick Implementation Guide

This is your complete guide to finish the Speech-to-Text system. Follow these steps in order.

## What's Already Done

1. `requirements.txt` - Updated with STT dependencies
2. `core/config.py` - Redis + SQLite configuration
3. `.env` - STT settings
4. `worker/errors.py` - Error definitions
5. `worker/constants.py` - Constants
6. Whisper.cpp built in `whisper/` directory

---

## 📋 Step-by-Step Implementation

### **STEP 1: Install Dependencies**

```bash
# Activate virtual environment
source myenv/bin/activate

# Install Python packages
pip install -r requirements.txt

# Install ffmpeg (for audio processing)
# macOS:
brew install ffmpeg

# Ubuntu/Debian:
# sudo apt-get install -y ffmpeg
```

---

### **STEP 2: Setup Project Structure**

```bash
# Create necessary directories
mkdir -p storage/uploads storage/results logs worker

# Create __init__.py files
touch worker/__init__.py
```

---

### **STEP 3: Run This Script to Create All Files**

Save this as `setup_stt.sh` and run it:

```bash
#!/bin/bash

# This script creates all necessary Python files for the STT system

echo "🚀 Setting up STT System files..."

# 1. Update core/database.py
cat > core/database.py << 'EOF'
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
    pool_pre_ping=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@contextmanager
def get_db_context():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    import repositories.models
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialized")

def drop_db():
    Base.metadata.drop_all(bind=engine)
EOF

# 2. Update core/messaging.py
cat > core/messaging.py << 'EOF'
"""Redis Queue management."""
import redis
from rq import Queue
from typing import Optional, Any, Dict
from core.config import get_settings
from core.logger import get_logger

settings = get_settings()
logger = get_logger(__name__)

class RedisQueueManager:
    def __init__(self):
        self.redis_conn = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            password=settings.redis_password
        )
        self.queue_high = Queue('stt_jobs_high', connection=self.redis_conn)
        self.queue_normal = Queue('stt_jobs', connection=self.redis_conn)
        self.queue_low = Queue('stt_jobs_low', connection=self.redis_conn)

    def enqueue_job(self, func_name: str, args: tuple = (), priority: str = "normal", **kwargs):
        queue = self.queue_high if priority == "high" else (self.queue_low if priority == "low" else self.queue_normal)
        job = queue.enqueue(func_name, args=args, job_timeout=settings.job_timeout, **kwargs)
        logger.info(f"Job {job.id} enqueued")
        return job

_queue_manager: Optional[RedisQueueManager] = None

def get_queue_manager() -> RedisQueueManager:
    global _queue_manager
    if _queue_manager is None:
        _queue_manager = RedisQueueManager()
    return _queue_manager
EOF

# 3. Create repositories/models.py
cat > repositories/models.py << 'EOF'
"""Database models."""
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
    __tablename__ = "jobs"
    id = Column(String, primary_key=True)
    job_id = Column(String, unique=True, index=True, nullable=False)
    status = Column(SQLEnum(JobStatusEnum), default=JobStatusEnum.PENDING)
    language = Column(String, nullable=False)
    original_filename = Column(String)
    file_path = Column(Text)
    file_size_mb = Column(Float)
    audio_duration_seconds = Column(Float)
    worker_id = Column(String)
    retry_count = Column(Integer, default=0)
    chunks_total = Column(Integer)
    chunks_completed = Column(Integer, default=0)
    transcription_text = Column(Text)
    result_file_path = Column(Text)
    error_message = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
EOF

echo "Files created successfully!"
echo ""
echo "Next steps:"
echo "1. Run: chmod +x setup_stt.sh && ./setup_stt.sh"
echo "2. Initialize database: python -c 'from core.database import init_db; init_db()'"
echo "3. Start Redis: redis-server"
echo "4. Refer to docs/WORKER_MODULES.md for worker implementation"
echo "5. Refer to docs/API_UPDATES.md for API route updates"
```

Make it executable and run:

```bash
chmod +x setup_stt.sh
./setup_stt.sh
```

---

### **STEP 4: Initialize Database**

```bash
# Create database tables
python -c "from core.database import init_db; init_db()"
```

---

### **STEP 5: Install and Start Redis**

```bash
# Install Redis (if not installed)
# macOS:
brew install redis

# Ubuntu:
# sudo apt-get install redis-server

# Start Redis server
redis-server

# Test Redis connection (in another terminal)
redis-cli ping
# Should return: PONG
```

---

### **STEP 6: Next Implementation Steps**

The following modules still need to be implemented. Refer to `docs/Implementation.md` for complete code:

#### **Worker Modules** (Follow Implementation.md Step 5)
- `worker/chunking.py` - Audio chunking logic
- `worker/transcriber.py` - Whisper.cpp interface
- `worker/merger.py` - Result merging
- `worker/processor.py` - Main STT processor

#### **Services** (Adapt existing pattern)
- Update `services/task_service.py` for STT job management
- Remove LLM-related services (keyword_service.py, sentiment_service.py)

#### **API Routes** (Adapt existing pattern)
- Update `internal/api/routes/task_routes.py` for:
  - POST `/upload` - Upload audio file
  - GET `/status/{job_id}` - Check job status
  - GET `/result/{job_id}` - Get transcription result
  - GET `/download/{job_id}` - Download result file

#### **Consumer/Worker** (Update existing)
- Update `cmd/consumer/main.py` to process STT jobs using RQ worker

---

### **STEP 7: Quick Test**

```bash
# Terminal 1: Start API
source myenv/bin/activate
python cmd/api/main.py

# Terminal 2: Start Worker
source myenv/bin/activate
python cmd/consumer/main.py

# Terminal 3: Test upload (create test script)
curl -X POST -F "file=@test.mp3" -F "language=vi" http://localhost:8000/api/upload
```

---

## 📚 Reference Documents

- **`docs/Implementation.md`** - Complete code for all modules (Steps 5-9)
- **`docs/Speech-to-Text.md`** - System specification
- **`README.md`** - Project overview

---

## 🏃 Running the System (After Full Implementation)

```bash
# 1. Activate environment
source myenv/bin/activate

# 2. Start Redis (Terminal 1)
redis-server

# 3. Start API (Terminal 2)
python cmd/api/main.py

# 4. Start Worker (Terminal 3)
python cmd/consumer/main.py

# 5. Test (Terminal 4)
python scripts/test_stt.py sample_audio.mp3
```

---

## ⚙️ Configuration Tips

### For Development (Default)
- Uses **SQLite** (`storage/stt.db`)
- **Redis** on localhost:6379
- **Whisper model**: medium
- **Language**: Vietnamese (vi)

### For Production
Update `.env`:
```bash
DATABASE_URL=postgresql://user:pass@localhost:5432/stt_db
REDIS_HOST=your-redis-host
DEFAULT_MODEL=large-v3
```

---

## 🐛 Troubleshooting

### "Module not found" errors
```bash
# Make sure you're in the project root and virtual env is activated
pwd  # Should show: /path/to/smap-speech-to-text
source myenv/bin/activate
```

### Redis connection errors
```bash
# Check if Redis is running
redis-cli ping

# Start Redis if not running
redis-server
```

### Whisper executable not found
```bash
# Verify whisper.cpp is built
ls -la whisper/whisper.cpp/main

# Should exist and be executable
# If not, rebuild whisper.cpp (see Implementation.md Step 2)
```

### Database errors
```bash
# Reinitialize database
python -c "from core.database import drop_db, init_db; drop_db(); init_db()"
```

---

## 📞 Next Steps

1. Complete Steps 1-5 above
2. 📖 Read `docs/Implementation.md` for complete worker module code
3. 💻 Implement worker modules (chunking, transcriber, merger, processor)
4. 🔌 Update API routes and services
5. ⚡ Update consumer to use RQ worker
6. Test end-to-end workflow

**Current Status:** Infrastructure ready, Worker modules pending implementation

**Est. Time to Complete:** 2-4 hours (copy-paste code from Implementation.md)
