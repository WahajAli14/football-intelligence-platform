"""Ask endpoint response models"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

from app.models.response.common import UsageInfo


class AskResponse(BaseModel):
    """Response model for /ask endpoint (full RAG)."""
    
    query: str = Field(..., examples=["Which team uses high pressing?"])
    answer: str = Field(..., examples=["Based on the documents, Arsenal uses high pressing..."])
    usage: UsageInfo
    cost_usd: float = Field(..., examples=[0.0000523])
    total_docs: int = Field(..., examples=[2])
    retrieved_documents: Optional[List[Dict[str, Any]]] = Field(default=None)
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "Which team uses high pressing?",
                "answer": "Based on Document 1, Arsenal uses high pressing...",
                "usage": {"input_tokens": 642, "output_tokens": 58, "total_tokens": 700},
                "cost_usd": 0.0000523,
                "total_docs": 2,
                "retrieved_documents": None
            }
        }