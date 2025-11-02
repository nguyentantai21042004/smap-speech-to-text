# Quick Implementation Checklist

## Requirements Summary
- MongoDB for database
- Detailed logging everywhere (using `core.logger`)
- Try-catch everywhere

---

## Files to Create/Update

### Already Exists
- [x] `core/logger.py` - Loguru logger (already configured)
- [x] `core/storage.py` - MinIO client (good logging example)
- [x] `worker/errors.py` - Error classes
- [x] `worker/constants.py` - Constants

---

## Phase 1: Core Infrastructure

### [ ] Task 1: Update Configuration (15 min)
**File:** `core/config.py`
```
Add to Settings class:
- mongodb_url
- mongodb_database
- mongodb_max_pool_size
- mongodb_min_pool_size
- redis_host
- redis_port
- redis_db
- redis_password
```

### [ ] Task 2: Create MongoDB Connection (30 min)
**File:** `core/database.py` (CREATE NEW)
```
Classes/Functions:
- class MongoDB
  - async connect()
  - async disconnect()
  - async get_collection()
  - async health_check()
- async get_database()
- async close_database()

Logging:
Connection attempt
Connection success
Connection failures
Health checks

Error Handling:
try-catch for ALL methods
```

### [ ] Task 3: Update Redis Queue (30 min)
**File:** `core/messaging.py` (UPDATE EXISTING)
```
Replace RabbitMQ with:
- class RedisQueueManager
  - __init__()
  - enqueue_job()
  - get_job_status()
  - get_queue_stats()
  - close()
- get_queue_manager()

Logging:
Redis connection
Job enqueue
Queue stats
Connection errors

Error Handling:
try-catch for ALL operations
```

### [ ] Task 4: Create MongoDB Models (30 min)
**File:** `repositories/models.py` (CREATE NEW)
```
Models:
- class JobStatus(Enum)
- class ChunkModel(BaseModel)
- class JobModel(BaseModel)
  - to_dict()
  - from_dict()
- class JobCreate(BaseModel)
- class JobUpdate(BaseModel)

Logging:
Model creation
Validation errors

Error Handling:
try-catch for dict conversions
```

### [ ] Task 5: Update Task Repository (45 min)
**File:** `repositories/task_repository.py` (UPDATE EXISTING)
```
Update class TaskRepository:
- async create_job()
- async get_job()
- async update_job()
- async update_status()
- async get_pending_jobs()
- async delete_job()

Logging (EVERY method):
Operation start
Success
Failures
Queries

Error Handling:
try-catch for EVERY method
```

---

## Phase 2: Worker Modules

### [ ] Task 6: Create Audio Chunking (45 min)
**File:** `worker/chunking.py` (CREATE NEW)
```
Classes/Functions:
- class AudioChunker
  - chunk_by_silence()
  - chunk_fixed_duration()
  - validate_audio()
- get_audio_duration()

Logging:
File loading
Format detection
Each chunk created
Loading errors
Final statistics

Error Handling:
try-catch for file operations
try-catch for chunking
Validate file exists
Validate format
```

### [ ] Task 7: Create Whisper Transcriber (30 min)
**File:** `worker/transcriber.py` (CREATE NEW)
```
Classes/Functions:
- class WhisperTranscriber
  - transcribe()
  - _build_command()
  - _parse_output()

Logging:
Transcription start
Command construction
Subprocess execution
Success with text length
Process failures
Processing time

Error Handling:
try-catch for subprocess
Handle timeouts
Handle crashes
Validate executable exists
```

### [ ] Task 8: Create Result Merger (30 min)
**File:** `worker/merger.py` (CREATE NEW)
```
Classes/Functions:
- class ResultMerger
  - merge_chunks()
  - remove_duplicates()
  - add_timestamps()

Logging:
Merge start
Each chunk
Completion
Failures

Error Handling:
try-catch for merge
Handle missing chunks
Validate chunk order
```

### [ ] Task 9: Create STT Processor (60 min)
**File:** `worker/processor.py` (CREATE NEW)
```
Main Function:
- async process_stt_job(job_id)
  - Download from MinIO
  - Chunk audio
  - Process chunks
  - Merge results
  - Upload to MinIO
  - Update database

Logging (EXTENSIVE):
Job start
Every step
Step success
Step failures
Metrics

Error Handling:
try-catch for EVERY step
Retry logic
Update job status on errors
```

---

## Phase 3: Services & API

### [ ] Task 10: Update Task Service (45 min)
**File:** `services/task_service.py` (UPDATE EXISTING)
```
Update methods:
- async create_task()
- async get_task_status()
- async get_task_result()

Logging:
Service calls
Operations
Failures

Error Handling:
try-catch for all methods
Validate inputs
```

### [ ] Task 11: Update API Routes (45 min)
**File:** `internal/api/routes/task_routes.py` (UPDATE EXISTING)
```
Update routes:
- POST /api/v1/tasks/upload
- GET /api/v1/tasks/{job_id}
- GET /api/v1/tasks/{job_id}/result

Logging:
Request received
Response sent
Errors
Processing time

Error Handling:
try-catch for endpoints
HTTP error handling
```

---

## Phase 4: Consumer & Initialization

### [ ] Task 12: Create STT Handler (30 min)
**File:** `internal/consumer/handlers/stt_handler.py` (CREATE NEW)
```
Functions:
- handle_stt_job(job_id)

Logging:
Job received
Processing
Failures

Error Handling:
try-catch
Retry transient errors
```

### [ ] Task 13: Update API Main (30 min)
**File:** `cmd/api/main.py` (UPDATE EXISTING)
```
Add:
- MongoDB startup
- MongoDB shutdown
- Health check

Logging:
Startup
Failures

Error Handling:
try-catch for init
```

### [ ] Task 14: Update Consumer Main (30 min)
**File:** `cmd/consumer/main.py` (UPDATE EXISTING)
```
Add:
- MongoDB init
- Redis worker init
- Start processing

Logging:
Worker startup
Failures

Error Handling:
try-catch for init
```

---

## Phase 5: Testing & Config

### [ ] Task 15: Create Test Script (20 min)
**File:** `scripts/test_upload.py` (CREATE NEW)
```
Script to:
- Upload test audio
- Poll status
- Display result
```

### [ ] Task 16: Update Requirements (10 min)
**File:** `requirements.txt` (UPDATE)
```
Add:
motor==3.3.2
pymongo==4.6.1
redis==5.0.1
rq==1.15.1
```

### [ ] Task 17: Create .env Example (10 min)
**File:** `.env.example` (UPDATE)
```
Add:
MONGODB_URL=mongodb://localhost:27017
MONGODB_DATABASE=stt_system
REDIS_HOST=localhost
REDIS_PORT=6379
```

---

## Implementation Order

```
Day 1: Core Infrastructure
├── Task 1 (Config) → 15 min
├── Task 2 (MongoDB) → 30 min
├── Task 3 (Redis) → 30 min
├── Task 4 (Models) → 30 min
└── Task 5 (Repository) → 45 min
    Total: ~2.5 hours

Day 2: Worker Modules
├── Task 6 (Chunking) → 45 min
├── Task 7 (Transcriber) → 30 min
├── Task 8 (Merger) → 30 min
└── Task 9 (Processor) → 60 min
    Total: ~3 hours

Day 3: Services & Integration
├── Task 10 (Service) → 45 min
├── Task 11 (API) → 45 min
├── Task 12 (Handler) → 30 min
├── Task 13 (API Main) → 30 min
└── Task 14 (Consumer Main) → 30 min
    Total: ~3 hours

Day 4: Testing
├── Task 15 (Test Script) → 20 min
├── Task 16 (Requirements) → 10 min
└── Task 17 (.env) → 10 min
    Total: ~40 min
```

**Total Time: ~9 hours**

---

## Logging Template (Copy-Paste Ready)

```python
from core.logger import get_logger

logger = get_logger(__name__)

def example_function(param1, param2):
    """Function with proper logging and error handling."""
    try:
        logger.info(f"Starting operation: param1={param1}, param2={param2}")

        # Do work
        result = do_something()

        logger.info(f"Operation successful: result={result}")
        logger.debug(f"Detailed info: {details}")

        return result

    except SpecificError as e:
        logger.error(f"Specific error occurred: {e}")
        logger.exception("Error details:")
        raise

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        logger.exception("Full error details:")
        raise
```

---

## Async Logging Template

```python
async def example_async_function(param):
    """Async function with proper logging and error handling."""
    try:
        logger.info(f"Starting async operation: param={param}")

        result = await async_operation()

        logger.info(f"Async operation successful: result={result}")
        return result

    except Exception as e:
        logger.error(f"Async operation failed: {e}")
        logger.exception("Error details:")
        raise
```

---

## Quick Test After Each Phase

**Phase 1:**
```bash
# Test MongoDB connection
python -c "import asyncio; from core.database import get_database; asyncio.run(get_database())"
```

**Phase 2:**
```bash
# Test chunking
python -c "from worker.chunking import AudioChunker; AudioChunker().chunk_by_silence('test.mp3')"
```

**Phase 3:**
```bash
# Test API
curl -X POST http://localhost:8000/api/v1/tasks/upload
```

**Phase 4:**
```bash
# Start worker
python cmd/consumer/main.py
```

---

## Ready to Start?

1. [ ] Review this checklist
2. [ ] Set up MongoDB: `docker run -d -p 27017:27017 mongo`
3. [ ] Set up Redis: `docker run -d -p 6379:6379 redis`
4. [ ] Start with Task 1
5. [ ] Check off each task as you complete it
6. [ ] Test after each phase

**Let's build this! 🚀**
