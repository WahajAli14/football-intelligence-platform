"""Search endpoint response models"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any


class DocumentResult(BaseModel):
    """Individual document result from retrieval."""
    
    document: str = Field(..., examples=["Arsenal usually rely on structured possession..."])
    metadata: Dict[str, Any] = Field(..., example={"team": "Arsenal", "tactical_approach": "High Pressing"})
    similarity_score: float = Field(..., examples=[0.4653])
    rank: int = Field(..., examples=[1])
    
    class Config:
        json_schema_extra = {
            "example": {
                "document": "Arsenal usually rely on structured possession, high pressing...",
                "metadata": {"team": "Arsenal", "tactical_approach": "High Pressing"},
                "similarity_score": 0.4653,
                "rank": 1
            }
        }


class SearchResponse(BaseModel):
    """Response model for /search endpoint."""
    
    query: str = Field(..., examples=["Which team uses high pressing?"])
    total_results: int = Field(..., examples=[2])
    results: List[DocumentResult]
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "Which team uses high pressing?",
                "total_results": 2,
                "results": []
            }
        }