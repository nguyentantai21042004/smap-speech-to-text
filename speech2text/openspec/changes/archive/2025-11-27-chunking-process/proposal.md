# Change: Sequential Smart Chunking for Long Audio

## Why

**Current Problem:**
- Audio > 2 minutes (120s) often timeout with 90s limit
- Small Whisper model on CPU: ~0.5-1.0x realtime (278s audio needs 140-280s)
- No progress feedback during long transcriptions
- Memory inefficient for very long audio (entire file loaded at once)

**Business Impact:**
- Cannot reliably process podcast episodes (5-60 minutes)
- Cannot handle video transcription (often > 5 minutes)
- Poor user experience with long wait times and frequent timeouts
- Limits usefulness of the service for real-world content

## What Changes

**Core Strategy: Sequential Smart Chunking**
- Split audio into 30-second chunks with 1-second overlap
- Process chunks sequentially (not parallel) to avoid CPU contention
- Use FFmpeg for fast, efficient audio splitting
- Smart merge strategy to handle word boundaries
- Flat memory usage (~500MB) regardless of audio length

**Key Implementation:**
1. **Audio Duration Detection** - Use ffprobe to get duration
2. **Fast Chunking** - FFmpeg stream splitting to 16kHz WAV chunks
3. **Sequential Processing** - Loop through chunks with progress logging
4. **Smart Merge** - Join transcriptions with overlap handling
5. **Immediate Cleanup** - Remove chunk files after processing

**Configuration:**
- `WHISPER_CHUNK_DURATION=30` (seconds, optimal for Whisper)
- `WHISPER_CHUNK_OVERLAP=1` (seconds, for word boundaries)
- Adaptive timeout: `min(90, audio_duration * 1.5)` seconds

**Why Sequential (not Parallel)?**
- Whisper.cpp already uses OpenMP for multi-core within single inference
- Parallel would cause CPU thrashing (context switching overhead)
- Memory explosion risk: 4 parallel chunks = 2GB RAM vs 500MB sequential
- Sequential is actually FASTER on CPU due to better cache locality

## Impact

**Affected Capabilities:**
- Speech transcription service (core functionality)
- API timeout behavior
- Memory usage patterns
- Progress logging

**Breaking Changes:**
- None (backward compatible)
- Audio < 30s uses fast path (no chunking)
- Audio > 30s automatically chunks

**Benefits:**
- ✅ Process audio up to 60 minutes without timeout
- ✅ Flat memory usage (~500MB) for any audio length
- ✅ Progress tracking (log chunk X/Y)
- ✅ Better debugging (know exact chunk that failed)
- ✅ Optimal quality (Whisper trained on ~30s segments)

**Affected Code:**
- `adapters/whisper/library_adapter.py` - Add chunking methods
- `services/transcription.py` - Integrate chunking logic
- `core/config.py` - Add chunking configuration
- Tests - Add chunking test cases

**Performance Estimates:**

| Audio Duration | Current | With Chunking | Status |
|---------------|---------|---------------|--------|
| 30s | 15-30s | 15-30s (no change) | ✅ |
| 120s | 60-120s | 60-120s | ✅ No timeout |
| 278s | **TIMEOUT** | 140-280s | ✅ Works |
| 10min | **TIMEOUT** | 5-10min | ✅ Works |

**Risks:**
- Minor quality degradation at chunk boundaries (mitigated by overlap)
- Slightly increased total time due to overlap (~3-5%)
- Complexity increase (mitigated by clear separation of concerns)

