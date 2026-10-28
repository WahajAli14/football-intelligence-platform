"""
BM25 (lexical/keyword) retrieval, built on top of the same chunks already
stored in ChromaDB - no separate corpus or storage. Phase 2B.

BM25 needs global term statistics (document frequency, average document
length) across the whole collection, so one index is built per collection
and cached in memory - rebuilding it per-query would be wasteful and would
also give wrong statistics (computed over whatever a single query's
candidate set happened to be, instead of the real corpus).

The cache is intentionally never invalidated automatically: it's built once
per collection_name per process lifetime. If a collection is re-ingested
while the process is still running, call invalidate_bm25_index(collection_name)
(or restart the process) so the next search rebuilds it from the new data.
"""
import re
from typing import Any, Dict, List, Tuple

import snowballstemmer
from rank_bm25 import BM25Okapi

from app.db.chroma_client import get_chroma_client, get_or_create_collection

_TOKEN_RE = re.compile(r"\w+")
_stemmer = snowballstemmer.stemmer("english")

# Standard short English stopword list. Without this, a long natural-
# language question's connecting words ("to", "the", "how", "did", "in")
# still contribute nonzero BM25 score in a small corpus, which can make an
# otherwise-irrelevant document look like a real match purely from generic
# word overlap - found via a real false-positive match in evals/gold_metrics
# testing (see EVAL_FINDINGS.md).
_STOPWORDS = frozenset("""
a about above after again against all am an and any are aren't as at be
because been before being below between both but by can't cannot could
couldn't did didn't do does doesn't doing don't down during each few for
from further had hadn't has hasn't have haven't having he he'd he'll he's
her here here's hers herself him himself his how how's i i'd i'll i'm i've
if in into is isn't it it's its itself let's me more most mustn't my
myself no nor not of off on once only or other ought our ours ourselves
out over own same shan't she she'd she'll she's should shouldn't so some
such than that that's the their theirs them themselves then there there's
these they they'd they'll they're they've this those through to too under
until up very was wasn't we we'd we'll we're we've were weren't what
what's when when's where where's which while who who's whom why why's
will with won't would wouldn't you you'd you'll you're you've your yours
yourself yourselves
""".split())

# collection_name -> (bm25_model, chunk_ids, documents, metadatas)
_index_cache: Dict[str, Tuple[BM25Okapi, List[str], List[str], List[Dict[str, Any]]]] = {}

# sorted tuple of collection_names -> (bm25_model, chunk_ids, documents,
# metadatas, collection_name_per_chunk). Separate from _index_cache: a
# combined index has its own term statistics (document frequency, average
# length) computed over the union of collections, which is NOT the same as
# looking at each collection's own index separately - see
# combined_bm25_search's docstring for why that distinction matters.
_combined_index_cache: Dict[Tuple[str, ...], Tuple[BM25Okapi, List[str], List[str], List[Dict[str, Any]], List[str]]] = {}


def _tokenize(text: str) -> List[str]:
    """
    Lowercase, drop stopwords, then stem ("pressing"/"pressed"/"press" all
    collapse to the same token). Without stemming, BM25's exact-match
    nature misses documents that use a different inflection of the query's
    words - found via a real false negative on the gold-labeled Arsenal
    pressing question (see EVAL_FINDINGS.md).
    """
    words = [t for t in _TOKEN_RE.findall(text.lower()) if t not in _STOPWORDS]
    return _stemmer.stemWords(words) if words else words


def _build_index(collection_name: str) -> Tuple[BM25Okapi, List[str], List[str], List[Dict[str, Any]]]:
    client = get_chroma_client()
    collection = get_or_create_collection(client, collection_name)
    data = collection.get(include=["documents", "metadatas"])

    chunk_ids = data["ids"]
    documents = data["documents"]
    metadatas = data["metadatas"]

    tokenized_corpus = [_tokenize(doc) for doc in documents]
    bm25 = BM25Okapi(tokenized_corpus)

    return bm25, chunk_ids, documents, metadatas


def get_bm25_index(collection_name: str) -> Tuple[BM25Okapi, List[str], List[str], List[Dict[str, Any]]]:
    if collection_name not in _index_cache:
        _index_cache[collection_name] = _build_index(collection_name)
    return _index_cache[collection_name]


def invalidate_bm25_index(collection_name: str) -> None:
    _index_cache.pop(collection_name, None)


def bm25_search(query: str, collection_name: str, n_results: int) -> List[Dict[str, Any]]:
    """
    Returns up to n_results chunks ranked by BM25 score, highest first.
    Chunks with zero score (no query term overlap at all) are excluded
    rather than padded in - they weren't actually matched by this method.
    """
    bm25, chunk_ids, documents, metadatas = get_bm25_index(collection_name)
    return _score_and_rank(bm25, chunk_ids, documents, metadatas, query, n_results)


def _score_and_rank(bm25, chunk_ids, documents, metadatas, query, n_results, collection_names=None):
    scores = bm25.get_scores(_tokenize(query))
    ranked_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)

    results = []
    for rank, i in enumerate(ranked_indices[:n_results], start=1):
        if scores[i] <= 0:
            break
        result = {
            "chunk_id": chunk_ids[i],
            "document": documents[i],
            "metadata": metadatas[i],
            "bm25_score": float(scores[i]),
            "rank": rank,
        }
        if collection_names is not None:
            result["collection_name"] = collection_names[i]
        results.append(result)

    return results


def _build_combined_index(collection_names: Tuple[str, ...]):
    all_chunk_ids, all_documents, all_metadatas, collection_name_per_chunk = [], [], [], []

    client = get_chroma_client()
    for name in collection_names:
        collection = get_or_create_collection(client, name)
        data = collection.get(include=["documents", "metadatas"])
        all_chunk_ids.extend(data["ids"])
        all_documents.extend(data["documents"])
        all_metadatas.extend(data["metadatas"])
        collection_name_per_chunk.extend([name] * len(data["ids"]))

    tokenized_corpus = [_tokenize(doc) for doc in all_documents]
    bm25 = BM25Okapi(tokenized_corpus)

    return bm25, all_chunk_ids, all_documents, all_metadatas, collection_name_per_chunk


def get_combined_bm25_index(collection_names: List[str]):
    key = tuple(sorted(collection_names))
    if key not in _combined_index_cache:
        _combined_index_cache[key] = _build_combined_index(key)
    return _combined_index_cache[key]


def invalidate_combined_bm25_index(collection_names: List[str]) -> None:
    _combined_index_cache.pop(tuple(sorted(collection_names)), None)


def combined_bm25_search(query: str, collection_names: List[str], n_results: int) -> List[Dict[str, Any]]:
    """
    BM25 over the union of all given collections, sharing one set of corpus
    statistics (document frequency, average length) across all of them.

    This matters when retrieving across multiple sources of very different
    size: scoring each collection with its OWN separate BM25 index and then
    comparing those scores (or even their ranks - see
    rag_service._retrieve_hybrid's docstring) is not meaningful, because a
    small, generic collection's statistics make an irrelevant match look
    deceptively strong relative to a large, specific collection's (found via
    a real false-positive in evals/gold_metrics testing across
    football_profiles + ucl_2025 - see EVAL_FINDINGS.md). One shared index
    avoids that by construction - every chunk from every selected collection
    is scored against the same global statistics.
    """
    if len(collection_names) == 1:
        bm25, chunk_ids, documents, metadatas = get_bm25_index(collection_names[0])
        return _score_and_rank(
            bm25, chunk_ids, documents, metadatas, query, n_results,
            collection_names=[collection_names[0]] * len(chunk_ids),
        )

    bm25, chunk_ids, documents, metadatas, collection_name_per_chunk = get_combined_bm25_index(collection_names)
    return _score_and_rank(
        bm25, chunk_ids, documents, metadatas, query, n_results,
        collection_names=collection_name_per_chunk,
    )
