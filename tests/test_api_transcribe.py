import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
import importlib.util
import sys
from pathlib import Path

# Import cmd.api.main by path to avoid conflict with stdlib cmd
file_path = Path("cmd/api/main.py").resolve()
spec = importlib.util.spec_from_file_location("cmd.api.main", file_path)
main_module = importlib.util.module_from_spec(spec)
# We need to ensure relative imports in main.py work.
# main.py uses 'from core.config ...' which works if PYTHONPATH=.
# But 'cmd.api.main' is not in sys.modules properly if we just load it.
# We might need to add it to sys.modules.
sys.modules["cmd.api.main"] = main_module
spec.loader.exec_module(main_module)
create_app = main_module.create_app


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


def test_transcribe_endpoint_success(client):
    mock_result = {
        "text": "Hello World",
        "duration": 1.5,
        "download_duration": 0.5,
        "file_size_mb": 1.0,
        "model": "small",
    }

    with patch(
        "internal.api.routes.transcribe_routes.transcribe_service"
    ) as mock_service:
        mock_service.transcribe_from_url = AsyncMock(return_value=mock_result)

        response = client.post(
            "/transcribe", json={"audio_url": "http://example.com/audio.mp3"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["error_code"] == 0
        assert data["data"] == mock_result


def test_transcribe_endpoint_too_large(client):
    with patch(
        "internal.api.routes.transcribe_routes.transcribe_service"
    ) as mock_service:
        mock_service.transcribe_from_url = AsyncMock(
            side_effect=ValueError("File too large")
        )

        response = client.post(
            "/transcribe", json={"audio_url": "http://example.com/large.mp3"}
        )

        if response.status_code != 413:
            print(f"Response: {response.json()}")

        assert response.status_code == 413
        assert "too large" in response.json()["detail"]


def test_transcribe_endpoint_error(client):
    with patch(
        "internal.api.routes.transcribe_routes.transcribe_service"
    ) as mock_service:
        mock_service.transcribe_from_url = AsyncMock(
            side_effect=Exception("Internal error")
        )

        response = client.post(
            "/transcribe", json={"audio_url": "http://example.com/error.mp3"}
        )

        if response.status_code != 500:
            print(f"Response: {response.json()}")

        assert response.status_code == 500
        assert "Internal server error" in response.json()["detail"]
