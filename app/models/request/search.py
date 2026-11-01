from typing import Optional

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
    document_ids: Optional[list[str]] = Field(
        default=None,
        description=(
            "Explicit document IDs to restrict the search to (Phase 2C). "
            "Never inferred from the query - omit or leave empty for no "
            "filtering, the default. Not supported with retrieval_mode "
            "\"hybrid\"."
        ),
        examples=[["doc_1"]]
    )

    class Config:
        json_schema_extra = {
            "example": {
                "query": "Which team uses high pressing?",
                "n_results": 3,
                "source_ids": ["ucl_2025"],
                "document_ids": None
            }
        }