"""
Whisper Library Adapter - Direct C library integration for Whisper.cpp
Replaces subprocess-based CLI wrapper with direct shared library calls.
Provides significant performance improvements by loading model once and reusing context.
"""

import ctypes
import os
import sys
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Optional, Any
import numpy as np  # type: ignore

from core.config import get_settings
from core.logger import logger
from core.errors import TranscriptionError


@contextmanager
def capture_native_logs(source: str, level: str = "info"):
    """
    Capture stdout/stderr emitted by native libraries (ctypes) and pipe them through Loguru.

    Args:
        source: Short name describing the native component (e.g., "whisper_init")
        level: Log level name to use when forwarding messages
    """

    log_method = getattr(logger, level, logger.info)

    if not hasattr(sys.stdout, "fileno") or not hasattr(sys.stderr, "fileno"):
        # Environment does not support low-level FD redirection (e.g., some tests)
        yield
        return

    try:
        stdout_fd = sys.stdout.fileno()
        stderr_fd = sys.stderr.fileno()

        stdout_dup = os.dup(stdout_fd)
        stderr_dup = os.dup(stderr_fd)

        stdout_pipe_r, stdout_pipe_w = os.pipe()
        stderr_pipe_r, stderr_pipe_w = os.pipe()

        stdout_lines: list[str] = []
        stderr_lines: list[str] = []
        collector_lock = threading.Lock()

        def _forward(pipe_fd: int, collector: list[str]):
            with os.fdopen(pipe_fd, "r", encoding="utf-8", errors="ignore") as pipe:
                for line in pipe:
                    text = line.strip()
                    if text:
                        with collector_lock:
                            collector.append(text)

        stdout_thread = threading.Thread(
            target=_forward, args=(stdout_pipe_r, stdout_lines), daemon=True
        )
        stderr_thread = threading.Thread(
            target=_forward, args=(stderr_pipe_r, stderr_lines), daemon=True
        )

        stdout_thread.start()
        stderr_thread.start()

        os.dup2(stdout_pipe_w, stdout_fd)
        os.dup2(stderr_pipe_w, stderr_fd)

        try:
            yield
        finally:
            os.dup2(stdout_dup, stdout_fd)
            os.dup2(stderr_dup, stderr_fd)

            os.close(stdout_pipe_w)
            os.close(stderr_pipe_w)
            os.close(stdout_dup)
            os.close(stderr_dup)

            stdout_thread.join(timeout=0.5)
            stderr_thread.join(timeout=0.5)

            if stdout_lines:
                log_method(f"[{source}:stdout]\n" + "\n".join(stdout_lines))
            if stderr_lines:
                log_method(f"[{source}:stderr]\n" + "\n".join(stderr_lines))

    except Exception as capture_error:
        logger.debug(f"Failed to capture native logs ({source}): {capture_error}")
        yield


class WhisperLibraryError(Exception):
    """Base exception for Whisper library errors"""

    pass


class LibraryLoadError(WhisperLibraryError):
    """Failed to load .so files"""

    pass


class ModelInitError(WhisperLibraryError):
    """Failed to initialize Whisper context"""

    pass


class TranscriptionError(WhisperLibraryError):
    """Failed to transcribe audio"""

    pass


# Model configuration mapping
MODEL_CONFIGS = {
    "small": {
        "dir": "whisper_small_xeon",
        "model": "ggml-small-q5_1.bin",
        "size_mb": 181,
        "ram_mb": 500,
    },
    "medium": {
        "dir": "whisper_medium_xeon",
        "model": "ggml-medium-q5_1.bin",
        "size_mb": 1500,
        "ram_mb": 2000,
    },
}


class WhisperLibraryAdapter:
    """
    Direct C library integration for Whisper.cpp.
    Loads shared libraries and Whisper model once, reuses context for all requests.
    """

    def __init__(self, model_size: Optional[str] = None):
        """
        Initialize Whisper library adapter.

        Args:
            model_size: Model size (small/medium), defaults to settings

        Raises:
            LibraryLoadError: If libraries cannot be loaded
            ModelInitError: If Whisper context cannot be initialized
        """
        settings = get_settings()
        self.model_size = model_size or settings.whisper_model_size
        self.artifacts_dir = Path(settings.whisper_artifacts_dir)

        logger.info(f"Initializing WhisperLibraryAdapter with model={self.model_size}")

        # Validate model size
        if self.model_size not in MODEL_CONFIGS:
            raise ValueError(
                f"Unsupported model size: {self.model_size}. Must be one of {list(MODEL_CONFIGS.keys())}"
            )

        self.config = MODEL_CONFIGS[self.model_size]
        self.lib_dir = self.artifacts_dir / self.config["dir"]
        self.model_path = self.lib_dir / self.config["model"]

        # Load libraries and initialize context
        self.lib = None
        self.ctx = None

        try:
            self._load_libraries()
            self._initialize_context()
            logger.info(
                f"WhisperLibraryAdapter initialized successfully (model={self.model_size})"
            )
        except Exception as e:
            logger.error(f"Failed to initialize WhisperLibraryAdapter: {e}")
            raise

    def _load_libraries(self) -> None:
        """
        Load Whisper shared libraries in correct dependency order.

        Raises:
            LibraryLoadError: If any library fails to load
        """
        try:
            logger.debug(f"Loading libraries from: {self.lib_dir}")

            # Validate library directory exists
            if not self.lib_dir.exists():
                raise LibraryLoadError(
                    f"Library directory not found: {self.lib_dir}. "
                    f"Run artifact download script first."
                )

            # Set LD_LIBRARY_PATH for this process
            old_ld_path = os.environ.get("LD_LIBRARY_PATH", "")
            new_ld_path = (
                f"{self.lib_dir}:{old_ld_path}" if old_ld_path else str(self.lib_dir)
            )
            os.environ["LD_LIBRARY_PATH"] = new_ld_path
            logger.debug(f"Set LD_LIBRARY_PATH={new_ld_path}")

            # Load dependencies in correct order (CRITICAL!)
            # 1. Base libraries first
            logger.debug("Loading libggml-base.so.0...")
            libggml_base = ctypes.CDLL(
                str(self.lib_dir / "libggml-base.so.0"), mode=ctypes.RTLD_GLOBAL
            )

            logger.debug("Loading libggml-cpu.so.0...")
            libggml_cpu = ctypes.CDLL(
                str(self.lib_dir / "libggml-cpu.so.0"), mode=ctypes.RTLD_GLOBAL
            )

            # 2. GGML core
            logger.debug("Loading libggml.so.0...")
            libggml = ctypes.CDLL(
                str(self.lib_dir / "libggml.so.0"), mode=ctypes.RTLD_GLOBAL
            )

            # 3. Whisper (depends on GGML)
            logger.debug("Loading libwhisper.so...")
            with capture_native_logs("whisper_load", level="debug"):
                self.lib = ctypes.CDLL(str(self.lib_dir / "libwhisper.so"))

            logger.info("All Whisper libraries loaded successfully")

        except OSError as e:
            raise LibraryLoadError(f"Failed to load Whisper libraries: {e}")
        except Exception as e:
            raise LibraryLoadError(f"Unexpected error loading libraries: {e}")

    def _initialize_context(self) -> None:
        """
        Initialize Whisper context from model file.

        Raises:
            ModelInitError: If context initialization fails
        """
        try:
            logger.debug(f"Initializing Whisper context from: {self.model_path}")

            # Validate model file exists
            if not self.model_path.exists():
                raise ModelInitError(
                    f"Model file not found: {self.model_path}. "
                    f"Run artifact download script first."
                )

            # Define function signature
            # whisper_context* whisper_init_from_file(const char* path)
            self.lib.whisper_init_from_file.argtypes = [ctypes.c_char_p]
            self.lib.whisper_init_from_file.restype = ctypes.c_void_p

            # Initialize context
            model_path_bytes = str(self.model_path).encode("utf-8")
            with capture_native_logs("whisper_init"):
                self.ctx = self.lib.whisper_init_from_file(model_path_bytes)

            if not self.ctx:
                raise ModelInitError(
                    f"whisper_init_from_file() returned NULL. "
                    f"Model file may be corrupted: {self.model_path}"
                )

            logger.info(
                f"Whisper context initialized (model={self.model_size}, ram~{self.config['ram_mb']}MB)"
            )

        except ModelInitError:
            raise
        except Exception as e:
            raise ModelInitError(f"Failed to initialize Whisper context: {e}")

    def transcribe(self, audio_path: str, language: str = "vi", **kwargs) -> str:
        """
        Transcribe audio file using Whisper library.

        Args:
            audio_path: Path to audio file (must be 16kHz WAV)
            language: Language code (vi, en, etc.)
            **kwargs: Additional parameters (for compatibility)

        Returns:
            Transcribed text

        Raises:
            TranscriptionError: If transcription fails
        """
        try:
            logger.debug(f"Transcribing: {audio_path} (language={language})")

            # Validate audio file exists
            if not os.path.exists(audio_path):
                raise TranscriptionError(f"Audio file not found: {audio_path}")

            # Load audio data with librosa (resampled to 16kHz mono)
            audio_data, audio_duration = self._load_audio(audio_path)

            # Call whisper_full() for transcription
            result = self._call_whisper_full(audio_data, language, audio_duration)

            logger.debug(f"Transcription successful: {len(result['text'])} chars")
            return result["text"]

        except TranscriptionError:
            raise
        except Exception as e:
            raise TranscriptionError(f"Transcription failed: {e}")

    def _load_audio(self, audio_path: str) -> tuple[np.ndarray, float]:
        """
        Load audio file and convert to format expected by Whisper.
        Whisper expects: 16kHz, mono, float32, range [-1, 1]

        Args:
            audio_path: Path to audio file

        Returns:
            Tuple of (audio_samples, duration_seconds)

        Raises:
            TranscriptionError: If audio loading fails
        """
        try:
            import librosa
            import soundfile as sf
            
            logger.debug(f"Loading audio file: {audio_path}")
            
            # Load audio with librosa (handles multiple formats via ffmpeg)
            # librosa automatically resamples to target sr and converts to mono
            audio_data, sample_rate = librosa.load(
                audio_path,
                sr=16000,  # Resample to 16kHz
                mono=True,  # Convert to mono
                dtype=np.float32,  # float32 format
            )
            
            # Calculate duration
            duration = len(audio_data) / sample_rate
            
            # Validate audio data
            if len(audio_data) == 0:
                raise TranscriptionError("Audio file is empty or has zero duration")
            
            # Ensure data is in range [-1, 1] (librosa should do this, but verify)
            max_val = np.abs(audio_data).max()
            if max_val > 1.0:
                logger.warning(f"Audio data exceeds [-1, 1] range, normalizing (max={max_val:.2f})")
                audio_data = audio_data / max_val
            
            logger.info(
                f"Audio loaded: duration={duration:.2f}s, samples={len(audio_data)}, "
                f"sample_rate={sample_rate}Hz, channels=mono"
            )
            
            return audio_data, duration

        except Exception as e:
            logger.error(f"Failed to load audio: {e}")
            raise TranscriptionError(f"Failed to load audio: {e}")

    def _call_whisper_full(
        self, audio_data: np.ndarray, language: str, audio_duration: float
    ) -> dict[str, Any]:
        """
        Call whisper_full() C function to perform transcription.

        Args:
            audio_data: Audio samples (float32, 16kHz, mono)
            language: Language code
            audio_duration: Duration of audio in seconds

        Returns:
            Dictionary with transcription results

        Raises:
            TranscriptionError: If whisper_full() fails
        """
        try:
            logger.debug(f"Starting Whisper inference (language={language})")
            
            # Define Whisper API functions - use opaque struct approach
            # Don't define full struct, let whisper_full_default_params() handle it
            self.lib.whisper_full_default_params.argtypes = [ctypes.c_int]
            self.lib.whisper_full_default_params.restype = ctypes.c_void_p  # Treat as opaque pointer
            
            self.lib.whisper_full.argtypes = [
                ctypes.c_void_p,  # ctx
                ctypes.c_void_p,  # params (opaque pointer from whisper_full_default_params)
                ctypes.POINTER(ctypes.c_float),  # samples
                ctypes.c_int,  # n_samples
            ]
            self.lib.whisper_full.restype = ctypes.c_int
            
            # For params modification, we need whisper_full_default_params_by_ref
            self.lib.whisper_full_default_params_by_ref.argtypes = [ctypes.c_int]
            self.lib.whisper_full_default_params_by_ref.restype = ctypes.c_void_p
            
            self.lib.whisper_free_params.argtypes = [ctypes.c_void_p]
            self.lib.whisper_free_params.restype = None
            
            self.lib.whisper_full_n_segments.argtypes = [ctypes.c_void_p]
            self.lib.whisper_full_n_segments.restype = ctypes.c_int
            
            self.lib.whisper_full_get_segment_text.argtypes = [
                ctypes.c_void_p,
                ctypes.c_int,
            ]
            self.lib.whisper_full_get_segment_text.restype = ctypes.c_char_p
            
            self.lib.whisper_full_get_segment_t0.argtypes = [
                ctypes.c_void_p,
                ctypes.c_int,
            ]
            self.lib.whisper_full_get_segment_t0.restype = ctypes.c_int64
            
            self.lib.whisper_full_get_segment_t1.argtypes = [
                ctypes.c_void_p,
                ctypes.c_int,
            ]
            self.lib.whisper_full_get_segment_t1.restype = ctypes.c_int64
            
            # Get default parameters using by_ref version (allocates on heap)
            # WHISPER_SAMPLING_GREEDY = 0
            params_ptr = self.lib.whisper_full_default_params_by_ref(0)
            if not params_ptr:
                raise TranscriptionError("Failed to get default whisper params")
            
            # Note: We cannot easily modify params fields without full struct definition
            # For now, use default params and rely on model's language detection
            # TODO: Add struct definition to modify language, n_threads, etc.
            
            # Prepare audio data as ctypes array
            n_samples = len(audio_data)
            audio_array = (ctypes.c_float * n_samples)(*audio_data)
            
            # Call whisper_full
            logger.debug(f"Calling whisper_full with {n_samples} samples (language={language})")
            start_time = time.time()
            
            try:
                result = self.lib.whisper_full(
                    self.ctx,
                    params_ptr,  # Pass params pointer
                    audio_array,
                    n_samples,
                )
            finally:
                # Free params
                self.lib.whisper_free_params(params_ptr)
            
            inference_time = time.time() - start_time
            
            if result != 0:
                raise TranscriptionError(f"whisper_full returned error code: {result}")
            
            # Extract segments
            n_segments = self.lib.whisper_full_n_segments(self.ctx)
            logger.debug(f"Whisper inference completed: {n_segments} segments in {inference_time:.2f}s")
            
            if n_segments == 0:
                logger.warning("Whisper returned 0 segments - audio may be silent or invalid")
                return {
                    "text": "",
                    "segments": [],
                    "language": language,
                    "inference_time": inference_time,
                }
            
            # Collect all segments
            segments = []
            full_text_parts = []
            
            for i in range(n_segments):
                # Get segment text
                text_ptr = self.lib.whisper_full_get_segment_text(self.ctx, i)
                text = text_ptr.decode("utf-8") if text_ptr else ""
                
                # Get timestamps (in 10ms units)
                t0 = self.lib.whisper_full_get_segment_t0(self.ctx, i)
                t1 = self.lib.whisper_full_get_segment_t1(self.ctx, i)
                
                # Convert to seconds
                start_time_s = t0 / 100.0
                end_time_s = t1 / 100.0
                
                segments.append({
                    "start": start_time_s,
                    "end": end_time_s,
                    "text": text.strip(),
                })
                
                full_text_parts.append(text.strip())
            
            full_text = " ".join(full_text_parts)
            
            # Calculate confidence (placeholder - Whisper doesn't provide direct confidence)
            # We use a heuristic: if we got segments, assume reasonable confidence
            confidence = 0.95 if n_segments > 0 else 0.0
            
            logger.info(
                f"Transcription complete: {len(full_text)} chars, "
                f"{n_segments} segments, {inference_time:.2f}s"
            )
            
            return {
                "text": full_text,
                "segments": segments,
                "language": language,
                "inference_time": inference_time,
                "confidence": confidence,
            }

        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            raise TranscriptionError(f"Transcription failed: {e}")

    def __del__(self):
        """Clean up Whisper context on deletion"""
        if self.ctx and self.lib:
            try:
                logger.debug("Freeing Whisper context...")
                self.lib.whisper_free.argtypes = [ctypes.c_void_p]
                self.lib.whisper_free.restype = None
                self.lib.whisper_free(self.ctx)
                logger.debug("Whisper context freed")
            except Exception as e:
                logger.error(f"Error freeing Whisper context: {e}")


# Global singleton instance
_whisper_library_adapter: Optional[WhisperLibraryAdapter] = None


def get_whisper_library_adapter() -> WhisperLibraryAdapter:
    """
    Get or create global WhisperLibraryAdapter instance (singleton).
    This ensures model is loaded once and reused across all requests.

    Returns:
        WhisperLibraryAdapter instance
    """
    global _whisper_library_adapter

    try:
        if _whisper_library_adapter is None:
            logger.info("Creating WhisperLibraryAdapter instance...")
            _whisper_library_adapter = WhisperLibraryAdapter()
            logger.info("WhisperLibraryAdapter singleton initialized")

        return _whisper_library_adapter

    except Exception as e:
        logger.error(f"Failed to get WhisperLibraryAdapter: {e}")
        raise
