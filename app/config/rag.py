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