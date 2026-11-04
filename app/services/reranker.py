"""
Cross-encoder reranking (Phase 2D-1). Takes a candidate pool already
retrieved by other methods (dense, BM25) and re-scores each candidate
directly against the query - a cross-encoder sees query and chunk together,
rather than comparing independently-computed embeddings or term overlap,
so it can judge relevance more directly than either retriever alone.

The model is loaded once per process and cached, same pattern as
bm25_index.py's in-memory index cache - loading a transformer model per
call would be wasteful.
"""
from typing import Any, Dict, List, Optional

from sentence_transformers import CrossEncoder

from app.config.rag import RERANKER_MODEL

_model: Optional[CrossEncoder] = None


def get_reranker() -> CrossEncoder:
    global _model
    if _model is None:
        _model = CrossEncoder(RERANKER_MODEL)
    return _model


def rerank(query: str, candidates: List[Dict[str, Any]], n_results: int) -> List[Dict[str, Any]]:
    """
    Re-scores every candidate against the query with the cross-encoder and
    returns the top n_results, highest score first. candidates must each
    have a "document" field; "chunk_id"/"metadata" (if present) are carried
    through unchanged. Does not assume or preserve any incoming rank/score -
    the cross-encoder score is the only ranking signal used here.
    """
    if not candidates:
        return []

    model = get_reranker()
    pairs = [(query, c["document"]) for c in candidates]
    scores = model.predict(pairs)

    scored = list(zip(candidates, scores))
    scored.sort(key=lambda pair: pair[1], reverse=True)

    reranked = []
    for rank, (candidate, score) in enumerate(scored[:n_results], start=1):
        reranked.append({
            **candidate,
            "similarity_score": round(float(score), 6),
            "rank": rank,
        })

    return reranked
