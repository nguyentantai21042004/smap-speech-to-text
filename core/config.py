"""
Configuration management using Pydantic Settings.
Follows Single Responsibility Principle - only handles configuration.
"""

from functools import lru_cache
from typing import Optional
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


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

    # MongoDB Settings (Primary Database)
    mongodb_url: str = Field(default="mongodb://localhost:27017", alias="MONGODB_URL")
    mongodb_database: str = Field(default="stt_system", alias="MONGODB_DATABASE")
    mongodb_root_user: Optional[str] = Field(default=None, alias="MONGODB_ROOT_USER")
    mongodb_root_password: Optional[str] = Field(default=None, alias="MONGODB_ROOT_PASSWORD")
    mongodb_max_pool_size: int = Field(default=10, alias="MONGODB_MAX_POOL_SIZE")
    mongodb_min_pool_size: int = Field(default=1, alias="MONGODB_MIN_POOL_SIZE")

    # RabbitMQ Settings (Message Queue)
    rabbitmq_host: str = Field(default="localhost", alias="RABBITMQ_HOST")
    rabbitmq_port: int = Field(default=5672, alias="RABBITMQ_PORT")
    rabbitmq_user: str = Field(default="guest", alias="RABBITMQ_USER")
    rabbitmq_password: str = Field(default="guest", alias="RABBITMQ_PASSWORD")
    rabbitmq_vhost: str = Field(default="/", alias="RABBITMQ_VHOST")
    rabbitmq_queue_name: str = Field(
        default="stt_jobs_queue", alias="RABBITMQ_QUEUE_NAME"
    )
    rabbitmq_exchange_name: str = Field(
        default="stt_exchange", alias="RABBITMQ_EXCHANGE_NAME"
    )
    rabbitmq_routing_key: str = Field(default="stt.job", alias="RABBITMQ_ROUTING_KEY")

    # MinIO (Object Storage)
    minio_endpoint: str = Field(default="localhost:9000", alias="MINIO_ENDPOINT")
    minio_access_key: str = Field(default="minioadmin", alias="MINIO_ACCESS_KEY")
    minio_secret_key: str = Field(default="minioadmin", alias="MINIO_SECRET_KEY")
    minio_bucket_name: str = Field(default="stt-audio-files", alias="MINIO_BUCKET")
    minio_use_ssl: bool = Field(default=False, alias="MINIO_USE_SSL")

    # Storage (temporary processing)
    temp_dir: str = Field(default="/tmp/stt_processing", alias="TEMP_DIR")

    # Whisper Settings
    whisper_executable: str = Field(
        default="./whisper/whisper.cpp/main", alias="WHISPER_EXECUTABLE"
    )
    whisper_models_dir: str = Field(
        default="./whisper/whisper.cpp/models", alias="WHISPER_MODELS_DIR"
    )

    # Chunking Settings
    chunk_duration: int = Field(default=30, alias="CHUNK_DURATION")
    silence_threshold: int = Field(default=-40, alias="SILENCE_THRESHOLD")
    min_silence_duration: float = Field(default=1.0, alias="MIN_SILENCE_DURATION")

    # Processing Settings
    max_retries: int = Field(default=3, alias="MAX_RETRIES")
    job_timeout: int = Field(default=3600, alias="JOB_TIMEOUT")
    chunk_timeout: int = Field(default=300, alias="CHUNK_TIMEOUT")
    max_concurrent_jobs: int = Field(default=1, alias="MAX_CONCURRENT_JOBS")

    # Logging
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_file: str = Field(default="logs/stt.log", alias="LOG_FILE")

    # Scheduler
    scheduler_timezone: str = Field(
        default="Asia/Ho_Chi_Minh", alias="SCHEDULER_TIMEZONE"
    )

    @property
    def rabbitmq_url(self) -> str:
        """Construct RabbitMQ connection URL."""
        return (
            f"amqp://{self.rabbitmq_user}:{self.rabbitmq_password}"
            f"@{self.rabbitmq_host}:{self.rabbitmq_port}/{self.rabbitmq_vhost}"
        )

    @property
    def mongodb_connection_url(self) -> str:
        """Construct MongoDB connection URL with authentication if credentials provided."""
        # If MONGODB_URL already contains credentials (@), use it as-is
        if "@" in self.mongodb_url:
            return self.mongodb_url
        
        # If MONGODB_ROOT_USER and MONGODB_ROOT_PASSWORD are provided, build auth URL
        if self.mongodb_root_user and self.mongodb_root_password:
            # Extract host and port from existing URL
            # Remove "mongodb://" prefix
            url_without_protocol = self.mongodb_url.replace("mongodb://", "")
            
            # Split by "/" to separate host:port and database path
            url_parts = url_without_protocol.split("/")
            host_port = url_parts[0]
            
            # Build authenticated URL
            auth_url = f"mongodb://{self.mongodb_root_user}:{self.mongodb_root_password}@{host_port}"
            
            # Add database to path (use mongodb_database from config)
            # This is required for authentication to work
            if self.mongodb_database:
                auth_url += f"/{self.mongodb_database}"
            
            # Add authSource parameter (required for MongoDB authentication)
            # Use the same database name as authSource
            if self.mongodb_database:
                auth_url += f"?authSource={self.mongodb_database}"
            
            return auth_url
        
        # Otherwise, use original MONGODB_URL
        return self.mongodb_url


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    Using lru_cache to ensure single instance (Singleton pattern).
    """
    return Settings()
