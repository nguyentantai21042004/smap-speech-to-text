"""
Unit tests for audio chunking functionality.
"""

import os
import tempfile
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from adapters.whisper.library_adapter import WhisperLibraryAdapter
from core.config import get_settings


class TestChunking:
    """Tests for chunking functionality"""

    def test_get_audio_duration_with_valid_file(self, mocker):
        """Test duration detection with valid audio file"""
        # Mock subprocess to return valid ffprobe output
        mock_result = Mock()
        mock_result.stdout = '{"format": {"duration": "120.5"}}'
        mock_result.returncode = 0

        mocker.patch('subprocess.run', return_value=mock_result)

        # Create adapter (will fail to init, but we only need the method)
        with patch.object(WhisperLibraryAdapter, '__init__', lambda x, model_size=None: None):
            adapter = WhisperLibraryAdapter()
            duration = adapter._get_audio_duration("/fake/path.mp3")

            assert duration == 120.5

    def test_get_audio_duration_with_invalid_file(self, mocker):
        """Test duration detection with invalid audio file"""
        from core.errors import TranscriptionError

        # Mock subprocess to raise error
        mock_result = Mock()
        mock_result.stderr = "Invalid audio file"

        mocker.patch('subprocess.run', side_effect=Exception("ffprobe failed"))

        with patch.object(WhisperLibraryAdapter, '__init__', lambda x, model_size=None: None):
            adapter = WhisperLibraryAdapter()

            with pytest.raises(TranscriptionError):
                adapter._get_audio_duration("/fake/invalid.mp3")

    def test_split_audio_calculates_chunks_correctly(self, mocker):
        """Test that chunk boundaries are calculated correctly"""
        # Mock subprocess for ffmpeg
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stderr = ""

        mocker.patch('subprocess.run', return_value=mock_result)

        with patch.object(WhisperLibraryAdapter, '__init__', lambda x, model_size=None: None):
            adapter = WhisperLibraryAdapter()

            # Test with 90 seconds, 30s chunks, 1s overlap
            # Expected chunks: (0-30), (29-59), (58-88), (87-90)
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                temp_path = f.name

            try:
                chunk_files = adapter._split_audio(temp_path, duration=90.0, chunk_duration=30, overlap=1)

                # Should create 4 chunks
                assert len(chunk_files) == 4

                # Verify ffmpeg was called 4 times
                assert mocker.patch('subprocess.run').call_count >= 4

            finally:
                if os.path.exists(temp_path):
                    os.remove(temp_path)

    def test_split_audio_short_file_no_split(self, mocker):
        """Test that short audio (< chunk_duration) creates only 1 chunk"""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stderr = ""

        mocker.patch('subprocess.run', return_value=mock_result)

        with patch.object(WhisperLibraryAdapter, '__init__', lambda x, model_size=None: None):
            adapter = WhisperLibraryAdapter()

            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                temp_path = f.name

            try:
                chunk_files = adapter._split_audio(temp_path, duration=20.0, chunk_duration=30, overlap=1)

                # Should create 1 chunk
                assert len(chunk_files) == 1

            finally:
                if os.path.exists(temp_path):
                    os.remove(temp_path)

    def test_merge_chunks_basic(self):
        """Test basic chunk merging"""
        with patch.object(WhisperLibraryAdapter, '__init__', lambda x, model_size=None: None):
            adapter = WhisperLibraryAdapter()

            chunk_texts = ["Hello world", "this is a", "test"]
            merged = adapter._merge_chunks(chunk_texts)

            assert merged == "Hello world this is a test"

    def test_merge_chunks_with_empty_strings(self):
        """Test merging chunks with empty strings"""
        with patch.object(WhisperLibraryAdapter, '__init__', lambda x, model_size=None: None):
            adapter = WhisperLibraryAdapter()

            chunk_texts = ["Hello", "", "world", "   ", "test"]
            merged = adapter._merge_chunks(chunk_texts)

            assert merged == "Hello world test"

    def test_merge_chunks_with_whitespace(self):
        """Test merging chunks with extra whitespace"""
        with patch.object(WhisperLibraryAdapter, '__init__', lambda x, model_size=None: None):
            adapter = WhisperLibraryAdapter()

            chunk_texts = ["  Hello  ", "  world  "]
            merged = adapter._merge_chunks(chunk_texts)

            assert merged == "Hello world"

    def test_chunking_configuration(self):
        """Test that chunking configuration is properly loaded"""
        settings = get_settings()

        assert hasattr(settings, 'whisper_chunk_enabled')
        assert hasattr(settings, 'whisper_chunk_duration')
        assert hasattr(settings, 'whisper_chunk_overlap')

        # Check default values
        assert settings.whisper_chunk_duration == 30
        assert settings.whisper_chunk_overlap == 1

    @patch.object(WhisperLibraryAdapter, '_get_audio_duration')
    @patch.object(WhisperLibraryAdapter, '_transcribe_direct')
    @patch.object(WhisperLibraryAdapter, '_transcribe_chunked')
    def test_transcribe_uses_direct_for_short_audio(self, mock_chunked, mock_direct, mock_duration):
        """Test that short audio uses direct transcription"""
        mock_duration.return_value = 25.0
        mock_direct.return_value = "Test transcription"

        with patch.object(WhisperLibraryAdapter, '__init__', lambda x, model_size=None: None):
            adapter = WhisperLibraryAdapter()
            adapter.ctx = MagicMock()  # Mock context
            adapter.lib = MagicMock()  # Mock library

            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                temp_path = f.name

            try:
                result = adapter.transcribe(temp_path, language="en")

                # Should use direct transcription
                mock_direct.assert_called_once()
                mock_chunked.assert_not_called()

                assert result == "Test transcription"

            finally:
                if os.path.exists(temp_path):
                    os.remove(temp_path)

    @patch.object(WhisperLibraryAdapter, '_get_audio_duration')
    @patch.object(WhisperLibraryAdapter, '_transcribe_direct')
    @patch.object(WhisperLibraryAdapter, '_transcribe_chunked')
    def test_transcribe_uses_chunked_for_long_audio(self, mock_chunked, mock_direct, mock_duration):
        """Test that long audio uses chunked transcription"""
        mock_duration.return_value = 120.0
        mock_chunked.return_value = "Long transcription"

        with patch.object(WhisperLibraryAdapter, '__init__', lambda x, model_size=None: None):
            adapter = WhisperLibraryAdapter()
            adapter.ctx = MagicMock()  # Mock context
            adapter.lib = MagicMock()  # Mock library

            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                temp_path = f.name

            try:
                result = adapter.transcribe(temp_path, language="en")

                # Should use chunked transcription
                mock_chunked.assert_called_once()
                mock_direct.assert_not_called()

                assert result == "Long transcription"

            finally:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
