"""Request models package for API endpoints."""

from app.models.request.search import SearchRequest
from app.models.request.stats import StatsResetRequest

__all__ = [
    "SearchRequest",
    "StatsResetRequest",
]
