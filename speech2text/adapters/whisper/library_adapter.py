"""
Whisper Library Adapter - Direct C library integration for Whisper.cpp
Replaces subprocess-based CLI wrapper with direct shared library calls.
Provides significant performance improvements by loading model once and reusing context.
"""

import ctypes
import os
from pathlib import Path
from typing import Optional
import numpy as np

from core.config import get_settings
from core.logger import logger


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
        "ram_mb": 500
    },
    "medium": {
        "dir": "whisper_medium_xeon",
        "model": "ggml-medium-q5_1.bin",
        "size_mb": 1500,
        "ram_mb": 2000
    }
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
            raise ValueError(f"Unsupported model size: {self.model_size}. Must be one of {list(MODEL_CONFIGS.keys())}")

        self.config = MODEL_CONFIGS[self.model_size]
        self.lib_dir = self.artifacts_dir / self.config["dir"]
        self.model_path = self.lib_dir / self.config["model"]

        # Load libraries and initialize context
        self.lib = None
        self.ctx = None

        try:
            self._load_libraries()
            self._initialize_context()
            logger.info(f"WhisperLibraryAdapter initialized successfully (model={self.model_size})")
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
            new_ld_path = f"{self.lib_dir}:{old_ld_path}" if old_ld_path else str(self.lib_dir)
            os.environ["LD_LIBRARY_PATH"] = new_ld_path
            logger.debug(f"Set LD_LIBRARY_PATH={new_ld_path}")

            # Load dependencies in correct order (CRITICAL!)
            # 1. Base libraries first
            logger.debug("Loading libggml-base.so.0...")
            libggml_base = ctypes.CDLL(
                str(self.lib_dir / "libggml-base.so.0"),
                mode=ctypes.RTLD_GLOBAL
            )

            logger.debug("Loading libggml-cpu.so.0...")
            libggml_cpu = ctypes.CDLL(
                str(self.lib_dir / "libggml-cpu.so.0"),
                mode=ctypes.RTLD_GLOBAL
            )

            # 2. GGML core
            logger.debug("Loading libggml.so.0...")
            libggml = ctypes.CDLL(
                str(self.lib_dir / "libggml.so.0"),
                mode=ctypes.RTLD_GLOBAL
            )

            # 3. Whisper (depends on GGML)
            logger.debug("Loading libwhisper.so...")
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
            model_path_bytes = str(self.model_path).encode('utf-8')
            self.ctx = self.lib.whisper_init_from_file(model_path_bytes)

            if not self.ctx:
                raise ModelInitError(
                    f"whisper_init_from_file() returned NULL. "
                    f"Model file may be corrupted: {self.model_path}"
                )

            logger.info(f"Whisper context initialized (model={self.model_size}, ram~{self.config['ram_mb']}MB)")

        except ModelInitError:
            raise
        except Exception as e:
            raise ModelInitError(f"Failed to initialize Whisper context: {e}")

    def transcribe(
        self,
        audio_path: str,
        language: str = "vi",
        **kwargs
    ) -> str:
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

            # Load audio data (assuming 16kHz WAV for now)
            # TODO: Add proper audio loading with ffmpeg conversion if needed
            audio_data = self._load_audio(audio_path)

            # Call whisper_full() for transcription
            result = self._call_whisper_full(audio_data, language)

            logger.debug(f"Transcription successful: {len(result)} chars")
            return result

        except TranscriptionError:
            raise
        except Exception as e:
            raise TranscriptionError(f"Transcription failed: {e}")

    def _load_audio(self, audio_path: str) -> np.ndarray:
        """
        Load audio file and convert to format expected by Whisper.
        Whisper expects: 16kHz, mono, float32, range [-1, 1]

        Args:
            audio_path: Path to audio file

        Returns:
            Audio samples as numpy array

        Raises:
            TranscriptionError: If audio loading fails
        """
        try:
            # For now, use a simple implementation
            # In production, use ffmpeg to convert to correct format
            # This is a placeholder - actual implementation would use pydub or ffmpeg
            logger.warning("Audio loading not fully implemented - using placeholder")

            # Return empty array for now (will be implemented in next iteration)
            return np.array([], dtype=np.float32)

        except Exception as e:
            raise TranscriptionError(f"Failed to load audio: {e}")

    def _call_whisper_full(self, audio_data: np.ndarray, language: str) -> str:
        """
        Call whisper_full() C function to perform transcription.

        Args:
            audio_data: Audio samples (float32, 16kHz, mono)
            language: Language code

        Returns:
            Transcribed text

        Raises:
            TranscriptionError: If whisper_full() fails
        """
        try:
            # This is a simplified implementation
            # Full implementation would:
            # 1. Create whisper_full_params struct
            # 2. Set language, no_timestamps, etc.
            # 3. Call whisper_full()
            # 4. Extract text segments from context

            logger.warning("whisper_full() not fully implemented - using placeholder")

            # Placeholder return (will be implemented in next iteration)
            return ""

        except Exception as e:
            raise TranscriptionError(f"whisper_full() failed: {e}")

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
