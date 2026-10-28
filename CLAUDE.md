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

1. ✅ `evals/questions.py` — 23 test cases covering all five required
   categories (football-profile factual, UEFA-report factual, multi-context
   single-source, cross-source, hallucination-resistance). Every reference was
   independently verified against the actual source documents.
2. ✅ `evals/run_eval.py` — runs every question through the real
   `rag_chain.ask()` (never a mock path) and builds a `ragas`
   `EvaluationDataset` of `SingleTurnSample`s. Per-question failures are
   isolated so one bad call doesn't lose the whole run. Stats are scoped to
   the run via `reset_stats()` before and `get_stats()` after.
3. ✅ RAGAS metrics (Faithfulness, Context Precision/Recall, Answer
   Relevancy) wired up via `evals/judge.py` (locked judge: `gpt-4.1`,
   `temperature=0` — see that file's docstring for why) and scored with
   rate-limit handling and per-question checkpointing. Baseline recorded in
   `evals/results/`; breakdown by category via `evals/analyze_results.py`.
   See `PROJECT_PLAN.md` Phase 1 §4.3 for a known Context Precision
   limitation on the `multi_context`/`unsupported` categories — read that
   before treating a low aggregate score as a retrieval problem.

Phase 1 is complete.

**Phase 2 — Retrieval Quality, in progress.** Per `PROJECT_PLAN.md`:

- ✅ 2A — chunk lineage metadata, gold retrieval labels
  (`evals/gold_labels.py`), deterministic metrics
  (`evals/gold_metrics.py`, `evals/retrieval_eval.py`).
- ✅ 2B — hybrid retrieval (dense + BM25, RRF) implemented, measured
  against the gold labels, and **rejected** — underperforms dense-only on
  every deterministic metric, on both the original and cleaned-chunking
  collections. `DEFAULT_RETRIEVAL_MODE` stays `"dense"`. Chunking cleanup
  (`clean_and_merge_chunks`, the `_v2` collections) is a confirmed,
  independent win, kept regardless of the hybrid outcome. Full numbers in
  `EVAL_FINDINGS.md`.
- ⬜ 2C (explicit metadata filtering), 2D (reranking) — not started. Do
  not add reranking, memory, or agents (Phase 3+) without discussing it
  first.

Before running a full `evals/run_eval.py` pass (generation + RAGAS judge,
~19 OpenAI calls per question) while iterating on a retrieval change, use
`evals/retrieval_eval.py` first — Recall@k/Precision@k/MRR/nDCG@k against
the gold labels, zero OpenAI calls. Only spend a full run once a
retrieval-only result looks genuinely promising (see EVAL_FINDINGS.md's
quota-exhaustion entry for why this matters).

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

See `EVAL_FINDINGS.md` for the resolved counterpart - failure points
already diagnosed and fixed (or deliberately deferred with a documented
reason) while building the evaluation pipeline. Check there before
re-investigating something from scratch.

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
