"""
RAGAS judge configuration for the Phase 1 evaluation baseline.

Locked for every run of this evaluation dataset - see PROJECT_PLAN.md's
Retrieval Experiment Discipline. Changing judge model or embedding model
changes the measuring instrument itself, so a later score difference could
mean "retrieval got better" or just "the judge changed."

judge_model:
    gpt-4.1, not a GPT-5+/6+ model. Verified live against the raw OpenAI API
    (not ragas) that every GPT-5+/6+ model (gpt-5, gpt-5-mini, gpt-6.1-sol,
    gpt-6-luna) rejects temperature=0 outright ("Only the default (1) value
    is supported"), while gpt-4.1 and gpt-4.1-mini accept it. We initially
    used gpt-6-luna (cheaper, stronger on benchmarks than the gpt-4.1-mini
    generator), but empirical testing (3 repeated calls on identical
    input, across all 4 metrics, across multiple real questions) showed
    genuine run-to-run variance - e.g. Faithfulness swinging 0.44 to 0.78 on
    the exact same answer+context, because gpt-6-luna's temperature is
    permanently forced to 1.0 with no override, by OpenAI itself, not by
    ragas. gpt-4.1 removes that noise at the source (real temperature=0)
    instead of managing it with repeated-sampling/averaging, and is still a
    stronger, different-tier judge than the gpt-4.1-mini generator.

judge_embedding_model:
    text-embedding-3-small, used by Answer/Response Relevancy to compare
    synthetic questions (generated from the answer) against the original
    question via cosine similarity. Plenty accurate for comparing short
    questions; cost is negligible at this dataset size either way.
"""
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import AsyncOpenAI
from ragas.embeddings.base import embedding_factory
from ragas.llms.base import llm_factory

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

JUDGE_MODEL = "gpt-4.1"
JUDGE_TEMPERATURE = 0
JUDGE_EMBEDDING_MODEL = "text-embedding-3-small"


def _api_key()-> str:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set in environment variables.")
    return api_key


def build_judge_llm():
    client = AsyncOpenAI(api_key=_api_key())
    return llm_factory(
        model=JUDGE_MODEL,
        client=client,
        temperature=JUDGE_TEMPERATURE,
    )

def build_judge_embeddings():
    client = AsyncOpenAI(api_key=_api_key())
    return embedding_factory(
        "openai",
        model=JUDGE_EMBEDDING_MODEL,
        client=client,
        interface="modern"
    )