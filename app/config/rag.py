DEFAULT_COLLECTION = "football_docs_chunked"
DEFAULT_N_RESULTS = 3

DEFAULT_CHUNK_STRATEGY = "paragraph"
DEFAULT_CHUNK_SIZE = 400
DEFAULT_CHUNK_OVERLAP = 50

# Bumped manually when the retrieval setup itself changes (e.g. hybrid
# retrieval, a different embedding model) - deliberately independent of the
# chunking parameters above, which describe how chunks were produced, not
# what retrieval index they're served from.
INDEX_VERSION = "v1"

# --- Phase 2B: hybrid retrieval (dense + BM25, fused with RRF) ---
RETRIEVAL_MODE_DENSE = "dense"
RETRIEVAL_MODE_HYBRID = "hybrid"
DEFAULT_RETRIEVAL_MODE = RETRIEVAL_MODE_DENSE

# How many candidates each method (dense, BM25) contributes to fusion,
# before RRF ranks the union and the result gets truncated back down to
# n_results. Wider than n_results on purpose - fusion needs a real pool to
# re-rank, not just each method's already-final top n_results.
HYBRID_CANDIDATE_POOL = 20

# Cormack, Clarke, Buettcher, "Reciprocal Rank Fusion Outperforms Condorcet
# and Individual Rank Learning Methods," SIGIR 2009 - k=60 per the original
# paper (PROJECT_PLAN.md Phase 2B). Fixed, not tuned, so this stays a single
# clean variable change against the frozen baseline.
RRF_K = 60

# --- Phase 2D-1: reranking ---
# Locked experiment spec (PROJECT_PLAN.md Phase 2D) - not tuned mid-run.
# Unlike 2B's hybrid mode, candidates are NOT fused with RRF first: the
# deduplicated union of each method's own top-N is handed to the reranker
# intact, since RRF pre-fusion is exactly what underperformed in 2B.
RETRIEVAL_MODE_RERANK = "rerank"
RERANK_CANDIDATE_POOL = 10  # per retriever (dense, BM25), before dedup
RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"