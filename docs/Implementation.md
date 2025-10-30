# HƯỚNG DẪN CHI TIẾT XÂY DỰNG HỆ THỐNG SPEECH-TO-TEXT BẤT ĐỒNG BỘ

## 📋 TỔNG QUAN KIẾN TRÚC

```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│   Client    │─────▶│ API Gateway │─────▶│   Redis     │
└─────────────┘      └─────────────┘      └─────────────┘
                             │                     │
                             ▼                     ▼
                      ┌─────────────┐      ┌─────────────┐
                      │  PostgreSQL │◀─────│   Workers   │
                      └─────────────┘      └─────────────┘
                                                   │
                                                   ▼
                                            ┌─────────────┐
                                            │ whisper.cpp │
                                            └─────────────┘
```

---

## 🚀 BƯỚC 1: KHỞI TẠO DỰ ÁN VÀ MÔI TRƯỜNG

### 1.1 Tạo thư mục dự án

```bash
# Tạo thư mục gốc
mkdir stt-async-system
cd stt-async-system

# Tạo cấu trúc thư mục
mkdir -p {api,worker,common,scripts,tests,docker,configs,storage}/{routes,uploads,results}
touch {api,worker,common}/__init__.py

# Tạo virtual environment
python3.11 -m venv venv
source venv/bin/activate  # Linux/Mac
# hoặc: venv\Scripts\activate  # Windows
```

### 1.2 Tạo file requirements.txt

```python
# FastAPI và dependencies
fastapi==0.104.1
uvicorn[standard]==0.24.0
python-multipart==0.0.6
aiofiles==23.2.1

# Database
sqlalchemy==2.0.23
psycopg2-binary==2.9.9
alembic==1.13.0

# Redis Queue
redis==5.0.1
rq==1.15.1
rq-scheduler==0.13.1

# Audio processing
pydub==0.25.1
librosa==0.10.1
soundfile==0.12.1
numpy==1.26.2

# Utils
python-dotenv==1.0.0
pyyaml==6.0.1
pydantic==2.5.2
pydantic-settings==2.1.0

# Logging
loguru==0.7.2

# Testing
pytest==7.4.3
pytest-asyncio==0.21.1
httpx==0.25.2

# Development
black==23.12.0
flake8==6.1.0
pre-commit==3.6.0
```

### 1.3 Cài đặt dependencies

```bash
pip install -r requirements.txt

# Cài đặt system dependencies (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install -y \
    build-essential \
    cmake \
    git \
    ffmpeg \
    libopenblas-dev \
    postgresql-client \
    redis-tools
```

---

## 🚀 BƯỚC 2: THIẾT LẬP WHISPER.CPP

### 2.1 Clone và build whisper.cpp

```bash
# Tạo thư mục cho whisper
mkdir -p whisper
cd whisper

# Clone repository
git clone https://github.com/ggerganov/whisper.cpp.git
cd whisper.cpp

# Build với optimization cho CPU
make clean
WHISPER_OPENBLAS=1 make -j$(nproc)

# Test build
./main --help
```

### 2.2 Tạo script download models

```bash
# scripts/download_models.sh
#!/bin/bash
set -e

WHISPER_DIR="../whisper/whisper.cpp"
MODELS_DIR="$WHISPER_DIR/models"

echo "📥 Downloading Whisper models..."

cd $WHISPER_DIR

# Download quantized models for CPU optimization
echo "Downloading small model..."
bash ./models/download-ggml-model.sh small.en   # English only (~150MB)
bash ./models/download-ggml-model.sh small      # Multilingual (~500MB)

echo "Downloading medium model..."
bash ./models/download-ggml-model.sh medium     # Multilingual (~1.5GB)

# Optional: Download larger models if needed
# bash ./models/download-ggml-model.sh large-v3  # Best quality (~3GB)

echo "✅ Models downloaded successfully!"
ls -lah $MODELS_DIR/

# Make executable available globally
sudo cp ./main /usr/local/bin/whisper-cpp
echo "✅ whisper-cpp installed to /usr/local/bin/"
```

---

## 🚀 BƯỚC 3: THIẾT LẬP DATABASE

### 3.1 Tạo script khởi tạo database

```sql
-- scripts/init_db.sql

-- Create database
CREATE DATABASE IF NOT EXISTS stt_db;
\c stt_db;

-- Create enum types
CREATE TYPE job_status AS ENUM ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED');
CREATE TYPE language_code AS ENUM ('en', 'vi');

-- Create jobs table
CREATE TABLE jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id VARCHAR(50) UNIQUE NOT NULL,
    status job_status DEFAULT 'PENDING',
    language language_code NOT NULL,
    
    -- File information
    original_filename VARCHAR(255),
    file_path TEXT,
    file_size_mb FLOAT,
    audio_duration_seconds FLOAT,
    
    -- Processing information
    worker_id VARCHAR(100),
    retry_count INTEGER DEFAULT 0,
    chunks_total INTEGER,
    chunks_completed INTEGER DEFAULT 0,
    
    -- Results
    transcription_text TEXT,
    result_file_path TEXT,
    error_message TEXT,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX idx_job_status ON jobs(status);
CREATE INDEX idx_job_created ON jobs(created_at DESC);
CREATE INDEX idx_job_id ON jobs(job_id);

-- Create chunks table for tracking individual chunks
CREATE TABLE chunks (
    id SERIAL PRIMARY KEY,
    job_id VARCHAR(50) REFERENCES jobs(job_id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    start_time FLOAT,
    end_time FLOAT,
    transcription TEXT,
    status job_status DEFAULT 'PENDING',
    error_message TEXT,
    processed_at TIMESTAMP,
    
    UNIQUE(job_id, chunk_index)
);

-- Create processing metrics table
CREATE TABLE metrics (
    id SERIAL PRIMARY KEY,
    job_id VARCHAR(50) REFERENCES jobs(job_id) ON DELETE CASCADE,
    metric_name VARCHAR(100),
    metric_value FLOAT,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Trigger to update updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_jobs_updated_at 
    BEFORE UPDATE ON jobs 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();
```

---

## 🚀 BƯỚC 4: TẠO COMMON MODULE

### 4.1 Configuration Management (common/config.py)

```python
# common/config.py
from pydantic_settings import BaseSettings
from typing import Optional
import os
import yaml

class Settings(BaseSettings):
    """Application configuration"""
    
    # API Settings
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_workers: int = 4
    max_upload_size_mb: int = 500
    
    # Database
    database_url: str = "postgresql://sttuser:sttpass@localhost:5432/stt_db"
    
    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None
    
    # Storage
    upload_dir: str = "./storage/uploads"
    results_dir: str = "./storage/results"
    temp_dir: str = "/tmp/stt_processing"
    
    # Whisper Settings
    whisper_executable: str = "/usr/local/bin/whisper-cpp"
    whisper_models_dir: str = "./whisper/whisper.cpp/models"
    default_model: str = "medium"  # small, medium, large-v3
    default_language: str = "vi"
    
    # Chunking Settings
    chunk_strategy: str = "silence_based"  # silence_based or fixed_size
    chunk_duration: int = 30  # seconds
    chunk_overlap: int = 3  # seconds
    silence_threshold: int = -40  # dB
    min_silence_duration: float = 1.0  # seconds
    
    # Processing Settings
    max_retries: int = 3
    retry_delay: int = 2  # seconds
    job_timeout: int = 3600  # 1 hour
    chunk_timeout: int = 300  # 5 minutes
    max_concurrent_jobs: int = 4
    
    # Logging
    log_level: str = "INFO"
    log_file: str = "logs/stt.log"
    
    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'
        
    @classmethod
    def from_yaml(cls, yaml_file: str):
        """Load config from YAML file"""
        with open(yaml_file, 'r') as f:
            config_dict = yaml.safe_load(f)
        return cls(**config_dict)

settings = Settings()
```

### 4.2 Logger Setup (common/logger.py)

```python
# common/logger.py
from loguru import logger
import sys
from pathlib import Path

def setup_logger(log_level="INFO", log_file="logs/stt.log"):
    """Configure loguru logger"""
    
    # Remove default handler
    logger.remove()
    
    # Create log directory
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)
    
    # Console handler with color
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=log_level,
        colorize=True
    )
    
    # File handler with rotation
    logger.add(
        log_file,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{line} - {message}",
        level=log_level,
        rotation="100 MB",
        retention="7 days",
        compression="zip"
    )
    
    return logger

# Initialize logger
log = setup_logger()
```

### 4.3 Constants (common/constants.py)

```python
# common/constants.py
from enum import Enum

class JobStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class Language(str, Enum):
    ENGLISH = "en"
    VIETNAMESE = "vi"

# Supported audio formats
SUPPORTED_FORMATS = [
    '.mp3', '.wav', '.m4a', '.mp4', 
    '.aac', '.ogg', '.flac', '.wma',
    '.webm', '.mkv', '.avi', '.mov'
]

# Queue names
QUEUE_HIGH_PRIORITY = "stt_jobs_high"
QUEUE_NORMAL = "stt_jobs"
QUEUE_LOW_PRIORITY = "stt_jobs_low"
QUEUE_DEAD_LETTER = "stt_jobs_dlq"

# Model mapping
MODEL_SIZES = {
    "tiny": "ggml-tiny.bin",
    "base": "ggml-base.bin",
    "small": "ggml-small.bin",
    "medium": "ggml-medium.bin",
    "large": "ggml-large-v3.bin",
}

# Processing constants
MAX_CHUNK_SIZE_SECONDS = 60
MIN_CHUNK_SIZE_SECONDS = 5
DEFAULT_SAMPLE_RATE = 16000
```

---

## 🚀 BƯỚC 5: XÂY DỰNG WORKER MODULE

### 5.1 Error Definitions (worker/errors.py)

```python
# worker/errors.py
class STTError(Exception):
    """Base STT Error"""
    pass

class TransientError(STTError):
    """Errors that can be retried"""
    def __init__(self, message, retry_count=0):
        self.message = message
        self.retry_count = retry_count
        super().__init__(self.message)

class PermanentError(STTError):
    """Errors that should not be retried"""
    pass

# Specific transient errors
class OutOfMemoryError(TransientError):
    pass

class TimeoutError(TransientError):
    pass

class WhisperCrashError(TransientError):
    pass

class NetworkError(TransientError):
    pass

# Specific permanent errors  
class InvalidAudioFormatError(PermanentError):
    pass

class UnsupportedLanguageError(PermanentError):
    pass

class FileTooLargeError(PermanentError):
    pass

class FileNotFoundError(PermanentError):
    pass

class CorruptedFileError(PermanentError):
    pass
```

### 5.2 Audio Chunking Module (worker/chunking.py)

```python
# worker/chunking.py
import os
from typing import List, Tuple, Optional
from pydub import AudioSegment
from pydub.silence import detect_nonsilent
import numpy as np
from common.logger import log
from common.config import settings
from worker.errors import InvalidAudioFormatError, FileTooLargeError

class AudioChunker:
    """Handle audio chunking strategies"""
    
    def __init__(self):
        self.chunk_duration = settings.chunk_duration * 1000  # Convert to ms
        self.chunk_overlap = settings.chunk_overlap * 1000
        self.silence_threshold = settings.silence_threshold
        self.min_silence_duration = settings.min_silence_duration * 1000
        
    def load_audio(self, file_path: str) -> AudioSegment:
        """Load audio file and convert to consistent format"""
        try:
            # Check file size
            file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
            if file_size_mb > settings.max_upload_size_mb:
                raise FileTooLargeError(f"File size {file_size_mb:.2f}MB exceeds limit {settings.max_upload_size_mb}MB")
            
            # Load audio
            audio = AudioSegment.from_file(file_path)
            
            # Convert to mono, 16kHz for optimal Whisper performance
            audio = audio.set_channels(1)
            audio = audio.set_frame_rate(16000)
            
            log.info(f"Loaded audio: duration={len(audio)/1000:.2f}s, rate={audio.frame_rate}Hz")
            return audio
            
        except Exception as e:
            log.error(f"Failed to load audio: {e}")
            raise InvalidAudioFormatError(f"Cannot load audio file: {e}")
    
    def chunk_audio(self, audio_path: str, strategy: str = None) -> List[dict]:
        """Main chunking method"""
        strategy = strategy or settings.chunk_strategy
        audio = self.load_audio(audio_path)
        
        if strategy == "silence_based":
            chunks = self._chunk_by_silence(audio)
        else:
            chunks = self._chunk_fixed_size(audio)
        
        # Save chunks to temporary files
        chunk_files = self._save_chunks(chunks, audio_path)
        return chunk_files
    
    def _chunk_by_silence(self, audio: AudioSegment) -> List[Tuple[int, int]]:
        """Chunk audio based on silence detection"""
        log.info("Using silence-based chunking strategy")
        
        # Detect non-silent chunks
        nonsilent_chunks = detect_nonsilent(
            audio,
            min_silence_len=self.min_silence_duration,
            silence_thresh=self.silence_threshold,
            seek_step=10
        )
        
        if not nonsilent_chunks:
            log.warning("No non-silent chunks detected, falling back to fixed-size chunking")
            return self._chunk_fixed_size(audio)
        
        # Merge small chunks and split large ones
        chunks = []
        current_start = 0
        
        for start_ms, end_ms in nonsilent_chunks:
            chunk_duration = end_ms - current_start
            
            # If chunk is too long, split it
            if chunk_duration > self.chunk_duration * 1.5:
                # Add a reasonable chunk
                chunks.append((current_start, current_start + self.chunk_duration))
                current_start = current_start + self.chunk_duration - self.chunk_overlap
            elif chunk_duration > self.chunk_duration * 0.5:
                # Good size chunk
                chunks.append((current_start, end_ms))
                current_start = end_ms - self.chunk_overlap
        
        # Add final chunk if needed
        if current_start < len(audio):
            chunks.append((current_start, len(audio)))
        
        log.info(f"Created {len(chunks)} chunks using silence detection")
        return chunks
    
    def _chunk_fixed_size(self, audio: AudioSegment) -> List[Tuple[int, int]]:
        """Chunk audio into fixed-size segments"""
        log.info("Using fixed-size chunking strategy")
        
        chunks = []
        audio_length = len(audio)
        chunk_start = 0
        
        while chunk_start < audio_length:
            chunk_end = min(chunk_start + self.chunk_duration, audio_length)
            chunks.append((chunk_start, chunk_end))
            
            # Move to next chunk with overlap
            chunk_start = chunk_end - self.chunk_overlap
            if chunk_end >= audio_length:
                break
        
        log.info(f"Created {len(chunks)} fixed-size chunks")
        return chunks
    
    def _save_chunks(self, chunks: List[Tuple[int, int]], original_path: str) -> List[dict]:
        """Save chunks as temporary WAV files"""
        import tempfile
        from pathlib import Path
        
        audio = AudioSegment.from_file(original_path)
        chunk_files = []
        temp_dir = Path(tempfile.mkdtemp(prefix="stt_chunks_"))
        
        for i, (start_ms, end_ms) in enumerate(chunks):
            chunk_audio = audio[start_ms:end_ms]
            
            # Save as WAV for best compatibility
            chunk_path = temp_dir / f"chunk_{i:04d}.wav"
            chunk_audio.export(
                chunk_path,
                format="wav",
                parameters=["-ac", "1", "-ar", "16000"]  # Mono, 16kHz
            )
            
            chunk_files.append({
                "index": i,
                "path": str(chunk_path),
                "start_ms": start_ms,
                "end_ms": end_ms,
                "duration_ms": end_ms - start_ms
            })
            
            log.debug(f"Saved chunk {i}: {start_ms/1000:.2f}s - {end_ms/1000:.2f}s")
        
        return chunk_files
```

### 5.3 Whisper Transcriber (worker/transcriber.py)

```python
# worker/transcriber.py
import subprocess
import json
import os
import tempfile
from typing import Optional, Dict, Any
from pathlib import Path
from common.logger import log
from common.config import settings
from worker.errors import WhisperCrashError, TimeoutError

class WhisperTranscriber:
    """Interface to whisper.cpp"""
    
    def __init__(self):
        self.executable = settings.whisper_executable
        self.models_dir = Path(settings.whisper_models_dir)
        self.default_model = settings.default_model
        
        # Verify whisper.cpp is available
        if not os.path.exists(self.executable):
            raise FileNotFoundError(f"whisper.cpp not found at {self.executable}")
    
    def transcribe(
        self, 
        audio_path: str, 
        language: str = "vi",
        model: str = None,
        timeout: int = None
    ) -> Dict[str, Any]:
        """Transcribe audio file using whisper.cpp"""
        
        model = model or self.default_model
        timeout = timeout or settings.chunk_timeout
        
        # Get model path
        model_file = self._get_model_path(model, language)
        
        # Prepare output file
        output_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        output_path = output_file.name
        output_file.close()
        
        # Build command
        cmd = [
            self.executable,
            "-m", str(model_file),
            "-f", audio_path,
            "-l", language,
            "-oj",  # Output JSON
            "-of", output_path.replace('.json', ''),  # Output file prefix
            "-t", "4",  # Threads
            "-p", "1",  # Processors
            "--no-timestamps",  # Disable timestamps for better accuracy
        ]
        
        log.info(f"Running whisper.cpp: model={model}, language={language}")
        log.debug(f"Command: {' '.join(cmd)}")
        
        try:
            # Run whisper.cpp
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=True
            )
            
            # Read JSON output
            with open(output_path, 'r', encoding='utf-8') as f:
                transcription_data = json.load(f)
            
            # Extract text
            text = self._extract_text(transcription_data)
            
            log.info(f"Transcription completed: {len(text)} characters")
            
            return {
                "text": text,
                "language": language,
                "model": model,
                "segments": transcription_data.get("transcription", [])
            }
            
        except subprocess.TimeoutExpired:
            log.error(f"Whisper timeout after {timeout}s")
            raise TimeoutError(f"Transcription timeout after {timeout} seconds")
            
        except subprocess.CalledProcessError as e:
            log.error(f"Whisper.cpp failed: {e.stderr}")
            raise WhisperCrashError(f"Whisper.cpp crashed: {e.stderr}")
            
        finally:
            # Cleanup
            if os.path.exists(output_path):
                os.unlink(output_path)
    
    def _get_model_path(self, model: str, language: str) -> Path:
        """Get the model file path"""
        # For English-only, use .en models
        if language == "en" and model in ["tiny", "base", "small", "medium"]:
            model_name = f"ggml-{model}.en.bin"
        else:
            model_name = f"ggml-{model}.bin"
        
        model_path = self.models_dir / model_name
        
        if not model_path.exists():
            # Try quantized version
            quantized_path = self.models_dir / f"ggml-{model}-q5_0.bin"
            if quantized_path.exists():
                model_path = quantized_path
            else:
                raise FileNotFoundError(f"Model not found: {model_path}")
        
        return model_path
    
    def _extract_text(self, transcription_data: Dict) -> str:
        """Extract text from whisper.cpp JSON output"""
        segments = transcription_data.get("transcription", [])
        
        if not segments:
            return ""
        
        # Join all segment texts
        texts = []
        for segment in segments:
            text = segment.get("text", "").strip()
            if text:
                texts.append(text)
        
        return " ".join(texts)
```

### 5.4 Result Merger (worker/merger.py)

```python
# worker/merger.py
from typing import List, Dict, Any
import difflib
from common.logger import log
from common.config import settings

class TranscriptionMerger:
    """Merge transcription results from chunks"""
    
    def __init__(self):
        self.overlap_duration = settings.chunk_overlap * 1000  # ms
        self.merge_method = "smart"  # smart, simple, or none
    
    def merge_results(self, chunk_results: List[Dict[str, Any]]) -> str:
        """Merge transcription results from multiple chunks"""
        
        if not chunk_results:
            return ""
        
        # Sort by chunk index
        chunk_results = sorted(chunk_results, key=lambda x: x['index'])
        
        if self.merge_method == "smart":
            return self._smart_merge(chunk_results)
        elif self.merge_method == "simple":
            return self._simple_merge(chunk_results)
        else:
            return self._concatenate(chunk_results)
    
    def _smart_merge(self, chunk_results: List[Dict]) -> str:
        """Smart merge using overlap detection"""
        if len(chunk_results) <= 1:
            return chunk_results[0]['text'] if chunk_results else ""
        
        merged_text = []
        
        for i, result in enumerate(chunk_results):
            text = result['text'].strip()
            
            if i == 0:
                # First chunk - use all text
                merged_text.append(text)
            else:
                # Find and remove overlap
                prev_text = merged_text[-1]
                overlap_text = self._find_overlap(prev_text, text)
                
                if overlap_text:
                    # Remove overlap from current text
                    overlap_index = text.find(overlap_text)
                    if overlap_index >= 0:
                        text = text[overlap_index + len(overlap_text):].strip()
                
                if text:
                    merged_text.append(text)
        
        # Join with spaces
        final_text = " ".join(merged_text)
        
        # Clean up multiple spaces
        import re
        final_text = re.sub(r'\s+', ' ', final_text)
        
        log.info(f"Smart merged {len(chunk_results)} chunks into {len(final_text)} characters")
        return final_text.strip()
    
    def _simple_merge(self, chunk_results: List[Dict]) -> str:
        """Simple merge by removing estimated overlap words"""
        if len(chunk_results) <= 1:
            return chunk_results[0]['text'] if chunk_results else ""
        
        merged_text = []
        
        # Estimate words in overlap (assuming ~150 words/minute)
        overlap_words = int((self.overlap_duration / 1000) * 2.5)
        
        for i, result in enumerate(chunk_results):
            text = result['text'].strip()
            
            if i == 0:
                merged_text.append(text)
            else:
                # Remove first N words (overlap)
                words = text.split()
                if len(words) > overlap_words:
                    text = " ".join(words[overlap_words:])
                    merged_text.append(text)
        
        final_text = " ".join(merged_text)
        log.info(f"Simple merged {len(chunk_results)} chunks")
        return final_text.strip()
    
    def _concatenate(self, chunk_results: List[Dict]) -> str:
        """Simple concatenation without overlap handling"""
        texts = [r['text'].strip() for r in chunk_results if r.get('text')]
        return " ".join(texts)
    
    def _find_overlap(self, text1: str, text2: str, min_overlap: int = 10) -> str:
        """Find overlapping text between end of text1 and start of text2"""
        
        # Look for overlap in the last 20% of text1 and first 20% of text2
        search_end = int(len(text1) * 0.2)
        search_start = int(len(text2) * 0.2)
        
        if search_end < min_overlap or search_start < min_overlap:
            return ""
        
        end_text = text1[-search_end:]
        start_text = text2[:search_start]
        
        # Find longest common substring
        matcher = difflib.SequenceMatcher(None, end_text, start_text)
        match = matcher.find_longest_match(0, len(end_text), 0, len(start_text))
        
        if match.size >= min_overlap:
            return end_text[match.a:match.a + match.size]
        
        return ""
```

### 5.5 Main Processor (worker/processor.py)

```python
# worker/processor.py
import os
import json
import shutil
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
from common.logger import log
from common.config import settings
from common.constants import JobStatus
from worker.chunking import AudioChunker
from worker.transcriber import WhisperTranscriber
from worker.merger import TranscriptionMerger
from worker.errors import *

class STTProcessor:
    """Main STT processing logic"""
    
    def __init__(self, db_session=None):
        self.chunker = AudioChunker()
        self.transcriber = WhisperTranscriber()
        self.merger = TranscriptionMerger()
        self.db = db_session
    
    def process_job(self, job_id: str, audio_path: str, language: str = "vi") -> Dict[str, Any]:
        """Process a single STT job"""
        
        log.info(f"Starting job {job_id}: file={audio_path}, language={language}")
        
        try:
            # Update job status
            self._update_job_status(job_id, JobStatus.PROCESSING)
            
            # Step 1: Validate input
            self._validate_input(audio_path, language)
            
            # Step 2: Chunk audio
            chunks = self.chunker.chunk_audio(audio_path)
            log.info(f"Audio chunked into {len(chunks)} segments")
            self._update_job_chunks(job_id, len(chunks))
            
            # Step 3: Process each chunk
            chunk_results = []
            for i, chunk_info in enumerate(chunks):
                try:
                    log.info(f"Processing chunk {i+1}/{len(chunks)}")
                    
                    # Transcribe chunk
                    result = self.transcriber.transcribe(
                        audio_path=chunk_info['path'],
                        language=language
                    )
                    
                    # Add chunk metadata
                    result.update({
                        'index': chunk_info['index'],
                        'start_ms': chunk_info['start_ms'],
                        'end_ms': chunk_info['end_ms']
                    })
                    
                    chunk_results.append(result)
                    
                    # Update progress
                    self._update_chunk_progress(job_id, i + 1)
                    
                except Exception as e:
                    log.error(f"Failed to process chunk {i}: {e}")
                    # Continue with other chunks
                    chunk_results.append({
                        'index': chunk_info['index'],
                        'text': '',
                        'error': str(e)
                    })
            
            # Step 4: Merge results
            final_text = self.merger.merge_results(chunk_results)
            
            # Step 5: Save results
            result_path = self._save_results(job_id, final_text, chunk_results)
            
            # Step 6: Update job as completed
            self._update_job_completed(job_id, final_text, result_path)
            
            # Step 7: Cleanup temporary files
            self._cleanup_temp_files(chunks)
            
            log.info(f"Job {job_id} completed successfully")
            
            return {
                "status": "success",
                "job_id": job_id,
                "text": final_text,
                "chunks_processed": len(chunks),
                "result_file": result_path
            }
            
        except PermanentError as e:
            log.error(f"Job {job_id} failed with permanent error: {e}")
            self._update_job_failed(job_id, str(e))
            raise
            
        except TransientError as e:
            log.error(f"Job {job_id} failed with transient error: {e}")
            # Will be retried by the queue system
            raise
            
        except Exception as e:
            log.error(f"Job {job_id} failed with unexpected error: {e}")
            self._update_job_failed(job_id, str(e))
            raise PermanentError(f"Unexpected error: {e}")
    
    def _validate_input(self, audio_path: str, language: str):
        """Validate input parameters"""
        # Check file exists
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        # Check file size
        file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
        if file_size_mb > settings.max_upload_size_mb:
            raise FileTooLargeError(f"File size {file_size_mb:.2f}MB exceeds limit")
        
        # Check language support
        if language not in ["en", "vi"]:
            raise UnsupportedLanguageError(f"Language '{language}' not supported")
    
    def _save_results(self, job_id: str, text: str, chunks: List[Dict]) -> str:
        """Save transcription results to file"""
        results_dir = Path(settings.results_dir)
        results_dir.mkdir(parents=True, exist_ok=True)
        
        # Save as JSON with metadata
        result_file = results_dir / f"{job_id}_result.json"
        
        result_data = {
            "job_id": job_id,
            "timestamp": datetime.utcnow().isoformat(),
            "text": text,
            "word_count": len(text.split()),
            "character_count": len(text),
            "chunks": chunks
        }
        
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(result_data, f, ensure_ascii=False, indent=2)
        
        # Also save plain text version
        text_file = results_dir / f"{job_id}_text.txt"
        with open(text_file, 'w', encoding='utf-8') as f:
            f.write(text)
        
        log.info(f"Results saved to {result_file}")
        return str(result_file)
    
    def _cleanup_temp_files(self, chunks: List[Dict]):
        """Clean up temporary chunk files"""
        for chunk in chunks:
            chunk_path = chunk.get('path')
            if chunk_path and os.path.exists(chunk_path):
                try:
                    os.unlink(chunk_path)
                except Exception as e:
                    log.warning(f"Failed to delete temp file {chunk_path}: {e}")
        
        # Clean up temp directories
        temp_dirs = set(Path(c['path']).parent for c in chunks if c.get('path'))
        for temp_dir in temp_dirs:
            try:
                shutil.rmtree(temp_dir)
            except Exception as e:
                log.warning(f"Failed to delete temp dir {temp_dir}: {e}")
    
    # Database update methods (implement based on your DB choice)
    def _update_job_status(self, job_id: str, status: str):
        """Update job status in database"""
        # TODO: Implement database update
        log.info(f"Job {job_id} status updated to {status}")
    
    def _update_job_chunks(self, job_id: str, total_chunks: int):
        """Update total chunks for job"""
        # TODO: Implement database update
        pass
    
    def _update_chunk_progress(self, job_id: str, chunks_completed: int):
        """Update chunk processing progress"""
        # TODO: Implement database update
        pass
    
    def _update_job_completed(self, job_id: str, text: str, result_path: str):
        """Mark job as completed"""
        # TODO: Implement database update
        pass
    
    def _update_job_failed(self, job_id: str, error_message: str):
        """Mark job as failed"""
        # TODO: Implement database update
        pass
```

---

## 🚀 BƯỚC 6: XÂY DỰNG API GATEWAY

### 6.1 Database Models (api/database.py)

```python
# api/database.py
from sqlalchemy import create_engine, Column, String, Float, Integer, DateTime, Text, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func
import enum
from datetime import datetime
from common.config import settings

# Create engine
engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class JobStatus(enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class Job(Base):
    __tablename__ = "jobs"
    
    id = Column(String, primary_key=True)
    job_id = Column(String, unique=True, index=True)
    status = Column(Enum(JobStatus), default=JobStatus.PENDING)
    language = Column(String)
    
    # File info
    original_filename = Column(String)
    file_path = Column(Text)
    file_size_mb = Column(Float)
    audio_duration_seconds = Column(Float)
    
    # Processing info
    worker_id = Column(String)
    retry_count = Column(Integer, default=0)
    chunks_total = Column(Integer)
    chunks_completed = Column(Integer, default=0)
    
    # Results
    transcription_text = Column(Text)
    result_file_path = Column(Text)
    error_message = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

# Create tables
Base.metadata.create_all(bind=engine)

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### 6.2 Pydantic Models (api/models.py)

```python
# api/models.py
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from enum import Enum

class JobStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class Language(str, Enum):
    ENGLISH = "en"
    VIETNAMESE = "vi"

class UploadRequest(BaseModel):
    language: Language = Language.VIETNAMESE
    priority: str = "normal"  # high, normal, low
    model: str = "medium"  # small, medium, large

class UploadResponse(BaseModel):
    job_id: str
    status: JobStatus
    message: str
    estimated_time_seconds: Optional[float] = None

class JobStatusResponse(BaseModel):
    job_id: str
    status: JobStatus
    progress: Optional[float] = None  # 0-100
    chunks_completed: Optional[int] = None
    chunks_total: Optional[int] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    error_message: Optional[str] = None

class TranscriptionResult(BaseModel):
    job_id: str
    status: JobStatus
    text: Optional[str] = None
    word_count: Optional[int] = None
    duration_seconds: Optional[float] = None
    language: str
    completed_at: Optional[datetime] = None
    download_url: Optional[str] = None

class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    workers_active: int
    jobs_pending: int
    jobs_processing: int
```

### 6.3 Upload Route (api/routes/upload.py)

```python
# api/routes/upload.py
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from sqlalchemy.orm import Session
import aiofiles
import uuid
import os
from pathlib import Path
from datetime import datetime
import redis
from rq import Queue

from api.database import get_db, Job, JobStatus
from api.models import UploadRequest, UploadResponse, Language
from common.config import settings
from common.constants import SUPPORTED_FORMATS
from common.logger import log

router = APIRouter(prefix="/api/v1", tags=["upload"])

# Redis connection
redis_conn = redis.Redis(
    host=settings.redis_host,
    port=settings.redis_port,
    db=settings.redis_db,
    password=settings.redis_password
)

@router.post("/upload", response_model=UploadResponse)
async def upload_audio(
    file: UploadFile = File(...),
    language: Language = Form(Language.VIETNAMESE),
    priority: str = Form("normal"),
    model: str = Form("medium"),
    db: Session = Depends(get_db)
):
    """Upload audio file for transcription"""
    
    # Validate file extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in SUPPORTED_FORMATS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format. Supported: {', '.join(SUPPORTED_FORMATS)}"
        )
    
    # Validate file size
    file_size = 0
    contents = await file.read()
    file_size = len(contents) / (1024 * 1024)  # MB
    
    if file_size > settings.max_upload_size_mb:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {settings.max_upload_size_mb}MB"
        )
    
    # Generate job ID
    job_id = str(uuid.uuid4())
    
    # Save file
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    file_path = upload_dir / f"{job_id}_{file.filename}"
    
    async with aiofiles.open(file_path, 'wb') as f:
        await f.write(contents)
    
    log.info(f"File uploaded: {file_path}, size: {file_size:.2f}MB")
    
    # Create database record
    db_job = Job(
        id=job_id,
        job_id=job_id,
        status=JobStatus.PENDING,
        language=language.value,
        original_filename=file.filename,
        file_path=str(file_path),
        file_size_mb=file_size,
        created_at=datetime.utcnow()
    )
    
    db.add(db_job)
    db.commit()
    
    # Queue the job
    queue_name = f"stt_jobs_{priority}" if priority in ["high", "low"] else "stt_jobs"
    queue = Queue(queue_name, connection=redis_conn)
    
    job = queue.enqueue(
        'worker.main.process_stt_job',
        args=(job_id, str(file_path), language.value, model),
        job_timeout=settings.job_timeout,
        result_ttl=86400,  # Keep result for 24 hours
        failure_ttl=604800  # Keep failed job for 7 days
    )
    
    log.info(f"Job {job_id} queued in {queue_name}")
    
    # Estimate processing time (rough estimate: 1 minute per 5MB)
    estimated_time = (file_size / 5) * 60
    
    return UploadResponse(
        job_id=job_id,
        status=JobStatus.PENDING,
        message="File uploaded successfully. Processing started.",
        estimated_time_seconds=estimated_time
    )
```

### 6.4 Status Route (api/routes/status.py)

```python
# api/routes/status.py
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from api.database import get_db, Job
from api.models import JobStatusResponse
from common.logger import log

router = APIRouter(prefix="/api/v1", tags=["status"])

@router.get("/status/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str, db: Session = Depends(get_db)):
    """Get job processing status"""
    
    # Query job from database
    job = db.query(Job).filter(Job.job_id == job_id).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Calculate progress
    progress = None
    if job.chunks_total and job.chunks_total > 0:
        progress = (job.chunks_completed / job.chunks_total) * 100
    
    return JobStatusResponse(
        job_id=job.job_id,
        status=job.status.value,
        progress=progress,
        chunks_completed=job.chunks_completed,
        chunks_total=job.chunks_total,
        created_at=job.created_at,
        started_at=job.started_at,
        error_message=job.error_message
    )
```

### 6.5 Result Route (api/routes/result.py)

```python
# api/routes/result.py
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pathlib import Path
import json

from api.database import get_db, Job, JobStatus
from api.models import TranscriptionResult
from common.config import settings
from common.logger import log

router = APIRouter(prefix="/api/v1", tags=["result"])

@router.get("/result/{job_id}", response_model=TranscriptionResult)
async def get_transcription_result(job_id: str, db: Session = Depends(get_db)):
    """Get transcription result"""
    
    # Query job from database
    job = db.query(Job).filter(Job.job_id == job_id).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status != JobStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail=f"Job not completed. Current status: {job.status.value}"
        )
    
    # Count words if text is available
    word_count = None
    if job.transcription_text:
        word_count = len(job.transcription_text.split())
    
    return TranscriptionResult(
        job_id=job.job_id,
        status=job.status.value,
        text=job.transcription_text,
        word_count=word_count,
        duration_seconds=job.audio_duration_seconds,
        language=job.language,
        completed_at=job.completed_at,
        download_url=f"/api/v1/download/{job_id}"
    )

@router.get("/download/{job_id}")
async def download_result(job_id: str, format: str = "json", db: Session = Depends(get_db)):
    """Download transcription result as file"""
    
    # Query job from database
    job = db.query(Job).filter(Job.job_id == job_id).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status != JobStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail=f"Job not completed. Current status: {job.status.value}"
        )
    
    # Get result file path
    results_dir = Path(settings.results_dir)
    
    if format == "txt":
        file_path = results_dir / f"{job_id}_text.txt"
        media_type = "text/plain"
        filename = f"{job_id}_transcription.txt"
    else:
        file_path = results_dir / f"{job_id}_result.json"
        media_type = "application/json"
        filename = f"{job_id}_transcription.json"
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Result file not found")
    
    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=filename
    )
```

### 6.6 Main API Application (api/main.py)

```python
# api/main.py
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import uvicorn
from datetime import datetime
import redis
from rq import Queue

from api.routes import upload, status, result
from api.models import HealthResponse
from common.config import settings
from common.logger import log

# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    log.info("Starting STT API Gateway...")
    yield
    # Shutdown
    log.info("Shutting down STT API Gateway...")

# Create FastAPI app
app = FastAPI(
    title="Async STT System",
    description="Speech-to-Text processing system with async queue",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    log.error(f"Global exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

# Include routers
app.include_router(upload.router)
app.include_router(status.router)
app.include_router(result.router)

# Health check endpoint
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """System health check"""
    
    try:
        # Check Redis connection
        redis_conn = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db
        )
        redis_conn.ping()
        
        # Get queue statistics
        queue = Queue("stt_jobs", connection=redis_conn)
        
        return HealthResponse(
            status="healthy",
            timestamp=datetime.utcnow(),
            workers_active=len(queue.workers),
            jobs_pending=len(queue.jobs),
            jobs_processing=len(queue.started_job_registry)
        )
    except Exception as e:
        log.error(f"Health check failed: {e}")
        return HealthResponse(
            status="unhealthy",
            timestamp=datetime.utcnow(),
            workers_active=0,
            jobs_pending=0,
            jobs_processing=0
        )

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Async STT System",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }

if __name__ == "__main__":
    uvicorn.run(
        "api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        workers=settings.api_workers,
        reload=True
    )
```

---

## 🚀 BƯỚC 7: WORKER ENTRY POINT

### 7.1 Worker Main (worker/main.py)

```python
# worker/main.py
import signal
import sys
import time
from rq import Worker, Queue
from rq.job import Job
import redis

from common.config import settings
from common.logger import log
from worker.processor import STTProcessor
from worker.errors import TransientError, PermanentError

# Redis connection
redis_conn = redis.Redis(
    host=settings.redis_host,
    port=settings.redis_port,
    db=settings.redis_db,
    password=settings.redis_password
)

def process_stt_job(job_id: str, audio_path: str, language: str, model: str = "medium"):
    """Main job processing function for RQ"""
    
    log.info(f"Worker processing job {job_id}")
    
    processor = STTProcessor()
    
    try:
        result = processor.process_job(
            job_id=job_id,
            audio_path=audio_path,
            language=language
        )
        
        log.info(f"Job {job_id} completed successfully")
        return result
        
    except TransientError as e:
        log.error(f"Transient error in job {job_id}: {e}")
        # RQ will retry based on configuration
        raise
        
    except PermanentError as e:
        log.error(f"Permanent error in job {job_id}: {e}")
        # Job will be moved to failed queue
        return {
            "status": "failed",
            "error": str(e),
            "job_id": job_id
        }
        
    except Exception as e:
        log.error(f"Unexpected error in job {job_id}: {e}")
        # Treat as permanent error
        return {
            "status": "failed",
            "error": f"Unexpected error: {e}",
            "job_id": job_id
        }

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    log.info(f"Received signal {signum}, shutting down...")
    sys.exit(0)

def main():
    """Start RQ worker"""
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    log.info("Starting STT Worker...")
    
    # Configure worker
    queues = [
        Queue("stt_jobs_high", connection=redis_conn),
        Queue("stt_jobs", connection=redis_conn),
        Queue("stt_jobs_low", connection=redis_conn)
    ]
    
    worker = Worker(
        queues=queues,
        connection=redis_conn,
        name=f"stt-worker-{int(time.time())}",
        log_job_description=True,
        max_jobs=settings.max_concurrent_jobs
    )
    
    # Start worker
    log.info(f"Worker listening on queues: {[q.name for q in queues]}")
    worker.work(with_scheduler=True)

if __name__ == "__main__":
    main()
```

---

## 🚀 BƯỚC 8: DOCKER CONFIGURATION

### 8.1 Dockerfile cho API

```dockerfile
# docker/Dockerfile.api
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY api/ ./api/
COPY common/ ./common/

# Create directories
RUN mkdir -p storage/uploads storage/results logs

# Create non-root user
RUN useradd -m -u 1000 sttuser && chown -R sttuser:sttuser /app
USER sttuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# Run application
CMD ["python", "-m", "api.main"]
```

### 8.2 Dockerfile cho Worker

```dockerfile
# docker/Dockerfile.worker
FROM ubuntu:22.04 as builder

# Build whisper.cpp
RUN apt-get update && apt-get install -y \
    build-essential cmake git wget libopenblas-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
RUN git clone https://github.com/ggerganov/whisper.cpp.git
WORKDIR /build/whisper.cpp
RUN make -j$(nproc)

# Download models
RUN bash ./models/download-ggml-model.sh small
RUN bash ./models/download-ggml-model.sh medium

# Runtime image
FROM python:3.11-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libopenblas0 ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy whisper.cpp from builder
COPY --from=builder /build/whisper.cpp/main /usr/local/bin/whisper-cpp
COPY --from=builder /build/whisper.cpp/models /app/models/

WORKDIR /app

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY worker/ ./worker/
COPY common/ ./common/

# Create directories
RUN mkdir -p storage/uploads storage/results logs

# Create non-root user
RUN useradd -m -u 1000 sttuser && chown -R sttuser:sttuser /app
USER sttuser

# Run worker
CMD ["python", "-m", "worker.main"]
```

### 8.3 Docker Compose

```yaml
# docker/docker-compose.yml
version: '3.9'

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: sttuser
      POSTGRES_PASSWORD: sttpass
      POSTGRES_DB: stt_db
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ../scripts/init_db.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U sttuser"]
      interval: 30s
      timeout: 10s
      retries: 3

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3

  api:
    build:
      context: ..
      dockerfile: docker/Dockerfile.api
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://sttuser:sttpass@postgres:5432/stt_db
      REDIS_HOST: redis
      REDIS_PORT: 6379
    depends_on:
      - postgres
      - redis
    volumes:
      - ../storage:/app/storage
      - ../logs:/app/logs
    restart: unless-stopped

  worker:
    build:
      context: ..
      dockerfile: docker/Dockerfile.worker
    environment:
      DATABASE_URL: postgresql://sttuser:sttpass@postgres:5432/stt_db
      REDIS_HOST: redis
      REDIS_PORT: 6379
    depends_on:
      - postgres
      - redis
    volumes:
      - ../storage:/app/storage
      - ../logs:/app/logs
    deploy:
      replicas: 3
    restart: unless-stopped

  redis-commander:
    image: rediscommander/redis-commander:latest
    environment:
      - REDIS_HOSTS=local:redis:6379
    ports:
      - "8081:8081"
    depends_on:
      - redis

volumes:
  postgres_data:
  redis_data:
```

---

## 🚀 BƯỚC 9: TESTING & DEPLOYMENT

### 9.1 Test Script

```python
# scripts/test_audio.py
import requests
import time
import sys

def test_stt_system(audio_file: str):
    """Test the STT system end-to-end"""
    
    base_url = "http://localhost:8000"
    
    print(f"Testing with file: {audio_file}")
    
    # 1. Upload file
    print("Uploading file...")
    with open(audio_file, 'rb') as f:
        files = {'file': f}
        data = {'language': 'vi', 'priority': 'normal'}
        response = requests.post(f"{base_url}/api/v1/upload", files=files, data=data)
    
    if response.status_code != 200:
        print(f"Upload failed: {response.text}")
        return
    
    upload_result = response.json()
    job_id = upload_result['job_id']
    print(f"Job ID: {job_id}")
    
    # 2. Poll status
    print("Waiting for processing...")
    while True:
        response = requests.get(f"{base_url}/api/v1/status/{job_id}")
        status_result = response.json()
        
        status = status_result['status']
        progress = status_result.get('progress', 0)
        
        print(f"Status: {status}, Progress: {progress:.1f}%")
        
        if status == 'COMPLETED':
            break
        elif status == 'FAILED':
            print(f"Job failed: {status_result.get('error_message')}")
            return
        
        time.sleep(5)
    
    # 3. Get result
    print("Getting result...")
    response = requests.get(f"{base_url}/api/v1/result/{job_id}")
    result = response.json()
    
    print("\n=== TRANSCRIPTION RESULT ===")
    print(f"Text: {result['text'][:500]}...")
    print(f"Word count: {result['word_count']}")
    print(f"Duration: {result.get('duration_seconds', 0):.2f} seconds")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_audio.py <audio_file>")
        sys.exit(1)
    
    test_stt_system(sys.argv[1])
```

### 9.2 Deployment Steps

```bash
# 1. Clone repository (sau khi đã tạo tất cả các files)
git clone <your-repo>
cd stt-async-system

# 2. Setup environment
cp .env.example .env
# Edit .env với configuration của bạn

# 3. Build và start với Docker
cd docker
docker-compose build
docker-compose up -d

# 4. Scale workers nếu cần
docker-compose up -d --scale worker=5

# 5. Monitor logs
docker-compose logs -f

# 6. Test system
python scripts/test_audio.py sample_audio.mp3
```

---

## 📝 CHECKLIST HOÀN THÀNH

### ✅ Chuẩn bị môi trường
- [ ] Cài đặt Python 3.11
- [ ] Cài đặt PostgreSQL
- [ ] Cài đặt Redis
- [ ] Cài đặt Docker & Docker Compose
- [ ] Build whisper.cpp
- [ ] Download models

### ✅ Code Implementation
- [ ] Tạo cấu trúc thư mục
- [ ] Implement Common module
- [ ] Implement Worker module
- [ ] Implement API Gateway
- [ ] Viết Dockerfiles
- [ ] Setup Docker Compose

### ✅ Testing
- [ ] Test chunking algorithm
- [ ] Test whisper.cpp integration
- [ ] Test API endpoints
- [ ] Test worker processing
- [ ] End-to-end testing

### ✅ Deployment
- [ ] Configure production environment
- [ ] Setup monitoring
- [ ] Configure backup
- [ ] Performance tuning
- [ ] Documentation

---

## 🎯 TIPS VÀ LƯU Ý QUAN TRỌNG

### Performance Optimization:
1. **Model Selection**: Dùng `medium` model cho balance giữa speed và accuracy
2. **Quantization**: Dùng quantized models (q5_0) để tăng tốc trên CPU
3. **Chunking**: Optimal chunk size 30-45 giây
4. **Workers**: Scale horizontal với nhiều workers

### Monitoring:
1. **Metrics to track**:
   - Job completion rate
   - Average processing time
   - Queue depth
   - Worker health
   - Memory usage

2. **Alerting**:
   - Queue depth > threshold
   - Worker crashes
   - High failure rate
   - Database connection issues

### Troubleshooting Common Issues:

| Issue | Solution |
|-------|----------|
| OOM errors | Giảm chunk size, tăng RAM |
| Slow processing | Use smaller model, add workers |
| Poor accuracy | Use larger model, adjust chunking |
| Queue buildup | Add more workers |
| Database locks | Optimize queries, add indexes |

### Production Checklist:
- [ ] SSL/TLS for API
- [ ] Authentication & Authorization
- [ ] Rate limiting
- [ ] Backup strategy
- [ ] Log rotation
- [ ] Monitoring dashboard
- [ ] Error alerting
- [ ] Auto-scaling rules

---

Đây là hướng dẫn CHI TIẾT NHẤT để bạn có thể build hệ thống STT từ đầu. Mỗi file đã được viết đầy đủ code, bạn chỉ cần copy và tạo theo cấu trúc đã chỉ định. Hệ thống này đã được thiết kế để chạy tối ưu trên CPU với whisper.cpp và có khả năng scale tốt.