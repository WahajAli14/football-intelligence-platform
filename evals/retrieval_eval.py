"""
Retrieval-only evaluation: Recall@k, Precision@k, MRR, nDCG@k against
evals/gold_labels[_v2].py - no answer generation, no RAGAS judge calls.

evals/run_eval.py's full pipeline costs roughly 19 OpenAI calls per
question (1 generation call, then several per RAGAS metric -
ContextPrecisionWithReference alone calls the judge once per retrieved
chunk, not once per question). That's fine for recording an official
baseline, but far too expensive to run on every small retrieval change
while iterating - which is exactly what burned through this project's
OpenAI quota partway through a Phase 2B experiment (see EVAL_FINDINGS.md).

Use this while developing a retrieval change; only run the full
evals/run_eval.py once a retrieval-only result here looks genuinely
promising. This only costs an embedding call per question for dense
retrieval (BM25 is local, free) - no chat completion calls at all, so it
can run in the lightweight .venv, not .venv-eval - there's no ragas
dependency anywhere in this file.

Usage:
    .venv/bin/python -m evals.retrieval_eval
    RETRIEVAL_MODE=hybrid CHUNK_VERSION=v2 .venv/bin/python -m evals.retrieval_eval
    RETRIEVAL_MODE=rerank CHUNK_VERSION=v2 RERANK_POOL=20 .venv/bin/python -m evals.retrieval_eval
"""
import json
import os
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from app.config.rag import (
    DEFAULT_N_RESULTS,
    DEFAULT_RETRIEVAL_MODE,
    RERANK_CANDIDATE_POOL,
    RETRIEVAL_MODE_RERANK,
)
from app.config.source import get_source_config
from app.services.rag_chain import get_rag_chain
from app.services.rag_service import _build_rerank_candidates
from app.services.reranker import rerank as cross_encoder_rerank
from evals.gold_labels import gold_labels as gold_labels_v1
from evals.gold_labels_v2 import gold_labels_v2
from evals.gold_metrics import _mean, _mrr, _ndcg_at_k, _precision_at_k, _recall_at_k
from evals.questions import evaluation_questions

RESULTS_DIR = Path(__file__).resolve().parent / "results"

RETRIEVAL_MODE = os.environ.get("RETRIEVAL_MODE", DEFAULT_RETRIEVAL_MODE)
CHUNK_VERSION = os.environ.get("CHUNK_VERSION", "v1")
if CHUNK_VERSION == "v2":
    from app.config import source as _source_config
    for _cfg in _source_config.KNOWLEDGE_SOURCES.values():
        _cfg["collection"] = _cfg["collection"] + "_v2"

# Phase 2D-2: override the locked 2D-1 pool size (10) for a labeled,
# separate experiment without touching the frozen default - see
# PROJECT_PLAN.md's "2D-2 - candidate pool expansion" for the recorded
# hypothesis this is testing.
RERANK_POOL = int(os.environ.get("RERANK_POOL", RERANK_CANDIDATE_POOL))

GOLD_LABELS = {"v1": gold_labels_v1, "v2": gold_labels_v2}[CHUNK_VERSION]
METRICS = ["recall_at_k", "precision_at_k", "mrr", "ndcg_at_k"]


def _oracle_recall_at_k(pool_chunk_ids, gold, k):
    """
    The best Recall@k any selector could achieve from this exact pool,
    limited only by the k-slot output - see PROJECT_PLAN.md's 2D-2 writeup.
    Separates a capacity limit (only k slots) from a selection limit (the
    gap between this ceiling and the reranker's actual Recall@k).
    """
    if not gold:
        return None
    hits_in_pool = len(set(pool_chunk_ids) & gold)
    return min(k, hits_in_pool) / len(gold)


def main():
    rag_chain = get_rag_chain()
    rows = []
    failures = []

    for i, item in enumerate(evaluation_questions, 1):
        print(f"[{i}/{len(evaluation_questions)}] {item['user_input']}")
        query = item["user_input"]

        try:
            if RETRIEVAL_MODE == RETRIEVAL_MODE_RERANK:
                # Built once here (not via RAGChain.retrieve) so the pool
                # can be reused for the union/oracle diagnostics below
                # instead of rebuilding it a second time, and so
                # candidate-generation and reranking latency can be timed
                # separately - see PROJECT_PLAN.md's 2D-2 writeup for why
                # the earlier double-build mattered once latency entered
                # the picture.
                collections = [
                    (get_source_config(sid)["collection"], None, None)
                    for sid in item["source_ids"]
                ]
                t0 = time.perf_counter()
                candidates = _build_rerank_candidates(query, collections, pool=RERANK_POOL)
                t1 = time.perf_counter()
                retrieved_docs = cross_encoder_rerank(query, candidates, DEFAULT_N_RESULTS)
                t2 = time.perf_counter()
                candidate_gen_latency_s = t1 - t0
                rerank_latency_s = t2 - t1
            else:
                t0 = time.perf_counter()
                retrieved_docs = rag_chain.retrieve(
                    query=query,
                    source_ids=item["source_ids"],
                    n_results=DEFAULT_N_RESULTS,
                    retrieval_mode=RETRIEVAL_MODE,
                )
                t1 = time.perf_counter()
                candidate_gen_latency_s = None
                rerank_latency_s = None
        except Exception as e:
            print(f"   FAILED: {e}")
            failures.append({"user_input": query, "error": str(e)})
            continue

        retrieved_chunk_ids = [d["chunk_id"] for d in retrieved_docs]
        gold = set(GOLD_LABELS[query]["relevant_chunk_ids"])

        row = {
            "user_input": query,
            "category": item["category"],
            "retrieved_chunk_ids": retrieved_chunk_ids,
            "gold_is_empty": len(gold) == 0,
            "recall_at_k": _recall_at_k(retrieved_chunk_ids, gold),
            "precision_at_k": _precision_at_k(retrieved_chunk_ids, gold),
            "mrr": _mrr(retrieved_chunk_ids, gold),
            "ndcg_at_k": _ndcg_at_k(retrieved_chunk_ids, gold),
            "latency_s": (candidate_gen_latency_s + rerank_latency_s) if RETRIEVAL_MODE == RETRIEVAL_MODE_RERANK else (t1 - t0),
        }

        # Phase 2D-1/2D-2 diagnostics: recall over the pre-rerank union
        # (was the gold chunk findable at all?) and Oracle Recall@k (the
        # best Recall@k achievable from that exact pool) so a low final
        # recall can be attributed to candidate generation, the k-slot
        # output cap, or the reranker's own judgment, rather than guessed
        # at after the fact the way Phase 2B's candidate-pool analysis had
        # to be.
        if RETRIEVAL_MODE == RETRIEVAL_MODE_RERANK:
            pool_chunk_ids = [c["chunk_id"] for c in candidates]
            row["union_recall"] = _recall_at_k(pool_chunk_ids, gold)
            row["oracle_recall_at_k"] = _oracle_recall_at_k(pool_chunk_ids, gold, DEFAULT_N_RESULTS)
            row["candidate_gen_latency_s"] = candidate_gen_latency_s
            row["rerank_latency_s"] = rerank_latency_s

        rows.append(row)

    scored_rows = [r for r in rows if not r["gold_is_empty"]]
    empty_rows = [r for r in rows if r["gold_is_empty"]]

    print(f"\nRetrieval mode: {RETRIEVAL_MODE}, chunk version: {CHUNK_VERSION}")
    print(f"{len(scored_rows)} scored, {len(empty_rows)} excluded (empty gold set), "
          f"{len(failures)} failed retrieval")

    aggregate = {m: _mean([r[m] for r in scored_rows]) for m in METRICS}
    aggregate["mean_latency_s"] = _mean([r["latency_s"] for r in rows])
    if RETRIEVAL_MODE == RETRIEVAL_MODE_RERANK:
        aggregate["union_recall"] = _mean([r["union_recall"] for r in scored_rows])
        aggregate["oracle_recall_at_k"] = _mean([r["oracle_recall_at_k"] for r in scored_rows])
        aggregate["mean_candidate_gen_latency_s"] = _mean([r["candidate_gen_latency_s"] for r in rows])
        aggregate["mean_rerank_latency_s"] = _mean([r["rerank_latency_s"] for r in rows])
    print("\nOverall aggregate:")
    for name, value in aggregate.items():
        print(f"  {name}: {value}")

    by_category = defaultdict(list)
    for r in scored_rows:
        by_category[r["category"]].append(r)

    header = f"{'category':<18} {'n':>3}  " + "  ".join(f"{m:>14}" for m in METRICS)
    print("\n" + header)
    print("-" * len(header))
    for category, cat_rows in sorted(by_category.items()):
        means = [_mean([r[m] for r in cat_rows]) for m in METRICS]
        values = "  ".join(f"{'None' if m is None else m:>14}" for m in means)
        print(f"{category:<18} {len(cat_rows):>3}  {values}")

    RESULTS_DIR.mkdir(exist_ok=True)
    out_path = RESULTS_DIR / f"retrieval_only_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    out_path.write_text(json.dumps({
        "retrieval_mode": RETRIEVAL_MODE,
        "chunk_version": CHUNK_VERSION,
        "n_results": DEFAULT_N_RESULTS,
        "rerank_pool": RERANK_POOL if RETRIEVAL_MODE == RETRIEVAL_MODE_RERANK else None,
        "aggregate": aggregate,
        "retrieval_failures": failures,
        "per_question": rows,
    }, indent=2))
    print(f"\nSaved to {out_path}")


if __name__ == "__main__":
    main()
