"""
Break down a saved baseline's scores by question category (football_profile,
uefa_report, multi_context, cross_source, unsupported), so it's possible to
see whether low scores are general or concentrated in harder question types.

Usage:
    .venv-eval/bin/python -m evals.analyze_results
    .venv-eval/bin/python -m evals.analyze_results evals/results/baseline_20261001T130615Z.json
"""

import json
import sys
from collections import defaultdict
from pathlib import Path

RESULTS_DIR = Path(__file__).resolve().parent / "results"
METRICS = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]


def _mean(values):
    scored = [v for v in values if v is not None]
    return round(sum(scored) / len(scored), 4) if scored else None


def latest_results_file():
    files = sorted(RESULTS_DIR.glob("baseline_*.json"))
    if not files:
        raise FileNotFoundError(f"No baseline_*.json files found in {RESULTS_DIR}")
    return files[-1]


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else latest_results_file()
    data = json.loads(path.read_text())

    print(f"Analyzing: {path}")
    print(f"Judge: {data['judge_model']} (temperature={data.get('judge_temperature')})")
    print(f"Retrieval mode: {data.get('retrieval_mode', 'dense (predates retrieval_mode field)')}")
    print(f"Chunk version: {data.get('chunk_version', 'v1 (predates chunk_version field)')}")
    print(f"Overall aggregate: {data['aggregate']}\n")

    by_category = defaultdict(list)
    for row in data["per_question"]:
        by_category[row.get("category", "uncategorized")].append(row)

    header = f"{'category':<18} {'n':>3}  " + "  ".join(f"{m:>18}" for m in METRICS)
    print(header)
    print("-" * len(header))

    for category, rows in sorted(by_category.items()):
        means = [_mean([r[m] for r in rows]) for m in METRICS]
        values = "  ".join(f"{'None' if m is None else m:>18}" for m in means)
        print(f"{category:<18} {len(rows):>3}  {values}")


if __name__ == "__main__":
    main()
