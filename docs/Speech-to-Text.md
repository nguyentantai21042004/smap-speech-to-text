# Đặc Tả Yêu Cầu Kỹ Thuật (SRS) - Hệ Thống Speech-to-Text Bất Đồng Bộ

## I. Tổng Quan Dự Án

| Thuộc tính         | Chi tiết                                                                           |
|--------------------|------------------------------------------------------------------------------------|
| Tên dự án          | Hệ thống Chuyển giọng nói thành văn bản Bất đồng bộ (Async STT System)            |
| Mục tiêu           | Xây dựng một dịch vụ STT phi thương mại, độ chính xác cao (tiếng Anh & tiếng Việt), hoạt động hiệu quả trên cơ sở hạ tầng chỉ có CPU. |
| Ràng buộc chính    | Không GPU, Không phí API bên thứ ba. Tốc độ xử lý chấp nhận chậm (bất đồng bộ).    |
| Công nghệ lõi      | whisper.cpp (cho hiệu năng tối ưu trên CPU)                                        |

---

## II. Yêu Cầu Chức Năng (Functional Requirements)

| Mã yêu cầu | Mô tả                                                                                      |
|------------|--------------------------------------------------------------------------------------------|
| FR1.0      | **Upload Audio:** Hệ thống phải cung cấp một API endpoint để người dùng tải lên file audio/video. |
| FR1.1      | **Hỗ trợ định dạng:** Phải hỗ trợ các định dạng input phổ biến (.mp3, .wav, .m4a, .mp4, v.v.). |
| FR2.0      | **Xử lý Bất đồng bộ:** Sau khi nhận file, API phải phản hồi ngay lập tức với một Job ID và không giữ kết nối chờ đợi quá trình chuyển đổi. |
| FR3.0      | **Chuyển đổi Ngôn ngữ:** Model phải hỗ trợ nhận dạng và chuyển đổi cho tiếng Anh (EN) và tiếng Việt (VI). |
| FR4.0      | **Kiểm tra trạng thái:** Cung cấp API endpoint để người dùng kiểm tra trạng thái của Job ID (Ví dụ: PENDING, PROCESSING, COMPLETED, FAILED).|
| FR5.0      | **Lấy kết quả:** Khi trạng thái là COMPLETED, người dùng có thể tải về file text (hoặc JSON) chứa toàn bộ nội dung đã được chuyển đổi. |

---

## III. Yêu Cầu Phi Chức Năng (Non-Functional Requirements)

| Mã yêu cầu | Mô tả                                                                                       |
|------------|---------------------------------------------------------------------------------------------|
| NFR1.0     | **Tốc độ xử lý (CPU):** Cần tối ưu model whisper.cpp (dùng quantization 4-bit/5-bit) để đạt tốc độ tốt nhất có thể trên CPU.    |
| NFR2.0     | **Độ bền vững:** Hệ thống phải sử dụng hàng đợi (Queue) để đảm bảo Job không bị mất nếu Worker bị lỗi hoặc khởi động lại.           |
| NFR3.0     | **Khả năng mở rộng:** Kiến trúc Worker (xử lý) phải dễ dàng mở rộng theo chiều ngang (thêm nhiều Worker chạy trên nhiều CPU server khác nhau).|
| NFR4.0     | **Tính chính xác:** Sử dụng Model Whisper lớn nhất có thể chạy ổn định trên CPU (ví dụ: medium hoặc large-v3 quantized).           |

---

## IV. Kiến Trúc Hệ Thống (Architectural Design)

Hệ thống sẽ được chia thành ba thành phần chính:

### 1. API Gateway (Frontend Service)
- **Mục đích:** Nhận yêu cầu từ người dùng và quản lý trạng thái Job.
- **Công nghệ:** Python (FastAPI/Flask) hoặc Node.js.
- **Chức năng:**
  - Nhận file audio.
  - Lưu trữ file gốc (hoặc metadata) vào Storage (ví dụ: Local Disk, S3).
  - Tạo một Job ID duy nhất và lưu trạng thái PENDING vào Database.
  - Đẩy thông điệp (Job) vào Message Queue.
  - Trả về Job ID cho người dùng.

### 2. Message Queue (Hàng đợi)
- **Mục đích:** Đảm bảo luồng công việc ổn định và xử lý bất đồng bộ.
- **Công nghệ đề xuất:** Redis Queue (RQ) (đơn giản, dễ dùng với Python) hoặc RabbitMQ (mạnh mẽ hơn).
- **Nội dung Job:** Chứa thông tin cần thiết: Job ID, Đường dẫn đến file audio, Model/Ngôn ngữ cần dùng.

### 3. Worker Processes (Backend/Processing)
- **Mục đích:** Thực hiện công việc STT tốn kém CPU.
- **Công nghệ:** Python Worker (chạy whisper.cpp qua subprocess).
- **Chức năng:**
  - Lấy Job: Lấy một Job từ Message Queue.
  - Tiền xử lý & Chunking: Dùng pydub (hoặc ffmpeg) để chuẩn hóa và chia audio thành các Chunks (theo khoảng lặng).
  - Xử lý STT: Lặp qua từng Chunk, gọi whisper.cpp để phiên âm.
  - Tổng hợp: Nối các đoạn văn bản từ các Chunk lại theo đúng thứ tự.
  - Lưu kết quả: Lưu văn bản cuối cùng vào Database (liên kết với Job ID).
  - Cập nhật trạng thái: Chuyển trạng thái Job sang COMPLETED (hoặc FAILED).

---

## V. Các Thư Viện và Công Cụ Chính

| Loại        | Công cụ đề xuất           | Vai trò                                                         |
|-------------|--------------------------|------------------------------------------------------------------|
| Core STT    | whisper.cpp (Quantized)  | Lõi xử lý Speech-to-Text tối ưu cho CPU                          |
| Tiền xử lý  | pydub, ffmpeg            | Xử lý định dạng audio, chia nhỏ (chunking) file                  |
| Hàng đợi    | Redis Queue (RQ) / Redis | Quản lý và phân phối các Job STT                                 |
| Lập trình   | Python 3.x               | Ngôn ngữ chính cho API Gateway và Worker                         |
| Database    | PostgreSQL/MongoDB       | Lưu trữ metadata Job, trạng thái, và kết quả text cuối cùng      |

---

## VI. Chunking Strategy (Chiến Lược Chia Nhỏ Audio)

### 6.1 Giới Thiệu Vấn Đề

Khi xử lý file audio dài (>5 phút) với Whisper trên CPU:
- **Vấn đề 1:** Memory tăng đột ngột → OOM (Out of Memory)
- **Vấn đề 2:** Không thể khôi phục nếu crash giữa chừng
- **Vấn đề 3:** Thời gian xử lý quá lâu → UX tệ

**Giải pháp:** Chia audio thành các chunk nhỏ, xử lý tuần tự, merge kết quả.

---

### 6.2 Thuật Toán Chunking Chi Tiết

#### **Phương Pháp 1: Fixed-Size Chunking (Đơn Giản, Khuyến Nghị Ban Đầu)**

```
Quy tắc:
- Chunk size: 30 giây (có thể tuning từ 20-60s)
- Overlap: 5 giây (giữ ngữ cảnh khi merge)
- Max silence threshold: 1.5 giây

Ví dụ: File 2 phút (120s)
- Chunk 1: 0s → 30s
- Chunk 2: 25s → 55s (overlap 5s)
- Chunk 3: 50s → 80s (overlap 5s)
- Chunk 4: 75s → 105s (overlap 5s)
- Chunk 5: 100s → 120s (overlap 5s)
```

**Ưu điểm:**
- Dễ implement
- Memory usage dự đoán được
- Dễ debug

**Nhược điểm:**
- ❌ Có thể cut giữa một từ
- ❌ Xử lý chậm vì dư thừa overlap

---

#### **Phương Pháp 2: Silence-Based Chunking (Tối Ưu, Khuyến Nghị)**

```
Quy tắc:
- Threshold âm lượng (dB): -40dB (silence)
- Min silence duration: 1.0 giây (tối thiểu để cut)
- Max chunk duration: 45 giây (tránh chunk quá dài)
- Min chunk duration: 5 giây (tránh quá nhỏ)
- Overlap: 3 giây

Ví dụ:
Audio: [....SPEECH....1s_SILENCE....SPEECH....0.5s_SILENCE....SPEECH....]
                     ↑ (cắt ở đây)                           ↑ (không cắt, <1s)

Kết quả chunks sẽ tự nhiên nằm tại các điểm tạm dừng → kết quả nối tốt hơn
```

**Ưu điểm:**
- Cắt tại điểm tự nhiên → merge kết quả mượt hơn
- Ít overlap → tiết kiệm processing time
- Độ chính xác cao hơn (khỏe từ lỡ cut giữa từ)

**Nhược điểm:**
- ❌ Phức tạp hơn
- ❌ Cần pre-processing để detect silence
- ❌ Có thể fail với audio nhiều tiếng ồn

---

### 6.3 Recommendation: Hybrid Approach (BEST PRACTICE)

```python
# Pseudocode
def chunk_audio(audio_path, language='vi'):
    """
    Chia audio thành chunks với hybrid strategy
    """
    audio = load_audio(audio_path)
    duration = get_duration(audio)

    # Step 1: Try silence-based chunking
    chunks = detect_chunks_by_silence(
        audio,
        silence_threshold=-40,  # dB
        min_silence=1.0,        # giây
        max_chunk=45,           # giây
        min_chunk=5,            # giây
    )

    # Step 2: Fallback to fixed-size if silence detection fails
    if len(chunks) == 0 or chunks contain very long chunks:
        chunks = chunk_fixed_size(audio, chunk_size=30, overlap=5)

    # Step 3: Add overlap context
    chunks_with_overlap = add_overlap_context(chunks, overlap_duration=3)

    return chunks_with_overlap
```

---

### 6.4 Merge Strategy (Nối Kết Quả)

**Vấn đề:** Khi merge text từ các chunk, có thể bị duplicate từ (do overlap).

**Giải pháp - Simple Merge (Đủ tốt):**

```python
def merge_transcriptions(chunk_results, overlap_duration=3):
    """
    chunk_results = [
        {"chunk_id": 0, "start": 0, "end": 30, "text": "Hello world"},
        {"chunk_id": 1, "start": 25, "end": 55, "text": "world is beautiful"},
        ...
    ]

    Strategy: Keep only non-overlapping part from each chunk
    """
    if not chunk_results:
        return ""

    final_text = ""

    for i, result in enumerate(chunk_results):
        text = result["text"]

        if i == 0:
            # First chunk: use all
            final_text += text
        else:
            # Remove overlap words from beginning
            # (simple: remove first N words that likely overlap)
            words = text.split()
            overlap_words = estimate_overlap_words(overlap_duration)

            final_text += " " + " ".join(words[overlap_words:])

    return final_text.strip()

def estimate_overlap_words(overlap_duration):
    """
    Ước lượng: ~150 words/minute = 2.5 words/second
    3 giây overlap ≈ 7-8 từ
    """
    return int(overlap_duration * 2.5)
```

**Giải pháp - Advanced (Tối Ưu):**

```python
def merge_with_nlp(chunk_results):
    """
    Dùng NLP để smart merge (nếu có thời gian/resource)
    - Detect sentence boundaries
    - Remove exact duplicate phrases
    - Use Levenshtein distance để fuzzy match
    """
    # Có thể implement sau nếu merge simple không tốt
    pass
```

---

### 6.5 Configuration Recommendation

```yaml
# config.yaml
CHUNKING:
  # Strategy: 'silence_based' hoặc 'fixed_size'
  strategy: 'silence_based'

  # For silence-based chunking
  silence_threshold: -40              # dB (detect silence)
  min_silence_duration: 1.0           # giây
  max_chunk_duration: 45              # giây
  min_chunk_duration: 5               # giây
  overlap_duration: 3                 # giây

  # For fixed-size chunking (fallback)
  fixed_chunk_size: 30                # giây
  fixed_overlap_size: 5               # giây

  # Merge strategy
  merge_method: 'word_based'          # 'word_based' hoặc 'nlp_based'

PROCESSING:
  # Languages supported
  languages:
    - 'en'
    - 'vi'

  # Timeout per chunk (để tránh infinite processing)
  chunk_timeout: 300                  # giây (5 phút)
  max_chunks_per_job: 200             # safety limit
```

---

### 6.6 Testing Strategy cho Chunking

```python
# Unit tests cần có
def test_chunking():
    """
    Test case 1: Short audio (10s) → 1 chunk
    Test case 2: Medium audio (60s) → 3-4 chunks
    Test case 3: Long audio (600s) → ~15 chunks
    Test case 4: Audio with much silence → chunks at right positions
    Test case 5: Audio with no silence → fallback to fixed size
    Test case 6: Merge không có duplicate → độ dài text hợp lý
    """
    pass
```

---

---

## VII. Error Handling & Retry Logic

### 7.1 Error Categories

#### **Category A: Transient Errors (Có thể Retry)**

| Error | Nguyên nhân | Retry? | Strategy |
|-------|-----------|--------|----------|
| OOM (Out of Memory) | Chunk quá lớn | Có | Reduce chunk size + retry |
| Timeout | Processing lâu | Có | Extend timeout + retry |
| Temporary Network | Network hiccup | Có | Exponential backoff |
| Whisper Crash | Model bug hiếm | Có | Restart worker + retry |

#### **Category B: Permanent Errors (Không nên Retry)**

| Error | Nguyên nhân | Retry? | Action |
|-------|-----------|--------|--------|
| Invalid Audio Format | File corrupt | ❌ Không | → FAILED, notify user |
| Unsupported Language | Lang không support | ❌ Không | → FAILED immediately |
| File Too Large | >2GB | ❌ Không | → FAILED, check limits |
| Disk Full | Storage hết chỗ | Có (1 lần) | Alert admin, then FAILED |

---

### 7.2 Retry Policy Detail

#### **Policy Configuration:**

```yaml
RETRY_POLICY:
  # Transient errors
  max_retries: 3

  # Exponential backoff
  initial_delay: 2              # giây
  max_delay: 300                # giây (5 phút)
  backoff_multiplier: 3         # exponential: 2s → 6s → 18s
  jitter: true                  # thêm random để tránh thundering herd

  # Dead letter queue (sau khi fail tất cả retries)
  dead_letter_enabled: true
  dead_letter_ttl: 604800       # giây (7 ngày lưu logs)
```

#### **Retry Flow:**

```
Job Start
    ↓
Processing
    ↓
ERROR OCCUR?
    ↓
    YES → Is Transient Error?
          ↓
          YES → Retry Count < 3?
                ↓
                YES → Wait(exponential_backoff) → Requeue job
                ↓
                NO → Send to Dead Letter Queue
          ↓
          NO → Send to Dead Letter Queue
    ↓
    NO → Continue
    ↓
Job Complete/Failed
```

---

### 7.3 Implementation Detail

#### **Step 1: Define Error Types**

```python
# errors.py
class STTError(Exception):
    """Base STT Error"""
    pass

class TransientError(STTError):
    """Có thể retry"""
    def __init__(self, message, retry_count=0):
        self.message = message
        self.retry_count = retry_count
        super().__init__(self.message)

class PermanentError(STTError):
    """Không retry"""
    pass

# Specific errors
class OutOfMemoryError(TransientError):
    pass

class TimeoutError(TransientError):
    pass

class InvalidAudioFormatError(PermanentError):
    pass

class UnsupportedLanguageError(PermanentError):
    pass
```

---

#### **Step 2: Worker Processing Loop**

```python
# worker.py
import time
import logging
from rq import Worker
from rq.job import JobStatus

logger = logging.getLogger(__name__)

def process_stt_job(job_id, audio_path, language):
    """
    Main worker function
    """
    try:
        logger.info(f"Processing job {job_id}")

        # Step 1: Validate input
        validate_audio_file(audio_path)
        validate_language(language)

        # Step 2: Chunk audio
        chunks = chunk_audio(audio_path)

        # Step 3: Process each chunk
        results = []
        for i, chunk in enumerate(chunks):
            try:
                result = transcribe_chunk(chunk, language)
                results.append(result)
                logger.info(f"Chunk {i} completed")
            except TransientError as e:
                logger.warning(f"Chunk {i} transient error: {e}")
                raise  # Re-raise để worker handle retry

        # Step 4: Merge results
        final_text = merge_transcriptions(results)

        logger.info(f"Job {job_id} completed successfully")
        return {
            "status": "COMPLETED",
            "text": final_text,
            "segments": results
        }

    except PermanentError as e:
        logger.error(f"Job {job_id} permanent error: {e}")
        return {
            "status": "FAILED",
            "error": str(e),
            "error_type": type(e).__name__
        }

    except TransientError as e:
        logger.error(f"Job {job_id} transient error: {e}")
        # Không handle ở đây, để RQ handle retry
        raise

# Worker wrapper (để RQ trigger retry)
def worker_process_with_retry(job_id, audio_path, language):
    """
    Wrapper để RQ retry trên TransientError
    """
    try:
        return process_stt_job(job_id, audio_path, language)
    except TransientError as e:
        # RQ sẽ tự động retry dựa vào config
        raise
```

---

#### **Step 3: Job Enqueue with Retry Config**

```python
# api.py (API Gateway)
from rq import Queue
from rq.job import Job
import redis

redis_conn = redis.Redis()
queue = Queue('stt_jobs', connection=redis_conn)

@app.post("/api/transcribe")
def transcribe_audio(file: UploadFile):
    """
    Upload audio file → Enqueue job
    """
    # Save file
    file_path = save_uploaded_file(file)

    # Enqueue job with retry config
    job = queue.enqueue(
        'worker.worker_process_with_retry',
        args=(generate_job_id(), file_path, 'vi'),
        job_timeout=600,  # 10 minutes timeout per attempt
        result_ttl=86400,  # Keep result 24 hours
        failure_ttl=604800,  # Keep failed job 7 days
        retry=Retry(
            max=3,
            interval=[2, 6, 18]  # Exponential: 2s, 6s, 18s
        )
    )

    return {
        "job_id": job.id,
        "status": "PENDING"
    }
```

---

#### **Step 4: Dead Letter Queue Handler**

```python
# dead_letter_handler.py
def handle_dead_letter_job(job):
    """
    Callback: gọi khi job fail sau tất cả retries
    """
    logger.error(f"Job {job.id} moved to DLQ after {job.meta.get('retry_count', 0)} retries")

    # Update database: mark job as FAILED
    db.update_job_status(
        job_id=job.id,
        status="FAILED",
        error_message=str(job.exc_info),
        final_retry_count=job.meta.get('retry_count', 0)
    )

    # Optional: Send notification to user/admin
    send_notification(
        user_id=job.meta.get('user_id'),
        message=f"Transcription job {job.id} failed after 3 retries"
    )

    # Optional: Store job details for investigation
    archive_failed_job(job)

# Register callback
worker.push_job_done_callback(handle_dead_letter_job)
```

---

### 7.4 Monitoring & Alerting

```yaml
MONITORING:
  # Metrics to track
  metrics:
    - job_success_rate      # % jobs completed successfully
    - job_failure_rate      # % jobs failed permanently
    - avg_retry_count       # average retries per job
    - chunk_processing_time # per chunk duration
    - total_processing_time # job completion time

  # Alerts
  alerts:
    - If retry_rate > 20% → Investigate (possible memory issue)
    - If avg_retry_count > 1.5 → Alert (too many retries)
    - If DLQ_queue_depth > 100 → Critical alert
    - If worker_crash > 5/hour → Restart worker service
```

---

### 7.5 User-Facing Error Messages

```python
# Mapping lỗi backend → Message cho user
ERROR_MESSAGES = {
    "InvalidAudioFormatError": "File audio không hỗ trợ. Hãy thử .mp3, .wav, hoặc .m4a",
    "UnsupportedLanguageError": "Ngôn ngữ không được hỗ trợ. Chỉ hỗ trợ: English, Tiếng Việt",
    "OutOfMemoryError": "File quá lớn. Vui lòng dùng file < 500MB",
    "TimeoutError": "Xử lý quá lâu. Hãy thử lại hoặc liên hệ support",
    "GenericError": "Có lỗi xảy ra. Vui lòng thử lại sau"
}
```

---

---

## VIII. Dockerfile Configuration

### 8.1 Multi-Stage Build Dockerfile (Tối Ưu)

```dockerfile
# Stage 1: Builder - compile whisper.cpp
FROM ubuntu:22.04 as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    git \
    wget \
    libopenblas-dev \
    && rm -rf /var/lib/apt/lists/*

# Clone and build whisper.cpp
WORKDIR /build
RUN git clone https://github.com/ggerganov/whisper.cpp.git
WORKDIR /build/whisper.cpp
RUN make -j$(nproc)

# Download quantized models (small, medium)
RUN bash ./models/download-ggml-model.sh small  # ~500MB
RUN bash ./models/download-ggml-model.sh medium # ~1.5GB

---

# Stage 2: Runtime - Python application
FROM python:3.11-slim-bookworm

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libopenblas0 \
    ffmpeg \
    redis-server \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy whisper.cpp from builder
COPY --from=builder /build/whisper.cpp/main /app/bin/whisper.cpp
COPY --from=builder /build/whisper.cpp/models /app/models/

# Copy Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY api/ ./api/
COPY worker/ ./worker/
COPY config.yaml ./

# Create non-root user for security
RUN useradd -m -u 1000 sttuser
USER sttuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# Default command (can override)
CMD ["python", "-m", "api.main"]

# Expose ports
EXPOSE 8000 6379
```

---

### 8.2 Docker Compose (Full Stack)

```yaml
# docker-compose.yml
version: '3.9'

services:
  # API Gateway
  api:
    build:
      context: .
      dockerfile: Dockerfile
      target: runtime
    ports:
      - "8000:8000"
    environment:
      - REDIS_URL=redis://redis:6379
      - DATABASE_URL=postgresql://user:pass@postgres:5432/stt_db
      - LOG_LEVEL=INFO
    depends_on:
      - redis
      - postgres
    volumes:
      - ./uploaded_files:/app/uploaded_files
      - ./results:/app/results
    command: python -m api.main
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Worker Process (múi multiple instances)
  worker:
    build:
      context: .
      dockerfile: Dockerfile
      target: runtime
    depends_on:
      - redis
      - postgres
    environment:
      - REDIS_URL=redis://redis:6379
      - DATABASE_URL=postgresql://user:pass@postgres:5432/stt_db
      - LOG_LEVEL=INFO
      - WORKER_CONCURRENCY=2  # 2 concurrent jobs per worker
    volumes:
      - ./uploaded_files:/app/uploaded_files
      - ./results:/app/results
    command: rq worker stt_jobs --with-scheduler
    deploy:
      replicas: 3  # 3 worker instances = 6 concurrent jobs max

  # Message Queue (Redis)
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Database (PostgreSQL)
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: sttuser
      POSTGRES_PASSWORD: sttpass
      POSTGRES_DB: stt_db
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/init.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U sttuser"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Optional: Monitoring Dashboard (Redis Commander)
  redis-commander:
    image: rediscommander/redis-commander:latest
    environment:
      - REDIS_HOSTS=local:redis:6379
    ports:
      - "8081:8081"
    depends_on:
      - redis

volumes:
  redis_data:
  postgres_data:
```

---

### 8.3 Build & Run Commands

```bash
# Build image
docker build -t stt-system:latest .

# Run with Docker Compose
docker-compose up -d

# Scale workers
docker-compose up -d --scale worker=5

# View logs
docker-compose logs -f worker

# Stop all
docker-compose down

# Clean up volumes
docker-compose down -v
```

---

### 8.4 Dockerfile Optimization Tips

| Technique | Benefit | Example |
|-----------|---------|---------|
| Multi-stage build | Reduce final image size (remove build tools) | Used above |
| Layer caching | Faster rebuild | Put `pip install` trước `COPY code` |
| .dockerignore | Smaller build context | Exclude `*.log`, `__pycache__`, etc |
| Non-root user | Security | `USER sttuser` |
| Health checks | Automatic restart on failure | `HEALTHCHECK --interval=30s` |
| Slim base images | Smaller size | `python:3.11-slim-bookworm` |

---

### 8.5 Resource Limits (docker-compose)

```yaml
services:
  api:
    deploy:
      resources:
        limits:
          cpus: '2'        # Max 2 CPU cores
          memory: 2G       # Max 2GB RAM
        reservations:
          cpus: '1'
          memory: 1G

  worker:
    deploy:
      resources:
        limits:
          cpus: '4'        # 4 cores per worker (for STT processing)
          memory: 6G       # 6GB RAM per worker
        reservations:
          cpus: '2'
          memory: 3G
```

---

---

## Summary Table

| Aspect | Recommendation |
|--------|-----------------|
| **Chunking** | Silence-based (hybrid with fixed-size fallback) |
| **Chunk Duration** | 30-45 seconds |
| **Overlap** | 3-5 seconds |
| **Max Retries** | 3 times |
| **Retry Backoff** | Exponential: 2s → 6s → 18s |
| **Dockerfile** | Multi-stage build, slim base, health checks |
| **Docker Compose** | 3 workers × 2 concurrency = 6 total jobs parallel |
| **Error Handling** | Transient (retry) vs Permanent (fail fast) |
