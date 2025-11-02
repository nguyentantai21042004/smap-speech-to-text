# Quick Start: Parallel Processing

## TL;DR - 4x Faster Transcription! 🚀

Make your speech-to-text processing **4x faster** with one configuration change.

---

## 1. Enable Parallel Processing

Add to your `.env`:

```bash
# Enable parallel transcription
USE_PARALLEL_TRANSCRIPTION=true

# Number of workers (recommended: your CPU core count)
MAX_PARALLEL_WORKERS=4
```

---

## 2. That's It!

Restart your worker:

```bash
python cmd/consumer/main.py
```

Your chunks will now transcribe in parallel! 🎉

---

## Quick Configuration Guide

### How Many Workers Should I Use?

```bash
# Check your CPU cores
python -c "import os; print(f'CPU cores: {os.cpu_count()}')"
```

**Recommendation Table:**

| Your CPU | Workers | Expected Speed |
|----------|---------|----------------|
| 2 cores | `MAX_PARALLEL_WORKERS=2` | 2x faster |
| 4 cores | `MAX_PARALLEL_WORKERS=4` | 4x faster ⭐ |
| 8 cores | `MAX_PARALLEL_WORKERS=6` | 5-6x faster |
| 16+ cores | `MAX_PARALLEL_WORKERS=8` | 6-8x faster |

**Sweet Spot**: `CPU cores` or `CPU cores - 1`

---

## Before vs After

### Before (Sequential)

```
30-minute audio → 60 chunks → 600 seconds total
(Each chunk processed one at a time)
⏱️ 10 minutes to transcribe
```

### After (4 Workers)

```
30-minute audio → 60 chunks → 150 seconds total
(4 chunks processed simultaneously)
⏱️ 2.5 minutes to transcribe
```

**Result: 4x faster!** 🚀

---

## Example Configurations

### Development (Laptop)

```bash
# .env for laptop (4 cores, 8GB RAM)
USE_PARALLEL_TRANSCRIPTION=true
MAX_PARALLEL_WORKERS=2
MAX_CONCURRENT_JOBS=1
```

### Production (Server)

```bash
# .env for server (8 cores, 16GB RAM)
USE_PARALLEL_TRANSCRIPTION=true
MAX_PARALLEL_WORKERS=6
MAX_CONCURRENT_JOBS=2
```

### High-Performance

```bash
# .env for powerful server (16 cores, 32GB RAM)
USE_PARALLEL_TRANSCRIPTION=true
MAX_PARALLEL_WORKERS=8
MAX_CONCURRENT_JOBS=4
```

---

## Verify It's Working

Watch your logs when processing a job:

```bash
# You should see this:
🚀 Using parallel transcription mode
Transcribing 60 chunks in parallel (workers=4)...

# Multiple chunks processing simultaneously:
[1/60] Transcribing: chunk_001.wav
[2/60] Transcribing: chunk_002.wav
[3/60] Transcribing: chunk_003.wav
[4/60] Transcribing: chunk_004.wav

# Progress updates as chunks complete:
[1/60] Completed in 8.2s: 1245 chars
Progress: 1/60 (1.7%)

[3/60] Completed in 9.1s: 1389 chars
Progress: 2/60 (3.3%)

# Final summary:
Parallel transcription complete in 165.3s
Success rate: 100.0% (60/60)
```

**Not seeing this?** Check your configuration:

```bash
# Verify settings are loaded
cat .env | grep PARALLEL

# Expected output:
# USE_PARALLEL_TRANSCRIPTION=true
# MAX_PARALLEL_WORKERS=4
```

---

## Disable Parallel Processing

If you need to (low resources, debugging, etc.):

```bash
# In .env
USE_PARALLEL_TRANSCRIPTION=false
```

The system will fall back to sequential processing:

```
🐌 Using sequential transcription mode
Transcribing chunk 1/60: chunk_001.wav
Chunk 1 transcribed: 1245 chars
Transcribing chunk 2/60: chunk_002.wav
...
```

---

## Resource Requirements

Each worker needs:
- **CPU**: 1 core
- **Memory**: ~1.5 GB (for Whisper medium model)

**Total for 4 workers**: 4 cores + 6-8 GB RAM

**Check your resources:**

```bash
# CPU
lscpu | grep "CPU(s)"

# Memory
free -h
```

---

## Performance Monitoring

### Monitor CPU Usage

```bash
# Real-time CPU usage
htop

# Or
top
```

You should see multiple `whisper-cli` processes running simultaneously.

### Monitor Memory

```bash
# Memory usage
free -h

# Or detailed process memory
ps aux | grep whisper
```

### Monitor Progress

```bash
# Tail worker logs
tail -f logs/stt.log

# Or console output
python cmd/consumer/main.py
```

---

## Troubleshooting

### High CPU Usage (100%)

**Solution**: Reduce workers

```bash
MAX_PARALLEL_WORKERS=2  # Instead of 4
```

### Out of Memory

**Solution**: Reduce workers or use smaller model

```bash
MAX_PARALLEL_WORKERS=2
DEFAULT_WHISPER_MODEL=small  # Instead of medium
```

### Not Faster

**Check**:
1. Is parallel mode enabled? `USE_PARALLEL_TRANSCRIPTION=true`
2. Do you have enough CPU cores?
3. Is your disk fast enough? (Use SSD, not HDD)

---

## Benchmark Your System

Test with a sample audio file:

```bash
# Sequential mode
USE_PARALLEL_TRANSCRIPTION=false python test_benchmark.py

# Parallel mode with 2 workers
USE_PARALLEL_TRANSCRIPTION=true MAX_PARALLEL_WORKERS=2 python test_benchmark.py

# Parallel mode with 4 workers
USE_PARALLEL_TRANSCRIPTION=true MAX_PARALLEL_WORKERS=4 python test_benchmark.py
```

Compare the times!

---

## Advanced Tips

### Auto-detect Workers

Use all available CPU cores:

```bash
MAX_PARALLEL_WORKERS=$(python -c "import os; print(os.cpu_count())")
```

### Docker Configuration

Allocate enough resources to your container:

```yaml
# docker-compose.yml
services:
  worker:
    image: smap-stt-worker
    cpus: 4
    mem_limit: 8g
    environment:
      - MAX_PARALLEL_WORKERS=4
```

### Production Optimization

```bash
# High-priority processing
nice -n -10 python cmd/consumer/main.py

# Or use systemd service with priority
```

---

## Need More Help?

- **Full Documentation**: [PARALLEL_PROCESSING.md](PARALLEL_PROCESSING.md)
- **Configuration Guide**: [CONFIGURATION_GUIDE.md](CONFIGURATION_GUIDE.md)
- **Performance Tuning**: Check server resources and adjust workers

---

## Summary

Add 2 lines to `.env`
Restart worker
Enjoy 4x faster transcription!

```bash
# .env
USE_PARALLEL_TRANSCRIPTION=true
MAX_PARALLEL_WORKERS=4
```

That's it! 🎉
