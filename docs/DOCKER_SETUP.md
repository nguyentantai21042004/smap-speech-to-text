# Docker Setup với Model Management

## 📦 Các service trong Docker Compose

### Services đã update:

1. **MongoDB** - Database
2. **RabbitMQ** - Legacy message broker (giữ lại để tương thích)
3. **Redis** - Job queue (thay thế RabbitMQ)
4. **MinIO** - Object storage cho audio files và Whisper models
5. **API** - REST API service  
6. **Consumer** - STT Worker (xử lý transcription jobs)
7. **Scheduler** - Periodic tasks

---

## 🚀 Quick Start

### 1. Upload Whisper Models lên MinIO

**Trước tiên, start chỉ MinIO:**
```bash
docker-compose up -d minio
```

**Upload model qua MinIO Web UI:**
1. Mở http://localhost:9001
2. Login: `minioadmin` / `minioadmin`
3. Tạo bucket: `stt-audio-files`
4. Tạo folder: `whisper-models/`
5. Upload: `ggml-medium.bin` vào `whisper-models/`

**Hoặc dùng script:**
```bash
# Đảm bảo model file có sẵn local
ls whisper/models/ggml-medium.bin

# Upload lên MinIO
python scripts/upload_models_to_minio.py medium
```

### 2. Start tất cả services

```bash
# Start all services
docker-compose up -d

# Check logs
docker-compose logs -f consumer  # Consumer sẽ tự động download model
```

### 3. Verify

```bash
# Check services
docker-compose ps

# Check Consumer logs (should see model download)
docker logs smap-consumer

# Test API
curl http://localhost:8000/api/v1/tasks/health
```

---

## 🔧 Configuration

### Environment Variables (.env)

```bash
# MongoDB
MONGODB_ROOT_USER=admin
MONGODB_ROOT_PASSWORD=admin123
MONGODB_DATABASE=stt_system

# MinIO
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=stt-audio-files

# Model Download
SKIP_MODEL_DOWNLOAD=false
MODEL_TO_DOWNLOAD=medium
DEFAULT_MODEL=medium

# Consumer
MAX_CONCURRENT_JOBS=2
CONSUMER_REPLICAS=2
```

---

## Services Details

### Consumer Service (STT Worker)

**Dockerfile:** `cmd/consumer/Dockerfile`

**Features:**
- Tự động download Whisper models từ MinIO
- Cache models trong Docker volume
- Xử lý STT jobs từ Redis Queue
- Support audio chunking và merging

**Environment Variables:**
- `SKIP_MODEL_DOWNLOAD` - Skip model download (default: false)
- `MODEL_TO_DOWNLOAD` - Model to download (default: medium)
- `WHISPER_MODELS_DIR` - Models directory (default: /app/whisper/models)

**Volumes:**
- `whisper_models:/app/whisper/models` - Persist models

**Entrypoint:**
```bash
/docker-entrypoint.sh
  → Check if model exists
  → Download from MinIO if missing
  → Start consumer process
```

### API Service

**Dockerfile:** `cmd/api/Dockerfile`

**Endpoints:**
- `POST /api/v1/tasks/upload` - Upload audio
- `GET /api/v1/tasks/{job_id}/status` - Get status
- `GET /api/v1/tasks/{job_id}/result` - Get result
- `GET /api/v1/tasks/health` - Health check

**Dependencies:**
- MongoDB - Job storage
- Redis - Job queue
- MinIO - Audio storage

### Scheduler Service

**Dockerfile:** `cmd/scheduler/Dockerfile`

**Tasks:**
- Cleanup old jobs
- Monitor queue
- Health checks
- Metrics collection

---

## 🐳 Docker Commands

### Start services

```bash
# All services
docker-compose up -d

# Specific service
docker-compose up -d consumer

# With rebuild
docker-compose up -d --build
```

### Check logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f consumer
docker-compose logs -f api

# Last 100 lines
docker logs --tail=100 smap-consumer
```

### Scale consumers

```bash
# Run 4 consumer instances
docker-compose up -d --scale consumer=4
```

### Stop services

```bash
# Stop all
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

### Rebuild

```bash
# Rebuild all
docker-compose build

# Rebuild specific service
docker-compose build consumer

# Rebuild without cache
docker-compose build --no-cache consumer
```

---

## 🔍 Troubleshooting

### Consumer fails to start

**Check logs:**
```bash
docker logs smap-consumer
```

**Common issues:**

1. **Model download fails**
   ```
   Model not found in MinIO
   ```
   Solution: Upload model to MinIO first

2. **MinIO connection fails**
   ```
   Failed to connect to MinIO
   ```
   Solution: Check MinIO is running
   ```bash
   docker-compose ps minio
   curl http://localhost:9000/minio/health/live
   ```

3. **Redis connection fails**
   ```
   Failed to connect to Redis
   ```
   Solution: Check Redis is running
   ```bash
   docker-compose ps redis
   docker exec smap-redis redis-cli ping
   ```

### API can't queue jobs

**Check Redis:**
```bash
docker exec smap-redis redis-cli
> PING
> LLEN stt_jobs
> QUIT
```

**Check logs:**
```bash
docker logs smap-api
```

### Model download too slow

**Use smaller model for testing:**
```bash
# .env
MODEL_TO_DOWNLOAD=tiny

# Restart consumer
docker-compose restart consumer
```

**Or skip download (if model already present):**
```bash
# .env
SKIP_MODEL_DOWNLOAD=true

docker-compose restart consumer
```

---

## 📦 Volumes

| Volume | Purpose | Size |
|--------|---------|------|
| `mongodb_data` | MongoDB data | ~100MB |
| `redis_data` | Redis data | ~10MB |
| `minio_data` | Audio files + models | Variable |
| `whisper_models` | Whisper models cache | ~1-3GB/model |

**Check volume usage:**
```bash
docker volume ls
docker volume inspect smap-speech-to-text_whisper_models
```

**Clean volumes:**
```bash
# Stop services
docker-compose down

# Remove all volumes (WARNING: deletes data)
docker-compose down -v

# Remove specific volume
docker volume rm smap-speech-to-text_whisper_models
```

---

## 🎯 Best Practices

### Development

```bash
# Use docker-compose.yml
docker-compose up -d

# Mount source code for hot reload (API only)
volumes:
  - ./core:/app/core
  - ./services:/app/services
```

### Production

```yaml
# Use specific versions
image: python:3.11-slim  # Not :latest

# Set resource limits
deploy:
  resources:
    limits:
      cpus: '2.0'
      memory: 4G
    reservations:
      cpus: '1.0'
      memory: 2G

# Use secrets
secrets:
  - minio_access_key
  - minio_secret_key
```

### Model Management

1. **Pre-download models** before deployment
2. **Use Docker volumes** to persist models
3. **Monitor disk space** on host
4. **Backup MinIO** regularly

---

## Checklist

Deployment checklist:

- [ ] MinIO running and accessible
- [ ] Models uploaded to MinIO
- [ ] Environment variables configured
- [ ] All services start successfully
- [ ] Consumer downloads model successfully
- [ ] API health check passes
- [ ] Test transcription works
- [ ] Logs are clean (no errors)

---

## 📚 Related Docs

- [MODEL_DOWNLOAD_GUIDE.md](./MODEL_DOWNLOAD_GUIDE.md) - Detailed model management
- [QUICKSTART_MODEL_SETUP.md](./QUICKSTART_MODEL_SETUP.md) - 5-minute setup
- [ENV_CONFIG_EXPLANATION.md](./ENV_CONFIG_EXPLANATION.md) - Configuration details

