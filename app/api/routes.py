from fastapi import APIRouter, HTTPException

from app.models import (
    SearchRequest,
    SearchResponse,
    AskResponse,
    StatsResponse,
    StatsResetResponse,
    DocumentResult,
    UsageInfo
)
from app.services.rag_chain import get_rag_chain
from app.services.rag_service import search_accross_sources

router = APIRouter(prefix="/api/v1", tags=["football documents"])

# class SearchRequest(BaseModel):
#     query: str = Field(..., example="User's question about football", min_length=1)
#     n_results: int = Field(default=3, description="Number of results to return", ge=1, le=10)


# class DocumentResponse(BaseModel):
#     document: str
#     metadata: dict
#     similarity_score: float
#     rank: int


# class SearchResponse(BaseModel):
#     query: str
#     total_results: int
#     results: List[DocumentResponse]


# class UsageInfo(BaseModel):
#     input_tokens: int
#     output_tokens: int
#     total_tokens: int

# class AskResponse(BaseModel):
#     query: str
#     answer: str
#     total_docs: int
#     usage: UsageInfo
#     cost_usd: float
#     retrieved_documents: Optional[List] = None


rag_chain = get_rag_chain()

@router.post("/search", response_model=SearchResponse)
async def search_documents(request: SearchRequest):
    """
    Search football documents semantically.
    
    Example:
    POST /api/v1/search
    {
        "query": "Which team uses high pressing?",
        "n_results": 3,
        "source_id": "ucl_2025"

    }
    """
    
    if not request.query.strip() and len(request.query.strip()) == 0 :
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    source_ids = [source_id.value for source_id in request.source_ids]
    raw_results = search_accross_sources(request.query, source_ids, request.n_results)
    formatted_results = []

    for doc in raw_results:
        formatted_results.append(DocumentResult(
            document=doc["document"],
            metadata=doc["metadata"],
            similarity_score=doc["similarity_score"],
            rank=doc["rank"]
        ))
    
    return SearchResponse(
        query=request.query,
        total_results=len(formatted_results),
        results=formatted_results
    )


@router.post("/ask", response_model=AskResponse)
async def ask_football_question(request: SearchRequest):
    """
    Complete RAG endpoint: Retrieve + Generate.
    Returns a natural language answer grounded in your documents.
    """
    if not request.query.strip() and len(request.query.strip()) == 0 :
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    source_ids = [
        source_id.value
        for source_id in request.source_ids
    ]

    response = rag_chain.ask(
        query=request.query,
        source_ids=source_ids,
        n_results=request.n_results,
    )
    
    return AskResponse(
        query=response["query"],
        answer=response["answer"],
        usage=UsageInfo(**response["usage"]),
        cost_usd=response["cost_usd"],
        total_docs=response["total_docs"],
        retrieved_documents=response["retrieved_documents"]
    )


@router.get("/health")
async def health_check():
    """
    Health check endpoint to verify API is running.
    """
    return {
        "status": "healthy",
        "service": "football-rag",
        "documents_available": 8  # You can make this dynamic later
    }


@router.get("/info")
async def service_info():
    """
    Basic info about the service.
    """
    return {
        "name": "Football RAG API",
        "version": "1.0.0",
        "description": "Semantic search over football tactics documents",
        "endpoints": {
            "search": "POST /api/v1/search",
            "health": "GET /api/v1/health",
            "info": "GET /api/v1/info"
        }
    }


@router.get("/stats", response_model=StatsResponse)
async def get_stats():
    stats = rag_chain.get_stats()
    return StatsResponse(**stats)


@router.post("/stats/reset", response_model=StatsResetResponse)
async def reset_stats():
    previous_stats = rag_chain.get_stats()
    rag_chain.reset_stats()
    
    return StatsResetResponse(
        message="Statistics reset successfully",
        previous_stats=StatsResponse(**previous_stats)
    )
