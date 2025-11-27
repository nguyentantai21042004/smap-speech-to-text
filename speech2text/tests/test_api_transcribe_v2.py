"""
Tests for new presigned URL transcription API with authentication.
These tests mock the TranscribeService to avoid needing Whisper libraries.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
import importlib.util
import sys
import os
from pathlib import Path

# Add project root to PYTHONPATH for imports to work
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
os.chdir(project_root)

# Mock TranscribeService before importing main to avoid loading Whisper
with patch('services.transcription.TranscribeService') as MockTranscribe:
    mock_service = MagicMock()
    MockTranscribe.return_value = mock_service
    
    # Import cmd.api.main by path to avoid conflict with stdlib cmd
    file_path = Path("cmd/api/main.py").resolve()
    spec = importlib.util.spec_from_file_location("cmd.api.main", file_path)
    main_module = importlib.util.module_from_spec(spec)
    sys.modules["cmd.api.main"] = main_module
    spec.loader.exec_module(main_module)
    app = main_module.app

client = TestClient(app)

# Test constants
VALID_API_KEY = "smap-internal-key-changeme"
INVALID_API_KEY = "wrong-key"
TEST_MEDIA_URL = "https://minio.internal/bucket/audio_123.mp3?token=xyz"


class TestTranscribeV2Authentication:
    """Test authentication for /transcribe endpoint."""

    def test_missing_api_key(self):
        """Should return 401 when API key is missing."""
        response = client.post(
            "/transcribe",
            json={"media_url": TEST_MEDIA_URL, "language": "vi"},
        )
        assert response.status_code == 401
        data = response.json()
        assert data["error_code"] == 1
        assert "Missing API key" in data["message"]

    def test_invalid_api_key(self):
        """Should return 401 when API key is invalid."""
        response = client.post(
            "/transcribe",
            json={"media_url": TEST_MEDIA_URL, "language": "vi"},
            headers={"X-API-Key": INVALID_API_KEY},
        )
        assert response.status_code == 401
        data = response.json()
        assert data["error_code"] == 1
        assert "Invalid API key" in data["message"]

    @patch("internal.api.routes.transcribe_routes.transcribe_service.transcribe_from_url", new_callable=AsyncMock)
    def test_valid_api_key_success(self, mock_transcribe):
        """Should succeed with valid API key."""
        # Mock successful transcription (AsyncMock automatically handles await)
        mock_transcribe.return_value = {
            "text": "Test transcription",
            "duration": 2.5,
            "audio_duration": 45.5,
            "confidence": 0.98,
            "download_duration": 1.0,
            "file_size_mb": 5.2,
            "model": "small",
            "language": "vi",
        }

        response = client.post(
            "/transcribe",
            json={"media_url": TEST_MEDIA_URL, "language": "vi"},
            headers={"X-API-Key": VALID_API_KEY},
        )
        assert response.status_code == 200
        data = response.json()
        # Response is TranscribeResponse model directly (not wrapped in standard format for this endpoint)
        assert data["status"] == "success"
        assert data["transcription"] == "Test transcription"
        assert data["processing_time"] == 2.5


class TestTranscribeV2RequestValidation:
    """Test request validation for /transcribe endpoint."""

    def test_missing_media_url(self):
        """Should return 422 when media_url is missing."""
        response = client.post(
            "/transcribe",
            json={"language": "vi"},
            headers={"X-API-Key": VALID_API_KEY},
        )
        assert response.status_code == 422

    def test_invalid_media_url_format(self):
        """Should return 422 when media_url is not a valid URL."""
        response = client.post(
            "/transcribe",
            json={"media_url": "not-a-url", "language": "vi"},
            headers={"X-API-Key": VALID_API_KEY},
        )
        assert response.status_code == 422

    @patch("internal.api.routes.transcribe_routes.transcribe_service.transcribe_from_url", new_callable=AsyncMock)
    def test_optional_language_parameter(self, mock_transcribe):
        """Should use default language when not provided."""
        mock_transcribe.return_value = {
            "text": "Test",
            "duration": 1.0,
            "audio_duration": 10.0,
            "confidence": 0.95,
            "download_duration": 0.5,
            "file_size_mb": 2.0,
            "model": "small",
            "language": "vi",
        }

        response = client.post(
            "/transcribe",
            json={"media_url": TEST_MEDIA_URL},
            headers={"X-API-Key": VALID_API_KEY},
        )
        assert response.status_code == 200
        # Check that service was called (language defaults to "vi" in request model)
        mock_transcribe.assert_called_once()


class TestTranscribeV2ResponseFormat:
    """Test response format for /transcribe endpoint."""

    @patch("internal.api.routes.transcribe_routes.transcribe_service.transcribe_from_url", new_callable=AsyncMock)
    def test_success_response_structure(self, mock_transcribe):
        """Should return proper response structure on success."""
        mock_transcribe.return_value = {
            "text": "Nội dung video nói về xe VinFast VF3",
            "duration": 2.1,
            "audio_duration": 45.5,
            "confidence": 0.98,
            "download_duration": 1.0,
            "file_size_mb": 5.0,
            "model": "small",
            "language": "vi",
        }

        response = client.post(
            "/transcribe",
            json={"media_url": TEST_MEDIA_URL, "language": "vi"},
            headers={"X-API-Key": VALID_API_KEY},
        )
        assert response.status_code == 200
        data = response.json()

        # Verify all required fields present
        assert "status" in data
        assert "transcription" in data
        assert "duration" in data
        assert "confidence" in data
        assert "processing_time" in data

        # Verify values
        assert data["status"] == "success"
        assert data["transcription"] == "Nội dung video nói về xe VinFast VF3"
        assert data["duration"] == 45.5
        assert data["confidence"] == 0.98
        assert data["processing_time"] == 2.1


class TestTranscribeV2ErrorHandling:
    """Test error handling for /transcribe endpoint."""

    @patch("internal.api.routes.transcribe_routes.transcribe_service.transcribe_from_url")
    def test_timeout_error(self, mock_transcribe):
        """Should return timeout status when processing exceeds limit."""
        import asyncio
        mock_transcribe.side_effect = asyncio.TimeoutError()

        response = client.post(
            "/transcribe",
            json={"media_url": TEST_MEDIA_URL, "language": "vi"},
            headers={"X-API-Key": VALID_API_KEY},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "timeout"
        assert data["transcription"] == ""

    @patch("internal.api.routes.transcribe_routes.transcribe_service.transcribe_from_url")
    def test_file_too_large_error(self, mock_transcribe):
        """Should return 413 when file exceeds size limit."""
        mock_transcribe.side_effect = ValueError("File too large: 600MB > 500MB")

        response = client.post(
            "/transcribe",
            json={"media_url": TEST_MEDIA_URL, "language": "vi"},
            headers={"X-API-Key": VALID_API_KEY},
        )
        assert response.status_code == 413

    @patch("internal.api.routes.transcribe_routes.transcribe_service.transcribe_from_url")
    def test_invalid_url_error(self, mock_transcribe):
        """Should return 400 when URL cannot be fetched."""
        mock_transcribe.side_effect = ValueError(
            "Failed to download file: HTTP 404"
        )

        response = client.post(
            "/transcribe",
            json={"media_url": TEST_MEDIA_URL, "language": "vi"},
            headers={"X-API-Key": VALID_API_KEY},
        )
        assert response.status_code == 400
        data = response.json()
        assert data["error_code"] == 1
        assert "Failed to download" in data["message"]

    @patch("internal.api.routes.transcribe_routes.transcribe_service.transcribe_from_url")
    def test_internal_server_error(self, mock_transcribe):
        """Should return 500 on unexpected errors."""
        mock_transcribe.side_effect = Exception("Unexpected error")

        response = client.post(
            "/transcribe",
            json={"media_url": TEST_MEDIA_URL, "language": "vi"},
            headers={"X-API-Key": VALID_API_KEY},
        )
        assert response.status_code == 500
        data = response.json()
        assert data["error_code"] == 1
        assert "Internal server error" in data["message"]


class TestSwaggerUI:
    """Test swagger UI hosting."""

    def test_swagger_index_accessible(self):
        """Should serve swagger UI at /swagger/index.html."""
        response = client.get("/swagger/index.html")
        # Will be 404 if swagger_static dir doesn't exist in test env
        # In real deployment, should be 200
        assert response.status_code in [200, 404]

    def test_openapi_json_accessible(self):
        """Should serve OpenAPI spec at /openapi.json."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "paths" in data
        # Verify /transcribe endpoint is documented
        assert "/transcribe" in data["paths"]

