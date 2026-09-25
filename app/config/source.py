from enum import Enum
from typing import Any, Dict


class SourceID(str, Enum):
    """Enum for source IDs."""

    FOOTBALL_PROFILES = "football_profiles"
    UCL_2025 = "ucl_2025"


KNOWLEDGE_SOURCES: Dict[str, Dict[str, Any]] = {
    SourceID.FOOTBALL_PROFILES.value: {
        "collection": "football_docs_chunked",
        "title": "Football Team Profiles",
    },
    SourceID.UCL_2025.value: {
        "collection": "ucl_technical_report_2025",
        "title": "UEFA Champions League Technical Report 2024/25",
    },
}

def get_source_config(source_id: str) -> Dict[str, Any]:
    """
    Resolve a public source ID to its internal configuration.
    """

    source = KNOWLEDGE_SOURCES.get(source_id)

    if source is None:
        raise ValueError(f"Unknown source_id: {source_id}")

    return source