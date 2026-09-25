"""Stats endpoint response models"""

from pydantic import BaseModel, Field
from typing import Optional


class StatsResponse(BaseModel):
    """Statistics response for /stats endpoint."""
    
    total_requests: int = Field(..., examples=[5])
    total_input_tokens: int = Field(..., examples=[3210])
    total_output_tokens: int = Field(..., examples=[290])
    total_tokens: int = Field(..., examples=[3500])
    total_cost_usd: float = Field(..., examples=[0.0002615])
    average_cost_per_request: float = Field(..., examples=[0.0000523])
    model: str = Field(..., examples=["gpt-4.1-mini"])
    
    class Config:
        json_schema_extra = {
            "example": {
                "total_requests": 5,
                "total_input_tokens": 3210,
                "total_output_tokens": 290,
                "total_tokens": 3500,
                "total_cost_usd": 0.0002615,
                "average_cost_per_request": 0.0000523,
                "model": "gpt-4.1-mini"
            }
        }


class StatsResetResponse(BaseModel):
    """Response for stats reset endpoint."""
    
    message: str = Field(..., examples=["Statistics reset successfully"])
    previous_stats: Optional[StatsResponse] = Field(default=None)
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "Statistics reset successfully",
                "previous_stats": None
            }
        }


