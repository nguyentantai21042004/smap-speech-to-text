# Complete Implementation Schedule - STT System

## Your Requirements
- **Database:** MongoDB (using Motor async driver)
- **Logging:** Detailed logs in ALL logic (using existing loguru logger)
- **Error Handling:** Try-catch everywhere to catch and log bugs

## Implementation Overview

**Total Tasks:** 17
**Estimated Time:** 6-8 hours
**Current Status:** Ready to implement

---

## Phase 1: Core Infrastructure (Tasks 1-5)
Priority: CRITICAL | Est. Time: 2.5 hours

### Task 1: Update MongoDB Configuration
**File:** `core/config.py`
**Time:** 15 min
**Dependencies:** None

**What to add:**
```python
# MongoDB Settings (add to Settings class)
mongodb_url: str = Field(
    default="mongodb://localhost:27017",
    alias="MONGODB_URL"
)
mongodb_database: str = Field(
    default="stt_system",
    alias="MONGODB_DATABASE"
)
mongodb_max_pool_size: int = Field(default=10, alias="MONGODB_MAX_POOL_SIZE")
mongodb_min_pool_size: int = Field(default=1, alias="MONGODB_MIN_POOL_SIZE")

# Redis Settings (for job queue)
redis_host: str = Field(default="localhost", alias="REDIS_HOST")
redis_port: int = Field(default=6379, alias="REDIS_PORT")
redis_db: int = Field(default=0, alias="REDIS_DB")
redis_password: Optional[str] = Field(default=None, alias="REDIS_PASSWORD")
```

**Logging Requirements:**
- Log configuration loading
- Log MongoDB URL (masked password)

**Error Handling:**
- Validate MongoDB URL format
- Handle missing environment variables

---

### Task 2: Create MongoDB Connection
**File:** `core/database.py`
**Time:** 30 min
**Dependencies:** Task 1

**Key Features:**
- Async MongoDB connection using Motor
- Connection pooling
- Health check method
- Detailed logging for all operations

**Logging Points:**
```
Connection attempt
Connection success with pool info
❌ Connection failures with full exception
Collection access
Health check results
Disconnection events
```

**Error Handling:**
- Try-catch for connection
- Try-catch for collection access
- Try-catch for health checks
- Graceful disconnection on errors

---

### Task 3: Update Redis Queue Manager
**File:** `core/messaging.py`
**Time:** 30 min
**Dependencies:** Task 1

**Key Features:**
- Replace RabbitMQ with Redis Queue (RQ)
- Priority queues (high, normal, low)
- Job status tracking
- Queue statistics

**Logging Points:**
```
Redis connection attempt
Queue initialization
Job enqueue with job_id
Job status queries
❌ Connection failures
❌ Enqueue failures
```

**Error Handling:**
- Try-catch for Redis connection
- Try-catch for job operations
- Handle queue full scenarios

---

### Task 4: Create MongoDB Models
**File:** `repositories/models.py`
**Time:** 30 min
**Dependencies:** None

**Models to Create:**
1. **JobStatus** (Enum)
2. **ChunkModel** (Pydantic)
3. **JobModel** (Pydantic)
4. **JobCreate** (Pydantic)
5. **JobUpdate** (Pydantic)

**Logging Points:**
```
Model creation from dict
❌ Validation errors
Model to dict conversion
```

**Error Handling:**
- Try-catch for model validation
- Try-catch for dict conversion
- Log validation errors with details

---

### Task 5: Update Task Repository
**File:** `repositories/task_repository.py`
**Time:** 45 min
**Dependencies:** Task 2, Task 4

**Methods to Implement:**
- `create_job()` - Create new job
- `get_job()` - Get job by ID
- `update_job()` - Update job
- `update_status()` - Update job status
- `get_pending_jobs()` - Get pending jobs
- `delete_job()` - Delete job

**Logging Points (EVERY method):**
```
Operation start with parameters
Success with result details
❌ Failure with exception
🔍 Query operations
⚠️ Warning conditions (not found, etc.)
```

**Error Handling:**
- Try-catch for ALL database operations
- Specific error messages for each operation type
- Log full exception stack trace

---

## Phase 2: Worker Modules (Tasks 6-9)
Priority: HIGH | Est. Time: 3 hours

### Task 6: Create Audio Chunking Module
**File:** `worker/chunking.py`
**Time:** 45 min
**Dependencies:** None

**Key Features:**
- Silence-based chunking using pydub
- Fixed-duration chunking as fallback
- Audio validation
- Chunk metadata generation

**Logging Points:**
```
Audio file loading with path and size
Audio format detection
Duration calculation
🔍 Silence detection parameters
Each chunk creation with timestamps
❌ Audio loading errors
❌ Chunking failures
📊 Final chunk statistics (count, avg duration)
```

**Error Handling:**
- Try-catch for file loading
- Try-catch for format conversion
- Try-catch for silence detection
- Try-catch for chunk extraction
- Validate audio file exists
- Validate audio format supported
- Handle corrupted audio files

---

### Task 7: Create Whisper Transcriber
**File:** `worker/transcriber.py`
**Time:** 30 min
**Dependencies:** None

**Key Features:**
- Whisper.cpp subprocess execution
- Language detection support
- Model selection
- Output parsing

**Logging Points:**
```
Transcription start with chunk info
Whisper command construction
🔍 Subprocess execution details
Transcription success with text length
❌ Whisper process failures
❌ Timeout errors
📊 Processing time for each chunk
```

**Error Handling:**
- Try-catch for subprocess execution
- Try-catch for output parsing
- Handle Whisper crashes
- Handle timeouts
- Validate model file exists
- Validate executable exists

---

### Task 8: Create Result Merger
**File:** `worker/merger.py`
**Time:** 30 min
**Dependencies:** None

**Key Features:**
- Merge chunk transcriptions
- Remove duplicate text at boundaries
- Add timestamps
- Generate final result

**Logging Points:**
```
Merge start with chunk count
🔍 Processing each chunk with index
Boundary overlap detection
Merge completion with final text length
❌ Merge failures
```

**Error Handling:**
- Try-catch for merge operations
- Handle missing chunks
- Handle empty transcriptions
- Validate chunk order

---

### Task 9: Create Main STT Processor
**File:** `worker/processor.py`
**Time:** 60 min
**Dependencies:** Task 5, Task 6, Task 7, Task 8

**Key Features:**
- Main orchestration logic
- Download from MinIO
- Process chunks in parallel/serial
- Upload results to MinIO
- Update job status in MongoDB

**Logging Points:**
```
Job processing start with job_id
🔍 Download audio from MinIO
Audio download success
🔍 Chunking audio
Chunks created with count
🔍 Processing each chunk
Chunk transcription success
❌ Chunk transcription failure
🔍 Merging results
Merge success
🔍 Uploading results to MinIO
Upload success
🔍 Updating job status
Job completion
❌ Any failures with retry count
📊 Total processing time
📊 Performance metrics
```

**Error Handling (EXTENSIVE):**
- Try-catch for EVERY operation
- Try-catch for MinIO download
- Try-catch for chunking
- Try-catch for each chunk processing
- Try-catch for merging
- Try-catch for MinIO upload
- Try-catch for database updates
- Retry logic with exponential backoff
- Update job status on each error
- Log retry attempts

---

## Phase 3: Services & API (Tasks 10-11)
Priority: HIGH | Est. Time: 1.5 hours

### Task 10: Update Task Service
**File:** `services/task_service.py`
**Time:** 45 min
**Dependencies:** Task 5

**Methods to Update:**
- `create_task()` - Create and enqueue job
- `get_task_status()` - Get job status
- `get_task_result()` - Get transcription result

**Logging Points:**
```
Service method called with parameters
File upload to MinIO
Job creation in database
Job enqueue to Redis
❌ Any failures
📊 File size and format info
```

**Error Handling:**
- Try-catch for file validation
- Try-catch for MinIO operations
- Try-catch for database operations
- Try-catch for queue operations
- Validate file format
- Validate file size

---

### Task 11: Update API Routes
**File:** `internal/api/routes/task_routes.py`
**Time:** 45 min
**Dependencies:** Task 10

**Routes to Update:**
- `POST /api/v1/tasks/upload` - Upload audio
- `GET /api/v1/tasks/{job_id}` - Get status
- `GET /api/v1/tasks/{job_id}/result` - Get result

**Logging Points:**
```
Request received with endpoint
Request validation success
❌ Validation errors
🔍 Service call
Response sent with status code
❌ Any errors
📊 Request processing time
```

**Error Handling:**
- Try-catch for request validation
- Try-catch for service calls
- HTTP error handling (400, 404, 500)
- Return detailed error messages

---

## Phase 4: Consumer & Handlers (Tasks 12-14)
Priority: HIGH | Est. Time: 1.5 hours

### Task 12: Create STT Handler
**File:** `internal/consumer/handlers/stt_handler.py`
**Time:** 30 min
**Dependencies:** Task 9

**Key Features:**
- Handle job from queue
- Call processor
- Update job status
- Error handling and retry

**Logging Points:**
```
Job received from queue
Job processing started
Processing success
❌ Processing failure
🔍 Retry attempts
📊 Processing metrics
```

**Error Handling:**
- Try-catch for job processing
- Distinguish transient vs permanent errors
- Retry transient errors
- Mark permanent errors as failed
- Log all error details

---

### Task 13: Update API Main
**File:** `cmd/api/main.py`
**Time:** 30 min
**Dependencies:** Task 2

**Updates:**
- Initialize MongoDB on startup
- Close MongoDB on shutdown
- Add health check endpoint

**Logging Points:**
```
Application startup
MongoDB connection
Application ready
❌ Startup failures
Shutdown initiated
```

**Error Handling:**
- Try-catch for MongoDB init
- Graceful shutdown on errors

---

### Task 14: Update Consumer Main
**File:** `cmd/consumer/main.py`
**Time:** 30 min
**Dependencies:** Task 2, Task 3, Task 12

**Updates:**
- Initialize MongoDB
- Initialize Redis workers
- Start job processing

**Logging Points:**
```
Worker startup
MongoDB connection
Redis connection
Worker ready
🔍 Job processing
❌ Any failures
```

**Error Handling:**
- Try-catch for all initializations
- Graceful worker shutdown

---

## Phase 5: Testing & Dependencies (Tasks 15-17)
Priority: MEDIUM | Est. Time: 1 hour

### Task 15: Create Test Script
**File:** `scripts/test_upload.py`
**Time:** 20 min

**Features:**
- Upload test audio
- Poll for status
- Display result

**Logging:** Use print statements for user feedback

---

### Task 16: Update Requirements
**File:** `requirements.txt`
**Time:** 10 min

**Add:**
```
motor==3.3.2          # MongoDB async driver
pymongo==4.6.1        # MongoDB sync driver
redis==5.0.1          # Redis client
rq==1.15.1            # Redis Queue
```

---

### Task 17: Create .env Example
**File:** `.env.example`
**Time:** 10 min

**Include all MongoDB and Redis settings**

---

## Logging Standards (APPLY TO ALL TASKS)

### Log Levels
- **DEBUG:** Detailed diagnostic info, variable values
- **INFO:** General operations, success messages (✅)
- **WARNING:** Unexpected but handled situations (⚠️)
- **ERROR:** Errors that need attention (❌)
- **EXCEPTION:** Errors with full stack trace

### Log Format
```python
from core.logger import get_logger
logger = get_logger(__name__)

# Info
logger.info(f"Operation successful: details={value}")

# Debug
logger.debug(f"🔍 Processing: step={step}, data={data}")

# Error
logger.error(f"❌ Operation failed: {error}")
logger.exception("Full error details:")  # Logs stack trace
```

### Required Logging Points
1. Function entry with parameters
2. Function exit with results
3. Every database operation
4. Every external service call (MinIO, Whisper)
5. Every error with full details
6. Performance metrics (time, size)

---

## Error Handling Standards (APPLY TO ALL TASKS)

### Pattern 1: Simple Try-Catch
```python
try:
    logger.info(f"Starting operation: {params}")
    result = do_operation()
    logger.info(f"Operation successful: {result}")
    return result
except SpecificError as e:
    logger.error(f"❌ Specific error: {e}")
    logger.exception("Error details:")
    raise
except Exception as e:
    logger.error(f"❌ Unexpected error: {e}")
    logger.exception("Full error details:")
    raise
```

### Pattern 2: Try-Catch with Retry
```python
for attempt in range(max_retries):
    try:
        logger.info(f"Attempt {attempt + 1}/{max_retries}")
        result = do_operation()
        logger.info(f"Success on attempt {attempt + 1}")
        return result
    except TransientError as e:
        logger.warning(f"⚠️ Transient error on attempt {attempt + 1}: {e}")
        if attempt == max_retries - 1:
            logger.error(f"❌ All retries exhausted")
            raise
        time.sleep(retry_delay)
    except PermanentError as e:
        logger.error(f"❌ Permanent error: {e}")
        raise
```

### Pattern 3: Async Try-Catch
```python
async def operation():
    try:
        logger.info(f"Starting async operation")
        result = await async_operation()
        logger.info(f"Async operation successful")
        return result
    except Exception as e:
        logger.error(f"❌ Async operation failed: {e}")
        logger.exception("Error details:")
        raise
```

---

## Implementation Order

**Week 1: Core Infrastructure**
1. Task 1 → Task 2 → Task 3 → Task 4 → Task 5

**Week 1: Worker Modules**
2. Task 6 → Task 7 → Task 8 → Task 9

**Week 2: Services & API**
3. Task 10 → Task 11 → Task 12

**Week 2: Integration**
4. Task 13 → Task 14 → Task 15

**Week 2: Finalization**
5. Task 16 → Task 17

---

## Testing Checklist

After each phase:

**Phase 1:**
- [ ] MongoDB connection works
- [ ] Redis connection works
- [ ] Can create/read jobs in MongoDB

**Phase 2:**
- [ ] Can chunk audio files
- [ ] Whisper transcription works
- [ ] Can merge results

**Phase 3:**
- [ ] API endpoints respond
- [ ] File upload works
- [ ] Status retrieval works

**Phase 4:**
- [ ] Worker processes jobs
- [ ] Jobs complete successfully
- [ ] Errors are logged

**Phase 5:**
- [ ] End-to-end test passes
- [ ] All logs are detailed
- [ ] Error handling works

---

## Success Criteria

All 17 tasks completed
MongoDB integration working
Detailed logs in ALL files
Try-catch in ALL functions
End-to-end test passing
No silent failures
All errors logged with stack traces

---

## Next Steps

1. Review this schedule
2. Set up MongoDB and Redis locally
3. Start with Task 1 (Config updates)
4. Follow the implementation order
5. Test after each phase
6. Verify logging and error handling in each file

**Ready to start? Let's begin with Task 1!**
