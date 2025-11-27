"""
Transcriber Port.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any


class TranscriberPort(ABC):
    """Abstract interface for Transcription Engine."""

    @abstractmethod
    async def transcribe(
        self, audio_path: str, model: str, language: str
    ) -> Dict[str, Any]:
        """Transcribe an audio file."""
        pass
