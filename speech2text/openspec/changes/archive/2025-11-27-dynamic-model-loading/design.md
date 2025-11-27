# Dynamic Model Loading - Design

## Architecture Shift: CLI → Shared Library

### Current Architecture (CLI Wrapper)

```
┌─────────────┐
│  FastAPI    │
│  Request    │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────┐
│ subprocess.run()            │
│ → spawn whisper-cli process │
│ → load model from disk      │
│ → transcribe                │
│ → parse stdout              │
│ → kill process              │
└─────────────────────────────┘
       │
       ▼
┌─────────────┐
│  Response   │
└─────────────┘

Issues:
- Model loaded every request
- Process spawn overhead
- Fragile stdout parsing
- No model reuse
```

### New Architecture (Shared Library)

```
┌─────────────┐
│  FastAPI    │
│  Startup    │
└──────┬──────┘
       │
       ▼
┌──────────────────────────────┐
│ WhisperLibraryAdapter        │
│ → load .so files (once)      │
│ → whisper_init_from_file()   │
│ → keep context in memory     │
└──────────────────────────────┘
       │
       ▼
┌─────────────┐     ┌──────────────────────┐
│  Request 1  │────▶│ whisper_full(ctx)    │
└─────────────┘     │ (direct C call)      │
                    └──────────────────────┘
┌─────────────┐     ┌──────────────────────┐
│  Request 2  │────▶│ whisper_full(ctx)    │
└─────────────┘     │ (reuse same context) │
                    └──────────────────────┘

Benefits:
- Model loaded once
- Direct memory access
- No process overhead
- Context reuse
```

## Component Design

### 1. WhisperLibraryAdapter

New adapter class to replace `WhisperTranscriber`:

```python
class WhisperLibraryAdapter:
    def __init__(self, model_size: str = "small"):
        self.model_size = model_size
        self.lib_dir = self._get_lib_dir()
        self.model_path = self._get_model_path()
        
        # Load libraries
        self._load_dependencies()
        self.lib = ctypes.CDLL(str(self.lib_dir / "libwhisper.so"))
        
        # Initialize context (once)
        self.ctx = self.lib.whisper_init_from_file(
            self.model_path.encode('utf-8')
        )
    
    def transcribe(self, audio_path: str) -> str:
        # Direct C call, no subprocess
        return self._call_whisper_full(audio_path)
    
    def __del__(self):
        if self.ctx:
            self.lib.whisper_free(self.ctx)
```

### 2. Smart Entrypoint

`cmd/api/entrypoint.sh`:

```bash
#!/bin/bash
set -e

# Read model size from ENV
MODEL_SIZE=${WHISPER_MODEL_SIZE:-small}
MODEL_DIR="whisper_${MODEL_SIZE}_xeon"

# Download artifacts if not present
if [ ! -d "$MODEL_DIR" ]; then
    python3 scripts/download_whisper_artifacts.py $MODEL_SIZE
fi

# Set library path
export LD_LIBRARY_PATH="$PWD/$MODEL_DIR:$LD_LIBRARY_PATH"

# Start application
exec python3 cmd/api/main.py
```

### 3. Configuration Updates

Add to `core/config.py`:

```python
class Settings(BaseSettings):
    # Whisper Library Settings
    whisper_model_size: str = Field(default="small", alias="WHISPER_MODEL_SIZE")
    whisper_artifacts_dir: str = Field(default=".", alias="WHISPER_ARTIFACTS_DIR")
```

### 4. Dockerfile Changes

**Complete Dockerfile for Dynamic Model Loading:**

```dockerfile
FROM python:3.12-slim-bookworm AS base

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libgomp1 \
    ffmpeg \
    wget \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install Python dependencies
COPY pyproject.toml uv.lock ./
RUN pip install uv && uv sync --frozen

# Copy application code
COPY . .

# Copy scripts
COPY scripts/download_whisper_artifacts.py /app/scripts/
RUN chmod +x /app/scripts/download_whisper_artifacts.py

# Copy and setup entrypoint
COPY cmd/api/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Environment variables (can be overridden at runtime)
ENV WHISPER_MODEL_SIZE=small \
    MINIO_ENDPOINT=http://172.16.19.115:9000 \
    MINIO_ACCESS_KEY=smap \
    MINIO_SECRET_KEY=hcmut2025

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# Use entrypoint for dynamic model loading
ENTRYPOINT ["/entrypoint.sh"]
CMD ["python", "-m", "uvicorn", "cmd.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Key Changes from Current Dockerfile:**
1. ✅ Added `wget` for downloading artifacts
2. ✅ Copy `scripts/download_whisper_artifacts.py`
3. ✅ Copy and chmod `entrypoint.sh`
4. ✅ Add MinIO environment variables (overridable)
5. ✅ Set `WHISPER_MODEL_SIZE` as ENV (default: small)
6. ✅ Use entrypoint instead of direct CMD
7. ❌ **NO** hardcoded model downloads at build time
8. ❌ **NO** model-specific image variants

**docker-compose.yml Updates:**

```yaml
version: '3.8'

services:
  api:
    build:
      context: .
      dockerfile: cmd/api/Dockerfile
    ports:
      - "8000:8000"
    environment:
      # Change this to switch models (no rebuild needed!)
      - WHISPER_MODEL_SIZE=small  # or 'medium'
      
      # MinIO configuration
      - MINIO_ENDPOINT=http://172.16.19.115:9000
      - MINIO_ACCESS_KEY=smap
      - MINIO_SECRET_KEY=hcmut2025
      
      # App configuration
      - API_PORT=8000
      - DEBUG=true
    volumes:
      # Optional: cache models between container restarts
      - whisper_models:/app/whisper_small_xeon
      - whisper_models:/app/whisper_medium_xeon
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  whisper_models:
```

**Usage Examples:**

```bash
# Run with small model (default)
docker-compose up

# Run with medium model (just change ENV, no rebuild!)
WHISPER_MODEL_SIZE=medium docker-compose up

# Or edit docker-compose.yml and change:
# environment:
#   - WHISPER_MODEL_SIZE=medium
```

## Artifact Download Script

### scripts/download_whisper_artifacts.py

Python script to download Whisper artifacts from MinIO:

```python
#!/usr/bin/env python3
"""
Download Whisper artifacts from MinIO based on model size.
Usage: python scripts/download_whisper_artifacts.py [small|medium]
"""
import os
import sys
from pathlib import Path

try:
    import boto3
    from botocore.exceptions import ClientError
    from botocore.client import Config
except ImportError:
    print("Error: boto3 not installed. Install with: pip install boto3")
    sys.exit(1)

# MinIO Configuration (from environment or defaults)
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://172.16.19.115:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "smap")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "hcmut2025")
BUCKET_NAME = "whisper-artifacts"

def download_artifacts(model_size="small"):
    """Download Whisper artifacts for specified model size"""
    
    # Create output directory
    output_dir = Path(f"whisper_{model_size}_xeon")
    output_dir.mkdir(exist_ok=True)
    
    print(f"📦 Downloading Whisper {model_size.upper()} artifacts...")
    print(f"   From: {MINIO_ENDPOINT}/{BUCKET_NAME}")
    print(f"   To: {output_dir}/")
    print()
    
    # Create S3 client
    s3_client = boto3.client(
        's3',
        endpoint_url=MINIO_ENDPOINT,
        aws_access_key_id=MINIO_ACCESS_KEY,
        aws_secret_access_key=MINIO_SECRET_KEY,
        config=Config(signature_version='s3v4'),
        region_name='us-east-1'
    )
    
    # List of files to download
    prefix = f"whisper_{model_size}_xeon/"
    
    try:
        # List objects in bucket
        response = s3_client.list_objects_v2(Bucket=BUCKET_NAME, Prefix=prefix)
        
        if 'Contents' not in response:
            print(f"❌ No artifacts found for {model_size} model")
            return False
        
        # Download each file
        for obj in response['Contents']:
            key = obj['Key']
            filename = key.split('/')[-1]
            
            if not filename:  # Skip directory entries
                continue
            
            local_path = output_dir / filename
            file_size_mb = obj['Size'] / (1024 * 1024)
            
            print(f"⬇️  {filename} ({file_size_mb:.1f} MB)...", end=" ", flush=True)
            
            try:
                s3_client.download_file(BUCKET_NAME, key, str(local_path))
                print("✓")
            except ClientError as e:
                print(f"✗ Error: {e}")
                return False
        
        print()
        print(f"✅ Downloaded to: {output_dir}/")
        
        # Verify critical files exist
        required_files = [
            "libwhisper.so",
            "libggml.so.0",
            "libggml-base.so.0",
            "libggml-cpu.so.0",
            f"ggml-{model_size}-q5_1.bin"
        ]
        
        for file in required_files:
            if not (output_dir / file).exists():
                print(f"❌ Missing required file: {file}")
                return False
        
        print("✅ All required files verified")
        return True
        
    except ClientError as e:
        print(f"❌ Error accessing MinIO: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1:
        model_size = sys.argv[1].lower()
    else:
        model_size = os.getenv("WHISPER_MODEL_SIZE", "small")
    
    if model_size not in ["small", "medium"]:
        print("Usage: python download_whisper_artifacts.py [small|medium]")
        print(f"Or set WHISPER_MODEL_SIZE environment variable")
        sys.exit(1)
    
    success = download_artifacts(model_size)
    sys.exit(0 if success else 1)
```

### Key Features:
- Reads MinIO credentials from environment variables
- Downloads all files for specified model size
- Shows progress with file sizes
- Verifies all required files after download
- Returns proper exit codes for error handling

---
COPY cmd/api/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Model size can be set at runtime
ENV WHISPER_MODEL_SIZE=small

ENTRYPOINT ["/entrypoint.sh"]
```

## Library Loading Sequence

Critical: Dependencies must be loaded in correct order:

```python
# 1. Load base libraries first
libggml_base = ctypes.CDLL("libggml-base.so.0", mode=ctypes.RTLD_GLOBAL)
libggml_cpu = ctypes.CDLL("libggml-cpu.so.0", mode=ctypes.RTLD_GLOBAL)

# 2. Load GGML core
libggml = ctypes.CDLL("libggml.so.0", mode=ctypes.RTLD_GLOBAL)

# 3. Load Whisper (depends on above)
libwhisper = ctypes.CDLL("libwhisper.so")
```

## Model Path Mapping

```python
MODEL_CONFIGS = {
    "small": {
        "dir": "whisper_small_xeon",
        "model": "ggml-small-q5_1.bin",
        "size_mb": 181,
        "ram_mb": 500
    },
    "medium": {
        "dir": "whisper_medium_xeon",
        "model": "ggml-medium-q5_1.bin",
        "size_mb": 1500,
        "ram_mb": 2000
    }
}
```

## Error Handling

```python
class WhisperLibraryError(Exception):
    """Base exception for Whisper library errors"""
    pass

class LibraryLoadError(WhisperLibraryError):
    """Failed to load .so files"""
    pass

class ModelInitError(WhisperLibraryError):
    """Failed to initialize Whisper context"""
    pass
```

## Performance Expectations

| Metric | CLI (Before) | Library (After) | Improvement |
|--------|-------------|-----------------|-------------|
| First request latency | 2-3s | 0.5-1s | 60-75% |
| Subsequent requests | 2-3s | 0.1-0.3s | 90% |
| Memory usage (small) | ~200MB/req | ~500MB total | Constant |
| Memory usage (medium) | ~500MB/req | ~2GB total | Constant |
| Concurrent requests | Poor | Excellent | N/A |

## Migration Strategy

1. **Phase 1**: Implement `WhisperLibraryAdapter` alongside existing `WhisperTranscriber`
2. **Phase 2**: Add feature flag to switch between CLI and library
3. **Phase 3**: Test library integration thoroughly
4. **Phase 4**: Make library the default, deprecate CLI
5. **Phase 5**: Remove CLI code after validation

## Rollback Plan

- Keep CLI code until library is proven stable
- Feature flag allows instant rollback: `USE_WHISPER_LIBRARY=false`
- No data migration needed (stateless architecture)
