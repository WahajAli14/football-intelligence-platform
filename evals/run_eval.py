"""
Run evaluation questions through the real RAGChain and build a RAGAS dataset.

This first version does not run RAGAS metrics yet - it only verifies that the
retrieve -> generate -> dataset pipeline is wired correctly:
all questions run -> RAGChain answers -> retrieved documents are captured ->
references are attached -> dataset builds successfully.

RAGAS scoring is added in a follow-up step once this is confirmed working.
"""

from evals import _ragas_compat  # noqa: F401 - must run before importing ragas

from ragas import EvaluationDataset
from ragas.dataset_schema import SingleTurnSample

from app.config.rag import DEFAULT_N_RESULTS
from app.services.rag_chain import get_rag_chain
from evals.questions import evaluation_questions

rag_chain = get_rag_chain()


def build_evaluation_dataset():
    completed_samples = []
    failures = []

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

    return EvaluationDataset(samples=completed_samples), failures


if __name__ == "__main__":
    rag_chain.reset_stats()

    dataset, failures = build_evaluation_dataset()

    stats = rag_chain.get_stats()

    print(f"\nCompleted {len(dataset)}/{len(evaluation_questions)} evaluation samples.")
    if failures:
        print(f"{len(failures)} question(s) failed:")
        for f in failures:
            print(f"  - {f['user_input']}: {f['error']}")

    for sample in dataset:
        print("\n" + "=" * 80)
        print("Question:", sample.user_input)
        print("Answer:", sample.response)
        print("Reference:", sample.reference)
        print("Retrieved contexts:", len(sample.retrieved_contexts))

    print("\nEvaluation Run Stats:")
    print(f"Requests: {stats['total_requests']}")
    print(f"Input tokens: {stats['total_input_tokens']}")
    print(f"Output tokens: {stats['total_output_tokens']}")
    print(f"Total cost: ${stats['total_cost_usd']:.6f}")
