# Football Intelligence Platform

A tactical intelligence assistant that helps football analysts research, compare, and explain football information using grounded evidence from multiple knowledge sources. The current implementation is a Retrieval-Augmented Generation (RAG) backend: it loads football knowledge sources (a built-in team profiles dataset and the 2025 UEFA Champions League technical report), splits them into chunks, stores embeddings in a persistent ChromaDB database, retrieves relevant passages, and uses an OpenAI model to generate answers grounded in those passages.

RAG is the foundation of this project, not the final product. See [`PROJECT_PLAN.md`](PROJECT_PLAN.md) for the full architecture, phased roadmap (evaluation baseline → hybrid retrieval/reranking → context & guardrails → memory → ingestion platform → production engineering → security → MCP interface → agentic V2/V3), and the guiding principles behind it. See [`CLAUDE.md`](CLAUDE.md) for repo-specific working conventions.

## Project status

The current phase is **Phase 1 — Evaluation Baseline** (see `PROJECT_PLAN.md`). The RAG MVP described below is functionally complete and is the foundation the evaluation baseline will be measured against.

| Area | Status | Notes |
| --- | --- | --- |
| FastAPI application | Complete | API routing, CORS, startup/shutdown lifecycle, and interactive documentation |
| Document loading | Complete | Supports PDF, text files, raw text, directories, and the sample football dataset |
| PDF ingestion | Complete | Loads the included UEFA report and recreates its ChromaDB collection |
| Document chunking | Complete | Fixed, paragraph, and sentence-based semantic strategies |
| Vector storage | Complete | Persistent local ChromaDB collections and default embeddings |
| Semantic search | Complete | Ranked passages with metadata and similarity scores |
| RAG answer generation | Complete | Retrieves context and generates document-grounded OpenAI answers |
| Usage and cost tracking | Complete | Tracks token usage, request count, and estimated model cost in memory |
| Automated tests | Partial | A basic ChromaDB check exists; endpoint and service test coverage is still needed |
| Error handling | Partial | Common OpenAI errors are handled; API-wide error responses need further hardening |
| Deployment | Not started | No Docker, CI/CD, authentication, or production server configuration yet |
| Frontend | Not started | This repository currently provides a backend API only |

The completion figure is an estimate for a usable local MVP, not a production-readiness score.

## Features

- Persistent local vector storage with ChromaDB
- PDF and text document loading
- Configurable fixed, paragraph, and semantic chunking
- Semantic document search
- Retrieval plus OpenAI answer generation
- Prompts designed to reduce unsupported answers
- Source passages, metadata, ranks, and similarity scores in responses
- In-memory token usage and estimated cost statistics
- Swagger and ReDoc API documentation

## Technology stack

- Python
- FastAPI and Uvicorn
- ChromaDB
- OpenAI API
- Pydantic
- `unstructured`, `pypdf`, and `pdfminer.six`

## Project structure

```text
football-intelligence-platform/
├── app/
│   ├── api/routes.py               # API endpoints
│   ├── config/                     # RAG defaults, source registry, and model pricing
│   ├── data/football_docs.py       # Small built-in football dataset
│   ├── db/chroma_client.py         # Persistent ChromaDB client
│   ├── models/                     # Request and response schemas
│   ├── services/                   # Loading, chunking, retrieval, and generation
│   ├── chroma_db/                  # Local persistent vector database (gitignored)
│   └── main.py                     # FastAPI application entry point
├── data/
│   ├── README.md                   # Where to obtain source documents (not committed)
│   └── raw/pdfs/                   # Source PDFs (gitignored; see data/README.md)
├── logs/                           # Chunking experiment logs (gitignored)
├── scripts/ingest_pdf.py           # UEFA report ingestion command
├── test_chroma.py                  # Basic ChromaDB connectivity check
├── requirements.txt
├── PROJECT_PLAN.md                 # Full architecture and phased roadmap
├── CLAUDE.md                       # Repo-specific conventions for Claude Code
└── README.MD
```

## Prerequisites

- Python 3.10 or newer is recommended
- An OpenAI API key
- Optional: the `pdftotext` command for faster PDF extraction. If it is unavailable, the loader falls back to `unstructured`.

On Ubuntu/Debian, `pdftotext` can be installed with:

```bash
sudo apt-get install poppler-utils
```

## Setup

Run all commands from the project root.

1. Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

On Windows PowerShell:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
```

2. Install dependencies:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

3. Create a `.env` file in the project root:

```env
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4.1-mini
```

`OPENAI_MODEL` is optional and defaults to `gpt-4.1-mini`. Never commit the `.env` file or expose the API key.

## Ingest the PDF

The source PDF is **not** committed to this repository (large file; third-party redistribution terms unclear). See [`data/README.md`](data/README.md) for where to obtain it. Place it at:

```text
data/raw/pdfs/UCL_Technical-Report_2025_DIGITAL.pdf
```

Then ingest it before searching if the `ucl_technical_report_2025` collection is missing or needs to be rebuilt:

```bash
python -m scripts.ingest_pdf
```

This command:

1. extracts text from the PDF;
2. creates fixed-size chunks of 800 characters with 100 characters of overlap;
3. recreates the `ucl_technical_report_2025` collection; and
4. stores its embeddings and metadata in `app/chroma_db/`.

Warning: ingestion currently uses `recreate=True`, so rerunning it replaces that collection.

## Run the API

Start the development server from the project root:

```bash
uvicorn app.main:app --reload
```

The service will be available at:

- API root: <http://127.0.0.1:8000/>
- Swagger UI: <http://127.0.0.1:8000/football-docs>
- ReDoc: <http://127.0.0.1:8000/redoc>
- Health check: <http://127.0.0.1:8000/api/v1/health>

For access from another device on the local network:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## API endpoints

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/` | Basic service information |
| `GET` | `/api/v1/health` | Health check |
| `GET` | `/api/v1/info` | API name, version, and endpoint summary |
| `POST` | `/api/v1/search` | Retrieve semantically similar passages |
| `POST` | `/api/v1/ask` | Retrieve passages and generate a grounded answer |
| `GET` | `/api/v1/stats` | View in-memory LLM token and cost statistics |
| `POST` | `/api/v1/stats/reset` | Reset the in-memory LLM statistics |

`n_results` must be between 1 and 10 and defaults to 3.

### Search documents

```bash
curl -X POST http://127.0.0.1:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Which teams use high pressing?",
    "n_results": 3
  }'
```

The response includes the matching passage text, metadata, rank, and similarity score. Search performs retrieval only and does not make an answer-generation request to OpenAI.

### Ask a question

```bash
curl -X POST http://127.0.0.1:8000/api/v1/ask \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What tactical trends were visible in the competition?",
    "n_results": 3
  }'
```

This endpoint retrieves relevant passages and sends them to the configured OpenAI model. Its response includes the generated answer, retrieved passages, token usage, and estimated cost.

### View and reset usage statistics

```bash
curl http://127.0.0.1:8000/api/v1/stats
curl -X POST http://127.0.0.1:8000/api/v1/stats/reset
```

Statistics are stored in process memory. They reset when the server restarts and are not shared across multiple server workers.

## Utility commands

Check that ChromaDB can be opened:

```bash
python test_chroma.py
```

Run the built-in football dataset chunking experiment:

```bash
python -m app.services.vector_store_chunked \
  "Which team uses high pressing?" paragraph 400 50
```

Arguments are query, chunking strategy, chunk size, and overlap. Valid strategies are `fixed`, `paragraph`, and `semantic`.

## Data and configuration

- ChromaDB persists locally in `app/chroma_db/`.
- API search and ask routes currently use the `ucl_technical_report_2025` collection.
- The default retrieval count is 3.
- The OpenAI generation default is `gpt-4.1-mini`, temperature `0.3`, and maximum output length of 300 tokens.
- Model prices used for estimates are defined in `app/config/pricing.py` and must be maintained manually.

## Known limitations and next work

- Add unit and integration tests for loaders, chunking, retrieval, and every endpoint.
- Make the collection name and ingestion settings environment-configurable.
- Validate collection availability and document counts dynamically in the health endpoint.
- Improve API error propagation when OpenAI generation fails.
- Persist usage statistics if historical reporting is required.
- Review and update the hard-coded pricing table before relying on cost estimates.
- Add structured logging, authentication, rate limiting, and production CORS settings.
- Add Docker and deployment configuration.
- Add CI checks for formatting, linting, and tests.

## Troubleshooting

### `OPENAI_API_KEY is not set`

Confirm that `.env` exists in the project root and contains a valid `OPENAI_API_KEY`. The current application initializes the LLM service during startup, so the key is required to start the API, including when using retrieval-only routes.

### No relevant documents are returned

Run the PDF ingestion command again and confirm that it reports chunks in the `ucl_technical_report_2025` collection:

```bash
python -m scripts.ingest_pdf
```

### PDF extraction fails

Install the dependencies from `requirements.txt`. Installing `poppler-utils` so that `pdftotext` is available may also improve extraction reliability.

### Run command reports `No module named app`

Run Uvicorn from the repository root—the directory containing `app/` and `requirements.txt`.

## License

No license file is currently included. Add one before distributing or reusing the project publicly.
