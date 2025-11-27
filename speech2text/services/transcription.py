import os
import uuid
import shutil
import asyncio
import httpx
import time
from pathlib import Path
from typing import Dict, Any, Optional
from core.config import get_settings
from core.logger import logger
from adapters.whisper.engine import get_whisper_transcriber

settings = get_settings()


class TranscribeService:
    """
    Stateless service to download audio from URL and transcribe it.
    """

    def __init__(self):
        self.transcriber = get_whisper_transcriber()
        # Use configured temp dir
        self.temp_dir = Path(settings.temp_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.max_size_mb = settings.max_upload_size_mb

    async def transcribe_from_url(self, audio_url: str) -> Dict[str, Any]:
        """
        Download audio from URL and transcribe it.

        Args:
            audio_url: URL to download audio from

        Returns:
            Dictionary containing transcription text and metadata
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

            # 2. Transcribe
            # Whisper engine is synchronous/blocking, so run in executor
            loop = asyncio.get_running_loop()
            start_transcribe = time.time()

            # Use configured language and model
            language = settings.whisper_language
            model = settings.whisper_model

            transcription_text = await loop.run_in_executor(
                None,
                self.transcriber.transcribe,
                str(temp_file_path),
                language,
                model,
                None,  # timeout
            )
            transcribe_duration = time.time() - start_transcribe
            logger.info(f"Transcribed in {transcribe_duration:.2f}s")

            return {
                "text": transcription_text,
                "duration": transcribe_duration,
                "download_duration": download_duration,
                "file_size_mb": file_size_mb,
                "model": model,
            }

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
