"""
Configuration management using Pydantic Settings.
Follows Single Responsibility Principle - only handles configuration.
"""

from functools import lru_cache

from pydantic import Field  # type: ignore
from pydantic_settings import BaseSettings, SettingsConfigDict  # type: ignore


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        protected_namespaces=(),  # Allow 'model_*' fields
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

    # Whisper Library Settings (for direct C library integration)
    whisper_model_size: str = Field(default="small", alias="WHISPER_MODEL_SIZE")
    whisper_artifacts_dir: str = Field(default=".", alias="WHISPER_ARTIFACTS_DIR")
    whisper_language: str = Field(default="vi", alias="WHISPER_LANGUAGE")
    whisper_model: str = Field(default="small", alias="WHISPER_MODEL")

    # MinIO Configuration (for artifact download)
    minio_endpoint: str = Field(
        default="http://172.16.19.115:9000", alias="MINIO_ENDPOINT"
    )
    minio_access_key: str = Field(default="smap", alias="MINIO_ACCESS_KEY")
    minio_secret_key: str = Field(default="hcmut2025", alias="MINIO_SECRET_KEY")

    # Logging
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_file: str = Field(default="logs/stt.log", alias="LOG_FILE")

    # API Security
    internal_api_key: str = Field(
        default="smap-internal-key-changeme", alias="INTERNAL_API_KEY"
    )
    transcribe_timeout_seconds: int = Field(
        default=30, alias="TRANSCRIBE_TIMEOUT_SECONDS"
    )


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    Using lru_cache to ensure single instance (Singleton pattern).
    """
    return Settings()
