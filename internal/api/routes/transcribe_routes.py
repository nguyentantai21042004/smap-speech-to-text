from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, HttpUrl, Field
from services.transcription import TranscribeService
from internal.api.utils import success_response, error_response
from internal.api.dependencies.auth import verify_internal_api_key
from core.logger import logger
from typing import Optional
import asyncio

router = APIRouter()
# Initialize service once (singleton-like)
transcribe_service = TranscribeService()


class TranscribeRequest(BaseModel):
    """Request model for transcription from presigned URL."""
    media_url: HttpUrl = Field(
        ..., description="Presigned URL to audio/video file (e.g., MinIO)"
    )
    language: Optional[str] = Field(
        default="vi", description="Language hint for transcription (e.g., 'vi', 'en')"
    )


class TranscribeResponse(BaseModel):
    """Response model for transcription result."""
    status: str = Field(..., description="Status of transcription (success, timeout, error)")
    transcription: str = Field(..., description="Transcribed text")
    duration: float = Field(..., description="Audio duration in seconds")
    confidence: float = Field(..., description="Confidence score (0.0-1.0)")
    processing_time: float = Field(..., description="Processing time in seconds")


@router.post(
    "/transcribe",
    status_code=status.HTTP_200_OK,
    response_model=TranscribeResponse,
    tags=["Transcription"],
    summary="Transcribe audio from presigned URL",
    description="""
    Transcribe audio from a presigned URL (e.g., MinIO).
    
    **Authentication**: Requires `X-API-Key` header with internal API key.
    
    **Flow**:
    1. Download audio from `media_url` (streaming, not stored permanently)
    2. Optional: Extract audio from video using ffmpeg if needed
    3. Transcribe using Whisper backend with timeout protection
    4. Return transcription metadata
    
    **Timeout**: Processing will abort after configured timeout (default 30s).
    """,
)
async def transcribe(
    request: TranscribeRequest,
    api_key: str = Depends(verify_internal_api_key),
):
    """
    Transcribe audio from presigned URL with authentication and timeout.
    """
    try:
        logger.info(f"Transcription request from authenticated client for language={request.language}")
        
        # Convert HttpUrl to string
        url_str = str(request.media_url)
        
        # Call transcription service with timeout
        result = await transcribe_service.transcribe_from_url(
            audio_url=url_str,
            language=request.language,
        )
        
        # Map service result to response schema
        return TranscribeResponse(
            status="success",
            transcription=result["text"],
            duration=result.get("audio_duration", 0.0),
            confidence=result.get("confidence", 0.98),  # Placeholder until we extract from whisper
            processing_time=result["duration"],
        )
        
    except asyncio.TimeoutError:
        logger.error("Transcription timeout exceeded")
        return TranscribeResponse(
            status="timeout",
            transcription="",
            duration=0.0,
            confidence=0.0,
            processing_time=0.0,
        )
    except ValueError as e:
        error_msg = str(e)
        logger.error(f"Validation error: {error_msg}")
        if "too large" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=error_msg
            )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg)
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        logger.exception("Exception details:")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        )
