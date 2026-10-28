
from app.config.source import get_source_config
from app.db.chroma_client import get_chroma_client, get_or_create_collection
from app.config.rag import (
    DEFAULT_COLLECTION,
    DEFAULT_N_RESULTS,
    DEFAULT_RETRIEVAL_MODE,
    RETRIEVAL_MODE_DENSE,
    RETRIEVAL_MODE_HYBRID,
    HYBRID_CANDIDATE_POOL,
    RRF_K,
)
from app.services.bm25_index import combined_bm25_search


def _dense_search(query: str, collection_name: str, n_results: int):
    """
    Raw dense/embedding retrieval against Chroma. Returns chunks ranked by
    similarity, highest first - no fusion, no BM25 involved.
    """
    client = get_chroma_client()
    collection = get_or_create_collection(client, collection_name)

    results = collection.query(
        query_texts=[query],
        n_results=n_results,
        include=["documents", "metadatas", "distances"]
    )

    retrieved_docs = []

    if results["documents"] and len(results["documents"][0]) > 0:
        for i, (chunk_id, doc, meta, dist) in enumerate(
            zip(
                results["ids"][0],
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0]
            ),
            start=1
        ):
            retrieved_docs.append({
                "chunk_id": chunk_id,
                "document": doc,
                "metadata": meta,
                "similarity_score": round(1 / (1 + dist), 4),
                "rank": i
            })

    return retrieved_docs


def _rrf_fuse(rankings, n_results: int, k: int = RRF_K):
    """
    Reciprocal Rank Fusion across any number of ranked lists (each item
    needs a "rank" field, 1-indexed within its own list). A chunk's fused
    score is the sum of 1/(k + rank) across every ranking it appears in -
    missing from a ranking contributes 0 for that one, rather than being
    penalized or excluded. Only rank position is ever compared, never raw
    score magnitude - this is what lets RRF combine rankings with
    incompatible scales (cosine distance vs. BM25, or two different
    collections' own already-fused scores - see
    EVAL_FINDINGS.md on why comparing those directly is wrong) without
    normalizing any of them.
    """
    chunks_by_id = {}
    fused_scores = {}

    for ranking in rankings:
        for c in ranking:
            chunks_by_id.setdefault(c["chunk_id"], c)
            fused_scores[c["chunk_id"]] = fused_scores.get(c["chunk_id"], 0.0) + 1.0 / (k + c["rank"])

    ranked_ids = sorted(fused_scores, key=lambda cid: fused_scores[cid], reverse=True)

    fused_results = []
    for rank, chunk_id in enumerate(ranked_ids[:n_results], start=1):
        source = chunks_by_id[chunk_id]
        fused_results.append({
            "chunk_id": chunk_id,
            "document": source["document"],
            "metadata": source["metadata"],
            "similarity_score": round(fused_scores[chunk_id], 6),
            "rank": rank,
        })

    return fused_results


def _dense_search_multi(query: str, collections, pool: int):
    """
    collections: list of (collection_name, source_id_or_None, source_title_or_None)

    Fetches up to `pool` dense candidates from EACH collection, then merges
    them into one GLOBAL ranking by raw similarity score - valid across
    collections, since they share the same embedding model and distance
    metric (this is exactly what the dense-only cross-source merge already
    does). Returns the global top `pool`, re-ranked 1..pool.
    """
    all_candidates = []
    for collection_name, source_id, source_title in collections:
        candidates = _dense_search(query, collection_name, pool)
        if source_id:
            for c in candidates:
                c["metadata"] = {**c["metadata"], "source_id": source_id, "source_title": source_title}
        all_candidates.extend(candidates)

    all_candidates.sort(key=lambda c: c["similarity_score"], reverse=True)
    top = all_candidates[:pool]
    for rank, c in enumerate(top, start=1):
        c["rank"] = rank
    return top


def _bm25_search_multi(query: str, collections, pool: int):
    """
    collections: list of (collection_name, source_id_or_None, source_title_or_None)

    One global BM25 ranking across all given collections, scored against
    ONE shared index (see combined_bm25_search's docstring for why this -
    not per-collection BM25 scores/ranks merged afterward - is required).
    """
    collection_names = [c[0] for c in collections]
    source_by_collection = {c[0]: (c[1], c[2]) for c in collections}

    candidates = combined_bm25_search(query, collection_names, pool)
    for c in candidates:
        source_id, source_title = source_by_collection[c.pop("collection_name")]
        if source_id:
            c["metadata"] = {**c["metadata"], "source_id": source_id, "source_title": source_title}
    return candidates


def _retrieve_hybrid(query: str, collections, n_results: int):
    """
    collections: list of (collection_name, source_id_or_None, source_title_or_None)

    Builds ONE global dense ranking and ONE global BM25 ranking across all
    given collections (never per-collection rankings merged afterward - see
    _dense_search_multi/_bm25_search_multi), then applies RRF exactly once.
    This generalizes cleanly to a single collection (the list just has one
    entry) or several (cross-source), with identical fusion behavior either
    way - there is no separate "cross-source merge" step for hybrid mode.
    """
    pool = max(n_results, HYBRID_CANDIDATE_POOL)
    dense_candidates = _dense_search_multi(query, collections, pool)
    bm25_candidates = _bm25_search_multi(query, collections, pool)
    return _rrf_fuse([dense_candidates, bm25_candidates], n_results)


def retrieve_similar_documents(
    query: str,
    collection_name: str = DEFAULT_COLLECTION,
    n_results: int = DEFAULT_N_RESULTS,
    retrieval_mode: str = DEFAULT_RETRIEVAL_MODE,
):
    """
    Retrieve similar documents from a collection. Returns a list of
    documents with their metadata.

    retrieval_mode:
        "dense" (default) - embedding similarity only, unchanged from the
            frozen Phase 2A baseline.
        "hybrid" - dense + BM25 candidates fused with Reciprocal Rank
            Fusion (Phase 2B). similarity_score becomes the fused RRF
            score in this mode, not a cosine-distance transform.
    """
    if retrieval_mode == RETRIEVAL_MODE_DENSE:
        results = _dense_search(query, collection_name, n_results)
    elif retrieval_mode == RETRIEVAL_MODE_HYBRID:
        results = _retrieve_hybrid(query, [(collection_name, None, None)], n_results)
    else:
        raise ValueError(f"Unknown retrieval_mode: {retrieval_mode!r}")

    for r in results:
        r["retrieval_mode"] = retrieval_mode

    return results


def search_accross_sources(
    query: str,
    source_ids: list[str],
    n_results: int = DEFAULT_N_RESULTS,
    retrieval_mode: str = DEFAULT_RETRIEVAL_MODE,
) -> list[dict]:
    """
        Search across multiple sources and return results.
    """
    if retrieval_mode == RETRIEVAL_MODE_HYBRID:
        collections = []
        for source_id in source_ids:
            source_config = get_source_config(source_id)
            collections.append((source_config["collection"], source_id, source_config["title"]))

        top_results = _retrieve_hybrid(query, collections, n_results)
    else:
        all_results = []
        for source_id in source_ids:
            source_config = get_source_config(source_id)
            collection_name = source_config["collection"]

            source_results = retrieve_similar_documents(
                query,
                collection_name,
                n_results,
                retrieval_mode,
            )
            for result in source_results:
                metadata = result.setdefault("metadata", {})
                metadata["source_id"] = source_id
                metadata["source_title"] = source_config["title"]

            all_results.extend(source_results)

        # Sort by similarity score in descending order
        all_results.sort(key=lambda x: x["similarity_score"], reverse=True)
        top_results = all_results[:n_results]

    # Per-source ranks are meaningless after merging; reassign a global rank.
    for global_rank, result in enumerate(top_results, start=1):
        result["rank"] = global_rank

    for result in top_results:
        result["retrieval_mode"] = retrieval_mode

    return top_results


def search_and_display(query: str):
    """
    Helper function to search and print results nicely
    """
    
    print(f"\n🔍 Query: \"{query}\"")
    print("-" * 50)
    
    results = retrieve_similar_documents(query)
    
    if not results:
        print("❌ No results found.")
        return
    
    for doc in results:
        print(f"\n📄 Rank {doc['rank']}: {doc['metadata'].get('title', 'Unknown')}")
        print(f"   Similarity: {doc['similarity_score']:.4f}")
        print(f"   Preview: {doc['document'][:150]}...")


if __name__ == "__main__":
    print("=" * 50)
    print("🏃 TESTING RAG SERVICE")
    print("=" * 50)
    
    # Test 1: Pressing question
    search_and_display("Which team uses high pressing?")
    
    # Test 2: Specific team
    search_and_display("Tell me about Arsenal's playing style")
    
    # Test 3: Tactical concept
    search_and_display("What is possession football?")
    
    # Test 4: Competition style
    search_and_display("How are Champions League matches decided?")
