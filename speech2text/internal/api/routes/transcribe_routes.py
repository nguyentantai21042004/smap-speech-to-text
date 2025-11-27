from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, HttpUrl
from services.transcription import TranscribeService
from internal.api.utils import success_response
from core.logger import logger

router = APIRouter()
# Initialize service once (singleton-like)
transcribe_service = TranscribeService()


class TranscribeRequest(BaseModel):
    audio_url: HttpUrl


@router.post("/transcribe", status_code=status.HTTP_200_OK)
async def transcribe(request: TranscribeRequest):
    """
    Transcribe audio from URL.
    """
    try:
        # Convert HttpUrl to string
        url_str = str(request.audio_url)
        result = await transcribe_service.transcribe_from_url(url_str)
        return success_response(data=result, message="Transcription successful")
    except ValueError as e:
        error_msg = str(e)
        if "too large" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=error_msg
            )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg)
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )
