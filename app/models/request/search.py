from pydantic import BaseModel, Field

from app.config.source import SourceID

class SearchRequest(BaseModel):
    """
    Request model for searching and ask endpoints.

    """

    query: str = Field(
        ..., 
        min_length=1,
        example="Which team uses high pressing?", 
    )
    n_results: int = Field(
        default=3,
        description="Number of results to return",
        ge=1,
        le=10,
        examples=[3, 5, 10]
    )
    source_ids: list[SourceID] = Field(
        default = [SourceID.FOOTBALL_PROFILES],
        min_length=1,
        description="Source IDs to search in",
        examples=[["ucl_2025", "football_profiles"]]
    )

    class Config:
        json_schema_extra = {
            "example": {
                "query": "Which team uses high pressing?",
                "n_results": 3,
                "source_ids": ["ucl_2025"]
            }
        }