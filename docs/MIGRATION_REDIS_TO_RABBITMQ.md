# Migration from Redis Queue to RabbitMQ

## Summary

This document outlines the changes made to switch from Redis Queue (RQ) to RabbitMQ for message queue handling in the SMAP Speech-to-Text system.

## Changes Made

### 1. Configuration Files

#### .env.example
- **Removed**: Redis configuration (REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_PASSWORD)
- **Added**: RabbitMQ configuration (RABBITMQ_HOST, RABBITMQ_PORT, RABBITMQ_USER, RABBITMQ_PASSWORD, RABBITMQ_VHOST, RABBITMQ_QUEUE_NAME, RABBITMQ_EXCHANGE_NAME, RABBITMQ_ROUTING_KEY)
- **Removed unused fields**:
  - DEFAULT_MODEL
  - DEFAULT_LANGUAGE
  - CHUNK_STRATEGY
  - CHUNK_OVERLAP
  - RETRY_DELAY
- **Added**: API_WORKERS

#### core/config.py
- **Removed**: Redis fields (redis_host, redis_port, redis_db, redis_password)
- **Added**: api_workers field
- **Removed unused fields**: default_model, default_language, chunk_strategy, chunk_overlap, retry_delay
- **Kept**: RabbitMQ configuration fields with rabbitmq_url property

### 2. Dependencies

#### requirements.txt
- **Removed**:
  ```
  redis==5.0.1
  rq==1.15.1
  ```
- **Added**:
  ```
  aio-pika==9.3.1
  ```

### 3. Core Files

#### core/messaging.py
**Complete rewrite from Redis Queue to RabbitMQ**:

**Old (Redis Queue)**:
- Used `redis` and `rq` libraries
- Synchronous connection
- Three priority queues: high, normal, low
- Methods: `enqueue_job()`, `get_job()`, `get_job_status()`, `cancel_job()`, `delete_job()`, `get_queue_stats()`

**New (RabbitMQ)**:
- Uses `aio-pika` library
- Async connection with robust reconnection
- Single queue with priority support (0-10)
- Methods: `connect()`, `disconnect()`, `publish_job()`, `consume_jobs()`, `get_queue_size()`, `purge_queue()`

**Key differences**:
- RabbitMQ uses async/await pattern
- Messages are JSON-encoded with metadata
- Persistent delivery mode
- Fair dispatch with QoS
- Exchange and routing key configuration

### 4. Files That Need Further Updates

The following files still reference Redis Queue and need to be updated:

#### cmd/api/main.py
- Already updated to use RabbitMQ
- Calls `queue_manager.connect()` (async)
- Calls `queue_manager.disconnect()` (async)

#### cmd/consumer/main.py
- **NEEDS UPDATE** - Currently uses RQ Worker
- Should use `queue_manager.consume_jobs()` with async callback
- Needs complete rewrite for RabbitMQ async consumer pattern

#### services/task_service.py
- **NEEDS UPDATE** - Currently calls `queue_manager.enqueue_job()` with RQ syntax
- Should call `await queue_manager.publish_job()` with RabbitMQ syntax
- Change from:
  ```python
  rq_job = queue_manager.enqueue_job(
      func="worker.processor.process_stt_job",
      args=(job.job_id,),
      job_id=job.job_id,
      priority="normal"
  )
  ```
- To:
  ```python
  await queue_manager.publish_job(
      job_id=job.job_id,
      job_data={},
      priority=5
  )
  ```

#### internal/consumer/handlers/stt_handler.py
- **NEEDS UPDATE** - Currently async handler wrapped in sync for RQ
- Should be pure async handler for RabbitMQ message processing
- Needs to parse RabbitMQ message format (aio_pika.IncomingMessage)
- Should acknowledge/reject messages

#### internal/api/routes/task_routes.py
- **MAY NEED UPDATE** - Check health_check endpoint
- Currently checks `queue_manager.health_check()` - this is compatible

### 5. Documentation Created

#### docs/CONFIGURATION_GUIDE.md
- Comprehensive guide to all configuration fields
- Explains which fields are used and where
- Lists unused fields with recommendations
- Includes examples and troubleshooting

## Migration Checklist

- [x] Update .env.example
- [x] Update core/config.py
- [x] Update requirements.txt
- [x] Rewrite core/messaging.py for RabbitMQ
- [x] Create configuration documentation
- [ ] Update cmd/consumer/main.py
- [ ] Update services/task_service.py
- [ ] Update internal/consumer/handlers/stt_handler.py
- [ ] Update cmd/api/main.py RabbitMQ connection
- [ ] Test complete pipeline

## RabbitMQ vs Redis Queue Comparison

| Feature | Redis Queue (RQ) | RabbitMQ |
|---------|------------------|----------|
| **Pattern** | Synchronous | Asynchronous |
| **Library** | `rq` | `aio-pika` |
| **Connection** | Sync redis.Redis | Async connect_robust |
| **Job Enqueue** | `queue.enqueue()` | `exchange.publish()` |
| **Worker** | `Worker.work()` blocking | `queue.consume()` async |
| **Priority** | Multiple queues | Single queue with priority |
| **Persistence** | Optional | Built-in (durable queues) |
| **Reconnection** | Manual | Automatic (robust connection) |
| **Message Format** | Python pickle | JSON |

## Benefits of RabbitMQ

1. **Native async support** - Better integration with FastAPI and async code
2. **Auto-reconnection** - Robust connections handle network issues
3. **Industry standard** - More widely used in production
4. **Better tooling** - Management UI, monitoring, clustering
5. **Message durability** - Better guarantees for message persistence
6. **Flexible routing** - Exchange/routing key pattern
7. **Priority queues** - Native support vs separate queues

## Installation

### RabbitMQ via Docker

```bash
docker run -d --name rabbitmq \
  -p 5672:5672 \
  -p 15672:15672 \
  rabbitmq:3-management

# Access management UI
# http://localhost:15672 (guest/guest)
```

### Dependencies

```bash
pip install -r requirements.txt
```

## Testing

After migration, test the following:

1. **Connection**:
   ```bash
   # Start API
   python cmd/api/main.py
   # Check logs for RabbitMQ connection success
   ```

2. **Job Publishing**:
   ```bash
   # Upload audio file
   curl -X POST http://localhost:8000/api/v1/tasks/upload \
     -F "file=@test.mp3" \
     -F "language=vi" \
     -F "model=medium"
   ```

3. **Job Processing**:
   ```bash
   # Start worker
   python cmd/consumer/main.py
   # Check logs for message consumption
   ```

4. **Health Check**:
   ```bash
   curl http://localhost:8000/api/v1/tasks/health
   ```

## Rollback Plan

If you need to rollback to Redis Queue:

1. Restore old versions of modified files
2. Update requirements.txt to use redis/rq
3. Update .env to use Redis configuration
4. Restart services

Keep the old Redis-based files in git history for reference.

## Next Steps

1. Complete remaining file updates (see checklist above)
2. Run integration tests
3. Update deployment scripts
4. Update README with RabbitMQ installation instructions
5. Monitor production for any issues

## Support

For issues:
- Check RabbitMQ logs: `docker logs rabbitmq`
- Check application logs in `logs/stt.log`
- Verify RabbitMQ is running: `curl http://localhost:15672`
- Review RabbitMQ queue stats in management UI
