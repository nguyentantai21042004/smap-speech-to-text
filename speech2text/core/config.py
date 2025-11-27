"""
Configuration management using Pydantic Settings.
Follows Single Responsibility Principle - only handles configuration.
"""

from functools import lru_cache
from typing import Optional
from pathlib import Path

from pydantic import Field  # type: ignore
from pydantic_settings import BaseSettings, SettingsConfigDict  # type: ignore


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        protected_namespaces=(),  # Allow 'model_*' fields (e.g., model_used)
    )

    # Application
    app_name: str = Field(default="SMAP Speech-to-Text", alias="APP_NAME")
    app_version: str = Field(default="1.0.0", alias="APP_VERSION")
    environment: str = Field(default="development", alias="ENVIRONMENT")
    debug: bool = Field(default=True, alias="DEBUG")

    # API Service
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    api_reload: bool = Field(default=True, alias="API_RELOAD")
    api_workers: int = Field(default=1, alias="API_WORKERS")
    max_upload_size_mb: int = Field(default=500, alias="MAX_UPLOAD_SIZE_MB")

    # Storage (temporary processing)
    temp_dir: str = Field(default="/tmp/stt_processing", alias="TEMP_DIR")

    # Whisper Settings
    whisper_executable: str = Field(
        default="./whisper/bin/whisper-cli", alias="WHISPER_EXECUTABLE"
    )
    whisper_models_dir: str = Field(
        default="./whisper/models", alias="WHISPER_MODELS_DIR"
    )
    default_whisper_model: str = Field(default="medium", alias="DEFAULT_WHISPER_MODEL")
    whisper_language: str = Field(default="vi", alias="WHISPER_LANGUAGE")
    whisper_model: str = Field(default="small", alias="WHISPER_MODEL")

    # Whisper Quality/Accuracy Flags
    whisper_max_context: int = Field(
        default=0, alias="WHISPER_MAX_CONTEXT"
    )  # 0 = disable context reuse
    whisper_no_speech_thold: float = Field(
        default=0.7, alias="WHISPER_NO_SPEECH_THOLD"
    )  # Higher = less false positives
    whisper_entropy_thold: float = Field(
        default=2.6, alias="WHISPER_ENTROPY_THOLD"
    )  # Higher = less hallucination
    whisper_logprob_thold: float = Field(
        default=-0.8, alias="WHISPER_LOGPROB_THOLD"
    )  # Higher = filter low quality
    whisper_no_fallback: bool = Field(
        default=True, alias="WHISPER_NO_FALLBACK"
    )  # Disable temperature fallback
    whisper_suppress_regex: Optional[str] = Field(
        default=None, alias="WHISPER_SUPPRESS_REGEX"
    )  # Suppress specific tokens

    # Processing Settings
    chunk_timeout: int = Field(default=300, alias="CHUNK_TIMEOUT")

    # Logging
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_file: str = Field(default="logs/stt.log", alias="LOG_FILE")


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    Using lru_cache to ensure single instance (Singleton pattern).
    """
    return Settings()
