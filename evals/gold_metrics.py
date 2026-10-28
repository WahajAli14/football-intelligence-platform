"""
Deterministic retrieval metrics (Recall@k, Precision@k, MRR, nDCG@k) computed
against evals/gold_labels.py, independent of the RAGAS judge model - per
PROJECT_PLAN.md Phase 2A.

Reads a saved baseline JSON's retrieved_chunk_ids per question (added
specifically so this wouldn't need a new eval run) - this is pure
computation over already-collected data, no new RAG or judge calls happen
here. k is whatever was actually retrieved per question (DEFAULT_N_RESULTS,
normally 3), not a separately chosen cutoff.

Questions whose gold set is genuinely empty (the two true "unsupported"
questions - see evals/gold_labels.py) have undefined Recall/Precision/MRR/
nDCG (0/0) and are excluded from aggregates, same convention as Context
Precision's documented limitation (PROJECT_PLAN.md Phase 1 §4.3).
"partial_evidence" (non-empty gold set) is included normally.

Usage:
    .venv-eval/bin/python -m evals.gold_metrics
    .venv-eval/bin/python -m evals.gold_metrics evals/results/baseline_X.json
"""
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

from evals.gold_labels import gold_labels as gold_labels_v1
from evals.gold_labels_v2 import gold_labels_v2

RESULTS_DIR = Path(__file__).resolve().parent / "results"

# A baseline's own chunk_version field (added when run_eval.py started
# supporting CHUNK_VERSION) picks the matching gold-label set - the chunk
# IDs in each only exist in their own collections, so using the wrong one
# would silently score everything as a miss.
GOLD_LABELS_BY_CHUNK_VERSION = {"v1": gold_labels_v1, "v2": gold_labels_v2}


def latest_results_file():
    files = sorted(RESULTS_DIR.glob("baseline_*.json"))
    if not files:
        raise FileNotFoundError(f"No baseline_*.json files found in {RESULTS_DIR}")
    return files[-1]


def _recall_at_k(retrieved, gold):
    if not gold:
        return None
    return len(set(retrieved) & gold) / len(gold)


def _precision_at_k(retrieved, gold):
    if not gold or not retrieved:
        return None
    return len(set(retrieved) & gold) / len(retrieved)


def _mrr(retrieved, gold):
    if not gold:
        return None
    for rank, chunk_id in enumerate(retrieved, start=1):
        if chunk_id in gold:
            return 1.0 / rank
    return 0.0


def _ndcg_at_k(retrieved, gold):
    if not gold:
        return None
    seen = set()
    dcg = 0.0
    for rank, chunk_id in enumerate(retrieved, start=1):
        if chunk_id in gold and chunk_id not in seen:
            dcg += 1.0 / math.log2(rank + 1)
            seen.add(chunk_id)
    ideal_hits = min(len(gold), len(retrieved))
    idcg = sum(1.0 / math.log2(rank + 1) for rank in range(1, ideal_hits + 1))
    return dcg / idcg if idcg > 0 else None


def _mean(values):
    scored = [v for v in values if v is not None]
    return round(sum(scored) / len(scored), 4) if scored else None


def compute_metrics(baseline_path):
    data = json.loads(Path(baseline_path).read_text())
    chunk_version = data.get("chunk_version", "v1")
    gold_labels = GOLD_LABELS_BY_CHUNK_VERSION[chunk_version]

    rows = []
    skipped = []
    for row in data["per_question"]:
        user_input = row["user_input"]
        retrieved = row.get("retrieved_chunk_ids")

        if user_input not in gold_labels or retrieved is None:
            skipped.append(user_input)
            continue

        gold = set(gold_labels[user_input]["relevant_chunk_ids"])
        rows.append({
            "user_input": user_input,
            "category": row["category"],
            "gold_is_empty": len(gold) == 0,
            "recall_at_k": _recall_at_k(retrieved, gold),
            "precision_at_k": _precision_at_k(retrieved, gold),
            "mrr": _mrr(retrieved, gold),
            "ndcg_at_k": _ndcg_at_k(retrieved, gold),
        })

    return rows, skipped


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else latest_results_file()
    rows, skipped = compute_metrics(path)
    chunk_version = json.loads(path.read_text()).get("chunk_version", "v1")

    print(f"Deterministic retrieval metrics for: {path}")
    print(f"Chunk version: {chunk_version} (gold labels: evals/gold_labels{'_v2' if chunk_version == 'v2' else ''}.py)")
    if skipped:
        print(f"Skipped (no gold label, or baseline predates chunk_id surfacing): {skipped}")

    scored_rows = [r for r in rows if not r["gold_is_empty"]]
    empty_rows = [r for r in rows if r["gold_is_empty"]]

    print(f"\n{len(scored_rows)} question(s) with non-empty gold evidence scored, "
          f"{len(empty_rows)} excluded (empty gold set - Recall/Precision/MRR/nDCG undefined).\n")

    metrics = ["recall_at_k", "precision_at_k", "mrr", "ndcg_at_k"]

    aggregate = {m: _mean([r[m] for r in scored_rows]) for m in metrics}
    print("Overall aggregate (excludes empty-gold questions):")
    for name, value in aggregate.items():
        print(f"  {name}: {value}")

    by_category = defaultdict(list)
    for r in scored_rows:
        by_category[r["category"]].append(r)

    header = f"{'category':<18} {'n':>3}  " + "  ".join(f"{m:>14}" for m in metrics)
    print("\n" + header)
    print("-" * len(header))
    for category, cat_rows in sorted(by_category.items()):
        means = [_mean([r[m] for r in cat_rows]) for m in metrics]
        values = "  ".join(f"{m:>14}" for m in means)
        print(f"{category:<18} {len(cat_rows):>3}  {values}")

    if empty_rows:
        print(f"\nExcluded (empty gold set): {[r['user_input'] for r in empty_rows]}")


if __name__ == "__main__":
    main()
