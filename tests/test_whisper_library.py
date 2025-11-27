"""
Unit tests for WhisperLibraryAdapter
Tests library initialization and model loading.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from adapters.whisper.library_adapter import (
    WhisperLibraryAdapter,
    LibraryLoadError,
    ModelInitError,
    MODEL_CONFIGS,
    get_whisper_library_adapter,
)


class TestWhisperLibraryAdapter:
    """Test suite for WhisperLibraryAdapter"""

    def test_model_configs_exist(self):
        """Test that model configurations are defined"""
        assert "small" in MODEL_CONFIGS
        assert "medium" in MODEL_CONFIGS
        assert MODEL_CONFIGS["small"]["model"] == "ggml-small-q5_1.bin"
        assert MODEL_CONFIGS["medium"]["model"] == "ggml-medium-q5_1.bin"

    @patch("adapters.whisper.library_adapter.get_settings")
    def test_init_validates_model_size(self, mock_settings):
        """Test that initialization validates model size"""
        mock_settings.return_value = MagicMock(
            whisper_model_size="small",
            whisper_artifacts_dir="."
        )

        # Valid model size should not raise
        with patch.object(WhisperLibraryAdapter, '_load_libraries'):
            with patch.object(WhisperLibraryAdapter, '_initialize_context'):
                adapter = WhisperLibraryAdapter(model_size="small")
                assert adapter.model_size == "small"

    @patch("adapters.whisper.library_adapter.get_settings")
    def test_init_invalid_model_size(self, mock_settings):
        """Test that invalid model size raises ValueError"""
        mock_settings.return_value = MagicMock(
            whisper_model_size="invalid",
            whisper_artifacts_dir="."
        )

        with pytest.raises(ValueError, match="Unsupported model size"):
            WhisperLibraryAdapter(model_size="invalid")

    @patch("adapters.whisper.library_adapter.get_settings")
    @patch("adapters.whisper.library_adapter.ctypes.CDLL")
    @patch("pathlib.Path.exists")
    def test_load_libraries_success(self, mock_exists, mock_cdll, mock_settings):
        """Test successful library loading"""
        mock_settings.return_value = MagicMock(
            whisper_model_size="small",
            whisper_artifacts_dir="."
        )
        mock_exists.return_value = True
        mock_cdll.return_value = MagicMock()

        with patch.object(WhisperLibraryAdapter, '_initialize_context'):
            adapter = WhisperLibraryAdapter(model_size="small")
            assert adapter.lib is not None

    @patch("adapters.whisper.library_adapter.get_settings")
    @patch("pathlib.Path.exists")
    def test_load_libraries_missing_directory(self, mock_exists, mock_settings):
        """Test library loading fails when directory missing"""
        mock_settings.return_value = MagicMock(
            whisper_model_size="small",
            whisper_artifacts_dir="."
        )
        mock_exists.return_value = False

        with pytest.raises(LibraryLoadError, match="Library directory not found"):
            WhisperLibraryAdapter(model_size="small")

    @patch("adapters.whisper.library_adapter.get_settings")
    @patch("adapters.whisper.library_adapter.ctypes.CDLL")
    @patch("pathlib.Path.exists")
    def test_initialize_context_success(self, mock_exists, mock_cdll, mock_settings):
        """Test successful context initialization"""
        mock_settings.return_value = MagicMock(
            whisper_model_size="small",
            whisper_artifacts_dir="."
        )
        mock_exists.return_value = True

        # Mock library and context
        mock_lib = MagicMock()
        mock_lib.whisper_init_from_file.return_value = 12345  # Non-null pointer
        mock_cdll.return_value = mock_lib

        adapter = WhisperLibraryAdapter(model_size="small")
        assert adapter.ctx == 12345

    @patch("adapters.whisper.library_adapter.get_settings")
    @patch("adapters.whisper.library_adapter.ctypes.CDLL")
    @patch("pathlib.Path.exists")
    def test_initialize_context_null_context(self, mock_exists, mock_cdll, mock_settings):
        """Test context initialization fails when context is NULL"""
        mock_settings.return_value = MagicMock(
            whisper_model_size="small",
            whisper_artifacts_dir="."
        )
        mock_exists.return_value = True

        # Mock library returning NULL context
        mock_lib = MagicMock()
        mock_lib.whisper_init_from_file.return_value = None
        mock_cdll.return_value = mock_lib

        with pytest.raises(ModelInitError, match="whisper_init_from_file.*returned NULL"):
            WhisperLibraryAdapter(model_size="small")

    @patch("adapters.whisper.library_adapter.get_settings")
    @patch("adapters.whisper.library_adapter.ctypes.CDLL")
    @patch("pathlib.Path.exists")
    def test_transcribe_missing_audio_file(self, mock_exists, mock_cdll, mock_settings):
        """Test transcription fails when audio file missing"""
        mock_settings.return_value = MagicMock(
            whisper_model_size="small",
            whisper_artifacts_dir="."
        )

        def exists_side_effect(path=None):
            # Return True for library dir/model, False for audio file
            if "whisper_" in str(path) or "ggml-" in str(path):
                return True
            return False

        mock_exists.side_effect = exists_side_effect

        mock_lib = MagicMock()
        mock_lib.whisper_init_from_file.return_value = 12345
        mock_cdll.return_value = mock_lib

        adapter = WhisperLibraryAdapter(model_size="small")

        with patch("os.path.exists", return_value=False):
            from adapters.whisper.library_adapter import TranscriptionError
            with pytest.raises(TranscriptionError, match="Audio file not found"):
                adapter.transcribe("/nonexistent/audio.wav")

    @patch("adapters.whisper.library_adapter._whisper_library_adapter", None)
    @patch("adapters.whisper.library_adapter.WhisperLibraryAdapter")
    def test_get_whisper_library_adapter_singleton(self, mock_adapter_class):
        """Test that get_whisper_library_adapter returns singleton"""
        mock_instance = MagicMock()
        mock_adapter_class.return_value = mock_instance

        # First call creates instance
        adapter1 = get_whisper_library_adapter()
        assert adapter1 == mock_instance
        assert mock_adapter_class.call_count == 1

        # Second call returns same instance
        adapter2 = get_whisper_library_adapter()
        assert adapter2 == mock_instance
        assert mock_adapter_class.call_count == 1  # Should not create new instance


class TestModelConfigs:
    """Test suite for model configuration"""

    def test_small_model_config(self):
        """Test small model configuration"""
        config = MODEL_CONFIGS["small"]
        assert config["dir"] == "whisper_small_xeon"
        assert config["model"] == "ggml-small-q5_1.bin"
        assert config["size_mb"] == 181
        assert config["ram_mb"] == 500

    def test_medium_model_config(self):
        """Test medium model configuration"""
        config = MODEL_CONFIGS["medium"]
        assert config["dir"] == "whisper_medium_xeon"
        assert config["model"] == "ggml-medium-q5_1.bin"
        assert config["size_mb"] == 1500
        assert config["ram_mb"] == 2000
