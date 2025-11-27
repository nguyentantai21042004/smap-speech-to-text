"""
Whisper Transcriber Adapter.
"""

import asyncio
from typing import Dict, Any
from ports.transcriber import TranscriberPort
from adapters.whisper.engine import get_whisper_transcriber


class WhisperAdapter(TranscriberPort):
    """Adapter for Whisper transcription."""

    def __init__(self):
        self.transcriber = get_whisper_transcriber()

    async def transcribe(
        self, audio_path: str, model: str, language: str
    ) -> Dict[str, Any]:
        loop = asyncio.get_running_loop()
        # Use transcribe_with_retry for robustness
        text = await loop.run_in_executor(
            None, self.transcriber.transcribe_with_retry, audio_path, language, model
        )
        return {"text": text}
