"""
Configuration management using Pydantic Settings.
Follows Single Responsibility Principle - only handles configuration.
"""

from functools import lru_cache
from typing import Optional

from pydantic import Field, MongoDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = Field(default="SMAP Keyword Extraction", alias="APP_NAME")
    app_version: str = Field(default="1.0.0", alias="APP_VERSION")
    environment: str = Field(default="development", alias="ENVIRONMENT")
    debug: bool = Field(default=True, alias="DEBUG")

    # API Service
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    api_reload: bool = Field(default=True, alias="API_RELOAD")

    # MongoDB
    mongodb_url: str = Field(
        default="mongodb://localhost:27017", alias="MONGODB_URL"
    )
    mongodb_database: str = Field(
        default="smap_keyword_extraction", alias="MONGODB_DATABASE"
    )
    mongodb_min_pool_size: int = Field(default=10, alias="MONGODB_MIN_POOL_SIZE")
    mongodb_max_pool_size: int = Field(default=100, alias="MONGODB_MAX_POOL_SIZE")

    # RabbitMQ
    rabbitmq_host: str = Field(default="localhost", alias="RABBITMQ_HOST")
    rabbitmq_port: int = Field(default=5672, alias="RABBITMQ_PORT")
    rabbitmq_user: str = Field(default="guest", alias="RABBITMQ_USER")
    rabbitmq_password: str = Field(default="guest", alias="RABBITMQ_PASSWORD")
    rabbitmq_vhost: str = Field(default="/", alias="RABBITMQ_VHOST")
    rabbitmq_queue_name: str = Field(
        default="keyword_extraction_queue", alias="RABBITMQ_QUEUE_NAME"
    )
    rabbitmq_exchange_name: str = Field(
        default="keyword_extraction_exchange", alias="RABBITMQ_EXCHANGE_NAME"
    )
    rabbitmq_routing_key: str = Field(
        default="keyword.extraction", alias="RABBITMQ_ROUTING_KEY"
    )

    # Scheduler
    scheduler_timezone: str = Field(default="Asia/Ho_Chi_Minh", alias="SCHEDULER_TIMEZONE")
    
    # VnCoreNLP Service
    vncorenlp_url: str = Field(default="http://localhost:9000", alias="VNCORENLP_URL")
    
    # ML Models - PhoBERT Sentiment
    phobert_model_path: str = Field(
        default="artifacts/onnx/phobert_sentiment.onnx",
        alias="PHOBERT_MODEL_PATH"
    )
    phobert_tokenizer_path: str = Field(
        default="artifacts/tokenizer",
        alias="PHOBERT_TOKENIZER_PATH"
    )

    @property
    def rabbitmq_url(self) -> str:
        """Construct RabbitMQ connection URL."""
        return (
            f"amqp://{self.rabbitmq_user}:{self.rabbitmq_password}"
            f"@{self.rabbitmq_host}:{self.rabbitmq_port}/{self.rabbitmq_vhost}"
        )


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    Using lru_cache to ensure single instance (Singleton pattern).
    """
    return Settings()

