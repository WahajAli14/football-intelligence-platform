"""
Run evaluation questions through the real RAGChain, score them with RAGAS
(Faithfulness, Answer Relevancy, Context Precision, Context Recall), and
persist the result as a baseline for future retrieval experiments.

Pipeline: all questions run -> RAGChain answers -> retrieved documents are
captured -> references are attached -> dataset builds -> each sample is
scored against the judge model configured in evals/judge.py -> aggregate and
per-question results are saved to evals/results/baseline_<timestamp>.json.

Scoring is checkpointed to evals/results/checkpoint.json as each question
finishes, so an interrupted run (killed process, exhausted retries) can be
resumed without re-scoring questions that already completed. The checkpoint
is deleted once a run finishes cleanly.
"""
import asyncio
import json

from evals import _ragas_compat  # noqa: F401 - must run before importing ragas
from datetime import datetime, timezone
from pathlib import Path

from ragas import EvaluationDataset
from ragas.dataset_schema import SingleTurnSample
from ragas.metrics.collections import (
    AnswerRelevancy,
    ContextPrecisionWithReference,
    ContextRecall,
    Faithfulness,
)
from evals.judge import (
    JUDGE_EMBEDDING_MODEL,
    JUDGE_MODEL,
    JUDGE_TEMPERATURE,
    build_judge_embeddings,
    build_judge_llm,
)
from app.config.rag import DEFAULT_N_RESULTS
from app.services.rag_chain import get_rag_chain
from evals.questions import evaluation_questions

rag_chain = get_rag_chain()
RESULTS_DIR = Path(__file__).resolve().parent / "results"
CHECKPOINT_PATH = RESULTS_DIR / "checkpoint.json"


def build_evaluation_dataset():
    completed_samples = []
    failures = []
    chunk_ids_by_question = {}

    for i, item in enumerate(evaluation_questions, 1):
        print(f"[{i}/{len(evaluation_questions)}] {item['user_input']}")

        try:
            result = rag_chain.ask(
                query=item["user_input"],
                source_ids=item["source_ids"],
                n_results=DEFAULT_N_RESULTS,
            )
        except Exception as e:
            print(f"   FAILED: {e}")
            failures.append({"user_input": item["user_input"], "error": str(e)})
            continue

        retrieved_contexts = [
            doc["document"] for doc in result["retrieved_documents"]
        ]

        sample = SingleTurnSample(
            user_input=item["user_input"],
            response=result["answer"],
            retrieved_contexts=retrieved_contexts,
            reference=item["reference"],
        )

        completed_samples.append(sample)
        # which chunks were retrieved (needed for gold-label verification).
        chunk_ids_by_question[item["user_input"]] = [
            doc["chunk_id"] for doc in result["retrieved_documents"]
        ]

    return EvaluationDataset(samples=completed_samples), failures, chunk_ids_by_question


JUDGE_CONCURRENCY = 2
JUDGE_MAX_RETRIES = 4
JUDGE_RETRY_BASE_DELAY = 5  # seconds; doubles each retry (5, 10, 20, 40)

_judge_semaphore = asyncio.Semaphore(JUDGE_CONCURRENCY)


async def _call_with_retry(metric, item):
    async with _judge_semaphore:
        for attempt in range(JUDGE_MAX_RETRIES + 1):
            try:
                result = await metric.ascore(**item)
                return {"value": result.value, "reason": getattr(result, "reason", None)}
            except Exception as e:
                is_rate_limit = "rate_limit_exceeded" in str(e) or "429" in str(e)
                if is_rate_limit and attempt < JUDGE_MAX_RETRIES:
                    delay = JUDGE_RETRY_BASE_DELAY * (2 ** attempt)
                    print(f"   Rate limited, retrying in {delay}s (attempt {attempt + 1}/{JUDGE_MAX_RETRIES})...")
                    await asyncio.sleep(delay)
                    continue
                return {"value": None, "reason": f"FAILED: {e}"}


_SCORE_FIELDS = ("faithfulness", "answer_relevancy", "context_precision", "context_recall")


def _checkpoint_config():
    return {
        "judge_model": JUDGE_MODEL,
        "judge_temperature": JUDGE_TEMPERATURE,
        "judge_embedding_model": JUDGE_EMBEDDING_MODEL,
    }


def _load_checkpoint():
    if not CHECKPOINT_PATH.exists():
        return {}
    try:
        data = json.loads(CHECKPOINT_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        return {}

    if data.get("config") != _checkpoint_config():
        print("   Checkpoint was written under different judge settings - discarding it, starting fresh.")
        return {}

    rows = data.get("rows", {})
    # A row where any metric is None means retries were exhausted last time, not a
    # real score - don't let that count as "done", or it would be skipped forever.
    return {
        question: row
        for question, row in rows.items()
        if all(row.get(field) is not None for field in _SCORE_FIELDS)
    }


def _save_checkpoint(rows_by_question):
    RESULTS_DIR.mkdir(exist_ok=True)
    payload = json.dumps({"config": _checkpoint_config(), "rows": rows_by_question}, indent=2)
    tmp_path = CHECKPOINT_PATH.with_suffix(".tmp")
    tmp_path.write_text(payload)
    tmp_path.replace(CHECKPOINT_PATH)  # atomic on POSIX - never leaves a half-written checkpoint.json


async def _score_one_question(
    sample, category,
    retrieved_chunk_ids,
    faithfulness, answer_relevancy,
    context_precision, context_recall
):
    faithfulness_input = {
        "user_input": sample.user_input,
        "response": sample.response,
        "retrieved_contexts": sample.retrieved_contexts,
    }
    relevancy_input = {"user_input": sample.user_input, "response": sample.response}
    precision_input = {
        "user_input": sample.user_input,
        "reference": sample.reference,
        "retrieved_contexts": sample.retrieved_contexts,
    }
    recall_input = {
        "user_input": sample.user_input,
        "reference": sample.reference,
        "retrieved_contexts": sample.retrieved_contexts,
    }

    (
        faithfulness_result,
        relevancy_result,
        precision_result,
        recall_result,
    ) = await asyncio.gather(
        _call_with_retry(faithfulness, faithfulness_input),
        _call_with_retry(answer_relevancy, relevancy_input),
        _call_with_retry(context_precision, precision_input),
        _call_with_retry(context_recall, recall_input),
    )

    return {
        "user_input": sample.user_input,
        "category": category,
        "answer": sample.response,
        "reference": sample.reference,
        "retrieved_chunk_ids": retrieved_chunk_ids,
        "faithfulness": faithfulness_result["value"],
        "faithfulness_reason": faithfulness_result["reason"],
        "answer_relevancy": relevancy_result["value"],
        "answer_relevancy_reason": relevancy_result["reason"],
        "context_precision": precision_result["value"],
        "context_precision_reason": precision_result["reason"],
        "context_recall": recall_result["value"],
        "context_recall_reason": recall_result["reason"],
    }


async def score_dataset(dataset, category_by_question, chunk_ids_by_question):
    judge_llm = build_judge_llm()
    judge_embeddings = build_judge_embeddings()

    faithfulness = Faithfulness(llm=judge_llm)
    answer_relevancy = AnswerRelevancy(llm=judge_llm, embeddings=judge_embeddings)
    context_precision = ContextPrecisionWithReference(llm=judge_llm)
    context_recall = ContextRecall(llm=judge_llm)

    rows_by_question = _load_checkpoint()
    already_done = set(rows_by_question.keys())

    pending = [s for s in dataset if s.user_input not in already_done]

    if already_done:
        print(f"\nResuming from checkpoint: {len(already_done)} question(s) already scored, {len(pending)} remaining.")

    tasks = [
        asyncio.create_task(
            _score_one_question(
                sample,
                category_by_question[sample.user_input],
                chunk_ids_by_question[sample.user_input],
                faithfulness,
                answer_relevancy,
                context_precision,
                context_recall,
            )
        )
        for sample in pending
    ]

    for completed in asyncio.as_completed(tasks):
        row = await completed
        rows_by_question[row["user_input"]] = row
        _save_checkpoint(rows_by_question)
        print(f"   scored: {row['user_input']}")

    return rows_by_question


def _mean(values):
    scored = [v for v in values if v is not None]
    return round(sum(scored) / len(scored), 4) if scored else None


if __name__ == "__main__":
    rag_chain.reset_stats()

    dataset, failures, chunk_ids_by_question = build_evaluation_dataset()

    stats = rag_chain.get_stats()

    print(f"\nCompleted {len(dataset)}/{len(evaluation_questions)} evaluation samples.")
    if failures:
        print(f"{len(failures)} question(s) failed:")
        for f in failures:
            print(f"  - {f['user_input']}: {f['error']}")

    category_by_question = {q["user_input"]: q["category"] for q in evaluation_questions}

    rows_by_question = asyncio.run(score_dataset(dataset, category_by_question, chunk_ids_by_question))

    per_question = []
    for sample in dataset:
        row = rows_by_question[sample.user_input]
        per_question.append(row)

        print("\n" + "=" * 80)
        print("Question:", row["user_input"])
        print("Answer:", row["answer"])
        print(
            f"Faithfulness: {row['faithfulness']}  "
            f"AnswerRelevancy: {row['answer_relevancy']}  "
            f"ContextPrecision: {row['context_precision']}  "
            f"ContextRecall: {row['context_recall']}"
        )

    aggregate = {
        "faithfulness": _mean([r["faithfulness"] for r in per_question]),
        "answer_relevancy": _mean([r["answer_relevancy"] for r in per_question]),
        "context_precision": _mean([r["context_precision"] for r in per_question]),
        "context_recall": _mean([r["context_recall"] for r in per_question]),
    }

    print("\n" + "=" * 80)
    print("AGGREGATE BASELINE SCORES")
    for name, value in aggregate.items():
        print(f"  {name}: {value}")

    print("\nEvaluation Run Stats:")
    print(f"Requests: {stats['total_requests']}")
    print(f"Input tokens: {stats['total_input_tokens']}")
    print(f"Output tokens: {stats['total_output_tokens']}")
    print(f"Total cost: ${stats['total_cost_usd']:.6f}")

    RESULTS_DIR.mkdir(exist_ok=True)
    output_path = (
        RESULTS_DIR
        / f"baseline_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    )
    output_path.write_text(
        json.dumps(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "judge_model": JUDGE_MODEL,
                "judge_temperature": JUDGE_TEMPERATURE,
                "judge_embedding_model": JUDGE_EMBEDDING_MODEL,
                "generator_model": stats["model"],
                "n_results": DEFAULT_N_RESULTS,
                "aggregate": aggregate,
                "generation_stats": stats,
                "generation_failures": failures,
                "per_question": per_question,
            },
            indent=2,
        )
    )
    print(f"\nSaved results to {output_path}")

    CHECKPOINT_PATH.unlink(missing_ok=True)
