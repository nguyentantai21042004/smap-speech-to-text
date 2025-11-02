"""
FastAPI Service - Main entry point for SMAP Speech-to-Text API.
Implements clean separation of concerns with comprehensive logging and error handling:
- Routes are separated into modules
- MongoDB for data persistence
- RabbitMQ for job processing
- Comprehensive logging for all operations
"""

import warnings
from contextlib import asynccontextmanager

# Suppress expected warnings at startup
warnings.filterwarnings("ignore", message=".*protected namespace.*", category=UserWarning)
warnings.filterwarnings("ignore", message=".*ffmpeg.*", category=RuntimeWarning)
warnings.filterwarnings("ignore", message=".*avconv.*", category=RuntimeWarning)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import get_settings
from core.logger import logger
from core.database import get_database
from core.messaging import get_queue_manager
from internal.api.routes.task_routes import router as task_router
from internal.api.routes.health_routes import create_health_routes
from internal.api.routes.keyword_routes import create_keyword_routes
from internal.api.routes.sentiment_routes import create_sentiment_routes
from services import KeywordService, SentimentService


# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifespan - startup and shutdown.
    Connects to MongoDB and RabbitMQ on startup with comprehensive logging.
    """
    try:
        settings = get_settings()
        logger.info(
            f"========== Starting {settings.app_name} v{settings.app_version} API service =========="
        )
        logger.info(f"Environment: {settings.environment}")
        logger.info(f"Debug mode: {settings.debug}")
        logger.info(f"API: {settings.api_host}:{settings.api_port}")

        # Initialize MongoDB connection
        try:
            logger.info("Initializing MongoDB connection...")
            db = await get_database()
            await db.connect()
            logger.info("MongoDB connected successfully")

            # Create indexes (optional - will not fail if auth is missing)
            await db.create_indexes()

            # Health check
            logger.info("Performing MongoDB health check...")
            db_healthy = await db.health_check()
            if db_healthy:
                logger.info("MongoDB health check passed")
            else:
                logger.warning("MongoDB health check failed")

        except Exception as e:
            logger.error(f"Failed to initialize MongoDB: {e}")
            logger.exception("MongoDB initialization error details:")
            raise

        # Initialize RabbitMQ connection
        try:
            logger.info("Initializing RabbitMQ connection...")
            queue_manager = get_queue_manager()

            # Connect to RabbitMQ
            await queue_manager.connect()
            logger.info("RabbitMQ connected successfully")

            # Health check
            logger.info("Performing RabbitMQ health check...")
            rabbitmq_healthy = queue_manager.health_check()
            if rabbitmq_healthy:
                logger.info("RabbitMQ health check passed")
            else:
                logger.warning("RabbitMQ health check failed")

            # Store queue manager in app state
            app.state.queue_manager = queue_manager
            logger.info("RabbitMQ initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize RabbitMQ: {e}")
            logger.exception("RabbitMQ initialization error details:")
            raise

        logger.info(
            f"========== {settings.app_name} API service started successfully =========="
        )

        yield

        # Shutdown sequence
        logger.info("========== Shutting down API service ==========")

        # Disconnect from RabbitMQ
        try:
            if hasattr(app.state, "queue_manager"):
                logger.info("Disconnecting from RabbitMQ...")
                await app.state.queue_manager.disconnect()
                logger.info("RabbitMQ disconnected successfully")
        except Exception as e:
            logger.error(f"Error disconnecting from RabbitMQ: {e}")
            logger.exception("RabbitMQ disconnect error details:")

        # Disconnect from MongoDB
        try:
            logger.info("Disconnecting from MongoDB...")
            db = await get_database()
            await db.disconnect()
            logger.info("MongoDB disconnected successfully")
        except Exception as e:
            logger.error(f"Error disconnecting from MongoDB: {e}")
            logger.exception("MongoDB disconnect error details:")

        logger.info("========== API service stopped successfully ==========")

    except Exception as e:
        logger.error(f"Fatal error in application lifespan: {e}")
        logger.exception("Lifespan error details:")
        raise


def create_app() -> FastAPI:
    """
    Factory function to create and configure the FastAPI application.
    Includes comprehensive logging and error handling.

    Returns:
        FastAPI: Configured application instance
    """
    try:
        logger.info("Creating FastAPI application...")
        settings = get_settings()

        # OpenAPI metadata
        description = """
## SMAP Speech-to-Text API

A production-ready Speech-to-Text service powered by Whisper.cpp with MongoDB and RabbitMQ.

### Key Features

* **Audio Upload** - Upload audio files for transcription (MP3, WAV, M4A, etc.)
* **Async Processing** - Queue-based processing with RabbitMQ for heavy workloads
* **Real-time Progress** - Track transcription progress with chunk-level status
* **Multi-language Support** - Support for Vietnamese, English, and other languages
* **Multiple Models** - Choose from Whisper models: tiny, base, small, medium, large
* **Result Storage** - Results stored in MongoDB with MinIO object storage
* **Health Monitoring** - System health checks for MongoDB and RabbitMQ

### Processing Flow

1. **Upload** - Upload audio file via `/api/v1/tasks/upload`
2. **Queue** - Job is queued in RabbitMQ for processing
3. **Process** - Worker chunks audio, transcribes each chunk, and merges results
4. **Retrieve** - Get results via `/api/v1/tasks/{job_id}/result`

### Supported Audio Formats

MP3, WAV, M4A, MP4, AAC, OGG, FLAC, WMA, WEBM, MKV, AVI, MOV

### Authentication

Currently no authentication required. Add authentication headers as needed for production deployment.
        """

        tags_metadata = [
            {
                "name": "STT Tasks",
                "description": "Speech-to-text task operations. Upload audio files, track transcription progress, and retrieve results. Supports asynchronous processing with real-time status updates.",
            },
            {
                "name": "Health",
                "description": "Health check endpoints for monitoring API status and dependencies (MongoDB, RabbitMQ).",
            },
            {
                "name": "Keywords",
                "description": "Keyword extraction from Vietnamese text using various algorithms (TF-IDF, TextRank, etc.).",
            },
            {
                "name": "Sentiment Analysis",
                "description": "Sentiment analysis for Vietnamese text with batch processing support.",
            },
        ]

        # Create FastAPI application
        logger.debug("Configuring FastAPI instance...")
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
        logger.debug("FastAPI instance configured")

        # Add CORS middleware
        logger.debug("Adding CORS middleware...")
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Configure appropriately for production
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        logger.debug("CORS middleware added")

        # Include all API routes
        logger.debug("Including API routes...")
        
        # Task routes (STT)
        app.include_router(task_router)
        logger.info("✅ Task routes registered")
        
        # Health routes (no prefix - uses root "/" and "/health")
        health_router = create_health_routes(app)
        app.include_router(health_router)
        logger.info("✅ Health routes registered")
        
        # Keyword routes
        keyword_service = KeywordService()
        keyword_router = create_keyword_routes(keyword_service)
        app.include_router(keyword_router)
        logger.info("✅ Keyword routes registered")
        
        # Sentiment routes
        sentiment_service = SentimentService()
        sentiment_router = create_sentiment_routes(sentiment_service)
        app.include_router(sentiment_router)
        logger.info("✅ Sentiment routes registered")

        logger.info("FastAPI application created successfully")
        return app

    except Exception as e:
        logger.error(f"Failed to create FastAPI application: {e}")
        logger.exception("Application creation error details:")
        raise


# Create application instance
try:
    logger.info("Initializing SMAP Speech-to-Text API...")
    app = create_app()
    logger.info("Application instance created successfully")
except Exception as e:
    logger.error(f"Failed to create application instance: {e}")
    logger.exception("Startup error details:")
    raise


# Run with: uvicorn cmd.api.main:app --host 0.0.0.0 --port 8000 --reload
if __name__ == "__main__":
    import uvicorn
    import sys
    import os

    try:
        settings = get_settings()

        logger.info("========== Starting Uvicorn Server ==========")
        logger.info(f"Host: {settings.api_host}")
        logger.info(f"Port: {settings.api_port}")
        logger.info(f"Reload: {settings.api_reload}")
        logger.info(f"Workers: {settings.api_workers}")

        # When using reload=True, uvicorn spawns subprocess which needs PYTHONPATH
        # Ensure project root is in PYTHONPATH for subprocess
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
        
        # Set PYTHONPATH environment variable for subprocess (uvicorn reload)
        current_pythonpath = os.environ.get('PYTHONPATH', '')
        if project_root not in current_pythonpath:
            new_pythonpath = f"{project_root}:{current_pythonpath}" if current_pythonpath else project_root
            os.environ['PYTHONPATH'] = new_pythonpath
        
        # Use string path when reload=True, app instance when reload=False
        if settings.api_reload:
            # For reload, uvicorn needs string path and will import it
            # PYTHONPATH is already set above for subprocess
            uvicorn.run(
                "cmd.api.main:app",
                host=settings.api_host,
                port=settings.api_port,
                reload=True,
                log_level="info" if settings.debug else "warning",
            )
        else:
            # For production, pass app instance directly
            uvicorn.run(
                app,
                host=settings.api_host,
                port=settings.api_port,
                reload=False,
                log_level="info" if settings.debug else "warning",
            )

    except Exception as e:
        logger.error(f"Failed to start Uvicorn server: {e}")
        logger.exception("Uvicorn startup error details:")
        raise
