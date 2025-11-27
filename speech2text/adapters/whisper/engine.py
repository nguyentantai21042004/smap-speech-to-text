"""
Whisper.cpp transcriber interface.
Includes detailed logging and comprehensive error handling.
Auto-downloads models from MinIO if not present locally.
"""

import subprocess
import os
import time
from typing import Optional

from core.config import get_settings
from core.logger import logger
from core.errors import (
    WhisperCrashError,
    TimeoutError as STTTimeoutError,
    FileNotFoundError as STTFileNotFoundError,
)
from adapters.whisper.model_downloader import get_model_downloader

settings = get_settings()


class WhisperTranscriber:
    """Interface to Whisper.cpp for audio transcription."""

    def __init__(self):
        """Initialize Whisper transcriber."""
        logger.debug("WhisperTranscriber initialized")
        self._validate_whisper_setup()
        self._model_path_cache: dict[str, str] = {}
        self._model_downloader = None

    def _validate_whisper_setup(self) -> None:
        """
        Validate Whisper executable and models exist.

        Raises:
            FileNotFoundError: If executable or model not found
        """
        try:
            logger.debug("Validating Whisper setup...")

            # Check executable exists
            if not os.path.exists(settings.whisper_executable):
                error_msg = (
                    f"Whisper executable not found: {settings.whisper_executable}"
                )
                logger.error(f"{error_msg}")
                raise STTFileNotFoundError(error_msg)

            # Check executable is executable
            if not os.access(settings.whisper_executable, os.X_OK):
                error_msg = (
                    f"Whisper executable not executable: {settings.whisper_executable}"
                )
                logger.error(f"{error_msg}")
                raise PermissionError(error_msg)

            # Check models directory exists
            if not os.path.exists(settings.whisper_models_dir):
                error_msg = (
                    f"Whisper models directory not found: {settings.whisper_models_dir}"
                )
                logger.error(f"{error_msg}")
                raise STTFileNotFoundError(error_msg)

            logger.debug(
                f"Whisper setup validated: executable={settings.whisper_executable}"
            )

        except Exception as e:
            logger.error(f"Whisper setup validation failed: {e}")
            raise

    def transcribe(
        self,
        audio_path: str,
        language: str = "vi",
        model: str = "medium",
        timeout: Optional[int] = None,
    ) -> str:
        """
        Transcribe audio file using Whisper.cpp.

        Args:
            audio_path: Path to audio file
            language: Language code (en, vi, etc.)
            model: Whisper model to use
            timeout: Timeout in seconds

        Returns:
            Transcribed text

        Raises:
            FileNotFoundError: If audio file not found
            WhisperCrashError: If Whisper process crashes
            TimeoutError: If transcription times out
        """
        start_time = time.time()

        try:
            logger.info(
                f"Starting transcription: file={audio_path}, language={language}, model={model}"
            )

            # Validate audio file exists
            if not os.path.exists(audio_path):
                error_msg = f"Audio file not found: {audio_path}"
                logger.error(f"{error_msg}")
                raise STTFileNotFoundError(error_msg)

            # Get file size
            file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
            logger.debug(f"Audio file size: {file_size_mb:.2f}MB")

            # Build Whisper command
            command = self._build_command(audio_path, language, model)
            logger.debug(f"Whisper command: {' '.join(command)}")

            # Execute Whisper
            timeout = timeout or settings.chunk_timeout
            logger.debug(f"Executing Whisper with timeout: {timeout}s")

            result = subprocess.run(
                command, capture_output=True, text=True, timeout=timeout, check=False
            )

            elapsed_time = time.time() - start_time
            logger.debug(f"⏱️ Whisper execution completed in {elapsed_time:.2f}s")

            # Log full stderr for debugging (especially if stdout is empty)
            if result.stderr:
                logger.debug(f"Whisper stderr (full): {result.stderr}")

            # Check for errors
            if result.returncode != 0:
                error_msg = f"Whisper process failed with code {result.returncode}"
                logger.error(f"{error_msg}")
                logger.error(
                    f"Stderr: {result.stderr[:1000] if result.stderr else 'No stderr'}"
                )
                logger.error(
                    f"Stdout: {result.stdout[:500] if result.stdout else 'No stdout'}"
                )
                raise WhisperCrashError(error_msg)

            # Parse output
            # When using --output-txt, Whisper writes to file instead of stdout
            # Need to read from output file
            transcription = self._parse_output(result.stdout, result.stderr, audio_path)

            # If stdout is empty but process succeeded, check output file
            if not transcription and result.returncode == 0:
                logger.debug(f"Whisper stdout empty, checking output file...")
                logger.debug(f"Command: {' '.join(command)}")
                logger.debug(
                    f"Stdout: {result.stdout[:200] if result.stdout else '(empty)'}"
                )
                logger.debug(
                    f"Stderr: {result.stderr[:200] if result.stderr else '(empty)'}"
                )

            logger.info(
                f"Transcription successful: length={len(transcription)} chars, time={elapsed_time:.2f}s"
            )
            logger.debug(f"Transcription preview: {transcription[:100]}...")

            # Log performance metrics
            chars_per_second = (
                len(transcription) / elapsed_time if elapsed_time > 0 else 0
            )
            logger.info(f"Performance: {chars_per_second:.2f} chars/sec")

            return transcription

        except subprocess.TimeoutExpired as e:
            elapsed_time = time.time() - start_time
            error_msg = f"Transcription timeout after {elapsed_time:.2f}s"
            logger.error(f"{error_msg}")
            logger.exception("Timeout error details:")
            raise STTTimeoutError(error_msg)

        except WhisperCrashError as e:
            elapsed_time = time.time() - start_time
            logger.error(f"Whisper crash after {elapsed_time:.2f}s: {e}")
            raise

        except STTFileNotFoundError as e:
            logger.error(f"File not found: {e}")
            raise

        except Exception as e:
            elapsed_time = time.time() - start_time
            logger.error(f"Transcription failed after {elapsed_time:.2f}s: {e}")
            logger.exception("Transcription error details:")
            raise

    def _build_command(self, audio_path: str, language: str, model: str) -> list:
        """
        Build Whisper.cpp command.
        Auto-downloads model from MinIO if not present locally.

        Args:
            audio_path: Path to audio file
            language: Language code
            model: Model name

        Returns:
            Command as list of strings
        """
        try:
            logger.debug(
                f"Building Whisper command for model={model}, language={language}"
            )

            # OPTIMIZATION: Cache model path to avoid repeated checks/downloads
            # This is critical for parallel transcription where multiple chunks check the same model
            if model in self._model_path_cache:
                model_path = self._model_path_cache[model]
                # No log - already cached, silent success
            else:
                # Lazy-load model downloader (singleton, shared across all chunks)
                if self._model_downloader is None:
                    self._model_downloader = get_model_downloader()

                # Check and cache model path (only first time, subsequent chunks use cache)
                model_path = self._model_downloader.ensure_model_exists(model)
                self._model_path_cache[model] = model_path
                # Log only once when model is first checked/cached
                logger.debug(f"Model '{model}' ensured and cached: {model_path}")

            # Build command with optimized flags for quality and accuracy
            # Anti-repetition flags:
            # - --max-context 0: Disable context reuse between chunks (prevents repetition)
            # Anti-hallucination flags:
            # - --suppress-nst: Suppress non-speech tokens (removes [music], [noise], etc.)
            # - --no-speech-thold: Higher threshold = less false positives (default 0.6, we use 0.7)
            # - --entropy-thold: Higher threshold = less hallucination (default 2.4, we use 2.6)
            # - --logprob-thold: Higher threshold = filter low-quality predictions (default -1.0, we use -0.8)
            # Quality flags:
            # - --no-fallback: Disable temperature fallback for consistent output
            # - --suppress-regex: Optional regex to suppress specific tokens
            command = [
                settings.whisper_executable,
                "-m",
                model_path,
                "-f",
                audio_path,
                "-l",
                language,
                "--no-timestamps",  # No timestamps in output
                "--max-context",
                str(
                    settings.whisper_max_context
                ),  # Disable context reuse (anti-repetition)
                "--suppress-nst",  # Suppress non-speech tokens (anti-hallucination)
                "--no-speech-thold",
                str(
                    settings.whisper_no_speech_thold
                ),  # Higher threshold for speech detection
                "--entropy-thold",
                str(
                    settings.whisper_entropy_thold
                ),  # Higher threshold (less hallucination)
                "--logprob-thold",
                str(
                    settings.whisper_logprob_thold
                ),  # Higher threshold (filter low quality)
            ]

            # Add --no-fallback if enabled
            if settings.whisper_no_fallback:
                command.append("--no-fallback")

            # Add --suppress-regex if configured
            if settings.whisper_suppress_regex:
                command.extend(["--suppress-regex", settings.whisper_suppress_regex])

            logger.debug(f"Command built: {len(command)} arguments")

            return command

        except Exception as e:
            logger.error(f"Failed to build Whisper command: {e}")
            logger.exception("Command build error:")
            raise

    def _parse_output(self, stdout: str, stderr: str, audio_path: str = None) -> str:
        """
        Parse Whisper output to extract transcription.
        Whisper outputs transcription to stdout by default.

        Args:
            stdout: Standard output from Whisper
            stderr: Standard error from Whisper
            audio_path: Path to input audio file (for finding output file if needed)

        Returns:
            Transcribed text
        """
        try:
            logger.debug("Parsing Whisper output...")

            # Log stderr for debugging
            if stderr:
                logger.debug(f"Whisper stderr: {stderr[:500]}...")

            # Whisper outputs transcription to stdout (when not using --output-txt)
            transcription_text = ""

            if stdout and stdout.strip():
                transcription_text = stdout.strip()
                logger.debug(
                    f"Found transcription in stdout: {len(transcription_text)} chars"
                )
            else:
                logger.debug(
                    "No transcription in stdout, checking if transcription is in stderr..."
                )
                # Sometimes Whisper might output to stderr (unlikely but possible)
                if stderr and stderr.strip():
                    # Check if stderr looks like transcription (not error message)
                    stderr_lower = stderr.lower()
                    is_error = any(
                        word in stderr_lower
                        for word in ["error", "warning", "failed", "usage", "help"]
                    )

                    if not is_error and len(stderr.strip()) > 10:
                        logger.debug(
                            "Stderr might contain transcription, trying to parse..."
                        )
                        transcription_text = stderr.strip()

            if not transcription_text:
                logger.warning("No transcription found in stdout or stderr")
                return ""

            # Clean up output
            transcription_text = transcription_text.strip()
            # Remove any leading/trailing whitespace and newlines
            transcription_text = " ".join(transcription_text.split())

            logger.debug(f"Output parsed: {len(transcription_text)} chars")

            return transcription_text

        except Exception as e:
            logger.error(f"Failed to parse Whisper output: {e}")
            logger.exception("Output parsing error:")
            # Return empty string rather than failing
            return ""

    def transcribe_with_retry(
        self,
        audio_path: str,
        language: str = "vi",
        model: str = "medium",
        max_retries: int = 3,
        timeout: Optional[int] = None,
    ) -> str:
        """
        Transcribe with retry logic.

        Args:
            audio_path: Path to audio file
            language: Language code
            model: Whisper model
            max_retries: Maximum retry attempts
            timeout: Timeout per attempt

        Returns:
            Transcribed text

        Raises:
            Exception: If all retries fail
        """
        last_exception = None

        for attempt in range(max_retries):
            try:
                logger.info(f"Transcription attempt {attempt + 1}/{max_retries}")

                result = self.transcribe(audio_path, language, model, timeout)

                if result:
                    logger.info(f"Transcription successful on attempt {attempt + 1}")
                    return result
                else:
                    logger.warning(f"Empty transcription on attempt {attempt + 1}")
                    if attempt < max_retries - 1:
                        time.sleep(2**attempt)  # Exponential backoff
                        continue

            except STTTimeoutError as e:
                last_exception = e
                logger.warning(f"Timeout on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying after backoff...")
                    time.sleep(2**attempt)
                    continue
                else:
                    raise

            except WhisperCrashError as e:
                last_exception = e
                logger.warning(f"Whisper crash on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying after backoff...")
                    time.sleep(2**attempt)
                    continue
                else:
                    raise

            except Exception as e:
                logger.error(f"Unexpected error on attempt {attempt + 1}: {e}")
                last_exception = e
                raise

        # All retries exhausted
        error_msg = f"All {max_retries} transcription attempts failed"
        logger.error(f"{error_msg}")
        if last_exception:
            raise last_exception
        else:
            raise Exception(error_msg)


# Global singleton instance
_whisper_transcriber: Optional[WhisperTranscriber] = None


def get_whisper_transcriber() -> WhisperTranscriber:
    """
    Get or create global WhisperTranscriber instance (singleton).
    This ensures the transcriber is initialized once and reused across all jobs.

    Returns:
        WhisperTranscriber instance
    """
    global _whisper_transcriber

    try:
        if _whisper_transcriber is None:
            logger.info("Creating WhisperTranscriber instance...")
            _whisper_transcriber = WhisperTranscriber()
            logger.info("WhisperTranscriber singleton initialized")

        return _whisper_transcriber

    except Exception as e:
        logger.error(f"Failed to get whisper transcriber: {e}")
        logger.exception("WhisperTranscriber initialization error:")
        raise
