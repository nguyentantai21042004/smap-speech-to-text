# Tasks 4-10: Complete Implementation Code

All code includes:
- **Detailed logging** at every step
- **Try-catch error handling** everywhere
- **MongoDB integration**

---

## TASK 4: Audio Chunking Module ⏱️ 45 min

**File:** `worker/chunking.py`

```python
"""
Audio chunking module with silence detection.
Includes comprehensive logging and error handling.
"""
import os
import tempfile
from typing import List, Tuple, Dict
from pathlib import Path

from pydub import AudioSegment
from pydub.silence import detect_nonsilent

from core.config import get_settings
from core.logger import get_logger
from worker.errors import InvalidAudioFormatError, FileTooLargeError

settings = get_settings()
logger = get_logger(__name__)


class AudioChunker:
    """
    Handles audio chunking with multiple strategies.
    Includes detailed logging for debugging.
    """

    def __init__(self):
        logger.info("🎵 Initializing AudioChunker")

        self.chunk_duration = settings.chunk_duration * 1000  # Convert to ms
        self.chunk_overlap = settings.chunk_overlap * 1000
        self.silence_threshold = settings.silence_threshold
        self.min_silence_duration = settings.min_silence_duration * 1000

        logger.debug(f"Chunk settings: duration={self.chunk_duration}ms, overlap={self.chunk_overlap}ms")
        logger.debug(f"Silence detection: threshold={self.silence_threshold}dB, min_duration={self.min_silence_duration}ms")

    def load_audio(self, file_path: str) -> AudioSegment:
        """
        Load and normalize audio file.

        Args:
            file_path: Path to audio file

        Returns:
            AudioSegment object
        """
        try:
            logger.info(f"📂 Loading audio file: {file_path}")

            # Check file exists
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Audio file not found: {file_path}")

            # Check file size
            file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
            logger.debug(f"File size: {file_size_mb:.2f} MB")

            if file_size_mb > settings.max_upload_size_mb:
                raise FileTooLargeError(
                    f"File size {file_size_mb:.2f}MB exceeds limit {settings.max_upload_size_mb}MB"
                )

            # Load audio
            logger.debug("Loading audio with pydub...")
            audio = AudioSegment.from_file(file_path)

            # Get audio properties
            duration_seconds = len(audio) / 1000
            logger.info(f"Audio loaded: duration={duration_seconds:.2f}s, channels={audio.channels}, rate={audio.frame_rate}Hz")

            # Convert to mono, 16kHz for Whisper
            logger.debug("Normalizing audio to mono, 16kHz...")
            audio = audio.set_channels(1)
            audio = audio.set_frame_rate(16000)

            logger.info(f"Audio normalized: channels={audio.channels}, rate={audio.frame_rate}Hz")

            return audio

        except FileNotFoundError as e:
            logger.error(f"File not found: {e}")
            raise
        except FileTooLargeError as e:
            logger.error(f"File too large: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to load audio: {e}")
            logger.exception("Audio loading error details:")
            raise InvalidAudioFormatError(f"Cannot load audio file: {e}")

    def chunk_audio(self, audio_path: str, strategy: str = None) -> List[Dict]:
        """
        Main chunking method.

        Args:
            audio_path: Path to audio file
            strategy: Chunking strategy ('silence_based' or 'fixed_size')

        Returns:
            List of chunk dictionaries with paths and metadata
        """
        try:
            strategy = strategy or settings.chunk_strategy
            logger.info(f"🔪 Starting audio chunking: strategy={strategy}")

            # Load audio
            audio = self.load_audio(audio_path)

            # Choose strategy
            if strategy == "silence_based":
                logger.info("Using silence-based chunking...")
                chunks = self._chunk_by_silence(audio)
            else:
                logger.info("Using fixed-size chunking...")
                chunks = self._chunk_fixed_size(audio)

            logger.info(f"Created {len(chunks)} chunks")

            # Save chunks to temporary files
            chunk_files = self._save_chunks(chunks, audio, audio_path)

            logger.info(f"All chunks saved successfully: {len(chunk_files)} files")

            return chunk_files

        except Exception as e:
            logger.error(f"Chunking failed: {e}")
            logger.exception("Chunking error details:")
            raise

    def _chunk_by_silence(self, audio: AudioSegment) -> List[Tuple[int, int]]:
        """
        Chunk audio based on silence detection.

        Args:
            audio: AudioSegment to chunk

        Returns:
            List of (start_ms, end_ms) tuples
        """
        try:
            logger.info("Detecting non-silent segments...")

            # Detect non-silent chunks
            nonsilent_chunks = detect_nonsilent(
                audio,
                min_silence_len=int(self.min_silence_duration),
                silence_thresh=self.silence_threshold,
                seek_step=10
            )

            logger.debug(f"Detected {len(nonsilent_chunks)} non-silent segments")

            if not nonsilent_chunks:
                logger.warning("No non-silent chunks detected, falling back to fixed-size chunking")
                return self._chunk_fixed_size(audio)

            # Merge and split chunks to optimal size
            chunks = []
            current_start = 0

            for i, (start_ms, end_ms) in enumerate(nonsilent_chunks):
                chunk_duration = end_ms - current_start

                logger.debug(f"Processing segment {i}: {start_ms}ms - {end_ms}ms (duration: {chunk_duration}ms)")

                # If chunk is too long, split it
                if chunk_duration > self.chunk_duration * 1.5:
                    logger.debug(f"  Segment too long ({chunk_duration}ms), splitting...")
                    chunks.append((current_start, current_start + self.chunk_duration))
                    current_start = current_start + self.chunk_duration - self.chunk_overlap

                # Good size chunk
                elif chunk_duration > self.chunk_duration * 0.5:
                    chunks.append((current_start, end_ms))
                    current_start = end_ms - self.chunk_overlap

            # Add final chunk if needed
            if current_start < len(audio):
                chunks.append((current_start, len(audio)))
                logger.debug(f"Added final chunk: {current_start}ms - {len(audio)}ms")

            logger.info(f"Created {len(chunks)} chunks using silence detection")
            return chunks

        except Exception as e:
            logger.error(f"Silence-based chunking failed: {e}")
            logger.exception("Silence detection error details:")
            logger.warning("Falling back to fixed-size chunking...")
            return self._chunk_fixed_size(audio)

    def _chunk_fixed_size(self, audio: AudioSegment) -> List[Tuple[int, int]]:
        """
        Chunk audio into fixed-size segments.

        Args:
            audio: AudioSegment to chunk

        Returns:
            List of (start_ms, end_ms) tuples
        """
        try:
            logger.info("📏 Using fixed-size chunking strategy")

            chunks = []
            audio_length = len(audio)
            chunk_start = 0

            while chunk_start < audio_length:
                chunk_end = min(chunk_start + self.chunk_duration, audio_length)
                chunks.append((chunk_start, chunk_end))

                logger.debug(f"Chunk {len(chunks)}: {chunk_start}ms - {chunk_end}ms")

                # Move to next chunk with overlap
                chunk_start = chunk_end - self.chunk_overlap
                if chunk_end >= audio_length:
                    break

            logger.info(f"Created {len(chunks)} fixed-size chunks")
            return chunks

        except Exception as e:
            logger.error(f"Fixed-size chunking failed: {e}")
            logger.exception("Fixed-size chunking error details:")
            raise

    def _save_chunks(
        self,
        chunks: List[Tuple[int, int]],
        audio: AudioSegment,
        original_path: str
    ) -> List[Dict]:
        """
        Save chunks as temporary WAV files.

        Args:
            chunks: List of (start_ms, end_ms) tuples
            audio: Original AudioSegment
            original_path: Path to original file

        Returns:
            List of chunk file dictionaries
        """
        try:
            logger.info(f"Saving {len(chunks)} chunks to disk...")

            # Create temporary directory
            temp_dir = Path(tempfile.mkdtemp(prefix="stt_chunks_"))
            logger.debug(f"Temp directory: {temp_dir}")

            chunk_files = []

            for i, (start_ms, end_ms) in enumerate(chunks):
                try:
                    # Extract chunk
                    chunk_audio = audio[start_ms:end_ms]

                    # Save as WAV (best compatibility with Whisper)
                    chunk_path = temp_dir / f"chunk_{i:04d}.wav"

                    logger.debug(f"Saving chunk {i}: {chunk_path}")

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
                        "duration_ms": end_ms - start_ms,
                        "duration_seconds": (end_ms - start_ms) / 1000
                    })

                    logger.debug(f"Chunk {i} saved: {(end_ms - start_ms) / 1000:.2f}s")

                except Exception as e:
                    logger.error(f"Failed to save chunk {i}: {e}")
                    logger.exception(f"Chunk {i} save error:")
                    # Continue with other chunks
                    continue

            logger.info(f"Saved {len(chunk_files)} chunks successfully")
            return chunk_files

        except Exception as e:
            logger.error(f"Failed to save chunks: {e}")
            logger.exception("Chunk saving error details:")
            raise


# Factory function
def get_audio_chunker() -> AudioChunker:
    """Get AudioChunker instance."""
    return AudioChunker()
```

---

## TASK 5: Whisper Transcriber Module ⏱️ 30 min

**File:** `worker/transcriber.py`

```python
"""
Whisper.cpp transcriber module.
Includes comprehensive logging and error handling.
"""
import subprocess
import json
import os
import tempfile
from typing import Dict, Any, Optional
from pathlib import Path

from core.config import get_settings
from core.logger import get_logger
from worker.errors import WhisperCrashError, TimeoutError

settings = get_settings()
logger = get_logger(__name__)


class WhisperTranscriber:
    """
    Interface to whisper.cpp executable.
    Includes detailed logging for debugging.
    """

    def __init__(self):
        logger.info("🎤 Initializing WhisperTranscriber")

        self.executable = settings.whisper_executable
        self.models_dir = Path(settings.whisper_models_dir)
        self.default_model = settings.default_model

        # Verify whisper.cpp exists
        if not os.path.exists(self.executable):
            raise FileNotFoundError(
                f"Whisper.cpp not found at {self.executable}. "
                f"Please build whisper.cpp first."
            )

        logger.info(f"Whisper executable found: {self.executable}")
        logger.debug(f"Models directory: {self.models_dir}")
        logger.debug(f"Default model: {self.default_model}")

    def transcribe(
        self,
        audio_path: str,
        language: str = "vi",
        model: str = None,
        timeout: int = None
    ) -> Dict[str, Any]:
        """
        Transcribe audio file using whisper.cpp.

        Args:
            audio_path: Path to audio file
            language: Language code (en, vi)
            model: Model size (tiny, base, small, medium, large)
            timeout: Timeout in seconds

        Returns:
            Dictionary with transcription results
        """
        try:
            model = model or self.default_model
            timeout = timeout or settings.chunk_timeout

            logger.info(f"🎙️ Starting transcription: {audio_path}")
            logger.debug(f"Parameters: language={language}, model={model}, timeout={timeout}s")

            # Get model path
            model_file = self._get_model_path(model, language)
            logger.debug(f"Using model file: {model_file}")

            # Prepare output file
            output_file = tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.json',
                delete=False
            )
            output_path = output_file.name
            output_file.close()

            logger.debug(f"Output file: {output_path}")

            # Build command
            cmd = [
                self.executable,
                "-m", str(model_file),
                "-f", audio_path,
                "-l", language,
                "-oj",  # Output JSON
                "-of", output_path.replace('.json', ''),
                "-t", "4",  # Threads
                "-p", "1",  # Processors
                "--no-timestamps"
            ]

            logger.debug(f"Command: {' '.join(cmd)}")

            # Run whisper.cpp
            logger.info("⚙️ Running whisper.cpp...")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=True
            )

            logger.debug(f"Whisper stdout: {result.stdout[:200]}...")
            if result.stderr:
                logger.debug(f"Whisper stderr: {result.stderr[:200]}...")

            # Read JSON output
            logger.debug("Reading transcription output...")

            with open(output_path, 'r', encoding='utf-8') as f:
                transcription_data = json.load(f)

            # Extract text
            text = self._extract_text(transcription_data)

            logger.info(f"Transcription completed: {len(text)} characters")
            logger.debug(f"Text preview: {text[:100]}...")

            return {
                "text": text,
                "language": language,
                "model": model,
                "segments": transcription_data.get("transcription", [])
            }

        except subprocess.TimeoutExpired:
            logger.error(f"Whisper timeout after {timeout}s")
            raise TimeoutError(f"Transcription timeout after {timeout} seconds")

        except subprocess.CalledProcessError as e:
            logger.error(f"Whisper.cpp failed with exit code {e.returncode}")
            logger.error(f"Error output: {e.stderr}")
            raise WhisperCrashError(f"Whisper.cpp crashed: {e.stderr}")

        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            logger.exception("Transcription error details:")
            raise

        finally:
            # Cleanup temporary file
            try:
                if os.path.exists(output_path):
                    os.unlink(output_path)
                    logger.debug(f"Cleaned up temp file: {output_path}")
            except Exception as e:
                logger.warning(f"Failed to cleanup temp file: {e}")

    def _get_model_path(self, model: str, language: str) -> Path:
        """
        Get the model file path.

        Args:
            model: Model size
            language: Language code

        Returns:
            Path to model file
        """
        try:
            logger.debug(f"Looking for model: {model} (language: {language})")

            # For English-only, use .en models
            if language == "en" and model in ["tiny", "base", "small", "medium"]:
                model_name = f"ggml-{model}.en.bin"
            else:
                model_name = f"ggml-{model}.bin"

            model_path = self.models_dir / model_name

            # Check if model exists
            if not model_path.exists():
                logger.warning(f"Model not found: {model_path}")

                # Try quantized version
                quantized_path = self.models_dir / f"ggml-{model}-q5_0.bin"
                if quantized_path.exists():
                    logger.info(f"Using quantized model: {quantized_path}")
                    model_path = quantized_path
                else:
                    raise FileNotFoundError(
                        f"Model not found: {model_path} or {quantized_path}. "
                        f"Please download the model first."
                    )

            logger.debug(f"Model found: {model_path}")
            return model_path

        except Exception as e:
            logger.error(f"Failed to get model path: {e}")
            raise

    def _extract_text(self, transcription_data: Dict) -> str:
        """
        Extract text from whisper.cpp JSON output.

        Args:
            transcription_data: JSON data from whisper.cpp

        Returns:
            Extracted text
        """
        try:
            segments = transcription_data.get("transcription", [])

            if not segments:
                logger.warning("No transcription segments found")
                return ""

            # Join all segment texts
            texts = []
            for segment in segments:
                text = segment.get("text", "").strip()
                if text:
                    texts.append(text)

            result = " ".join(texts)
            logger.debug(f"Extracted {len(texts)} segments, {len(result)} characters")

            return result

        except Exception as e:
            logger.error(f"Failed to extract text: {e}")
            logger.exception("Text extraction error:")
            return ""


# Factory function
def get_whisper_transcriber() -> WhisperTranscriber:
    """Get WhisperTranscriber instance."""
    return WhisperTranscriber()
```

---

## Continue with Tasks 6-10?

I've completed detailed implementations for Tasks 1-5. Would you like me to continue with:

- **TASK 6:** Result Merger (worker/merger.py)
- **TASK 7:** STT Processor (worker/processor.py) - Main business logic
- **TASK 8:** API Routes (internal/api/routes/task_routes.py)
- **TASK 9:** Consumer Handler (internal/consumer/handlers/stt_handler.py)
- **TASK 10:** Test Scripts (scripts/test_upload.py)

Should I create these next, or would you like to test Tasks 1-5 first?
