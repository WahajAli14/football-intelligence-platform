# CLAUDE.md

Guidance for Claude Code (and any other agent) working in this repository.

## What this project is

Football Intelligence Platform — a RAG backend that answers football-tactics
questions grounded in multiple knowledge sources (a small built-in team
profiles dataset and the ingested UEFA Champions League technical report).
RAG is the current foundation, not the end product — see `PROJECT_PLAN.md`
for the full multi-phase roadmap (evaluation, hybrid retrieval, reranking,
memory, guardrails, ingestion platform, production engineering, security, MCP
interface, then V2 tool-calling/agent and V3 advanced-intelligence phases).

**Read `PROJECT_PLAN.md` before starting any non-trivial feature work.** It
defines the current phase, the canonical architectural rules, and the
dependency order between phases. Do not jump ahead to a later phase's
capability (e.g. hybrid retrieval, memory, agents) without checking that the
plan considers the prerequisites for it complete.

## Current phase

**Phase 1 — Evaluation Baseline.** Progress per `PROJECT_PLAN.md`'s Immediate
Execution Path:

1. ✅ `evals/questions.py` — 17 test cases covering all five required
   categories (football-profile factual, UEFA-report factual, multi-context
   single-source, cross-source, hallucination-resistance). Every reference was
   independently verified against the actual source documents.
2. ✅ `evals/run_eval.py` — runs every question through the real
   `rag_chain.ask()` (never a mock path) and builds a `ragas`
   `EvaluationDataset` of `SingleTurnSample`s. Per-question failures are
   isolated so one bad call doesn't lose the whole run. Stats are scoped to
   the run via `reset_stats()` before and `get_stats()` after.
3. ⬜ Not yet done: wiring up actual RAGAS metrics (Faithfulness, Context
   Precision/Recall, Answer Relevancy) on top of that dataset, and recording
   the baseline result. This is the next step.

Do not add hybrid retrieval, reranking, memory, or agents until the baseline
is recorded and later phases explicitly build on it.

## Architecture

```text
API / Presentation (FastAPI routes)
        ↓
Application / Orchestration (RAGChain)
        ↓
Domain / Service (retrieval, ranking/merging, context construction)
        ↓
Data Access (ChromaDB)      Provider Integration (OpenAI)
```

- `app/api/routes.py` — routes only. No retrieval or DB logic here.
- `app/services/rag_chain.py` — orchestrates retrieve → generate. No
  low-level Chroma/OpenAI details.
- `app/services/rag_service.py` — retrieval workflows, multi-source merging.
- `app/services/llm_service.py` — OpenAI client, prompt building, cost/usage
  tracking. Provider-specific code stays behind this boundary.
- `app/db/chroma_client.py` — ChromaDB access only.
- `app/config/source.py` — the `SourceID` allowlist. Public API surfaces only
  ever expose `source_id` values, never raw collection names.
- `app/models/request/`, `app/models/response/` — Pydantic schemas.

**Rules that apply to every change:**

- Routes stay thin; business logic lives in services.
- Never leak a raw Chroma collection name through a public response —
  `source_id` is the public contract (`app/config/source.py`).
- Keep provider-specific (OpenAI) code behind `llm_service.py`.
- A retrieval change (chunk size, overlap, hybrid vs dense, reranking,
  embedding model) is an experiment: baseline → change one variable → rerun
  eval → compare → keep/reject. Don't accept a technique just because it's
  more advanced — see "Retrieval Experiment Discipline" in
  `PROJECT_PLAN.md`.
- Memory (when it's built in Phase 4) supplies conversational context only —
  it must never replace or override the knowledge-base retrieval as the
  authoritative evidence source.
- MCP (Phase 9), when built, must call into the same service layer as the
  REST API — no separate retrieval implementation.

## Running the project

```bash
source .venv/bin/activate
pip install -r requirements.txt
python -m scripts.ingest_pdf        # ingest the UEFA report (recreate=True — rebuilds the collection)
uvicorn app.main:app --reload       # http://127.0.0.1:8000, docs at /football-docs
python test_chroma.py               # basic ChromaDB connectivity check
```

Requires a `.env` with `OPENAI_API_KEY` (see README.MD). Never commit `.env`.

### Running evaluations

Evaluation tooling (`ragas`) lives in a **separate virtual environment**, not
`.venv` — `ragas` pulls in a large, fast-moving dependency stack (langchain,
langgraph, instructor, etc.) that has no reason to dictate the production
API's dependency versions:

```bash
python3.13 -m venv .venv-eval
.venv-eval/bin/pip install -r requirements-eval.txt
.venv-eval/bin/python -m evals.run_eval
```

`requirements-eval.txt` is `-r requirements.txt` plus `ragas` — production's
`openai` pin must stay compatible with whatever `ragas` needs (`ragas`'s own
`instructor`/`langchain-openai` dependencies require `openai>=2.45`), since
both venvs are built from the same `requirements.txt` base. If you ever bump
`openai` in `requirements.txt`, rebuild `.venv` and rerun full regression
(`test_chroma.py`, `/search`, `/ask`, a forced OpenAI error) before rebuilding
`.venv-eval` on top of it.

`evals/_ragas_compat.py` is a **temporary** workaround for an open upstream
`ragas` bug (unconditional import of a removed `langchain_community` module —
see the file for issue links). Delete it once `ragas` ships a fix.

## Repo hygiene

- `.env`, `app/chroma_db/` (regenerable vector DB), `data/raw/pdfs/` (source
  PDFs — not redistributed, see `data/README.md`), `logs/` (generated
  runtime logs), `__pycache__/`, `.venv/` are all gitignored. Do not
  re-introduce them into git history.
- This repo pushes to the maintainer's personal GitHub account
  (`WahajAli14`) via an SSH host alias (`github-personal`), scoped to this
  folder only via repo-local `git config user.name`/`user.email` — do not
  change global git config when working here.

## Known code issues (flagged, not yet fixed)

- `/search` requires `OPENAI_API_KEY` to be set even though it never calls
  OpenAI, because `routes.py` calls `get_rag_chain()` at import time, which
  eagerly constructs `LLMService()`. A pure retrieval service (no LLM
  dependency) would let `/search` work independently of `/ask`.
- CORS is wide open (`allow_origins=["*"]`) — fine for local dev, needs
  explicit origins before any real deployment (Phase 6/7).
- `/health` returns a hardcoded `"documents_available": 8` regardless of
  actual collection state.
- `app/services/chunking.py`: fallback doc id typo, `'unkown'` instead of
  `'unknown'` (cosmetic).
