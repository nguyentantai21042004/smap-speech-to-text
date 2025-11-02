# RabbitMQ Migration Complete ✅

## Summary

Successfully migrated the SMAP Speech-to-Text system from Redis Queue to RabbitMQ with comprehensive logging and error handling throughout.

**Migration Date**: 2025-11-02
**Status**: **COMPLETE**

---

## All Changes Made

### 1. Configuration Files ✅

#### `.env.example`
- Removed Redis configuration (REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_PASSWORD)
- Added RabbitMQ configuration (complete AMQP setup)
- Removed unused fields (DEFAULT_MODEL, DEFAULT_LANGUAGE, CHUNK_STRATEGY, CHUNK_OVERLAP, RETRY_DELAY)
- Added missing API_WORKERS field
- Cleaned up and organized all sections

#### `core/config.py`
- Removed Redis fields (redis_host, redis_port, redis_db, redis_password)
- Added api_workers field
- Removed unused fields (default_model, default_language, chunk_strategy, chunk_overlap, retry_delay)
- Kept RabbitMQ configuration with rabbitmq_url property

### 2. Dependencies ✅

#### `requirements.txt`
- Removed: `redis==5.0.1`, `rq==1.15.1`
- Added: `aio-pika==9.3.1`

### 3. Core Components ✅

#### `core/messaging.py` - Complete Rewrite
**Old (Redis Queue)**:
- Synchronous connection
- Multiple priority queues
- RQ-based job management

**New (RabbitMQ)**:
- Async connection with auto-reconnect (`aio_pika.connect_robust`)
- Single exchange with routing key
- Single durable queue with priority support (0-10)
- Persistent message delivery
- Fair dispatch with QoS
- Comprehensive logging for all operations
- Methods: `connect()`, `disconnect()`, `publish_job()`, `consume_jobs()`, `health_check()`, `get_queue_size()`, `purge_queue()`

### 4. API Service ✅

#### `cmd/api/main.py`
- Updated docstrings (Redis → RabbitMQ)
- Changed initialization to `await queue_manager.connect()`
- Added proper `await queue_manager.disconnect()` in shutdown
- Updated API documentation/description
- Comprehensive logging for connection lifecycle

### 5. Task Management ✅

#### `services/task_service.py`
**Old**:
```python
rq_job = queue_manager.enqueue_job(
    func="worker.processor.process_stt_job",
    args=(job.job_id,),
    job_id=job.job_id,
    priority="normal"
)
```

**New**:
```python
await queue_manager.publish_job(
    job_id=job.job_id,
    job_data={
        "language": language,
        "model": model,
        "filename": filename
    },
    priority=5  # Normal priority (0-10)
)
```

### 6. Message Handling ✅

#### `internal/consumer/handlers/stt_handler.py` - Complete Rewrite
**Old (RQ)**:
- Sync wrapper for async function
- RQ-specific job handling
- Return-based status

**New (RabbitMQ)**:
- Pure async handler
- Handles `aio_pika.IncomingMessage`
- JSON message parsing with validation
- Message acknowledgment (`message.ack()`)
- Smart retry logic:
  - **TransientError**: Reject with requeue
  - **PermanentError**: Reject without requeue
  - **Unexpected errors**: Reject with requeue
- Comprehensive error logging

### 7. Consumer Service ✅

#### `cmd/consumer/main.py` - Complete Rewrite
**Old (RQ Worker)**:
- Used `Worker.work()` blocking call
- Synchronous worker management

**New (RabbitMQ Consumer)**:
- Fully async consumer service
- Connects to RabbitMQ and MongoDB on startup
- Starts async message consumption
- Graceful shutdown with signal handling (SIGTERM, SIGINT)
- Proper cleanup on exit
- Uses `queue_manager.consume_jobs()` with async callback
- Configurable prefetch count from `MAX_CONCURRENT_JOBS`

### 8. Documentation ✅

#### `docs/CONFIGURATION_GUIDE.md`
- Comprehensive guide to all configuration fields
- Explains which fields are used and where
- Lists unused fields with recommendations
- Includes RabbitMQ configuration examples
- Troubleshooting section

#### `docs/MIGRATION_REDIS_TO_RABBITMQ.md`
- Complete migration guide
- Comparison table Redis vs RabbitMQ
- Installation instructions
- Testing procedures
- Rollback plan

---

## File Changes Summary

| File | Status | Changes |
|------|--------|---------|
| `.env.example` | Updated | Redis → RabbitMQ, removed unused fields, added API_WORKERS |
| `core/config.py` | Updated | Removed Redis fields, added api_workers, removed unused fields |
| `requirements.txt` | Updated | redis/rq → aio-pika |
| `core/messaging.py` | Rewritten | Complete RabbitMQ implementation with async |
| `cmd/api/main.py` | Updated | RabbitMQ connection lifecycle |
| `services/task_service.py` | Updated | publish_job() instead of enqueue_job() |
| `internal/consumer/handlers/stt_handler.py` | Rewritten | RabbitMQ message handler with ack/reject |
| `cmd/consumer/main.py` | Rewritten | Async RabbitMQ consumer service |
| `docs/CONFIGURATION_GUIDE.md` | Created | Complete configuration documentation |
| `docs/MIGRATION_REDIS_TO_RABBITMQ.md` | Created | Migration guide and reference |
| `docs/MIGRATION_COMPLETE.md` | Created | This file |

**Total files changed**: 11
**Total lines changed**: ~1500+

---

## Installation & Setup

### 1. Install RabbitMQ

#### Using Docker (Recommended):
```bash
docker run -d --name rabbitmq \
  -p 5672:5672 \
  -p 15672:15672 \
  -e RABBITMQ_DEFAULT_USER=guest \
  -e RABBITMQ_DEFAULT_PASS=guest \
  rabbitmq:3-management
```

#### Verify RabbitMQ is running:
```bash
# Check Docker container
docker ps | grep rabbitmq

# Access management UI
open http://localhost:15672
# Login: guest / guest
```

### 2. Install Python Dependencies

```bash
# Activate virtual environment
source myenv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Verify aio-pika is installed
pip list | grep aio-pika
```

### 3. Configure Environment

```bash
# Copy example configuration
cp .env.example .env

# Edit .env with your settings
nano .env

# Key settings for RabbitMQ:
# RABBITMQ_HOST=localhost
# RABBITMQ_PORT=5672
# RABBITMQ_USER=guest
# RABBITMQ_PASSWORD=guest
# RABBITMQ_QUEUE_NAME=stt_jobs_queue
```

### 4. Start Services

#### Terminal 1 - MongoDB:
```bash
docker run -d --name mongodb -p 27017:27017 mongo:latest
```

#### Terminal 2 - MinIO:
```bash
docker run -d --name minio \
  -p 9000:9000 -p 9001:9001 \
  -e "MINIO_ROOT_USER=minioadmin" \
  -e "MINIO_ROOT_PASSWORD=minioadmin" \
  quay.io/minio/minio server /data --console-address ":9001"
```

#### Terminal 3 - API Server:
```bash
source myenv/bin/activate
python cmd/api/main.py

# Or with uvicorn:
uvicorn cmd.api.main:app --host 0.0.0.0 --port 8000 --reload
```

#### Terminal 4 - Consumer Worker:
```bash
source myenv/bin/activate
python cmd/consumer/main.py
```

---

## Testing the Migration

### 1. Health Check

```bash
curl http://localhost:8000/api/v1/tasks/health
```

**Expected response**:
```json
{
  "status": "healthy",
  "services": {
    "mongodb": "healthy",
    "rabbitmq": "healthy"
  }
}
```

### 2. Upload Audio File

```bash
curl -X POST http://localhost:8000/api/v1/tasks/upload \
  -F "file=@test.mp3" \
  -F "language=vi" \
  -F "model=medium"
```

**Expected response**:
```json
{
  "status": "success",
  "job_id": "abc123...",
  "message": "Task created and queued for processing"
}
```

### 3. Check Logs

**API logs** should show:
```
RabbitMQ connected successfully
Job published to RabbitMQ: job_id=abc123...
```

**Consumer logs** should show:
```
========== HANDLER: Message received ==========
Processing job: job_id=abc123...
========== HANDLER: STT processing completed ==========
HANDLER: Message acknowledged: job_id=abc123...
```

### 4. Monitor RabbitMQ

```bash
# Open RabbitMQ Management UI
open http://localhost:15672

# Check:
# - Connections: Should see API and Consumer connected
# - Queues: Should see stt_jobs_queue
# - Messages: Should see messages being processed
```

### 5. Check Job Status

```bash
curl http://localhost:8000/api/v1/tasks/{job_id}/status
```

### 6. Get Results

```bash
curl http://localhost:8000/api/v1/tasks/{job_id}/result
```

---

## Key Improvements

### 1. Architecture
- Native async/await pattern (better performance)
- Auto-reconnection with robust connections
- Message persistence (survive broker restart)
- Fair dispatch (workers get equal load)

### 2. Reliability
- Message acknowledgment (exactly-once processing)
- Smart retry logic (transient vs permanent errors)
- Durable queues and exchanges
- Message priority support

### 3. Monitoring
- RabbitMQ Management UI (http://localhost:15672)
- Queue statistics and metrics
- Connection monitoring
- Message tracking

### 4. Logging
- Comprehensive logging at every step
- Emoji markers for easy scanning (📝, ✅, ❌, 🔍, ⚠️)
- Detailed error messages with stack traces
- Request/response logging

---

## Troubleshooting

### RabbitMQ Connection Failed

**Symptoms**:
```
❌ Failed to initialize RabbitMQ: connection refused
```

**Solutions**:
```bash
# Check if RabbitMQ is running
docker ps | grep rabbitmq

# Start RabbitMQ
docker start rabbitmq

# Check logs
docker logs rabbitmq

# Verify port is open
telnet localhost 5672
```

### Messages Not Being Consumed

**Symptoms**:
- Jobs stay in PENDING status
- No consumer logs

**Solutions**:
```bash
# Check consumer is running
ps aux | grep "cmd/consumer/main.py"

# Start consumer
python cmd/consumer/main.py

# Check RabbitMQ queue
# Go to http://localhost:15672 → Queues → stt_jobs_queue
# Should see messages ready and consumer connected
```

### Message Requeued Repeatedly

**Symptoms**:
```
⚠️ HANDLER: Message requeued for retry: job_id=...
```

**Solutions**:
- Check MongoDB is running and accessible
- Check MinIO is running
- Check Whisper executable exists
- Check audio file is valid
- Review error logs for root cause

---

## Monitoring & Maintenance

### Daily Checks

1. **RabbitMQ Health**:
   - Open http://localhost:15672
   - Check connections (API + Consumer)
   - Check queue lengths (should be low)
   - Check message rates

2. **Disk Space**:
   - RabbitMQ message store
   - MongoDB data
   - MinIO storage
   - Temp directory (`/tmp/stt_processing`)

3. **Logs**:
   - API logs: Check for errors
   - Consumer logs: Check for retries
   - RabbitMQ logs: Check for warnings

### Weekly Maintenance

1. **Purge old messages** (if needed):
   ```bash
   # Via RabbitMQ UI: Queues → stt_jobs_queue → Purge
   ```

2. **Clean up failed jobs** in MongoDB

3. **Archive old transcriptions** from MinIO

### Performance Tuning

1. **Adjust concurrent jobs**:
   ```bash
   # In .env
   MAX_CONCURRENT_JOBS=8  # Increase for more parallel processing
   ```

2. **Adjust prefetch count**:
   - Currently uses `MAX_CONCURRENT_JOBS`
   - Lower value = more fair distribution
   - Higher value = better throughput

3. **Monitor memory usage**:
   - Each concurrent job uses memory for audio chunks
   - Adjust based on available RAM

---

## Next Steps

### Optional Enhancements

1. **Add Dead Letter Queue**:
   - Catch permanently failed messages
   - Investigate failures without blocking queue

2. **Add Message TTL**:
   - Prevent old messages from processing
   - Currently set via `JOB_TIMEOUT`

3. **Add Monitoring**:
   - Prometheus metrics
   - Grafana dashboards
   - Alert on queue buildup

4. **Add Rate Limiting**:
   - Prevent queue flooding
   - Protect downstream services

5. **Add Message Compression**:
   - Reduce network bandwidth
   - Store larger messages

---

## Success Metrics

**All services start without errors**
**API connects to RabbitMQ successfully**
**Consumer connects and listens to queue**
**Jobs are published to RabbitMQ**
**Jobs are consumed and processed**
**Messages are acknowledged properly**
**Failed jobs are retried (transient)**
**Failed jobs are rejected (permanent)**
**Health checks pass for all services**
**Comprehensive logging throughout**

---

## References

- **RabbitMQ Documentation**: https://www.rabbitmq.com/documentation.html
- **aio-pika Documentation**: https://aio-pika.readthedocs.io/
- **Configuration Guide**: `docs/CONFIGURATION_GUIDE.md`
- **Migration Guide**: `docs/MIGRATION_REDIS_TO_RABBITMQ.md`

---

## Support

For issues or questions:
1. Check logs in `logs/stt.log`
2. Check RabbitMQ management UI
3. Review error messages in console
4. Check this documentation

---

**Migration completed successfully! 🎉**

All components have been updated, tested, and documented.
The system is now using RabbitMQ with comprehensive logging and error handling throughout.
