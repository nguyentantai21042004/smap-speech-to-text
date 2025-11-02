# Quick Start: Model Setup

## 🚀 5-Minute Setup Guide

### Step 1: Start Infrastructure

```bash
# Start MongoDB, Redis, and MinIO
docker-compose -f docker-compose.models.yml up -d mongodb redis minio
```

**Wait for services to be healthy (~30 seconds)**

### Step 2: Upload Model to MinIO

**Option A: Using MinIO Web UI**

1. Open MinIO Console: http://localhost:9001
2. Login: `minioadmin` / `minioadmin`
3. Create bucket: `stt-audio-files`
4. Create folder: `whisper-models/`
5. Upload file: `ggml-medium.bin` to `whisper-models/`

**Option B: Using MinIO Client (mc)**

```bash
# Install mc
brew install minio/stable/mc  # macOS
# or download from: https://min.io/docs/minio/linux/reference/minio-mc.html

# Configure
mc alias set myminio http://localhost:9000 minioadmin minioadmin

# Create bucket
mc mb myminio/stt-audio-files

# Upload model
mc cp whisper/models/ggml-medium.bin myminio/stt-audio-files/whisper-models/

# Verify
mc ls myminio/stt-audio-files/whisper-models/
```

**Option C: Using Python Script**

```python
# scripts/upload_models_to_minio.py
from minio import Minio

client = Minio(
    "localhost:9000",
    access_key="minioadmin",
    secret_key="minioadmin",
    secure=False
)

# Create bucket
if not client.bucket_exists("stt-audio-files"):
    client.make_bucket("stt-audio-files")

# Upload model
client.fput_object(
    "stt-audio-files",
    "whisper-models/ggml-medium.bin",
    "whisper/models/ggml-medium.bin"
)

print("Model uploaded!")
```

### Step 3: Start Worker (Will Auto-Download Model)

```bash
# Start worker service
docker-compose -f docker-compose.models.yml up worker

# Check logs
docker logs smap-worker -f
```

**Expected output:**
```
================================================
SMAP Speech-to-Text - Starting...
================================================
Checking Whisper models...
📥 Downloading model: medium
Downloading model 'medium' from MinIO: whisper-models/ggml-medium.bin
Expected size: 1500MB
📥 Downloading to: /app/whisper/models/ggml-medium.bin
Download complete: 1500.00MB
Model downloaded and validated: medium
Model ready!
================================================
🚀 Starting application...
================================================
```

### Step 4: Start API

```bash
# Start API service
docker-compose -f docker-compose.models.yml up api
```

### Step 5: Test Transcription

```bash
# Upload audio file
curl -X POST http://localhost:8000/api/v1/tasks/upload \
  -F "file=@test_audio.mp3" \
  -F "language=vi" \
  -F "model=medium"

# Response:
{
  "status": "success",
  "job_id": "abc123...",
  "message": "Task created and queued for processing"
}

# Check status
curl http://localhost:8000/api/v1/tasks/{job_id}/status

# Get result
curl http://localhost:8000/api/v1/tasks/{job_id}/result
```

---

## 🔧 Troubleshooting

### Problem: Model download fails

```
❌ Model not found in MinIO: whisper-models/ggml-medium.bin
```

**Solution:**
1. Verify MinIO is running: `docker ps | grep minio`
2. Check model exists:
   ```bash
   mc ls myminio/stt-audio-files/whisper-models/
   ```
3. Upload model again (see Step 2)

### Problem: Worker fails to start

```
❌ Failed to download model
```

**Solution:**
1. Check MinIO connection:
   ```bash
   curl http://localhost:9000/minio/health/live
   ```
2. Check MinIO credentials in `docker-compose.models.yml`
3. Try manual download:
   ```bash
   docker exec -it smap-worker python scripts/setup_models.py medium
   ```

### Problem: Out of disk space

```
OSError: [Errno 28] No space left on device
```

**Solution:**
1. Check disk space: `df -h`
2. Clean Docker volumes:
   ```bash
   docker-compose down -v
   docker system prune -a
   ```
3. Use smaller model: `MODEL_TO_DOWNLOAD=tiny`

---

## Environment Variables

Create `.env` file:

```bash
# MinIO
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=stt-audio-files

# MongoDB
MONGODB_ROOT_USER=admin
MONGODB_ROOT_PASSWORD=admin123
MONGODB_DATABASE=stt_system

# Model Settings
SKIP_MODEL_DOWNLOAD=false
MODEL_TO_DOWNLOAD=medium
DEFAULT_MODEL=medium
DEFAULT_LANGUAGE=vi
```

---

## Verification Checklist

- [ ] MinIO running and accessible (http://localhost:9001)
- [ ] Model uploaded to MinIO (`whisper-models/ggml-medium.bin`)
- [ ] Worker started and downloaded model
- [ ] API running (http://localhost:8000/docs)
- [ ] Test upload successful

---

## 🎉 You're Ready!

Your STT system is now configured with automatic model management. Models will be:
- Downloaded automatically from MinIO
- Cached in Docker volume
- Reused across container restarts
- Never committed to Git

**Next steps:**
- See [MODEL_DOWNLOAD_GUIDE.md](./MODEL_DOWNLOAD_GUIDE.md) for detailed docs
- Configure production settings
- Scale workers as needed

