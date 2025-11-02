"""
Whisper.cpp transcriber interface.
Includes detailed logging and comprehensive error handling.
Auto-downloads models from MinIO if not present locally.
"""

import subprocess
import os
import time
from pathlib import Path
from typing import Optional

from core.config import get_settings
from core.logger import logger
from worker.errors import (
    WhisperCrashError,
    TimeoutError as STTTimeoutError,
    FileNotFoundError as STTFileNotFoundError,
)
from worker.model_downloader import get_model_downloader

settings = get_settings()


class WhisperTranscriber:
    """Interface to Whisper.cpp for audio transcription."""

    def __init__(self):
        """Initialize Whisper transcriber."""
        logger.debug("WhisperTranscriber initialized")
        self._validate_whisper_setup()

    def _validate_whisper_setup(self) -> None:
        """
        Validate Whisper executable and models exist.

        Raises:
            FileNotFoundError: If executable or model not found
        """
        try:
            logger.debug("🔍 Validating Whisper setup...")

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

            # Check for errors
            if result.returncode != 0:
                error_msg = f"Whisper process failed with code {result.returncode}"
                logger.error(f"{error_msg}")
                logger.error(f"Stderr: {result.stderr}")
                raise WhisperCrashError(error_msg)

            # Parse output
            transcription = self._parse_output(result.stdout, result.stderr)

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
                f"🔍 Building Whisper command for model={model}, language={language}"
            )

            # Ensure model exists (download from MinIO if missing)
            logger.info(f"Ensuring model '{model}' is available...")
            model_downloader = get_model_downloader()
            model_path = model_downloader.ensure_model_exists(model)

            logger.debug(f"Using model: {model_path}")

            # Build command with anti-hallucination flags
            command = [
                settings.whisper_executable,
                "-m",
                model_path,
                "-f",
                audio_path,
                "-l",
                language,
                "--output-txt",  # Output as text
                "--no-timestamps",  # No timestamps in output
                "--no-context",  # Disable context reuse between chunks (reduces repetition)
                "--suppress-hallucination",  # Suppress hallucinated text (reduces false predictions)
            ]

            logger.debug(f"Command built: {len(command)} arguments")

            return command

        except Exception as e:
            logger.error(f"Failed to build Whisper command: {e}")
            logger.exception("Command build error:")
            raise

    def _parse_output(self, stdout: str, stderr: str) -> str:
        """
        Parse Whisper output to extract transcription.

        Args:
            stdout: Standard output from Whisper
            stderr: Standard error from Whisper

        Returns:
            Transcribed text
        """
        try:
            logger.debug("🔍 Parsing Whisper output...")

            # Log stderr for debugging
            if stderr:
                logger.debug(f"Whisper stderr: {stderr[:500]}...")

            # Whisper outputs to stdout
            if not stdout:
                logger.warning("No output from Whisper")
                return ""

            # Clean up output
            # Whisper.cpp outputs the transcription directly
            transcription = stdout.strip()

            # Remove any leading/trailing whitespace and newlines
            transcription = " ".join(transcription.split())

            logger.debug(f"Output parsed: {len(transcription)} chars")

            return transcription

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
