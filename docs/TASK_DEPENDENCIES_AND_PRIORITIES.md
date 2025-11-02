# Task Dependencies & Priorities

## Visual Task Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    PHASE 1: CORE (2.5h)                      │
└─────────────────────────────────────────────────────────────┘

Task 1: Config          Task 4: Models
  (15min)                 (30min)
     │                       │
     ├──────┬───────┬────────┤
     ▼      ▼       ▼        ▼
Task 2:   Task 3:        Task 5:
MongoDB   Redis          Repository
(30min)   (30min)        (45min)
                            │
                            │
┌───────────────────────────┼─────────────────────────────────┐
│                    PHASE 2: WORKERS (3h)                     │
└───────────────────────────┼─────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
    Task 6:             Task 7:             Task 8:
   Chunking          Transcriber           Merger
   (45min)            (30min)             (30min)
        │                   │                   │
        └───────────────────┼───────────────────┘
                            ▼
                        Task 9:
                       Processor
                        (60min)
                            │
                            │
┌───────────────────────────┼─────────────────────────────────┐
│                 PHASE 3: SERVICES & API (1.5h)               │
└───────────────────────────┼─────────────────────────────────┘
                            │
                ┌───────────┴───────────┐
                ▼                       ▼
           Task 10:                 Task 11:
        Task Service              API Routes
           (45min)                  (45min)
                                       │
                                       │
┌──────────────────────────────────────┼───────────────────────┐
│              PHASE 4: INTEGRATION (1.5h)                     │
└──────────────────────────────────────┼───────────────────────┘
                                       │
        ┌──────────────────────────────┼──────────────┐
        ▼                              ▼              ▼
   Task 12:                       Task 13:       Task 14:
STT Handler                       API Main     Consumer Main
   (30min)                         (30min)        (30min)
        │                              │              │
        └──────────────────────────────┼──────────────┘
                                       │
┌──────────────────────────────────────┼───────────────────────┐
│               PHASE 5: TESTING (40min)                       │
└──────────────────────────────────────┼───────────────────────┘
                                       │
        ┌──────────────────────────────┼──────────────┐
        ▼                              ▼              ▼
   Task 15:                       Task 16:       Task 17:
Test Script                   Requirements     .env.example
   (20min)                        (10min)        (10min)
```

---

## Priority Matrix

### 🔴 CRITICAL (Must do first)
These are blocking tasks - nothing else can be done without them.

| Task | File | Time | Blocks |
|------|------|------|--------|
| 1 | `core/config.py` | 15m | 2, 3 |
| 2 | `core/database.py` | 30m | 5, 13, 14 |
| 4 | `repositories/models.py` | 30m | 5 |
| 5 | `repositories/task_repository.py` | 45m | 9, 10 |

**Total: 2 hours**

---

### 🟠 HIGH (Do second)
These implement core functionality.

| Task | File | Time | Depends On | Blocks |
|------|------|------|------------|--------|
| 3 | `core/messaging.py` | 30m | 1 | 14 |
| 6 | `worker/chunking.py` | 45m | - | 9 |
| 7 | `worker/transcriber.py` | 30m | - | 9 |
| 8 | `worker/merger.py` | 30m | - | 9 |
| 9 | `worker/processor.py` | 60m | 5,6,7,8 | 12 |

**Total: 3 hours 15 minutes**

---

### 🟡 MEDIUM (Do third)
These connect the system together.

| Task | File | Time | Depends On | Blocks |
|------|------|------|------------|--------|
| 10 | `services/task_service.py` | 45m | 5 | 11 |
| 11 | `internal/api/routes/task_routes.py` | 45m | 10 | - |
| 12 | `internal/consumer/handlers/stt_handler.py` | 30m | 9 | 14 |
| 13 | `cmd/api/main.py` | 30m | 2 | - |
| 14 | `cmd/consumer/main.py` | 30m | 2,3,12 | - |

**Total: 3 hours**

---

### 🟢 LOW (Do last)
These are for testing and documentation.

| Task | File | Time | Depends On |
|------|------|------|------------|
| 15 | `scripts/test_upload.py` | 20m | 13,14 |
| 16 | `requirements.txt` | 10m | - |
| 17 | `.env.example` | 10m | 1 |

**Total: 40 minutes**

---

## Parallel Execution Plan

You can do some tasks in parallel to save time:

### Batch 1 (Parallel)
```
Task 1: Config (15min)
  ↓
Task 4: Models (30min)
```
**Time: 45 minutes**

### Batch 2 (Parallel)
After Task 1 completes:
```
Task 2: MongoDB (30min)  |  Task 3: Redis (30min)
```
**Time: 30 minutes** (both run in parallel)

### Batch 3 (Sequential)
After Task 2 and Task 4 complete:
```
Task 5: Repository (45min)
```
**Time: 45 minutes**

### Batch 4 (Parallel)
Can all be done in parallel:
```
Task 6: Chunking (45min)
Task 7: Transcriber (30min)
Task 8: Merger (30min)
```
**Time: 45 minutes** (run all 3 in parallel)

### Batch 5 (Sequential)
After Batch 4 completes:
```
Task 9: Processor (60min)
```
**Time: 60 minutes**

### Batch 6 (Sequential then Parallel)
After Task 9:
```
Task 10: Service (45min)
  ↓
Task 11: API Routes (45min)  |  Task 12: Handler (30min)
```
**Time: 90 minutes** (45 + 45 in parallel)

### Batch 7 (Parallel)
After Batch 6:
```
Task 13: API Main (30min)  |  Task 14: Consumer Main (30min)
```
**Time: 30 minutes**

### Batch 8 (Parallel)
Final tasks:
```
Task 15: Test (20min)  |  Task 16: Requirements (10min)  |  Task 17: .env (10min)
```
**Time: 20 minutes**

---

## Optimized Timeline

If working alone (sequential):
- **Total Time: ~9 hours**
- Spread over 2-3 days

If using parallel approach:
- **Total Time: ~6 hours**
- Can be done in 1-2 days

---

## Daily Work Plan

### Day 1: Foundation (3 hours)
**Morning Session:**
- [ ] Task 1: Config (15min)
- [ ] Task 4: Models (30min)
- [ ] Task 2: MongoDB (30min)
- [ ] Task 3: Redis (30min)
- [ ] Task 5: Repository (45min)

**Afternoon Session:**
- [ ] Task 6: Chunking (45min)
- [ ] Task 7: Transcriber (30min)
- [ ] Task 8: Merger (30min)

**End of Day Test:**
```bash
# Test MongoDB connection
python -c "import asyncio; from core.database import get_database; asyncio.run(get_database())"

# Test models
python -c "from repositories.models import JobModel; print('Models OK')"

# Test repository
python -c "import asyncio; from repositories.task_repository import get_task_repository; print('Repository OK')"
```

---

### Day 2: Workers & Services (4 hours)
**Morning Session:**
- [ ] Task 9: Processor (60min)
- [ ] Task 10: Service (45min)
- [ ] Task 11: API Routes (45min)

**Afternoon Session:**
- [ ] Task 12: Handler (30min)
- [ ] Task 13: API Main (30min)
- [ ] Task 14: Consumer Main (30min)

**End of Day Test:**
```bash
# Test worker
python -c "from worker.processor import process_stt_job; print('Worker OK')"

# Start API (in terminal 1)
python cmd/api/main.py

# Start consumer (in terminal 2)
python cmd/consumer/main.py
```

---

### Day 3: Testing & Finalization (1 hour)
**Morning Session:**
- [ ] Task 15: Test Script (20min)
- [ ] Task 16: Requirements (10min)
- [ ] Task 17: .env (10min)
- [ ] End-to-end testing (20min)

**Final Test:**
```bash
# Upload test file
python scripts/test_upload.py test_audio.mp3

# Check logs
tail -f logs/app.log

# Check errors
tail -f logs/error.log
```

---

## Task Checklist with Dependencies

### Core Infrastructure
- [ ] **Task 1** → Config
  - Depends on: Nothing
  - Required by: Task 2, 3
  - Can start: Immediately

- [ ] **Task 2** → MongoDB
  - Depends on: Task 1
  - Required by: Task 5, 13, 14
  - Can start: After Task 1

- [ ] **Task 3** → Redis
  - Depends on: Task 1
  - Required by: Task 14
  - Can start: After Task 1 (parallel with Task 2)

- [ ] **Task 4** → Models
  - Depends on: Nothing
  - Required by: Task 5
  - Can start: Immediately (parallel with Task 1)

- [ ] **Task 5** → Repository
  - Depends on: Task 2, 4
  - Required by: Task 9, 10
  - Can start: After Task 2 AND 4

### Worker Modules
- [ ] **Task 6** → Chunking
  - Depends on: Nothing
  - Required by: Task 9
  - Can start: Immediately (parallel with others)

- [ ] **Task 7** → Transcriber
  - Depends on: Nothing
  - Required by: Task 9
  - Can start: Immediately (parallel with others)

- [ ] **Task 8** → Merger
  - Depends on: Nothing
  - Required by: Task 9
  - Can start: Immediately (parallel with others)

- [ ] **Task 9** → Processor
  - Depends on: Task 5, 6, 7, 8
  - Required by: Task 12
  - Can start: After Task 5, 6, 7, 8 complete

### Services & API
- [ ] **Task 10** → Service
  - Depends on: Task 5
  - Required by: Task 11
  - Can start: After Task 5

- [ ] **Task 11** → API Routes
  - Depends on: Task 10
  - Required by: Nothing
  - Can start: After Task 10

### Integration
- [ ] **Task 12** → Handler
  - Depends on: Task 9
  - Required by: Task 14
  - Can start: After Task 9

- [ ] **Task 13** → API Main
  - Depends on: Task 2
  - Required by: Testing
  - Can start: After Task 2

- [ ] **Task 14** → Consumer Main
  - Depends on: Task 2, 3, 12
  - Required by: Testing
  - Can start: After Task 2, 3, 12

### Testing
- [ ] **Task 15** → Test Script
  - Depends on: Task 13, 14
  - Required by: Nothing
  - Can start: After Task 13, 14

- [ ] **Task 16** → Requirements
  - Depends on: Nothing
  - Required by: Installation
  - Can start: Anytime

- [ ] **Task 17** → .env Example
  - Depends on: Task 1
  - Required by: Setup
  - Can start: After Task 1

---

## Critical Path Analysis

The **critical path** (longest sequence of dependent tasks):

```
Task 1 (15m)
  ↓
Task 2 (30m)
  ↓
Task 5 (45m)
  ↓
Task 9 (60m)
  ↓
Task 12 (30m)
  ↓
Task 14 (30m)
  ↓
Task 15 (20m)
```

**Critical Path Total: 3 hours 50 minutes**

Everything else can be done in parallel with these tasks, so:
- **Minimum Time (with unlimited parallelization): 3h 50m**
- **Realistic Time (working alone): 8-9 hours**
- **Comfortable Time (with breaks): 2-3 days**

---

## Resource Requirements

### Before Starting
- [ ] MongoDB running (local or Docker)
- [ ] Redis running (local or Docker)
- [ ] Whisper.cpp compiled
- [ ] Whisper models downloaded
- [ ] Python 3.10+ environment
- [ ] MinIO running (optional for testing)

### Docker Quick Setup
```bash
# Start MongoDB
docker run -d --name mongodb -p 27017:27017 mongo:7

# Start Redis
docker run -d --name redis -p 6379:6379 redis:7

# Start MinIO (optional)
docker run -d --name minio -p 9000:9000 -p 9001:9001 \
  -e MINIO_ROOT_USER=minioadmin \
  -e MINIO_ROOT_PASSWORD=minioadmin \
  minio/minio server /data --console-address ":9001"
```

---

## Success Metrics

After completing all tasks, verify:

### Functionality
- [ ] Can upload audio file via API
- [ ] Job is created in MongoDB
- [ ] Worker picks up job from Redis
- [ ] Audio is chunked
- [ ] Chunks are transcribed
- [ ] Results are merged
- [ ] Results are stored in MinIO
- [ ] Job status is updated
- [ ] Can retrieve results via API

### Logging
- [ ] All operations logged to `logs/app.log`
- [ ] All errors logged to `logs/error.log`
- [ ] Logs include timestamps
- [ ] Logs include function names and line numbers
- [ ] Errors include stack traces

### Error Handling
- [ ] Invalid file format returns error
- [ ] Missing file returns error
- [ ] Database errors are caught and logged
- [ ] Worker errors don't crash the process
- [ ] Retries work for transient errors
- [ ] Permanent errors are marked as failed

---

## Ready to Start?

Choose your approach:

**Approach 1: Sequential (Safest)**
- Follow tasks 1-17 in order
- Test after each task
- Time: 8-9 hours

**Approach 2: Batched (Faster)**
- Follow the batches above
- Test after each batch
- Time: 6-7 hours

**Approach 3: Aggressive Parallel (Fastest)**
- Do all independent tasks together
- Time: ~4 hours
- Risk: More debugging if issues arise

**Recommendation:** Use Approach 2 (Batched) for best balance of speed and safety.

**Next Step:** Start with Task 1! 🚀
