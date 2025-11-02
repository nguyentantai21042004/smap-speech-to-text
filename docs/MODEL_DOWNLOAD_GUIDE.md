# Whisper Model Download Guide

## 📦 Tổng quan

Dự án sử dụng Whisper models để chuyển đổi giọng nói thành văn bản. Models được lưu trong MinIO và tự động download khi cần.

## 🎯 Vấn đề đã giải quyết

1. **Trước đây:**
   - Model files (>100MB) không thể push lên GitHub
   - Phải commit binary files vào Git
   - Docker images rất nặng
   - Model files missing khi build Docker

2. **Giải pháp hiện tại:**
   - Models lưu trong MinIO (object storage)
   - Tự động download từ MinIO khi cần
   - Docker images nhẹ hơn
   - Không commit model files vào Git

---

## 📥 Cách Download Models

### Option 1: Tự động download (Recommended)

Models sẽ tự động download từ MinIO khi:
- Worker service khởi động (trong Docker)
- Transcription được gọi lần đầu (trong code)

**Trong Docker:**
```bash
docker-compose up worker
# → Entrypoint script tự động download model
```

**Trong code:**
```python
# worker/transcriber.py tự động download nếu model chưa có
transcriber = WhisperTranscriber()
transcriber.transcribe(audio_path, model="medium")  # Auto-download nếu thiếu
```

### Option 2: Download thủ công

**Download tất cả models:**
```bash
python scripts/setup_models.py
```

**Download model cụ thể:**
```bash
# Download chỉ model 'medium'
python scripts/setup_models.py medium

# Download nhiều models
python scripts/setup_models.py tiny base medium
```

### Option 3: Skip download (Development)

Nếu bạn đã có model files local:
```bash
# Đặt biến môi trường
export SKIP_MODEL_DOWNLOAD=true

# Hoặc trong Docker
docker run -e SKIP_MODEL_DOWNLOAD=true ...
```

---

## Available Models

| Model | Size | Quality | Speed | Use Case |
|-------|------|---------|-------|----------|
| `tiny` | 75 MB | ⭐ | ⚡⚡⚡⚡⚡ | Testing, demo |
| `base` | 142 MB | ⭐⭐ | ⚡⚡⚡⚡ | Quick transcription |
| `small` | 466 MB | ⭐⭐⭐ | ⚡⚡⚡ | Balanced |
| `medium` | 1.5 GB | ⭐⭐⭐⭐ | ⚡⚡ | Production (Vietnamese) |
| `large` | 2.9 GB | ⭐⭐⭐⭐⭐ | ⚡ | Best quality |

**Default model:** `medium` (best for Vietnamese)

---

## 🐳 Docker Setup

### 1. Upload Models to MinIO

Trước tiên, upload models lên MinIO:

```bash
# Upload model files to MinIO bucket
# Bucket: stt-audio-files (hoặc theo config)
# Path: whisper-models/ggml-{model}.bin

# Ví dụ với MinIO client:
mc cp whisper/models/ggml-medium.bin minio/stt-audio-files/whisper-models/
```

### 2. Build Docker Image

```bash
# Build worker image (không copy models)
docker build -f cmd/worker/Dockerfile -t stt-worker:latest .
```

**Image size:**
- Trước: ~4-5GB (with models)
- Sau: ~1-2GB (without models)

### 3. Run with Docker Compose

```yaml
# docker-compose.yml
services:
  worker:
    build:
      context: .
      dockerfile: cmd/worker/Dockerfile
    environment:
      # MinIO settings
      MINIO_ENDPOINT: minio:9000
      MINIO_ACCESS_KEY: minioadmin
      MINIO_SECRET_KEY: minioadmin
      MINIO_BUCKET: stt-audio-files
      
      # Model download settings
      SKIP_MODEL_DOWNLOAD: "false"  # Set to "true" to skip
      MODEL_TO_DOWNLOAD: "medium"   # Which model to download
      
    volumes:
      # Optional: Mount models directory to persist downloads
      - ./whisper/models:/app/whisper/models
```

### 4. Start Services

```bash
docker-compose up -d
```

**Luồng hoạt động:**
1. Worker container starts
2. Entrypoint script chạy
3. Check nếu model exists
4. Nếu không → download từ MinIO
5. Start worker process

---

## 🔧 Configuration

### Environment Variables

```bash
# Model download control
SKIP_MODEL_DOWNLOAD=false          # true = skip download
MODEL_TO_DOWNLOAD=medium           # Model to download at startup

# Whisper paths
WHISPER_EXECUTABLE=./whisper/bin/whisper-cli
WHISPER_MODELS_DIR=./whisper/models

# MinIO settings
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=stt-audio-files
```

### Model Storage in MinIO

**MinIO structure:**
```
bucket: stt-audio-files/
  ├── uploads/              # Audio uploads
  ├── results/              # Transcription results
  └── whisper-models/       # Whisper models
      ├── ggml-tiny.bin
      ├── ggml-base.bin
      ├── ggml-small.bin
      ├── ggml-medium.bin
      └── ggml-large.bin
```

---

## Usage Examples

### Example 1: Local Development

```bash
# 1. Upload models to MinIO (one time)
python scripts/setup_models.py medium

# 2. Run worker
rq worker stt_jobs --url redis://localhost:6379/0
```

### Example 2: Docker Development

```bash
# 1. Start infrastructure
docker-compose up -d mongodb redis minio

# 2. Upload models to MinIO
# Use MinIO web UI or client

# 3. Start worker (will auto-download model)
docker-compose up worker
```

### Example 3: Production Deployment

```yaml
# docker-compose.prod.yml
services:
  worker:
    image: your-registry/stt-worker:latest
    environment:
      MINIO_ENDPOINT: ${MINIO_ENDPOINT}
      MINIO_ACCESS_KEY: ${MINIO_ACCESS_KEY}
      MINIO_SECRET_KEY: ${MINIO_SECRET_KEY}
      MODEL_TO_DOWNLOAD: medium
    volumes:
      # Persist models across restarts
      - models_volume:/app/whisper/models
    deploy:
      replicas: 3

volumes:
  models_volume:
```

---

## Troubleshooting

### Issue 1: Model download fails

**Symptoms:**
```
Failed to download model: Model not found in MinIO
```

**Solutions:**
1. Check MinIO is running: `curl http://localhost:9000/minio/health/live`
2. Check model exists in MinIO:
   ```bash
   mc ls minio/stt-audio-files/whisper-models/
   ```
3. Verify MinIO credentials in `.env`
4. Upload model to MinIO:
   ```bash
   mc cp ggml-medium.bin minio/stt-audio-files/whisper-models/
   ```

### Issue 2: Model file corrupted

**Symptoms:**
```
Model file size mismatch: 500MB < 1500MB
```

**Solutions:**
1. Delete corrupted file:
   ```bash
   rm whisper/models/ggml-medium.bin
   ```
2. Re-download:
   ```bash
   python scripts/setup_models.py medium
   ```

### Issue 3: Docker build fails

**Symptoms:**
```
ERROR: whisper/models/ggml-medium.bin not found
```

**Solutions:**
- This is EXPECTED! Models should NOT be in Docker image
- Models will be downloaded at runtime
- Make sure entrypoint script is configured

### Issue 4: Out of disk space

**Symptoms:**
```
OSError: [Errno 28] No space left on device
```

**Solutions:**
1. Check disk space: `df -h`
2. Clean old models: `rm whisper/models/*.bin`
3. Download only needed model:
   ```bash
   export MODEL_TO_DOWNLOAD=tiny  # Smaller model
   ```

---

## 💡 Best Practices

### 1. Model Selection

- **Development:** Use `tiny` or `base` (faster, smaller)
- **Production (Vietnamese):** Use `medium` (best balance)
- **Best quality:** Use `large` (slower, needs more RAM)

### 2. Caching

Models are cached after first download:
- Local: `whisper/models/`
- Docker volume: Persist across container restarts
- MinIO: Single source of truth

### 3. CI/CD

```yaml
# .github/workflows/deploy.yml
- name: Build Docker image
  run: docker build -f cmd/worker/Dockerfile -t worker:latest .
  # No need to include models in image!

- name: Deploy
  run: |
    # Models will be downloaded at runtime from MinIO
    docker-compose up -d
```

### 4. Monitoring

Check model status:
```bash
python scripts/setup_models.py
# Shows which models are available
```

---

## 📚 Implementation Details

### Code Flow

```python
# worker/transcriber.py
class WhisperTranscriber:
    def transcribe(self, audio_path, model="medium"):
        # 1. Check if model exists
        model_downloader = get_model_downloader()
        
        # 2. Download from MinIO if missing
        model_path = model_downloader.ensure_model_exists(model)
        
        # 3. Run Whisper with model
        result = run_whisper(model_path, audio_path)
        return result
```

### Files Structure

```
.
├── worker/
│   ├── model_downloader.py     # Model download logic
│   └── transcriber.py          # Uses model_downloader
├── scripts/
│   ├── setup_models.py         # Manual download script
│   └── docker-entrypoint.sh    # Docker startup script
├── whisper/
│   ├── bin/                    # Whisper executable
│   └── models/                 # Models (gitignored)
│       ├── .gitkeep
│       └── .model_cache.json   # Download cache
└── cmd/
    └── worker/
        └── Dockerfile          # Worker image (no models)
```

---

## Checklist

### For Developers:

- [ ] Upload models to MinIO
- [ ] Configure MinIO credentials in `.env`
- [ ] Run `python scripts/setup_models.py` to test download
- [ ] Verify model exists in `whisper/models/`

### For Docker Deployment:

- [ ] Build image WITHOUT models: `docker build -f cmd/worker/Dockerfile`
- [ ] Verify image size < 2GB
- [ ] Set `MINIO_*` environment variables
- [ ] Test model auto-download on first run
- [ ] (Optional) Use volume to persist models

### For Production:

- [ ] Upload all needed models to MinIO
- [ ] Configure model checksums (optional)
- [ ] Set up model caching strategy
- [ ] Monitor disk space on workers
- [ ] Document model update procedures

---

## 🎉 Summary

**Benefits:**
- No large files in Git
- Smaller Docker images
- Automatic model management
- Easy to update models (just update MinIO)
- Models shared across deployments

**Tradeoffs:**
- First startup slower (download time)
- Requires MinIO setup
- Network dependency (for download)

**Solution:**
- Use Docker volumes to persist models
- Pre-download models in initialization phase
- Monitor MinIO availability

