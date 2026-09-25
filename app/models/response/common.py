"""Common response models for API endpoints."""
import json

from pydantic import BaseModel, Field
from datetime import datetime


class UsageInfo(BaseModel):
    input_tokens: int = Field(..., description="Number of tokens in the input prompt")
    output_tokens: int = Field(..., description="Number of tokens in the generated response")
    total_tokens: int  = Field(..., description="Total tokens used (input + output)")

    class Config:
        json_schema_extra = {
            "example": {
                "input_tokens": 150,
                "output_tokens": 300,
                "total_tokens": 450
            }
        }


class HealthResponse(BaseModel):
    """Health check response."""
    
    status: str = Field(..., examples=["healthy"])
    service: str = Field(..., examples=["football-rag"])
    timestamp: datetime = Field(...)
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "service": "football-rag",
                "timestamp": "2025-06-15T10:30:00"
            }
        }