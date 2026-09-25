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

**Phase 1 — Evaluation Baseline.** Immediate execution path per
`PROJECT_PLAN.md`:

1. Inspect the current `RAGChain` / retrieval / source-ID / request-response
   configuration (don't assume — verify against the actual code).
2. Document the baseline configuration (embedding model, chunking strategy,
   chunk size/overlap, `n_results`, retrieval mode, generation model).
3. Build `evals/questions.py` (~15 test cases: football-profile factual,
   UEFA-report factual, cross-source, multi-context, hallucination-resistance).
4. Build `evals/run_eval.py`, calling the real `rag_chain.ask()` — never a
   parallel mock path.
5. Run RAGAS metrics (Faithfulness, Answer/Response Relevancy, Context
   Precision, Context Recall) and record the baseline before changing
   retrieval.

Do not add hybrid retrieval, reranking, memory, or agents until this baseline
exists and later phases explicitly build on it.

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

- `app/services/llm_service.py` `generate_answer()`: several error paths
  (auth error, not-found, rate limit, generic `OpenAIError`) return a plain
  string instead of the `{"answer", "usage", "cost_usd"}` dict shape that
  `rag_chain.ask()` expects — this raises a `TypeError` on those paths
  instead of surfacing a clean error.
- `app/api/routes.py`: the empty-query check
  (`if not request.query.strip() and len(request.query.strip()) == 0`) is
  redundant and unreachable anyway, since `SearchRequest.query` already has
  `min_length=1`.
