import pytest
import os
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path
from services.transcription import TranscribeService


@pytest.mark.asyncio
async def test_transcribe_from_url_success():
    # Mock settings
    with patch("services.transcription.settings") as mock_settings:
        mock_settings.temp_dir = "/tmp/test_stt"
        mock_settings.max_upload_size_mb = 100
        mock_settings.whisper_language = "vi"
        mock_settings.whisper_model = "small"

        # Mock WhisperTranscriber
        mock_transcriber = MagicMock()
        mock_transcriber.transcribe.return_value = "Test transcription result"

        with patch(
            "services.transcription.get_whisper_transcriber",
            return_value=mock_transcriber,
        ):
            # Create service
            service = TranscribeService()

            # Mock httpx
            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_client = MagicMock()
                mock_client_cls.return_value.__aenter__.return_value = mock_client

                mock_response = AsyncMock()
                mock_response.status_code = 200
                mock_response.headers = {"content-length": "1024"}

                # Mock aiter_bytes
                async def mock_aiter_bytes():
                    yield b"fake audio data"

                mock_response.aiter_bytes = mock_aiter_bytes

                # stream is not async, it returns a context manager
                mock_stream = MagicMock()
                mock_stream.__aenter__.return_value = mock_response
                mock_stream.__aexit__.return_value = None
                mock_client.stream.return_value = mock_stream

                # Mock file operations to avoid actual disk writes if possible,
                # but TranscribeService writes to disk.
                # We can let it write to /tmp/test_stt (it's mocked temp_dir)
                # But we need to make sure directory exists or is mocked.
                # The service creates it in __init__.
                # Since we mocked settings after __init__ might be tricky if we don't be careful.
                # Actually we patch settings before creating service instance, so __init__ uses mocked settings.

                # We need to ensure the path exists or mock Path.mkdir
                with patch("pathlib.Path.mkdir") as mock_mkdir:
                    with patch("builtins.open", new_callable=MagicMock) as mock_open:
                        with patch("os.remove") as mock_remove:
                            with patch("pathlib.Path.exists", return_value=True):
                                # Mock file write
                                mock_file = MagicMock()
                                mock_open.return_value.__enter__.return_value = (
                                    mock_file
                                )

                                # Run test
                                result = await service.transcribe_from_url(
                                    "http://example.com/audio.mp3"
                                )

                                assert result["text"] == "Test transcription result"
                                assert result["model"] == "small"
                                assert "duration" in result

                                # Verify transcribe called
                                mock_transcriber.transcribe.assert_called_once()

                                # Verify cleanup (os.remove)
                                mock_remove.assert_called_once()


@pytest.mark.asyncio
async def test_transcribe_file_too_large():
    with patch("services.transcription.settings") as mock_settings:
        mock_settings.temp_dir = "/tmp/test_stt"
        mock_settings.max_upload_size_mb = 1  # 1MB limit

        with patch("services.transcription.get_whisper_transcriber"):
            service = TranscribeService()

            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_client = MagicMock()
                mock_client_cls.return_value.__aenter__.return_value = mock_client

                mock_response = AsyncMock()
                mock_response.status_code = 200
                # Content length 2MB
                mock_response.headers = {"content-length": str(2 * 1024 * 1024)}

                # stream is not async
                mock_stream = MagicMock()
                mock_stream.__aenter__.return_value = mock_response
                mock_stream.__aexit__.return_value = None
                mock_client.stream.return_value = mock_stream

                with pytest.raises(ValueError) as excinfo:
                    await service.transcribe_from_url("http://example.com/large.mp3")

                assert "File too large" in str(excinfo.value)
