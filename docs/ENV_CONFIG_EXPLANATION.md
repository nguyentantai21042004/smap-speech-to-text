# Giải thích Chi tiết File .env.example

## Tổng quan

File `.env.example` chứa tất cả các cấu hình môi trường cho hệ thống SMAP Speech-to-Text. File này được đọc bởi `core/config.py` sử dụng Pydantic Settings.

---

## 📋 Phân loại các cấu hình

### 1️⃣ **Cấu hình Bình thường (Standard Config)**
Các cấu hình này là chuẩn cho mọi ứng dụng web:
- `APP_NAME`, `APP_VERSION`, `ENVIRONMENT`, `DEBUG`
- `API_HOST`, `API_PORT`, `API_RELOAD`, `API_WORKERS`
- `MONGODB_URL`, `MONGODB_DATABASE`, `MONGODB_MAX_POOL_SIZE`
- `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`
- `MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`
- `LOG_LEVEL`, `LOG_FILE`

---

## 🎯 Cấu hình Đặc biệt (Special Configs)

### 2️⃣ **Whisper.cpp Settings** ⭐ Đặc biệt

```env
WHISPER_EXECUTABLE=./whisper/whisper.cpp/main
WHISPER_MODELS_DIR=./whisper/whisper.cpp/models
DEFAULT_MODEL=medium
DEFAULT_LANGUAGE=vi
```

**Vai trò:**
- Cấu hình engine STT (Whisper.cpp) để transcribe audio

**Tác động vào source:**
- **CÓ TÁC ĐỘNG** - Được sử dụng trong:
  - `worker/transcriber.py`:
    - `settings.whisper_executable` - Đường dẫn đến file thực thi Whisper
    - `settings.whisper_models_dir` - Thư mục chứa models
    - Dùng để build command chạy Whisper
    - Validate xem file và thư mục có tồn tại không

**Ví dụ sử dụng trong code:**
```python
# worker/transcriber.py:42-67
def _validate_whisper_setup(self):
    if not os.path.exists(settings.whisper_executable):
        raise FileNotFoundError(...)
    
    model_path = os.path.join(settings.whisper_models_dir, f"ggml-{model}.bin")
    command = [settings.whisper_executable, "-m", model_path, ...]
```

**Lưu ý:**
- Nếu `WHISPER_EXECUTABLE` sai → transcription sẽ fail ngay lập tức
- Nếu `WHISPER_MODELS_DIR` sai → không tìm thấy model, transcription fail

---

### 3️⃣ **Audio Chunking Settings** ⭐⭐⭐ RẤT ĐẶC BIỆT

```env
CHUNK_STRATEGY=silence_based
CHUNK_DURATION=30
CHUNK_OVERLAP=3
SILENCE_THRESHOLD=-40
MIN_SILENCE_DURATION=1.0
```

**Vai trò:**
- Cấu hình cách chia nhỏ audio file trước khi transcribe
- Audio dài cần chia nhỏ để xử lý hiệu quả hơn

**Tác động vào source:**
- **CÓ TÁC ĐỘNG MẠNH** - Được sử dụng trong:
  - `worker/chunking.py`: Logic chunking audio
  - `worker/processor.py`: Gọi chunking với settings

**Chi tiết từng field:**

#### `CHUNK_STRATEGY=silence_based`
- **Vai trò:** Chiến lược chia audio
  - `silence_based`: Chia tại điểm im lặng (thông minh hơn)
  - `fixed_duration`: Chia đều theo thời gian
- **Code location:** `worker/chunking.py:84-89`
- **Impact:** Ảnh hưởng đến chất lượng chunk (tránh cắt giữa câu)

#### `CHUNK_DURATION=30`
- **Vai trò:** Độ dài mỗi chunk (giây) - dùng cho `fixed_duration` strategy
- **Code location:** 
  - `worker/chunking.py:219, 288` - Dùng khi fallback
  - `worker/processor.py:255` - Truyền vào AudioChunker
- **Impact:** Chunk quá dài → transcription chậm, chunk quá ngắn → nhiều chunks

#### `SILENCE_THRESHOLD=-40`
- **Vai trò:** Ngưỡng im lặng (dBFS) - âm lượng dưới ngưỡng này coi là im lặng
- **Code location:** `worker/processor.py:257` → `worker/chunking.py:209`
- **Impact:** 
  - Giá trị thấp (-50) → ít chunk hơn (dễ nhầm tiếng ồn là lời nói)
  - Giá trị cao (-30) → nhiều chunk hơn (cắt nhiều hơn)

#### `MIN_SILENCE_DURATION=1.0`
- **Vai trò:** Thời gian im lặng tối thiểu (giây) để được coi là điểm cắt
- **Code location:** `worker/processor.py:256` → convert sang ms → `worker/chunking.py:209`
- **Impact:**
  - Giá trị nhỏ (0.5s) → cắt nhiều hơn (nhạy cảm với pause ngắn)
  - Giá trị lớn (2.0s) → ít cắt hơn (chỉ cắt khi pause dài)

**Ví dụ sử dụng trong code:**
```python
# worker/processor.py:250-258
chunker = AudioChunker()
chunks = chunker.chunk_audio(
    audio_path=audio_path,
    output_dir=chunks_dir,
    strategy=job.chunk_strategy,  # Từ CHUNK_STRATEGY
    chunk_duration=settings.chunk_duration,  # Từ CHUNK_DURATION
    min_silence_len=int(settings.min_silence_duration * 1000),  # Từ MIN_SILENCE_DURATION
    silence_thresh=settings.silence_threshold  # Từ SILENCE_THRESHOLD
)
```

**Lưu ý quan trọng:**
- Nếu `SILENCE_THRESHOLD` không phù hợp → chunks bị cắt không đúng chỗ
- Nếu `MIN_SILENCE_DURATION` quá nhỏ → cắt quá nhiều, mất context
- Nếu `MIN_SILENCE_DURATION` quá lớn → chunks quá dài, transcription chậm

---

### 4️⃣ **Processing Settings (Retry & Timeout)** ⭐⭐ Đặc biệt

```env
MAX_RETRIES=3
RETRY_DELAY=2
JOB_TIMEOUT=3600
CHUNK_TIMEOUT=300
MAX_CONCURRENT_JOBS=4
```

**Vai trò:**
- Cấu hình retry logic và timeout để xử lý lỗi và tránh hang

**Tác động vào source:**
- **CÓ TÁC ĐỘNG** - Được sử dụng trong:

#### `MAX_RETRIES=3`
- **Vai trò:** Số lần retry tối đa khi transcription fail
- **Code location:** `worker/transcriber.py:309`
- **Impact:** 
  - Giá trị cao → resilient hơn nhưng chậm hơn
  - Giá trị thấp → fail nhanh hơn khi gặp lỗi tạm thời

#### `RETRY_DELAY=2`
- **Vai trò:** Thời gian chờ giữa các lần retry (giây)
- **Code location:** (Có thể dùng trong retry logic, cần kiểm tra)
- **Impact:** Delay ngắn → retry nhanh nhưng có thể quá tải

#### `JOB_TIMEOUT=3600` (1 giờ)
- **Vai trò:** Timeout tối đa cho toàn bộ job (từ lúc bắt đầu đến khi hoàn thành)
- **Code location:** `core/messaging.py:115` - Khi enqueue job vào Redis Queue
- **Impact:**
  - Job quá dài sẽ bị kill → tránh hang
  - Giá trị cao → cho phép xử lý audio rất dài

#### `CHUNK_TIMEOUT=300` (5 phút)
- **Vai trò:** Timeout tối đa cho việc transcribe 1 chunk
- **Code location:** `worker/transcriber.py:119`
- **Impact:**
  - Chunk timeout → skip chunk đó, tiếp tục với chunk khác
  - Giá trị thấp → chunk lớn có thể bị timeout
  - Giá trị cao → chờ lâu nếu chunk có vấn đề

**Ví dụ sử dụng trong code:**
```python
# worker/transcriber.py:119
timeout = timeout or settings.chunk_timeout  # Dùng CHUNK_TIMEOUT

# worker/transcriber.py:309
transcription = transcriber.transcribe_with_retry(
    audio_path=chunk['file_path'],
    language=job.language,
    model=job.model_used,
    max_retries=settings.max_retries  # Dùng MAX_RETRIES
)
```

#### `MAX_CONCURRENT_JOBS=4`
- **Vai trò:** Số lượng job có thể xử lý đồng thời
- **Code location:** `cmd/consumer/main.py:53` - Logging only (có thể dùng cho queue concurrency)
- **Impact:** 
  - Giá trị cao → xử lý nhiều job cùng lúc nhưng tốn CPU/RAM
  - Giá trị thấp → ít job đồng thời, an toàn hơn

---

### 5️⃣ **Storage Settings** ⭐ Đặc biệt

```env
TEMP_DIR=/tmp/stt_processing
```

**Vai trò:**
- Thư mục tạm để lưu audio chunks trong quá trình xử lý

**Tác động vào source:**
- **CÓ TÁC ĐỘNG** - Được sử dụng trong:
  - `worker/processor.py`: Tạo temp directory để lưu chunks
  - Mỗi job tạo 1 temp directory riêng trong `TEMP_DIR`

**Ví dụ sử dụng:**
```python
# worker/processor.py:76
temp_dir = tempfile.mkdtemp(prefix=f"stt_{job_id}_")
# Temp dir sẽ được tạo trong hệ thống temp (có thể override bằng TEMP_DIR)
```

**Lưu ý:**
- Cần đảm bảo thư mục có quyền write
- Cần đủ dung lượng để lưu chunks (có thể = kích thước audio)

---

### 6️⃣ **MinIO Settings** ⭐ Quan trọng

```env
MINIO_BUCKET=stt-audio-files
MINIO_USE_SSL=False
```

**Vai trò:**
- Cấu hình object storage cho audio files và results

**Tác động vào source:**
- **CÓ TÁC ĐỘNG** - Được sử dụng trong:
  - `core/storage.py`: MinIOClient initialization
  - `services/task_service.py`: Upload audio lên MinIO
  - `worker/processor.py`: Download audio từ MinIO, upload results

**Code location:**
```python
# core/storage.py:25-38
self.client = Minio(
    settings.minio_endpoint,
    access_key=settings.minio_access_key,
    secret_key=settings.minio_secret_key,
    secure=settings.minio_use_ssl,  # Dùng MINIO_USE_SSL
)
self.bucket_name = settings.minio_bucket_name  # Dùng MINIO_BUCKET
```

---

### 7️⃣ **RabbitMQ Settings** ⚠️ Legacy (Đang được thay thế)

```env
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
RABBITMQ_USER=guest
RABBITMQ_PASSWORD=guest
RABBITMQ_VHOST=/
RABBITMQ_QUEUE_NAME=stt_jobs_queue
RABBITMQ_EXCHANGE_NAME=stt_exchange
RABBITMQ_ROUTING_KEY=stt.job
```

**Vai trò:**
- Cấu hình cho RabbitMQ (đang được thay thế bởi Redis Queue)

**Tác động vào source:**
- ⚠️ **HIỆN TẠI KHÔNG DÙNG** - Đang migration sang Redis Queue
- Code vẫn có trong `core/config.py` nhưng không được sử dụng trong STT processing
- Có thể vẫn dùng cho keyword extraction service (legacy)

---

## 📊 Bảng Tóm tắt: Field nào có tác động thực sự?

| Field | Có tác động? | File sử dụng | Mức độ quan trọng |
|-------|--------------|--------------|-------------------|
| `WHISPER_EXECUTABLE` | **CÓ** | `worker/transcriber.py` | ⭐⭐⭐ Critical |
| `WHISPER_MODELS_DIR` | **CÓ** | `worker/transcriber.py` | ⭐⭐⭐ Critical |
| `DEFAULT_MODEL` | **CÓ** | Có thể dùng khi không specify model | ⭐⭐ High |
| `DEFAULT_LANGUAGE` | **CÓ** | Có thể dùng khi không specify language | ⭐⭐ High |
| `CHUNK_STRATEGY` | **CÓ** | `worker/chunking.py`, `worker/processor.py` | ⭐⭐⭐ Critical |
| `CHUNK_DURATION` | **CÓ** | `worker/chunking.py`, `worker/processor.py` | ⭐⭐⭐ Critical |
| `SILENCE_THRESHOLD` | **CÓ** | `worker/chunking.py`, `worker/processor.py` | ⭐⭐⭐ Critical |
| `MIN_SILENCE_DURATION` | **CÓ** | `worker/chunking.py`, `worker/processor.py` | ⭐⭐⭐ Critical |
| `MAX_RETRIES` | **CÓ** | `worker/transcriber.py` | ⭐⭐ High |
| `CHUNK_TIMEOUT` | **CÓ** | `worker/transcriber.py` | ⭐⭐ High |
| `JOB_TIMEOUT` | **CÓ** | `core/messaging.py` | ⭐⭐ High |
| `MAX_CONCURRENT_JOBS` | ⚠️ **Chưa rõ** | `cmd/consumer/main.py` (chỉ log) | ⭐ Low |
| `TEMP_DIR` | ⚠️ **Có thể** | Hệ thống temp, có thể override | ⭐ Low |
| `MINIO_BUCKET` | **CÓ** | `core/storage.py` | ⭐⭐⭐ Critical |
| `MINIO_USE_SSL` | **CÓ** | `core/storage.py` | ⭐⭐ High |
| `API_WORKERS` | ❌ **KHÔNG** | `cmd/api/main.py` (chỉ log, không dùng) | ⭐ None |
| `RABBITMQ_*` | ❌ **KHÔNG** | Legacy, đang migration | ⭐ None |

---

## ⚠️ Field KHÔNG có tác dụng (Không dùng thực sự)

### `API_WORKERS` - KHÔNG CÓ TÁC DỤNG

```env
API_WORKERS=4
```

**Tình trạng:**
- ❌ **KHÔNG CÓ TÁC ĐỘNG** trong source code hiện tại
- Chỉ được **log ra** (dòng 234 trong `cmd/api/main.py`)
- **KHÔNG được truyền** vào `uvicorn.run()`

**Code hiện tại:**
```python
# cmd/api/main.py:236-242
uvicorn.run(
    "cmd.api.main:app",
    host=settings.api_host,
    port=settings.api_port,
    reload=settings.api_reload,
    log_level="info" if settings.debug else "warning",
    # ❌ THIẾU: workers=settings.api_workers
)
```

**Dockerfile:**
```dockerfile
# cmd/api/Dockerfile:42
CMD ["python", "-m", "uvicorn", "cmd.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
# ❌ THIẾU: --workers
```

**Lý do:**
- Uvicorn không hỗ trợ `--workers` trực tiếp (chỉ hỗ trợ single process)
- Để chạy multiple workers, cần:
  1. Dùng **Gunicorn** với uvicorn worker class
  2. Hoặc dùng `uvicorn --workers` (chỉ có trong uvicorn >= 0.15.0)
  3. Hoặc thêm `workers=settings.api_workers` vào `uvicorn.run()` (nếu version hỗ trợ)

**Để sử dụng `API_WORKERS`:**
1. **Option 1:** Sửa code để truyền vào `uvicorn.run()`:
```python
uvicorn.run(
    "cmd.api.main:app",
    host=settings.api_host,
    port=settings.api_port,
    reload=settings.api_reload,
    workers=settings.api_workers,  # Thêm dòng này
    log_level="info" if settings.debug else "warning",
)
```

2. **Option 2:** Sử dụng Gunicorn (recommended cho production):
```python
# requirements.txt
gunicorn==21.2.0

# Dockerfile CMD
CMD ["gunicorn", "cmd.api.main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000"]
```

3. **Option 3:** Chạy uvicorn trực tiếp với `--workers`:
```dockerfile
CMD ["python", "-m", "uvicorn", "cmd.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

---

## 🎯 Kết luận

### Các field ĐẶC BIỆT và QUAN TRỌNG nhất:

1. **Whisper Settings** (Critical):
   - `WHISPER_EXECUTABLE` - Phải đúng, nếu sai → transcription không chạy được
   - `WHISPER_MODELS_DIR` - Phải đúng, nếu sai → không tìm thấy model

2. **Chunking Settings** (Critical - ảnh hưởng chất lượng):
   - `CHUNK_STRATEGY` - Quyết định cách chia audio
   - `SILENCE_THRESHOLD` - Ảnh hưởng chất lượng chunk (có cắt đúng chỗ không)
   - `MIN_SILENCE_DURATION` - Ảnh hưởng số lượng chunks và chất lượng

3. **Timeout Settings** (High - ảnh hưởng reliability):
   - `CHUNK_TIMEOUT` - Chunk quá lâu sẽ bị timeout
   - `JOB_TIMEOUT` - Job quá lâu sẽ bị kill

4. **Retry Settings** (High):
   - `MAX_RETRIES` - Số lần retry khi fail

**Tất cả các field trên đều có tác động thực sự vào source code và ảnh hưởng đến hoạt động của hệ thống!**

**Ngoại lệ:**
- `API_WORKERS` - **KHÔNG có tác dụng** hiện tại (chỉ để log, cần fix để dùng được)

