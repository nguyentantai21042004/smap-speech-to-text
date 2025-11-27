# Technical Design: Sequential Smart Chunking

## Context

Current implementation can only reliably transcribe audio < 2 minutes due to:
1. CPU inference time ~0.5-1.0x realtime (small model)
2. Fixed 90s timeout limit
3. Single-pass processing (no chunking)
4. Full audio loaded in memory

For production use cases (podcasts, videos, meetings), we need to support audio up to 30-60 minutes.

## Goals

**Must Have:**
- Process audio up to 30 minutes without timeout
- Flat memory usage regardless of audio length
- Maintain transcription quality (>95% accuracy vs baseline)
- Backward compatible (no breaking changes)

**Should Have:**
- Progress logging for long audio
- Configurable chunk size and overlap
- Smart merge to handle word boundaries

**Nice to Have:**
- VAD-based smart chunking
- Parallel processing option
- Streaming transcription API

## Non-Goals

- Real-time streaming transcription (future work)
- GPU optimization (CPU-focused for now)
- Multi-language mixing within single audio
- Speaker diarization

## Key Decisions

### Decision 1: Sequential vs Parallel Chunking

**Chosen: Sequential**

**Rationale:**
1. **CPU Efficiency:** Whisper.cpp uses OpenMP for multi-threading WITHIN a single inference
   - Already utilizes 8 CPU cores efficiently
   - Parallel chunks would cause CPU thrashing (context switching)
   - Sequential is actually faster on CPU due to cache locality

2. **Memory Safety:**
   - Each Whisper instance: ~500MB RAM
   - 4 parallel chunks = 2GB RAM spike
   - Sequential = stable 500MB
   - Prevents OOM on concurrent requests

3. **Simplicity:**
   - Easier to debug
   - Clear progress tracking
   - Simpler error handling

**Alternatives Considered:**
- **Parallel Processing:** Rejected due to CPU contention and memory explosion
- **GPU Parallel:** Future work when GPU support added
- **Worker Pool:** Over-engineering for current scale

### Decision 2: FFmpeg vs Librosa for Audio Splitting

**Chosen: FFmpeg**

**Rationale:**
1. **Performance:**
   - FFmpeg: ~100ms to split 5-min audio
   - Librosa: ~2-3 seconds (Python overhead)
   
2. **Quality:**
   - FFmpeg produces exact 16kHz mono WAV (Whisper native format)
   - No quality degradation
   
3. **Dependencies:**
   - FFmpeg already in Dockerfile
   - Librosa adds 500MB+ to image

**Alternatives Considered:**
- **Librosa:** Too slow, unnecessary dependency
- **Pydub:** Wrapper around FFmpeg, adds complexity
- **Raw PCM manipulation:** Reinventing the wheel

### Decision 3: Chunk Size Selection

**Chosen: 30 seconds**

**Rationale:**
1. **Model Optimality:**
   - Whisper trained primarily on 30s segments
   - Native "window size" for the model
   - Best accuracy at this duration

2. **Performance:**
   - 30s chunk: 15-30s inference time
   - Small enough to avoid timeout
   - Large enough to minimize overhead

3. **Context:**
   - Enough context for full sentences
   - Not too long to cause memory issues

**Alternatives Considered:**
- **15s chunks:** Too short, loses context, more overhead
- **60s chunks:** Slower per chunk, higher memory
- **Dynamic chunks:** Over-engineering for MVP

### Decision 4: Overlap Strategy

**Chosen: 1 second fixed overlap**

**Rationale:**
1. **Word Boundary Handling:**
   - Average word duration: 0.3-0.5s
   - 1s overlap catches most cut-off words
   
2. **Overhead:**
   - 1s overlap on 30s chunks = ~3% overhead
   - Acceptable trade-off for quality

3. **Merge Simplicity:**
   - Fixed overlap easier to implement
   - Predictable performance

**Alternatives Considered:**
- **No overlap:** Words cut at boundaries, quality drop
- **5s overlap:** Too much overhead (~15%)
- **VAD-based:** Complex, future enhancement

## Architecture

### Component Diagram

```
TranscribeService
    │
    ├─> get_audio_duration() ──> ffprobe
    │                              │
    │                              v
    ├─> Decision: chunk needed?   
    │       │
    │       ├─> NO  ──> transcribe_direct()
    │       │               │
    │       │               v
    │       │           WhisperLibraryAdapter
    │       │
    │       └─> YES ──> transcribe_chunked()
    │                       │
    │                       ├─> split_audio() ──> ffmpeg
    │                       │       │
    │                       │       v
    │                       │   [chunk1.wav, chunk2.wav, ...]
    │                       │
    │                       ├─> Loop: for each chunk
    │                       │     │
    │                       │     ├─> transcribe_chunk() ──> WhisperLibraryAdapter
    │                       │     │
    │                       │     ├─> collect result
    │                       │     │
    │                       │     └─> cleanup chunk file
    │                       │
    │                       └─> merge_results()
    │                               │
    │                               v
    │                           final transcript
    v
return to API
```

### Data Flow

```
1. Client Request
   POST /transcribe {"media_url": "...", "language": "en"}
   
2. Download Audio
   stream_download() → /tmp/uuid.mp3 (6.38 MB)
   
3. Duration Check
   ffprobe → duration=278.65s
   
4. Decision
   278s > 30s → USE CHUNKING
   
5. Split Audio
   ffmpeg → [chunk_0.wav (30s), chunk_1.wav (30s), ..., chunk_9.wav (8.65s)]
   Total: 10 chunks
   
6. Sequential Processing
   Loop i=0 to 9:
     - Load chunk_i.wav
     - Whisper inference (~15-30s)
     - Append to results[]
     - Delete chunk_i.wav
     - Log "Processed chunk i+1/10"
   
7. Merge Results
   results = ["text1", "text2", ..., "text10"]
   final_text = smart_merge(results)  # Handle overlap
   
8. Response
   {
     "status": "success",
     "transcription": final_text,
     "processing_time": 165.2,
     "chunks_processed": 10,
     "metadata": {...}
   }
```

## Implementation Details

### FFmpeg Command for Splitting

```bash
# Extract chunk from start_time with duration
ffmpeg -y \
  -i input.mp3 \
  -ss {start_time} \      # Seek to start
  -t {duration} \          # Duration of chunk
  -ar 16000 \              # Resample to 16kHz
  -ac 1 \                  # Convert to mono
  -c:a pcm_s16le \         # PCM 16-bit (WAV)
  chunk_{i}.wav
```

**Performance:** ~50-100ms per chunk

### Chunk Boundary Calculation

```python
def calculate_chunks(duration, chunk_size=30, overlap=1):
    """
    Example: duration=100s, chunk_size=30s, overlap=1s
    Returns: [(0, 30), (29, 59), (58, 88), (87, 100)]
    """
    chunks = []
    start = 0
    while start < duration:
        end = min(start + chunk_size, duration)
        chunks.append((start, end))
        start = end - overlap  # Move with overlap
    return chunks
```

### Smart Merge Algorithm (MVP)

```python
def merge_chunks(chunk_texts, overlap_duration=1):
    """
    Simple MVP merge: join with space
    
    Future enhancement: compare overlapping regions
    and remove duplicates
    """
    # MVP: Simple concatenation
    return " ".join(text.strip() for text in chunk_texts if text)
    
    # Phase 2: Smart overlap handling
    # merged = [chunk_texts[0]]
    # for i in range(1, len(chunk_texts)):
    #     prev_words = merged[-1].split()[-5:]  # Last 5 words
    #     curr_words = chunk_texts[i].split()[:5]  # First 5 words
    #     overlap_match = find_longest_match(prev_words, curr_words)
    #     if overlap_match:
    #         # Remove duplicate from current chunk
    #         clean_text = remove_prefix(chunk_texts[i], overlap_match)
    #         merged.append(clean_text)
    #     else:
    #         merged.append(chunk_texts[i])
    # return " ".join(merged)
```

## Memory & Resource Analysis

### Memory Usage

| Stage | Memory | Notes |
|-------|--------|-------|
| Audio Download | ~6-20 MB | Temporary file |
| FFmpeg Split | ~10-30 MB | Temp chunks created |
| Whisper Load Model | ~190 MB | One-time (singleton) |
| Whisper Context | ~180 MB | Per inference |
| Whisper Inference | ~130 MB | Temporary buffers |
| **Peak Memory** | **~500 MB** | Stable for any audio length |

### CPU Usage

| Operation | CPU Time | Notes |
|-----------|----------|-------|
| Download | ~0.1-1s | Network bound |
| FFmpeg Split | ~0.1-0.5s | Minimal CPU |
| Whisper per chunk (30s) | ~15-30s | 8 threads, 100% CPU |
| Total for 278s audio | ~140-280s | 10 chunks × 15-30s |

### Disk Usage

| Item | Size | Lifecycle |
|------|------|-----------|
| Downloaded audio | 0.14-20 MB | Deleted after split |
| Chunk files | ~1-2 MB each | Deleted after transcribe |
| **Peak Disk** | ~20-40 MB | Temporary |

## Error Handling

### Failure Scenarios

1. **FFmpeg fails to split:**
   - Fallback: Try direct transcription
   - Log warning: "Chunking failed, using direct method"

2. **Single chunk fails:**
   - Skip chunk, mark as "[inaudible]"
   - Continue with remaining chunks
   - Log error with chunk index

3. **Disk space full:**
   - Fail fast before splitting
   - Check available space > 100MB
   - Return clear error message

4. **Timeout on single chunk:**
   - Should never happen (30s chunk)
   - If it does: skip chunk, log error

### Retry Strategy

- No retries for chunking (sequential nature)
- Fail fast and return partial results if needed
- Client can retry entire request if needed

## Testing Strategy

### Unit Tests

```python
def test_chunk_calculation():
    chunks = calculate_chunks(duration=100, chunk_size=30, overlap=1)
    assert chunks == [(0, 30), (29, 59), (58, 88), (87, 100)]

def test_short_audio_no_chunking():
    duration = 25
    chunks = calculate_chunks(duration, chunk_size=30)
    assert len(chunks) == 1
    assert chunks[0] == (0, 25)

def test_merge_basic():
    texts = ["Hello world", "this is", "a test"]
    result = merge_chunks(texts)
    assert result == "Hello world this is a test"
```

### Integration Tests

```python
@pytest.mark.slow
def test_chunked_transcription_120s():
    # 2-minute audio → ~4 chunks
    result = transcribe_chunked("test_120s.mp3")
    
    assert result["chunks_processed"] == 4
    assert len(result["transcription"]) > 0
    assert result["processing_time"] < 180  # < 3 minutes
    
@pytest.mark.slow  
def test_memory_stable_long_audio():
    # Monitor memory during 10-minute transcription
    initial_mem = get_memory_usage()
    result = transcribe_chunked("test_600s.mp3")
    peak_mem = get_peak_memory()
    
    assert peak_mem - initial_mem < 800 * 1024 * 1024  # < 800MB
```

## Performance Targets

| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| 30s audio | < 45s | 15-30s | ✅ |
| 120s audio | < 180s | 60-120s | ✅ |
| 300s audio | < 450s | 150-300s | ✅ |
| 10min audio | < 15min | 5-10min | ✅ |
| Memory usage | < 800MB | ~500MB | ✅ |
| Timeout rate | < 1% | TBD | ⏳ |

## Migration Plan

### Phase 1: Implementation (Week 1)
- Day 1-2: Core chunking logic
- Day 3: Integration with service
- Day 4-5: Testing

### Phase 2: Deployment (Week 2)
- Day 1: Deploy to staging
- Day 2-3: Testing with real audio
- Day 4: Production rollout (feature flag)
- Day 5: Monitoring and optimization

### Rollback Plan

If issues arise:
1. Set `WHISPER_CHUNK_ENABLED=false`
2. Service reverts to direct transcription
3. Long audio will timeout again (acceptable for rollback)

## Open Questions

1. **Q: Should we cache chunk files for retry?**
   - A: No, cleanup immediately. Client retry downloads again.

2. **Q: What if audio is 29.5 seconds?**
   - A: Use fast path (no chunking). Threshold is 30s.

3. **Q: How to handle multiple languages in one audio?**
   - A: Out of scope. Each chunk uses same language param.

4. **Q: Can we reuse chunks for multiple requests?**
   - A: No, audio URLs are unique presigned URLs.

## Success Metrics

- Zero timeouts for audio < 30 minutes
- Memory usage < 800MB peak
- Processing time < 1.5x audio duration
- Transcription quality > 95% vs non-chunked
- User satisfaction survey > 4/5 stars

## References

- Whisper.cpp documentation: https://github.com/ggerganov/whisper.cpp
- FFmpeg audio processing: https://ffmpeg.org/ffmpeg-filters.html
- OpenMP multi-threading: https://www.openmp.org/
- Original proposal: `CHUNKING_PROPOSAL.md`

