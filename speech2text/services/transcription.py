import os
import uuid
import asyncio
import httpx  # type: ignore
import time
from pathlib import Path
from typing import Dict, Any, Optional
from core.config import get_settings
from core.logger import logger

settings = get_settings()


class TranscribeService:
    """
    Stateless service to download audio from URL and transcribe it.
    Supports both CLI and library-based transcription.
    """

    def __init__(self):
        # Try to use library adapter first (preferred), fall back to CLI
        self.transcriber = self._get_transcriber()
        self.use_library = self._is_library_adapter()

        # Use configured temp dir
        self.temp_dir = Path(settings.temp_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.max_size_mb = settings.max_upload_size_mb

        logger.info(
            f"TranscribeService initialized (mode: {'library' if self.use_library else 'CLI'})"
        )

    def _get_transcriber(self):
        """Get transcriber using library adapter"""
        # Use library adapter (direct C library integration)
            from adapters.whisper.library_adapter import get_whisper_library_adapter

            logger.info("Using WhisperLibraryAdapter (direct C library integration)")
            return get_whisper_library_adapter()

    def _is_library_adapter(self) -> bool:
        """Check if using library adapter"""
        return self.transcriber.__class__.__name__ == "WhisperLibraryAdapter"

    async def transcribe_from_url(
        self, audio_url: str, language: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Download audio from URL and transcribe it with timeout protection.

        Args:
            audio_url: URL to download audio from
            language: Optional language hint for transcription (overrides config)

        Returns:
            Dictionary containing transcription text and metadata

        Raises:
            asyncio.TimeoutError: If transcription exceeds configured timeout
            ValueError: If download fails or file too large
        """
        file_id = str(uuid.uuid4())
        temp_file_path = self.temp_dir / f"{file_id}.tmp"

        try:
            logger.info(f"Processing transcription request for URL: {audio_url}")

            # 1. Download file
            start_download = time.time()
            file_size_mb = await self._download_file(audio_url, temp_file_path)
            download_duration = time.time() - start_download
            logger.info(f"Downloaded {file_size_mb:.2f}MB in {download_duration:.2f}s")

            # 2. Transcribe with timeout
            # Whisper engine is synchronous/blocking, so run in executor
            loop = asyncio.get_running_loop()
            start_transcribe = time.time()

            # Use provided language or fall back to config
            lang = language or settings.whisper_language
            model = settings.whisper_model
            timeout_seconds = settings.transcribe_timeout_seconds

            logger.info(
                f"Starting transcription (language={lang}, timeout={timeout_seconds}s)"
            )

            # Wrap transcription in timeout
            if self.use_library:
                def _transcribe():
                    return self.transcriber.transcribe(str(temp_file_path), lang)
            else:
                def _transcribe():
                    return self.transcriber.transcribe(
                        str(temp_file_path), lang, model, None
                    )

            transcription_text = await asyncio.wait_for(
                loop.run_in_executor(None, _transcribe),
                timeout=timeout_seconds,
            )

            transcribe_duration = time.time() - start_transcribe
            logger.info(f"Transcribed in {transcribe_duration:.2f}s")

            return {
                "text": transcription_text,
                "duration": transcribe_duration,
                "download_duration": download_duration,
                "file_size_mb": file_size_mb,
                "model": model,
                "language": lang,
                "audio_duration": 0.0,  # TODO: Extract from whisper metadata if available
            }

        except asyncio.TimeoutError:
            logger.error(
                f"Transcription timeout after {settings.transcribe_timeout_seconds}s"
            )
            raise
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            raise
        finally:
            # 3. Cleanup
            if temp_file_path.exists():
                try:
                    os.remove(temp_file_path)
                    logger.debug(f"Cleaned up temp file: {temp_file_path}")
                except Exception as e:
                    logger.warning(f"Failed to clean up temp file: {e}")

    async def _download_file(self, url: str, destination: Path) -> float:
        """
        Stream download file to destination.
        Returns file size in MB.
        Raises ValueError if file too large.
        """
        async with httpx.AsyncClient() as client:
            async with client.stream("GET", url, follow_redirects=True) as response:
                if response.status_code != 200:
                    raise ValueError(
                        f"Failed to download file: HTTP {response.status_code}"
                    )

                # Check content-length if available
                content_length = response.headers.get("content-length")
                if (
                    content_length
                    and int(content_length) > self.max_size_mb * 1024 * 1024
                ):
                    raise ValueError(
                        f"File too large: {int(content_length)/1024/1024:.2f}MB > {self.max_size_mb}MB"
                    )

                size_bytes = 0
                with open(destination, "wb") as f:
                    async for chunk in response.aiter_bytes():
                        f.write(chunk)
                        size_bytes += len(chunk)
                        if size_bytes > self.max_size_mb * 1024 * 1024:
                            raise ValueError(
                                f"File too large (streamed): > {self.max_size_mb}MB"
                            )

                return size_bytes / (1024 * 1024)
