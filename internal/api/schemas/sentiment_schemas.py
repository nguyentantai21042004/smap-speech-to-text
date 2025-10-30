"""
Sentiment Analysis Schemas.
Request and Response models for sentiment endpoints.
"""

from pydantic import BaseModel, Field
from typing import Dict, Optional, List


class SentimentRequest(BaseModel):
    """Request schema for sentiment analysis."""
    
    text: str = Field(..., description="Text to analyze", min_length=1, max_length=5000)
    
    class Config:
        json_schema_extra = {
            "example": {
                "text": "Sản phẩm này rất tuyệt vời, tôi rất hài lòng!"
            }
        }


class BatchSentimentRequest(BaseModel):
    """Request schema for batch sentiment analysis."""
    
    texts: List[str] = Field(..., description="List of texts to analyze", min_items=1, max_items=100)
    
    class Config:
        json_schema_extra = {
            "example": {
                "texts": [
                    "Sản phẩm này rất tốt!",
                    "Không hài lòng với dịch vụ.",
                    "Bình thường, không có gì đặc biệt."
                ]
            }
        }


class SentimentResult(BaseModel):
    """Sentiment analysis result data."""
    
    text: str = Field(..., description="Original input text")
    sentiment: str = Field(..., description="Predicted sentiment label")
    confidence: float = Field(..., description="Confidence score", ge=0, le=1)
    probabilities: Dict[str, float] = Field(..., description="Probability distribution over all labels")
    segmented_text: Optional[str] = Field(None, description="Segmented text (if segmentation enabled)")


class SentimentResponse(BaseModel):
    """Response schema for sentiment analysis."""
    
    success: bool = Field(..., description="Whether the request succeeded")
    data: Optional[SentimentResult] = Field(None, description="Sentiment analysis result")
    error: Optional[str] = Field(None, description="Error message if failed")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": {
                    "text": "Sản phẩm này rất tuyệt vời!",
                    "sentiment": "Positive",
                    "confidence": 0.95,
                    "probabilities": {
                        "Negative": 0.02,
                        "Neutral": 0.03,
                        "Positive": 0.95
                    },
                    "segmented_text": "Sản_phẩm này rất tuyệt_vời !"
                },
                "error": None
            }
        }


class BatchSentimentResponse(BaseModel):
    """Response schema for batch sentiment analysis."""
    
    success: bool = Field(..., description="Whether the request succeeded")
    data: Optional[List[SentimentResult]] = Field(None, description="List of sentiment results")
    error: Optional[str] = Field(None, description="Error message if failed")
    count: int = Field(..., description="Number of texts processed")


class ModelInfoResponse(BaseModel):
    """Response schema for model information."""
    
    name: str = Field(..., description="Model name")
    version: str = Field(..., description="Model version")
    description: str = Field(..., description="Model description")
    labels: List[str] = Field(..., description="Possible sentiment labels")
    framework: str = Field(..., description="ML framework used")
    base_model: str = Field(..., description="Base model architecture")
    segmentation_enabled: bool = Field(..., description="Whether segmentation is enabled")

