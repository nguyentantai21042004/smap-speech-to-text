"""
FastAPI Service - Main entry point (Refactored).
Implements clean separation of concerns:
- Routes are separated into modules
- Schemas are separated into dedicated files
- Only initialization logic remains in this file
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core import DatabaseManager, MessageBroker, get_settings, logger
from services import KeywordService, TaskService, SentimentService
from internal.api.routes import create_keyword_routes, create_task_routes, create_health_routes, create_sentiment_routes


# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifespan - startup and shutdown.
    Connects to database and message broker on startup.
    """
    settings = get_settings()
    logger.info(f"Starting {settings.app_name} API service...")

    # Connect to database
    try:
        await DatabaseManager.connect()
        logger.info("Database connected")
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        raise

    # Connect to message broker
    try:
        message_broker = MessageBroker()
        await message_broker.connect()
        app.state.message_broker = message_broker
        logger.info("Message broker connected")
    except Exception as e:
        logger.error(f"Failed to connect to message broker: {e}")
        raise

    logger.info("API service started successfully")

    yield

    # Shutdown
    logger.info("Shutting down API service...")

    # Disconnect from message broker
    try:
        if hasattr(app.state, "message_broker"):
            await app.state.message_broker.disconnect()
        logger.info("Message broker disconnected")
    except Exception as e:
        logger.error(f"Error disconnecting message broker: {e}")

    # Disconnect from database
    try:
        await DatabaseManager.disconnect()
        logger.info("Database disconnected")
    except Exception as e:
        logger.error(f"Error disconnecting database: {e}")

    logger.info("API service stopped")


def create_app() -> FastAPI:
    """
    Factory function to create and configure the FastAPI application.

    Returns:
        FastAPI: Configured application instance
    """
    settings = get_settings()

    # OpenAPI metadata
    description = """
## SMAP AI - NLP Service API

A production-ready microservices API for Vietnamese NLP tasks including keyword extraction and sentiment analysis.

### Key Features

* **Keyword Extraction** - Extract keywords from Vietnamese text using multiple methods
* **Sentiment Analysis** - Endpoint available; model not bundled in this source
* **Async Processing** - Queue-based processing for heavy workloads via RabbitMQ
* **Task Management** - Track and monitor asynchronous job execution
* **Health Monitoring** - System health checks for database and message broker

### Processing Modes

- **Synchronous** - Immediate response with results (recommended for small requests)
- **Asynchronous** - Queue-based processing with task tracking (recommended for batch operations)

### Authentication

Currently no authentication required. Add authentication headers as needed for production deployment.
    """

    tags_metadata = [
        {
            "name": "Health",
            "description": "Service health and status monitoring endpoints. Check API availability and dependencies status.",
        },
        {
            "name": "Keywords",
            "description": "Keyword extraction operations. Extract meaningful keywords from Vietnamese text using various algorithms. Supports both synchronous and asynchronous processing modes with caching.",
        },
        {
            "name": "Tasks",
            "description": "Task management for asynchronous operations. Create, retrieve, and monitor long-running background jobs. Track task status from pending → processing → completed/failed.",
        },
        {
            "name": "Sentiment Analysis",
            "description": "Sentiment endpoints are present for compatibility, but no model is bundled in this repository.",
        },
    ]

    # Create FastAPI application
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=description,
        lifespan=lifespan,
        openapi_tags=tags_metadata,
        contact={
            "name": "SMAP AI Team",
            "email": "support@smap.ai",
        },
        license_info={
            "name": "MIT License",
            "url": "https://opensource.org/licenses/MIT",
        },
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Initialize services (Dependency Injection)
    keyword_service = KeywordService()
    task_service = TaskService()
    sentiment_service = SentimentService()

    # Create and include routers
    keyword_router = create_keyword_routes(keyword_service)
    task_router = create_task_routes(task_service)
    sentiment_router = create_sentiment_routes(sentiment_service)
    health_router = create_health_routes(app)

    app.include_router(keyword_router)
    app.include_router(task_router)
    app.include_router(sentiment_router)
    app.include_router(health_router)

    return app


# Create application instance
app = create_app()


# Run with: uvicorn main:app --host 0.0.0.0 --port 8000 --reload
if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
    )

