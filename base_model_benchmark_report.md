## Base Model Benchmark Report

**Date:** November 27, 2025  
**Environment:** Docker Compose dev (`make -f Makefile.dev dev-base`)  
**Configuration Highlights:** `WHISPER_MODEL=base`, sequential chunking (30 s length, 1 s overlap), adaptive timeout (`max(base_timeout, duration × 1.5)`), auto thread detection capped at 8 threads.

### 1. Test Coverage

| Test | Audio Duration | Language / Content | Chunking Path | Result | RTF* |
|------|----------------|--------------------|---------------|--------|------|
| 1 | 266.06 s (≈4m26s) | Vietnamese music | Chunked (9 chunks) | Success | 0.10 |
| 2 | 565.26 s (≈9m25s) | Vietnamese gaming commentary | Chunked (19 chunks) | Success | 0.07 |
| 3 | 818.10 s (≈13m38s) | English MQTT tutorial | Chunked (28 chunks) | Success | 0.07 |
| 4 | 1108.69 s (≈18m29s) | Vietnamese TypeScript tutorial | Chunked (37 chunks) | Success | 0.11 |

\*Realtime Factor = processing time ÷ audio duration (lower is faster). All runs reported confidence 0.98 with fluent transcripts.

### 2. Small vs Base Benchmark

Small-model metrics are sourced from the previously generated HTML benchmark (same audio dataset and chunking parameters). Base metrics come from the Docker Compose dev rerun with the base model artifacts.

| Test | Content | Processing Time – Small (s) | Processing Time – Base (s) | Absolute Delta (s) | Speed-up (Small ÷ Base) |
|------|---------|----------------------------:|---------------------------:|--------------------:|------------------------:|
| 1 | Vietnamese music | 74.56 | 25.26 | 49.30 | 2.95 |
| 2 | Vietnamese gaming | 109.41 | 39.36 | 70.05 | 2.78 |
| 3 | English MQTT tutorial | 171.33 | 57.29 | 114.04 | 2.99 |
| 4 | Vietnamese TypeScript tutorial | 269.77 | 123.61 | 146.16 | 2.18 |

**Observations**
- Latency drops between 50% and 70%, keeping throughput stable even for 18-minute content.
- Confidence scores and transcript quality remain unchanged between models.
- Memory stays flat (~1 GB) thanks to sequential chunking; CPU utilization reaches the 8 thread cap.

### 3. Benchmark Insights

- **Consistency:** Processing time scales linearly with audio duration. No timeouts were observed for durations up to 18.5 minutes.
- **Adaptive Timeout:** For the longest file, the computed timeout (≈1663 s) left ample buffer relative to the actual 124 s base-model runtime.
- **Threading:** Auto-detected 8 threads provide the best balance on the current hardware; forcing fewer threads regresses throughput noticeably.
- **Chunk Management:** Every chunk is processed sequentially with immediate cleanup, so disk and RAM stay stable regardless of clip length.

### 4. Recommendations

1. **Default to Base Model:** The speedup and comparable accuracy justify making `base` the production default.
2. **Resource Requests:** Allocate ≥2 vCPU and 2.5 GB RAM per pod to cover the base model plus chunking overhead.
3. **Monitoring:** Track `processing_time / audio_duration` (<0.5 expected) and memory (>1.2 GB indicates misconfiguration).
4. **Next Benchmarks:** Optional follow-up includes short-audio fast-path validation (<30 s), concurrency stress tests (2–3 parallel jobs), and recording metrics for HPA tuning.

The base model now has clear benchmark data demonstrating superior latency with no regression in quality, enabling safe rollout in both Docker dev and Kubernetes environments.

