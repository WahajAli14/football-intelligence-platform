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
"""
import json
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from app.config.rag import DEFAULT_N_RESULTS, DEFAULT_RETRIEVAL_MODE, RETRIEVAL_MODE_RERANK
from app.config.source import get_source_config
from app.services.rag_chain import get_rag_chain
from app.services.rag_service import _build_rerank_candidates
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

GOLD_LABELS = {"v1": gold_labels_v1, "v2": gold_labels_v2}[CHUNK_VERSION]
METRICS = ["recall_at_k", "precision_at_k", "mrr", "ndcg_at_k"]


def main():
    rag_chain = get_rag_chain()
    rows = []
    failures = []

    for i, item in enumerate(evaluation_questions, 1):
        print(f"[{i}/{len(evaluation_questions)}] {item['user_input']}")
        try:
            retrieved_docs = rag_chain.retrieve(
                query=item["user_input"],
                source_ids=item["source_ids"],
                n_results=DEFAULT_N_RESULTS,
                retrieval_mode=RETRIEVAL_MODE,
            )
        except Exception as e:
            print(f"   FAILED: {e}")
            failures.append({"user_input": item["user_input"], "error": str(e)})
            continue

        retrieved_chunk_ids = [d["chunk_id"] for d in retrieved_docs]
        gold = set(GOLD_LABELS[item["user_input"]]["relevant_chunk_ids"])

        row = {
            "user_input": item["user_input"],
            "category": item["category"],
            "retrieved_chunk_ids": retrieved_chunk_ids,
            "gold_is_empty": len(gold) == 0,
            "recall_at_k": _recall_at_k(retrieved_chunk_ids, gold),
            "precision_at_k": _precision_at_k(retrieved_chunk_ids, gold),
            "mrr": _mrr(retrieved_chunk_ids, gold),
            "ndcg_at_k": _ndcg_at_k(retrieved_chunk_ids, gold),
        }

        # Phase 2D-1 diagnostic: recall over the pre-rerank union, so a low
        # final recall can be attributed to the reranker (gold chunk was in
        # the union, got ranked out) vs. candidate generation (gold chunk
        # was never in the union at all) rather than guessed at after the
        # fact the way Phase 2B's candidate-pool analysis had to be.
        if RETRIEVAL_MODE == RETRIEVAL_MODE_RERANK:
            collections = [
                (get_source_config(sid)["collection"], None, None)
                for sid in item["source_ids"]
            ]
            union_chunk_ids = [c["chunk_id"] for c in _build_rerank_candidates(item["user_input"], collections)]
            row["union_recall"] = _recall_at_k(union_chunk_ids, gold)

        rows.append(row)

    scored_rows = [r for r in rows if not r["gold_is_empty"]]
    empty_rows = [r for r in rows if r["gold_is_empty"]]

    print(f"\nRetrieval mode: {RETRIEVAL_MODE}, chunk version: {CHUNK_VERSION}")
    print(f"{len(scored_rows)} scored, {len(empty_rows)} excluded (empty gold set), "
          f"{len(failures)} failed retrieval")

    aggregate = {m: _mean([r[m] for r in scored_rows]) for m in METRICS}
    if RETRIEVAL_MODE == RETRIEVAL_MODE_RERANK:
        aggregate["union_recall"] = _mean([r["union_recall"] for r in scored_rows])
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
        "aggregate": aggregate,
        "retrieval_failures": failures,
        "per_question": rows,
    }, indent=2))
    print(f"\nSaved to {out_path}")


if __name__ == "__main__":
    main()
