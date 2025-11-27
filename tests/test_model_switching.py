"""
Integration tests for dynamic model switching.
Tests that model can be switched via WHISPER_MODEL_SIZE environment variable.
"""

import pytest
import os
from unittest.mock import patch, MagicMock

from adapters.whisper.library_adapter import (
    WhisperLibraryAdapter,
    MODEL_CONFIGS,
)


class TestModelSwitching:
    """Integration tests for dynamic model switching"""

    @patch("adapters.whisper.library_adapter.get_settings")
    @patch("adapters.whisper.library_adapter.ctypes.CDLL")
    @patch("pathlib.Path.exists")
    def test_switch_to_small_model(self, mock_exists, mock_cdll, mock_settings):
        """Test switching to small model via environment variable"""
        # Set environment variable
        os.environ["WHISPER_MODEL_SIZE"] = "small"

        mock_settings.return_value = MagicMock(
            whisper_model_size="small",
            whisper_artifacts_dir="."
        )
        mock_exists.return_value = True

        mock_lib = MagicMock()
        mock_lib.whisper_init_from_file.return_value = 12345
        mock_cdll.return_value = mock_lib

        adapter = WhisperLibraryAdapter()

        assert adapter.model_size == "small"
        assert adapter.config == MODEL_CONFIGS["small"]
        assert "whisper_small_xeon" in str(adapter.lib_dir)
        assert "ggml-small-q5_1.bin" in str(adapter.model_path)

    @patch("adapters.whisper.library_adapter.get_settings")
    @patch("adapters.whisper.library_adapter.ctypes.CDLL")
    @patch("pathlib.Path.exists")
    def test_switch_to_medium_model(self, mock_exists, mock_cdll, mock_settings):
        """Test switching to medium model via environment variable"""
        # Set environment variable
        os.environ["WHISPER_MODEL_SIZE"] = "medium"

        mock_settings.return_value = MagicMock(
            whisper_model_size="medium",
            whisper_artifacts_dir="."
        )
        mock_exists.return_value = True

        mock_lib = MagicMock()
        mock_lib.whisper_init_from_file.return_value = 12345
        mock_cdll.return_value = mock_lib

        adapter = WhisperLibraryAdapter()

        assert adapter.model_size == "medium"
        assert adapter.config == MODEL_CONFIGS["medium"]
        assert "whisper_medium_xeon" in str(adapter.lib_dir)
        assert "ggml-medium-q5_1.bin" in str(adapter.model_path)

    @patch("adapters.whisper.library_adapter.get_settings")
    @patch("adapters.whisper.library_adapter.ctypes.CDLL")
    @patch("pathlib.Path.exists")
    def test_model_config_matches_size(self, mock_exists, mock_cdll, mock_settings):
        """Test that model configuration matches selected size"""
        test_cases = [
            ("small", MODEL_CONFIGS["small"]),
            ("medium", MODEL_CONFIGS["medium"]),
        ]

        for model_size, expected_config in test_cases:
            mock_settings.return_value = MagicMock(
                whisper_model_size=model_size,
                whisper_artifacts_dir="."
            )
            mock_exists.return_value = True

            mock_lib = MagicMock()
            mock_lib.whisper_init_from_file.return_value = 12345
            mock_cdll.return_value = mock_lib

            adapter = WhisperLibraryAdapter(model_size=model_size)

            assert adapter.config == expected_config
            assert adapter.config["size_mb"] == expected_config["size_mb"]
            assert adapter.config["ram_mb"] == expected_config["ram_mb"]

    @patch("adapters.whisper.library_adapter.get_settings")
    def test_default_model_when_env_not_set(self, mock_settings):
        """Test that default model is used when WHISPER_MODEL_SIZE not set"""
        # Unset environment variable
        if "WHISPER_MODEL_SIZE" in os.environ:
            del os.environ["WHISPER_MODEL_SIZE"]

        mock_settings.return_value = MagicMock(
            whisper_model_size="small",  # Default from settings
            whisper_artifacts_dir="."
        )

        with patch.object(WhisperLibraryAdapter, '_load_libraries'):
            with patch.object(WhisperLibraryAdapter, '_initialize_context'):
                adapter = WhisperLibraryAdapter()
                assert adapter.model_size == "small"


class TestArtifactPaths:
    """Test artifact path resolution for different models"""

    @patch("adapters.whisper.library_adapter.get_settings")
    @patch("adapters.whisper.library_adapter.ctypes.CDLL")
    @patch("pathlib.Path.exists")
    def test_small_model_paths(self, mock_exists, mock_cdll, mock_settings):
        """Test that small model uses correct artifact paths"""
        mock_settings.return_value = MagicMock(
            whisper_model_size="small",
            whisper_artifacts_dir="/app"
        )
        mock_exists.return_value = True

        mock_lib = MagicMock()
        mock_lib.whisper_init_from_file.return_value = 12345
        mock_cdll.return_value = mock_lib

        adapter = WhisperLibraryAdapter(model_size="small")

        assert str(adapter.lib_dir).endswith("whisper_small_xeon")
        assert str(adapter.model_path).endswith("ggml-small-q5_1.bin")

    @patch("adapters.whisper.library_adapter.get_settings")
    @patch("adapters.whisper.library_adapter.ctypes.CDLL")
    @patch("pathlib.Path.exists")
    def test_medium_model_paths(self, mock_exists, mock_cdll, mock_settings):
        """Test that medium model uses correct artifact paths"""
        mock_settings.return_value = MagicMock(
            whisper_model_size="medium",
            whisper_artifacts_dir="/app"
        )
        mock_exists.return_value = True

        mock_lib = MagicMock()
        mock_lib.whisper_init_from_file.return_value = 12345
        mock_cdll.return_value = mock_lib

        adapter = WhisperLibraryAdapter(model_size="medium")

        assert str(adapter.lib_dir).endswith("whisper_medium_xeon")
        assert str(adapter.model_path).endswith("ggml-medium-q5_1.bin")
