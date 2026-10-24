# Evaluation Findings

A record of failure points discovered while building the Phase 1/2A
evaluation pipeline (`evals/`), and how each was resolved. `CLAUDE.md`'s
"Known code issues" section lists what's still open; this file is the
resolved counterpart - read it before re-investigating something that's
already been diagnosed here.

## Judge model: GPT-5+/6+ models reject temperature control

**What broke:** early baselines used `gpt-6-luna` as the judge. Repeated
scoring of identical input showed real run-to-run variance (e.g.
Faithfulness swinging 0.44 to 0.78 on the exact same answer+context).

**Root cause:** verified directly against the raw OpenAI API (not ragas)
that every GPT-5+/6+ model rejects `temperature != 1` outright ("Only the
default (1) value is supported"). The model's temperature was permanently
locked to 1.0 regardless of what was requested - this is an OpenAI-side
constraint, not a ragas bug.

**Resolution:** switched the judge to `gpt-4.1`, which honors
`temperature=0` for genuine reproducibility. See `evals/judge.py`'s
docstring for the full reasoning. Don't reach for repeated-sampling/
averaging to manage this kind of variance when a model that supports real
`temperature=0` is available - it treats the symptom, not the cause.

## Rate-limit crash on the first full gpt-4.1 run

**What broke:** the first full run against the new judge failed on ~64% of
questions with rate-limit errors.

**Root cause:** `asyncio.gather` fired all ~92 judge calls (23 questions x
4 metrics) simultaneously against a 30,000 TPM account limit for `gpt-4.1`.

**Resolution:** added a concurrency cap (`asyncio.Semaphore`, tuned to 2)
and exponential backoff retry (`evals/run_eval.py`'s `_call_with_retry`).

## Long runs getting killed mid-flight

**What broke:** the Bash tool's 30-minute background-task limit killed two
full eval runs partway through, independent of any code bug.

**Resolution:** restructured scoring to be per-question and checkpointed to
`evals/results/checkpoint.json` as each question finishes (atomic write via
temp-file + `Path.replace()`, judge-config fingerprint validation so a
checkpoint from different settings is discarded rather than silently
reused, and exclusion of partial-failure rows - a question with any `None`
metric doesn't count as "done"). Both real kill events were recovered from
cleanly afterward.

## RAGAS's modern metrics never populate `.reason`

**What looked broken:** every `{metric}_reason` field in every baseline
JSON is `null`.

**Root cause:** checked `ragas.metrics.collections`' actual source
(`faithfulness/metric.py`, `answer_relevancy/metric.py`,
`context_precision/metric.py`, `context_recall/metric.py`, ragas 0.4.3) -
none of them construct `MetricResult` with a `reason` argument, so it
defaults to `None` for every score, on every question, always. This is not
something our retry/checkpoint code could have captured even if it tried.

**Workaround, where the reason is actually needed:** `ContextPrecisionWithReference`
*does* generate a reason per retrieved chunk internally (visible in
`ContextPrecisionOutput`), it's just discarded before the aggregate score is
returned. To see it, replay the judge's per-chunk prompt/call directly
rather than relying on `metric.ascore()`'s return value - see the diagnostic
approach used to find the next two issues below.

## Context Precision is structurally unreliable for two categories

**What looked broken:** `multi_context` questions scored near-zero Context
Precision despite retrieval fetching exactly the right chunks;
`unsupported` questions produced wildly inconsistent Context Precision
(anywhere from 0 to ~1) across runs.

**Root cause:** `ContextPrecisionWithReference` judges each retrieved chunk
**in isolation** against the *whole* reference answer. For a comparison
question (`multi_context`) whose reference synthesizes two teams, no single
chunk about one team can ever satisfy that check - every chunk fails
regardless of retrieval quality. For "nothing is relevant" questions
(`unsupported`), there's no principled definition of a "useful" chunk, and
the judge gives inconsistent verdicts on near-identical chunks as a result.

**Resolution:** documented as a known limitation (`PROJECT_PLAN.md` Phase 1
§4.3). Read Context Precision per-category (`evals/analyze_results.py`),
never as a single aggregate, and never "fix" retrieval in response to a low
aggregate score without checking whether it's these two categories dragging
it down.

## `chunk_id` was silently dropped from the retrieval pipeline

**What broke:** no retrieved document - not in the `/search` or `/ask` API
response, not in the eval dataset - could be traced back to the specific
chunk it came from, which blocked building gold retrieval labels (nothing
stable to reference).

**Root cause:** `collection.query()`'s `results["ids"]` was requested from
Chroma but never read in `rag_service.py`'s `retrieve_similar_documents()`.

**Resolution:** surfaced `chunk_id` end-to-end - `rag_service.py`, the
`DocumentResult` response model (`/ask`'s response needed no change, since
it's a raw `List[Dict]`), and `evals/run_eval.py`'s baseline output
(`retrieved_chunk_ids` per question). Verified with a direct service call
and a live `/search` request before trusting it.

## PDF text-extraction order doesn't always match reading order

**What was found:** building gold retrieval labels for the Liverpool/Milan
pressing question, the supporting text turned out to be split across
non-contiguous chunk indices (412-415, then 417) - and 412-415 *logically
continue* a quote that starts in 417, despite having lower chunk indices.

**Root cause:** the UEFA report PDF interleaves a sidebar/pull-quote with
the main body paragraph on that page. `pdftotext`/`unstructured` extracted
them in a different order than the visual reading order.

**Status:** documented, not fixed. No amount of chunk-size/overlap tuning
can make a contiguous chunk range capture this passage - it needs a
layout-aware re-extraction (e.g. `unstructured`'s `hi_res` mode), which
would change every chunk ID and invalidate the gold labels built against
the current extraction. Deliberately deferred rather than bundled into
unrelated work. See `evals/gold_labels.py`'s note on this question.

## A hallucination-resistance reference turned out to be subtly wrong

**What was found:** the "unsupported" question about Erling Haaland's goal
tally assumed the corpus had zero information about him. Building gold
labels by searching the raw corpus (not retrieval output) found the report
*does* mention one specific Haaland goal (against Sparta Praha, on an
"eye-catching goals" list) - just not a cumulative tally, which is what the
question actually asks.

**Why it was almost missed:** the first search for "Haaland" used `| head
-5`, which truncated mid-chunk and cut off the one line that contained the
match - so it looked like "not found" on first pass. Caught by re-checking
directly against the raw file instead of trusting a piped/truncated view.

**Resolution:** split a new `partial_evidence` category out from
`unsupported` (relevant evidence exists but is insufficient, vs. no
relevant evidence at all). Rewrote the reference in `evals/questions.py` to
describe what the corpus actually contains, and gave it its own gold label
(`chunk810`) in `evals/gold_labels.py` rather than an empty one.

## Building gold retrieval labels from retrieval output would be circular

**Risk avoided:** if "relevant chunk" labels are built by looking at what
the current retriever returns, the labels just validate retrieval against
itself - a bad retriever and a "correct" gold set could agree with each
other for the wrong reason.

**Approach used:** dumped the full corpus directly via ChromaDB's `.get()`
(not `.query()` - no embedding similarity involved) to local JSONL files,
then found supporting chunks by searching the raw text for the specific
facts each reference cites. Gold labels were built with zero dependency on
what the retriever happens to rank highly.
