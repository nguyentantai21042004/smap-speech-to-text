# ✅ Answers to Your Questions

## Question 1: Project Structure

**Your Question:**
> "My previous structure also have a place to put logic of consumer, cmd/consumer is an entry point, and logic need to put to folder worker (it place a role like folder services of api? if it is, i agree)"

**Answer: YES, Exactly! ✅**

```
API Architecture:                  Consumer Architecture:
┌──────────────────────┐          ┌──────────────────────┐
│ cmd/api/main.py      │          │ cmd/consumer/main.py │
│ (Entry Point)        │          │ (Entry Point)        │
└──────────┬───────────┘          └──────────┬───────────┘
           │                                  │
           ▼                                  ▼
┌──────────────────────┐          ┌──────────────────────┐
│ internal/api/routes/ │          │ internal/consumer/   │
│ (HTTP Handlers)      │          │ handlers/            │
│                      │          │ (Message Handlers)   │
└──────────┬───────────┘          └──────────┬───────────┘
           │                                  │
           ▼                                  ▼
┌──────────────────────┐          ┌──────────────────────┐
│ services/            │          │ worker/              │
│ (Business Logic)     │          │ (Business Logic)     │
│ - task_service.py    │          │ - chunking.py        │
│ - etc.               │          │ - transcriber.py     │
└──────────────────────┘          │ - merger.py          │
                                  │ - processor.py       │
                                  └──────────────────────┘
```

**The Parallel:**
- `services/` for API = `worker/` for Consumer
- Both contain the **business logic layer**
- Entry points (`cmd/`) just bootstrap and route to logic

✅ **You are absolutely correct!**

---

## Question 2: Message Queue

**Your Question:**
> "About msg, queue, i prefer keep RabbitMQ instead of Redis, reverse rabbit and remove Redis"

**Answer: DONE! ✅**

### **What Changed:**

#### **Removed:**
- ❌ Redis Queue (RQ)
- ❌ `redis` package
- ❌ `rq` package
- ❌ `rq-scheduler` package

#### **Kept:**
- ✅ RabbitMQ with `aio-pika`
- ✅ Your existing `core/messaging.py` (already had RabbitMQ!)
- ✅ RabbitMQ configuration in `.env`

### **Updated Files:**

1. **`requirements.txt`**
   ```python
   # OLD (Removed):
   # redis==5.0.1
   # rq==1.15.1
   # rq-scheduler==0.13.1

   # NEW (Kept):
   aio-pika==9.3.1  # RabbitMQ async client
   ```

2. **`core/config.py`**
   ```python
   # OLD (Removed):
   # redis_host, redis_port, redis_db, redis_password

   # NEW (Kept):
   rabbitmq_host: str
   rabbitmq_port: int
   rabbitmq_user: str
   rabbitmq_password: str
   rabbitmq_queue_name: str
   rabbitmq_exchange_name: str
   rabbitmq_routing_key: str
   ```

3. **`.env`**
   ```bash
   # OLD (Removed):
   # REDIS_HOST=localhost
   # REDIS_PORT=6379

   # NEW (Kept):
   RABBITMQ_HOST=localhost
   RABBITMQ_PORT=5672
   RABBITMQ_USER=guest
   RABBITMQ_PASSWORD=guest
   RABBITMQ_QUEUE_NAME=stt_jobs_queue
   RABBITMQ_EXCHANGE_NAME=stt_exchange
   RABBITMQ_ROUTING_KEY=stt.job
   ```

✅ **RabbitMQ is now the only message queue system!**

---

## Question 3: Storage with MinIO

**Your Question:**
> "keep going with logic of this whisper, api for earning large file, and upload to storage (here, if need, put env for MinIO and config connection)"

**Answer: DONE! ✅**

### **What Added:**

1. **MinIO Configuration in `core/config.py`**
   ```python
   # MinIO (Object Storage)
   minio_endpoint: str = "localhost:9000"
   minio_access_key: str = "minioadmin"
   minio_secret_key: str = "minioadmin"
   minio_bucket_name: str = "stt-audio-files"
   minio_use_ssl: bool = False
   ```

2. **MinIO Environment Variables in `.env`**
   ```bash
   # MinIO Configuration
   MINIO_ENDPOINT=localhost:9000
   MINIO_ACCESS_KEY=minioadmin
   MINIO_SECRET_KEY=minioadmin
   MINIO_BUCKET=stt-audio-files
   MINIO_USE_SSL=False
   ```

3. **Created `core/storage.py`** - MinIO Client
   ```python
   class MinIOClient:
       def upload_file(...)      # Upload to MinIO
       def download_file(...)    # Download from MinIO
       def get_file_stream(...)  # Stream file
       def delete_file(...)      # Delete from MinIO
       def file_exists(...)      # Check existence
       def get_file_info(...)    # Get metadata
       def generate_presigned_url(...)  # Temporary URL
   ```

### **How to Use:**

```python
from core.storage import get_minio_client

# Upload file
minio = get_minio_client()
minio.upload_file(
    file_data=file_stream,
    object_name="uploads/job123/audio.mp3"
)

# Download file
minio.download_file(
    object_name="uploads/job123/audio.mp3",
    local_path="/tmp/audio.mp3"
)
```

### **Start MinIO Server:**

```bash
docker run -d \
  -p 9000:9000 \
  -p 9001:9001 \
  --name minio \
  -e "MINIO_ROOT_USER=minioadmin" \
  -e "MINIO_ROOT_PASSWORD=minioadmin" \
  -v minio_data:/data \
  minio/minio server /data --console-address ":9001"

# Access MinIO UI: http://localhost:9001
# Username: minioadmin
# Password: minioadmin
```

✅ **MinIO is fully configured and ready!**

---

## Question 4: Where to Chunk Audio?

**Your Question:**
> "Consumer earn file, chuck (i do not know many places to chunk file ?? when earn a requern api ? or when donwload file from storage ?)"

**Answer: Chunk AFTER downloading from MinIO (Consumer Side) ✅**

### **Complete Workflow:**

```
┌─────────────────────────────────────────────────────────────┐
│ CLIENT                                                        │
└───────────────────────────┬───────────────────────────────────┘
                            │
                            │ 1. Upload audio file
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ API (cmd/api/main.py)                                        │
│                                                               │
│ 2. Validate file (size, format)                              │
│ 3. Generate job_id                                           │
│ 4. Upload to MinIO                                           │
│    └─ Path: uploads/{job_id}/audio.mp3                       │
│ 5. Save job to database (status=PENDING)                     │
│ 6. Send message to RabbitMQ                                  │
│    └─ Message: {                                             │
│         "job_id": "abc123",                                  │
│         "minio_path": "uploads/abc123/audio.mp3",            │
│         "language": "vi"                                     │
│       }                                                       │
│ 7. Return job_id to client (HTTP 200) ← FAST!                │
└───────────────────────────┬───────────────────────────────────┘
                            │
                            │ RabbitMQ Message
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ CONSUMER (cmd/consumer/main.py)                              │
│                                                               │
│ 8. Receive message from RabbitMQ                             │
│ 9. Update database (status=PROCESSING)                       │
│ 10. Download from MinIO to /tmp                              │
│     └─ Local: /tmp/stt_processing/{job_id}/audio.mp3         │
│                                                               │
│ 11. ★ CHUNK AUDIO HERE! (worker/chunking.py) ★              │
│     └─ Split into chunks: /tmp/.../chunk_0001.wav            │
│                            /tmp/.../chunk_0002.wav            │
│                            ...                                │
│                                                               │
│ 12. Process each chunk (worker/transcriber.py)               │
│     └─ Call whisper.cpp for each chunk                       │
│                                                               │
│ 13. Merge results (worker/merger.py)                         │
│     └─ Combine all chunk transcriptions                      │
│                                                               │
│ 14. Upload result to MinIO                                   │
│     └─ Path: results/{job_id}/transcription.json             │
│                                                               │
│ 15. Update database (status=COMPLETED)                       │
│                                                               │
│ 16. Clean up /tmp files                                      │
└─────────────────────────────────────────────────────────────┘
```

### **Why Chunk on Consumer Side?**

| Aspect | API Side Chunking | Consumer Side Chunking |
|--------|------------------|------------------------|
| **API Response Time** | ❌ Slow (must chunk before responding) | ✅ Fast (respond immediately) |
| **Resource Usage** | ❌ API server CPU overload | ✅ Consumer server handles it |
| **Scalability** | ❌ Limited by API capacity | ✅ Can scale consumers independently |
| **Retry Logic** | ❌ Must re-upload on failure | ✅ Just retry processing |
| **File Size** | ❌ Risk of request timeout | ✅ No timeout issues |

### **Code Flow:**

**API Side** (`internal/api/routes/task_routes.py`):
```python
@router.post("/upload")
async def upload_audio(file: UploadFile, ...):
    # 1. Upload to MinIO (full file, no chunking)
    minio.upload_file(file, f"uploads/{job_id}/{filename}")

    # 2. Send message to RabbitMQ
    await message_broker.publish({
        "job_id": job_id,
        "minio_path": f"uploads/{job_id}/{filename}"
    })

    # 3. Return immediately
    return {"job_id": job_id, "status": "PENDING"}
```

**Consumer Side** (`worker/processor.py`):
```python
class STTProcessor:
    def process_job(self, job_id, minio_path, language):
        # 1. Download from MinIO
        local_path = f"/tmp/{job_id}/audio.mp3"
        minio.download_file(minio_path, local_path)

        # 2. ★ CHUNK HERE! ★
        chunker = AudioChunker()
        chunks = chunker.chunk_audio(local_path)
        # → Returns: [chunk_0001.wav, chunk_0002.wav, ...]

        # 3. Process each chunk
        results = []
        for chunk in chunks:
            result = transcriber.transcribe(chunk.path)
            results.append(result)

        # 4. Merge
        final_text = merger.merge_results(results)

        # 5. Upload result to MinIO
        minio.upload_file(final_text, f"results/{job_id}/result.json")

        return {"status": "COMPLETED"}
```

✅ **Chunking happens in `worker/chunking.py` after downloading from MinIO!**

---

## 🎯 Summary of Changes

### **✅ Completed:**

1. **Requirements Updated**
   - ✅ Removed: Redis, RQ
   - ✅ Added: MinIO client (`minio`)
   - ✅ Kept: RabbitMQ (`aio-pika`)

2. **Configuration Updated**
   - ✅ `core/config.py` - RabbitMQ + MinIO settings
   - ✅ `.env` - RabbitMQ + MinIO environment variables
   - ✅ Removed all Redis configuration

3. **New Files Created**
   - ✅ `core/storage.py` - MinIO client with full API
   - ✅ `worker/errors.py` - Error definitions
   - ✅ `worker/constants.py` - Constants

4. **Documentation Created**
   - ✅ `docs/UPDATED_IMPLEMENTATION_GUIDE.md` - Complete guide
   - ✅ `docs/ANSWERS_TO_QUESTIONS.md` - This file!

### **📝 To Do Next:**

1. **Create Worker Modules** (copy from `docs/Implementation.md`):
   - `worker/chunking.py` - Audio chunking (use AFTER downloading from MinIO)
   - `worker/transcriber.py` - Whisper.cpp interface
   - `worker/merger.py` - Result merging
   - `worker/processor.py` - Main processor (download → chunk → process → upload)

2. **Update API Routes**:
   - `internal/api/routes/task_routes.py` - Upload to MinIO, send to RabbitMQ

3. **Create Consumer Handler**:
   - `internal/consumer/handlers/stt_handler.py` - Process RabbitMQ messages

4. **Create Repository Models**:
   - `repositories/models.py` - Job and Chunk models (with MinIO paths)

---

## 🚀 Quick Start

```bash
# 1. Install dependencies
source myenv/bin/activate
pip install -r requirements.txt

# 2. Start services
docker run -d -p 5672:5672 -p 15672:15672 --name rabbitmq rabbitmq:3-management
docker run -d -p 9000:9000 -p 9001:9001 --name minio \
  -e MINIO_ROOT_USER=minioadmin -e MINIO_ROOT_PASSWORD=minioadmin \
  minio/minio server /data --console-address ":9001"

# 3. Initialize database
python -c "from core.database import init_db; init_db()"

# 4. Follow UPDATED_IMPLEMENTATION_GUIDE.md for next steps
```

---

## 📖 Reference Documents

- **`docs/UPDATED_IMPLEMENTATION_GUIDE.md`** - Complete implementation guide
- **`docs/Implementation.md`** - Full code for worker modules
- **`docs/Speech-to-Text.md`** - System specification

**All your questions are answered! Ready to implement! 🎉**
