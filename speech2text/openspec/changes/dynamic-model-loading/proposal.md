# Dynamic Whisper Model Loading

## Why

The current Whisper integration uses a CLI wrapper (`subprocess.run()` calling `whisper-cli`) which causes significant performance and operational issues:

**Performance Problems:**
- Each API request spawns a new process that loads the 181MB+ model from disk
- 100 requests = 100 model loads = massive latency overhead
- Cold start penalty of 1-2 seconds per request
- Not suitable for real-time or concurrent workloads

**Architecture Problems:**
- Model size (small/medium) is hardcoded in configuration or Dockerfile
- Changing models requires code changes + Docker rebuild
- Cannot optimize for different hardware (Xeon/GPU/CUDA)
- Parsing stdout from CLI is fragile and error-prone

**Operational Problems:**
- Static artifact downloads with no runtime flexibility
- No ENV-based model switching
- LD_LIBRARY_PATH must be set manually
- Dev and Prod require different Docker images

## What Changes

We will migrate from CLI wrapper to **Shared Library Integration** with **Dynamic Model Switching**:

1. **Replace subprocess calls** with direct C library integration via ctypes
2. **Load model once** at service startup and reuse for all requests
3. **ENV-based model selection**: `WHISPER_MODEL_SIZE=small|medium`
4. **Smart entrypoint** that auto-detects and loads correct `.so` files
5. **Unified Docker image** that works for both Dev (small) and Prod (medium)

### Technical Approach

**Shared Library Architecture:**
- Load `libwhisper.so`, `libggml.so.0`, `libggml-base.so.0`, `libggml-cpu.so.0`
- Initialize Whisper context once: `whisper_init_from_file()`
- Call `whisper_full()` directly for each transcription
- Free context on shutdown: `whisper_free()`

**Dynamic Model Switching:**
- Read `WHISPER_MODEL_SIZE` environment variable
- Map to correct model path: `whisper_small_xeon/ggml-small-q5_1.bin` or `whisper_medium_xeon/ggml-medium-q5_1.bin`
- Set `LD_LIBRARY_PATH` to corresponding `.so` directory
- Download artifacts on-demand if not present

## Verification Plan

### Automated Tests
1. **Unit Tests**: Test `WhisperLibraryAdapter` initialization and model loading
   ```bash
   PYTHONPATH=. uv run pytest tests/test_whisper_library.py
   ```

2. **Integration Tests**: Test model switching via ENV
   ```bash
   WHISPER_MODEL_SIZE=small PYTHONPATH=. uv run pytest tests/test_model_switching.py
   WHISPER_MODEL_SIZE=medium PYTHONPATH=. uv run pytest tests/test_model_switching.py
   ```

### Manual Verification
1. **Performance Comparison**:
   - Measure latency before (CLI) and after (library)
   - Expected: 50-90% reduction in transcription latency
   - Verify model loads only once at startup (check logs)

2. **Model Switching**:
   ```bash
   # Test small model
   WHISPER_MODEL_SIZE=small docker-compose up api
   curl -X POST http://localhost:8000/transcribe -d '{"audio_url":"..."}'
   
   # Test medium model (no rebuild)
   docker-compose down
   WHISPER_MODEL_SIZE=medium docker-compose up api
   curl -X POST http://localhost:8000/transcribe -d '{"audio_url":"..."}'
   ```

3. **Memory Usage**:
   - Small model: ~500 MB RAM
   - Medium model: ~2 GB RAM
   - Verify no memory leaks over 100+ requests
