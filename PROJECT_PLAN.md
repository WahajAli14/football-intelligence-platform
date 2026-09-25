# Football Intelligence Platform

## Product Statement

Football Intelligence Platform is a tactical intelligence assistant that helps
football analysts research, compare, and explain football information using
grounded evidence from multiple knowledge sources.

## Project Identity

- Project name: Football Intelligence Platform
- Local folder: football-intelligence-platform
- GitHub repository: football-intelligence-platform

## End Goal

Build a production-oriented AI platform for football knowledge and tactical
intelligence that can:

- ingest and manage multiple football knowledge sources
- retrieve information accurately across documents and structured sources
- generate grounded answers with citations
- evaluate retrieval and generation quality
- support metadata-aware, hybrid, and reranked retrieval
- maintain conversational memory safely
- expose capabilities through APIs and MCP
- evolve into an agentic football intelligence system with specialized agents
- be deployable, observable, secure, and maintainable

RAG is the foundation of the project, not the final product.

## Table of Contents

- Project Identity
- Product Statement
- End Goal
- Core Architecture
- Current Technology Stack
- Security Principles From the Beginning
- Current Baseline Configuration
- Current Progress
- Phase 1 - Evaluation Baseline
- Retrieval Experiment Discipline
- Phase 2 - Retrieval Quality
- Phase 3 - Context, Grounding and Advanced Guardrails
- Failure Handling
- Phase 4 - Conversation and Memory
- Phase 5 - Ingestion Platform
- Embedding / Index Version Migration
- Phase 6 - Production Engineering
- Phase 7 - Security and Permissions
- Phase 8 - User-Facing Football Intelligence Workflows
- Phase 9 - MCP Interface & Tool Exposure
- Phase 10 - V1 Portfolio Documentation
- V2 - Tools and Single-Agent Intelligence
- JEV Note
- V3 - Advanced Intelligence
- Ongoing Production Optimization
- Final Target Architecture
- Portfolio Goal
- High-Level Roadmap
- Guiding Principles
- Architectural Layering and Separation of Concerns
- Versioned Completion Targets
- Final Product Principle
- Canonical Rules
- Immediate Execution Path

## 1. Core Architecture

```text
Users / Client
      |
      v
FastAPI
      |
      v
RAG / Intelligence Orchestrator
      |
      +-------------------------+
      |                         |
      v                         v
Retrieval Layer            LLM Layer
      |                         ^
      v                         |
Vector / BM25 / Reranker        |
      |                         |
      +------ Context ----------+
                |
                v
          Grounded LLM
                |
                v
         Grounding / QA
```

Knowledge Sources:

- PDFs
- football profiles
- future structured football sources

Evolution:

```text
Evaluation -> Retrieval Experiments -> Hybrid Search -> Reranking
-> Context/Grounding -> Memory -> Guardrails -> Production Engineering
-> MCP Interface -> Tools/Agent -> Advanced Intelligence
```

## 2. Current Technology Stack

- Python
- FastAPI
- Pydantic
- ChromaDB
- OpenAI models
- PDF ingestion using pdftotext
- unstructured as PDF fallback
- Custom chunking
- Persistent vector storage
- Token and cost tracking
- Source registry
- Multi-source retrieval
- RAGAS evaluation planned

### 2.1 Security Principles From the Beginning

Basic security is a design constraint from the start rather than a late retrofit.

Apply from the beginning:

- environment variables and secrets management
- request/input validation
- public source allowlisting through SourceID
- safe error responses
- no raw collection names exposed through public APIs
- prompt-injection awareness
- token/request limits
- defensive prompt handling where user-controlled text can affect retrieval or
  generation

Advanced guardrails are implemented later in the Context and Generation Quality
phase:

- hallucination / grounding checks
- answer constraints
- refusal when evidence is insufficient
- prompt management and versioning
- stronger output validation

Add deeper security controls when the product requires them:

- document-level permissions
- source-level ACLs
- advanced authorization
- audit logging
- stronger tenant/user isolation

## Current Baseline Configuration

Before any retrieval improvement is evaluated, record the exact configuration
used for the baseline.

At minimum document:

- embedding model
- chunking strategy
- chunk size
- chunk overlap
- n_results
- retrieval mode
- source selection behavior
- vector database/index configuration relevant to retrieval
- generation model used during evaluation

The baseline must be captured before changing retrieval so later experiments
can be compared against a known reference configuration.

## 3. Current Progress

### Completed

- FastAPI application structure
- health endpoint
- /search
- /ask
- /stats
- /stats/reset
- persistent ChromaDB client
- football profile knowledge base
- OpenAI-based answer generation
- RAG orchestration
- token tracking
- cost tracking
- configurable RAG settings
- fixed chunking
- paragraph chunking
- sentence-grouping chunking
- chunk overlap
- chunk metadata
- document loader
- TXT loading
- directory loading
- chunked ingestion
- original vs chunked collection comparison
- longer football documents
- chunking experiments
- PDF folder structure
- real UEFA technical report ingestion
- pdftotext extraction
- unstructured PDF fallback
- fixed PDF chunking configuration
- reusable PDF ingestion script
- UEFA report Chroma collection
- PDF search through /search
- PDF answers through /ask
- public source_id abstraction
- knowledge source registry
- dynamic source routing
- multi-source /search
- multi-source /ask
- source attribution in retrieved metadata

### Current Stage

RAG evaluation baseline

The next goal is to establish measurable quality before adding more retrieval
complexity.

## Phase 1 - Evaluation Baseline

### 4.1 Evaluation Dataset

Create `evals/questions.py` containing approximately 15 controlled test cases:

- football-profile factual questions
- UEFA-report factual questions
- cross-source questions
- multi-context questions
- unsupported / hallucination-resistance questions

Each test case should contain:

```json
{
    "user_input": "...",
    "reference": "...",
    "source_ids": [...]
}
```

### 4.2 Evaluation Runner

Create:

`evals/run_eval.py`

The runner should:

1. load evaluation questions
2. call the real `rag_chain.ask()`
3. collect generated responses
4. collect retrieved contexts
5. preserve reference answers
6. build the evaluation dataset
7. later pass it to RAGAS

### 4.3 RAGAS Integration

Initial metrics:

- Faithfulness
- Answer / Response Relevancy
- Context Precision
- Context Recall

Later add:

- Factual Correctness
- additional task-specific metrics where useful

Store evaluation outputs so later retrieval changes can be compared against the
baseline.

### 4.4 Retrieval Experiment Discipline

Every meaningful retrieval change should be treated as an experiment rather
than automatically being accepted.

```text
Define baseline
      ↓
Change ONE meaningful variable
      ↓
Run the same evaluation dataset
      ↓
Compare quality + latency + cost
      ↓
Keep / reject / investigate
```

Examples:

- 800-token chunks vs 500-token chunks
- different overlap values
- dense-only vs hybrid retrieval
- different n_results
- reranking vs no reranking
- different embedding models

Track at minimum:

- Context Precision
- Context Recall
- Faithfulness
- Answer / Response Relevancy
- latency
- token usage
- estimated cost

A new retrieval technique should not remain in the system merely because it is
more advanced. It should show measurable value.

## Phase 2 - Retrieval Quality

After the baseline is measured:

### Metadata Filtering

Support filtering by useful metadata such as:

- source
- document
- team
- competition
- season
- page or section where available

Do not expose raw database collection names to public clients.

### Better Source and Document Metadata

Add richer identifiers:

- source ID
- document ID
- source title
- document title
- page metadata
- chunk position
- ingestion version

### Hybrid Retrieval

Combine:

Dense/vector retrieval
+
Lexical/BM25 retrieval

Normalize and merge candidate scores.

### Reranking

Retrieve a wider candidate pool and rerank the candidates before generation.

Target flow:

```text
Query
 -> dense + lexical retrieval
 -> candidate pool
 -> reranker
 -> final contexts
 -> LLM
```

For advanced experimentation in V3, a JEV-based stage may be evaluated after
the standard reranker:

```text
Candidate Retrieval
        ↓
Hybrid Search
        ↓
Reranker
        ↓
JEV
        ↓
Final Context
        ↓
LLM
```

JEV is optional. It should only remain if evaluation shows measurable
improvement over the simpler reranking pipeline.

Measure every major retrieval change against the RAGAS baseline.

## Phase 3 - Context, Grounding and Advanced Guardrails

Basic guardrails already exist from the beginning. This phase strengthens
generation-time controls after retrieval is measurable and stable.

Add:

- query rewriting / expansion when justified
- context compression
- context/token budgeting
- stronger citation formatting
- anti-hallucination instructions
- grounded-answer checks
- answer constraints
- graceful refusal / "insufficient information" behavior
- prompt management and versioning
- stronger prompt-injection defenses
- output validation and advanced guardrails

The model should distinguish:

retrieved evidence
vs
model-generated synthesis

### Failure Handling

The system must distinguish between infrastructure failure and insufficient
evidence.

#### Infrastructure Failure

```text
Infrastructure / provider / database failure
        ↓
Controlled error
        ↓
No fabricated answer
```

Examples include:

- vector database unavailable
- LLM provider failure
- ingestion/index corruption
- timeout or dependency failure

The system should return a controlled error and must not generate an answer
pretending retrieval succeeded.

#### Insufficient Evidence

```text
Retrieval succeeds
        ↓
Evidence is insufficient
        ↓
Grounded refusal / insufficient-information response
```

The system should explicitly state that the available evidence is insufficient
rather than inventing missing facts.

## Phase 4 - Conversation and Memory

Memory remains part of V1, but it should only be implemented after retrieval
quality and the evaluation baseline are stable.

Important separation:

knowledge retrieval != conversation memory

Target flow:

```text
User Query
    ↓
Retrieve authoritative football evidence
    ↓
Retrieve relevant conversation history
    ↓
Context Builder
    ↓
LLM
```

Implement:

- session IDs
- short-term conversational history
- relevant memory selection
- token-aware history management
- reference resolution across turns where useful

Memory provides conversational context. The football knowledge base remains
the authoritative evidence source.

Do not allow conversation memory to replace or override authoritative
retrieval.

## Phase 5 - Ingestion Platform

Evolve ingestion beyond one-off scripts and formalize the data pipeline:

```text
Source
  ↓
Extract
  ↓
Clean
  ↓
Validate
  ↓
Deduplicate
  ↓
Chunk
  ↓
Embed
  ↓
Store
  ↓
Index
```

This pipeline should preserve source lineage and make ingestion decisions
measurable and repeatable.

Add:

- batching
- upsert
- update/delete support
- document deduplication safeguards
- PDF boilerplate cleaning
- page-level metadata
- chunking policies by document type
- embedding-model/version metadata
- upload API
- background ingestion jobs
- ingestion status endpoint

Eventually move from collection-per-document patterns toward a scalable shared
knowledge-base design with metadata-based isolation where appropriate.

### Embedding / Index Version Migration

When changing embedding models or other index-defining settings, do not
overwrite the existing baseline index in place.

Use a versioned migration flow:

```text
Embedding model v1
       ↓
New embedding model
       ↓
New versioned index / collection
       ↓
Re-embed corpus
       ↓
Evaluate against v1
       ↓
Promote only if better
```

The same principle applies to major index configuration changes that would
invalidate comparability with the current baseline.

## Phase 6 - Production Engineering

### Logging and Monitoring

Track:

- request latency
- retrieval latency
- LLM latency
- token usage
- cost
- source usage
- retrieval scores
- failures
- ingestion events

### Testing

Add:

- unit tests
- integration tests
- ingestion tests
- retrieval regression tests
- evaluation regression tests

### Deployment

Add:

- Dockerfile
- Docker Compose
- Poppler system dependency
- environment-based configuration
- health/readiness checks
- CI/CD

Later add caching and asynchronous/background processing where justified.

## Phase 7 - Security and Permissions

Before exposing broader capabilities:

- source-level permissions
- document-level access controls
- validated source selection
- prompt-injection defenses
- safe tool boundaries
- secrets management
- request limits
- audit logging

Retrieval permissions must be enforced before documents are supplied to the
LLM.

## Phase 8 - User-Facing Football Intelligence Workflows

V1 should expose clear analyst-oriented workflows rather than behaving only
like a generic RAG API.

Core product actions:

**Ask** — Example: How does Arsenal build against a high press?

**Compare** — Example: Compare Arsenal and Bayern's pressing approaches.

**Research** — Example: What does the UEFA report say about transition
efficiency?

**Evidence / Explain** — Example: What evidence supports this tactical
conclusion?

The product layer should make the platform useful to a football analyst while
continuing to use the same evaluated retrieval and grounding pipeline
underneath.

## Phase 9 - MCP Interface & Tool Exposure

V1 exposes stable platform capabilities through MCP; V2 enables agents to
intelligently consume those capabilities through tools and MCP workflows.

MCP is part of V1 because it is an interface for exposing stable capabilities,
not inherently an agentic feature.

The REST API and MCP interface must reuse the same underlying
application/service layer:

```text
REST API ----+
             |
             +----> Application / Service Layer
             |
MCP ---------+
                    |
                    v
              Retrieval / RAG
                    |
                    v
                 Data
```

Possible MCP capabilities:

- search football knowledge
- retrieve report evidence
- compare teams or tactical concepts
- inspect available knowledge sources
- expose supported analytical functions

Example:

```text
MCP Client
    ↓
search_football_knowledge()
    ↓
Search Service
    ↓
Retrieval Pipeline
```

Architectural rule:

MCP must not contain a separate retrieval implementation.

It should expose existing, tested capabilities through a second interface.

External MCP consumption is optional and belongs to V2 when agentic workflows
need it.

## Phase 10 - V1 Portfolio Documentation

After V1 implementation is complete, package the engineering work so the
repository demonstrates measured decisions rather than only technologies.

Required portfolio artifacts:

```text
V1 implementation complete
        ↓
Benchmark results
        ↓
Architecture diagram
        ↓
README
        ↓
Demo
        ↓
Technical decisions
        ↓
Before / after metrics
        ↓
Portfolio-ready
```

Document comparisons such as:

```text
Baseline retrieval
      ↓
Hybrid retrieval
      ↓
Reranking
```

Show the effect on:

- Context Recall
- Context Precision
- Faithfulness
- Answer / Response Relevancy
- latency
- token usage
- cost

Also document important engineering decisions such as chunking strategy,
source abstraction, ingestion design, security boundaries, and why particular
techniques were kept or rejected.

## 12. V2 - Tools and Single-Agent Intelligence

Only after V1 capabilities are measurable, stable, and exposed.

### Tool Calling

Turn useful platform capabilities into tools such as:

- tactical document search
- team profile retrieval
- report comparison
- evidence lookup
- statistics lookup when structured sources are added

### Single Orchestrating Agent

Build one football intelligence agent that decides when to use available
tools.

Progression:

```text
RAG
 ↓
Stable Services
 ↓
MCP / Tool Exposure
 ↓
Tool Calling
 ↓
Single Agent
 ↓
Agent Evaluation
```

Do not introduce multiple agents unless the single-agent architecture has a
measurable limitation.

### JEV Note

JEV remains intentionally undefined in this plan until its exact role and
definition are agreed.

For now, it is only an optional advanced experiment in the flow:

```text
Candidate Retrieval
        ↓
Hybrid Search
        ↓
Reranker
        ↓
JEV
        ↓
Final Context
        ↓
LLM
```

It is not a V1 requirement and should only be retained if it demonstrates
measurable value.

## 13. V3 - Advanced Intelligence

V3 stays deliberately small and experimental.

Only add these capabilities when they provide measurable product value:

- specialized agents
- multi-agent orchestration
- optional JEV experiments
- advanced structured football analytics

Potential specialized roles, only if justified:

**Retrieval Agent** — Finds and organizes evidence.

**Tactical Analysis Agent** — Synthesizes tactical information from retrieved
evidence.

**QA / Reviewer Agent** — Checks grounding, citations, and unsupported claims.

Potential flow:

```text
User
 -> Orchestrator
 -> Retrieval Agent
 -> Analysis Agent
 -> QA / Reviewer
 -> Final answer
```

JEV and multi-agent orchestration are not mandatory milestones. They should
only remain if they outperform simpler approaches or unlock a clear product
capability.

## 14. Ongoing Production Optimization

Optimization is an engineering activity applied when measurements justify it,
not a separate "advanced intelligence" feature.

Focus on:

- retrieval quality
- candidate counts
- chunk sizes
- overlap
- reranking strategy
- embedding choices
- token consumption
- LLM cost
- latency
- caching
- batch ingestion
- database layout
- source routing
- deduplication
- prompt efficiency

Avoid premature optimization.

## 15. Final Target Architecture

```text
                         CLIENTS
                            |
                 +----------+----------+
                 |                     |
                 v                     v
              REST API            MCP Interface
                 |                     |
                 +----------+----------+
                            |
                            v
                 Application / Orchestrator
                            |
          +-----------------+-----------------+
          |                                   |
          v                                   v
      Retrieval                         Memory / State
          |
   +------+------+
   |             |
   v             v
Dense Search    BM25
   |             |
   +------v------+
       Reranker
          |
          v
   Context Builder
          |
          v
     Grounded LLM
          |
          v
 Guardrails / Grounding / QA
          |
          v
       Response
```

V2 adds tool calling and a single agent above the same services.
V3 may add specialized agents, JEV experiments, and structured analytics.

Knowledge Layer:

- football profiles
- UEFA technical reports
- future tactical reports
- future structured football data

Evaluation Layer:

- RAGAS
- retrieval regression tests
- answer quality tests
- agent evaluation

## 16. Portfolio Goal

The finished project should demonstrate more than "I built a chatbot."

It should demonstrate:

- backend API engineering
- document ingestion pipelines
- vector databases
- embeddings and retrieval
- multi-source knowledge architecture
- RAG evaluation
- hybrid retrieval
- reranking
- LLM orchestration
- observability
- cost awareness
- security
- production deployment
- MCP
- agent architecture

The repository should clearly show architectural evolution and measured
improvements rather than simply accumulating AI features.

## 17. High-Level Roadmap

```text
Phase 1  — Evaluation Baseline                         CURRENT
Phase 2  — Retrieval Quality                           NEXT
Phase 3  — Context + Grounding + Guardrails            PLANNED
Phase 4  — Memory                                      PLANNED
Phase 5  — Ingestion Platform                          PLANNED
Phase 6  — Production Engineering                      PLANNED
Phase 7  — Security and Permissions                    PLANNED
Phase 8  — User-Facing Product Workflows               PLANNED
Phase 9  — MCP Interface & Tool Exposure               PLANNED
Phase 10 — Portfolio Documentation                     PLANNED
-------------------------------------------------------------
V1 — PRODUCTION FOOTBALL INTELLIGENCE RAG
-------------------------------------------------------------
Phase 11 — Tool Calling                                V2
Phase 12 — Single Orchestrating Agent                  V2
Phase 13 — MCP-Powered Agent Workflows                 V2
Phase 14 — Agent Evaluation                            V2
-------------------------------------------------------------
V2 — AGENTIC FOOTBALL INTELLIGENCE
-------------------------------------------------------------
Phase 15 — Specialized Agents                          V3, OPTIONAL
Phase 16 — Multi-Agent Orchestration                   V3, OPTIONAL
Phase 17 — JEV Experiments                             V3, OPTIONAL / EXPERIMENTAL
Phase 18 — Structured Football Analytics               V3
-------------------------------------------------------------
V3 — ADVANCED INTELLIGENCE
-------------------------------------------------------------
```

V1 is the portfolio-ready stopping point.

V2 and V3 are extensions, not prerequisites for shipping the project.

The project should not move into V2 until V1 retrieval quality, evaluation,
security, testing, deployment, MCP exposure, and interfaces are stable.

## 18. Guiding Principles

1. Build one capability at a time.
2. Test every major change before moving forward.
3. Measure retrieval quality rather than assuming improvement.
4. Keep routes thin and business logic in services.
5. Keep public source IDs separate from database implementation details.
6. Prefer explicit source selection before automatic routing.
7. Do not add agents where ordinary application logic is sufficient.
8. Do not add complexity solely for portfolio buzzwords.
9. Keep claims grounded in retrieved evidence.
10. Optimize only after the main architecture works.
11. Preserve proper layering and separation of concerns throughout every
    phase.
12. Keep knowledge retrieval authoritative; memory only supplies
    conversational context.
13. Make advanced techniques such as hybrid retrieval, reranking, JEV, and
    agents earn their place through measurable value.
14. Treat MCP as an interface over existing services, never as a duplicate
    implementation path.

## 19. Architectural Layering and Separation of Concerns

The project should maintain clear boundaries between layers so that each
component has one primary responsibility and can evolve independently.

Recommended layering:

```text
API / Presentation Layer
        |
        v
Application / Orchestration Layer
        |
        v
Domain / Service Layer
        |
        +-------------------+
        |                   |
        v                   v
Retrieval Layer         LLM / Generation Layer
        |                   |
        v                   v
Data Access Layer       Provider Integrations
        |
        v
Infrastructure Layer
```

### Layer Responsibilities

**API / Presentation Layer**

- FastAPI routes
- request/response validation
- HTTP status codes
- public API contracts
- no retrieval or database business logic

**Application / Orchestration Layer**

- RAGChain
- coordinates retrieval, generation, evaluation, and future tools
- should not contain low-level Chroma/OpenAI implementation details

**Domain / Service Layer**

- source resolution
- retrieval workflows
- ranking/merging logic
- context construction
- ingestion workflows
- evaluation workflows

**Data Access Layer**

- ChromaDB access
- collection/index operations
- future lexical/vector-store adapters
- no API-specific behavior

**Provider / Integration Layer**

- OpenAI or other LLM clients
- embedding providers
- external APIs
- MCP interface adapters and future external MCP integrations

**Infrastructure Layer**

- configuration
- logging
- Docker
- secrets/environment handling
- monitoring
- background jobs

### Architectural Rules

1. Routes stay thin.
2. Database-specific details must not leak into public API contracts.
3. LLM-provider-specific code should remain behind a service/provider
   boundary.
4. Retrieval logic should be reusable outside FastAPI routes.
5. Evaluation code should call the same production retrieval/generation path
   wherever possible.
6. Ingestion should be independent from query-serving code.
7. Cross-layer imports should move inward through defined interfaces, not
   create circular dependencies.
8. Shared models/configuration should live in clear common modules rather than
   being duplicated.
9. New features such as hybrid search, reranking, agents, or MCP should fit
   into an existing layer or justify a new one.
10. Refactor when responsibilities begin to mix, rather than allowing one
    large service or route file to become the system.

This layering is a project requirement, not a cosmetic cleanup task. Every
major phase should preserve separation of concerns and avoid unnecessary
coupling.

## 20. Versioned Completion Targets

### V1 - Production Football Intelligence RAG

V1 is the portfolio-ready product.

Required capabilities:

- Core RAG
- multi-source retrieval
- RAGAS evaluation baseline
- formal retrieval experiment workflow
- metadata-aware retrieval
- hybrid retrieval when evaluation demonstrates value
- reranking when evaluation demonstrates value
- context management and grounding
- conversational memory after retrieval is stable
- basic + advanced guardrails
- robust ingestion pipeline
- security fundamentals
- observability
- automated tests
- Docker/deployment
- analyst-oriented user workflows
- MCP Interface & Tool Exposure
- proper layered architecture and separation of concerns
- benchmark results and portfolio documentation

Recommended dependency order:

```text
Core RAG
   ↓
Evaluation baseline
   ↓
Retrieval experiments
   ↓
Metadata filtering
   ↓
Hybrid + reranking
   ↓
Context + grounding
   ↓
Memory
   ↓
Guardrails / security hardening
   ↓
Ingestion hardening
   ↓
Observability + testing
   ↓
Docker / deployment
   ↓
Analyst workflows
   ↓
MCP Interface & Tool Exposure
   ↓
Portfolio documentation
   ↓
V1 COMPLETE
```

#### V1 Guardrail Model

From the beginning:

- input validation
- source allowlisting
- prompt-injection awareness
- safe errors
- token/request limits
- secrets management
- no raw collection names exposed

After retrieval is stable:

- hallucination / grounding checks
- answer constraints
- refusal when evidence is insufficient
- prompt management
- stronger output validation

#### Memory Rule

knowledge retrieval != conversation memory

Memory supplies conversational context.
The knowledge base supplies authoritative evidence.
Memory must never replace or override evidence retrieval.

#### MCP Rule

```text
REST API ----+
             +----> Same services
MCP ---------+
```

V1 builds and exposes capabilities.
MCP does not get its own retrieval pipeline.

### V2 - Agentic Football Intelligence

V2 teaches an agent to use the reliable capabilities built in V1.

Scope:

- tool calling
- single orchestrating football intelligence agent
- MCP-powered workflows
- richer analysis workflows
- agent evaluation

Progression:

```text
Stable V1 Services
      ↓
Tool Calling
      ↓
Single Agent
      ↓
MCP-Powered Workflows
      ↓
Agent Evaluation
      ↓
V2 COMPLETE
```

Do not add multiple agents merely for architectural novelty.

### V3 - Advanced Intelligence

V3 is intentionally small and experimental.

Scope:

- specialized agents
- multi-agent orchestration
- optional JEV experiments
- advanced structured football analytics

Potential advanced retrieval experiment:

```text
Candidate Retrieval
        ↓
Hybrid Search
        ↓
Reranker
        ↓
JEV
        ↓
Final Context
        ↓
LLM
```

JEV is optional.

Specialized agents and multi-agent orchestration are optional.

They should only be adopted when they outperform simpler alternatives or
enable a clear product capability.

Advanced permissions, tracing, and optimization are not "V3 intelligence"
features. They should be added to the production architecture whenever real
requirements justify them.

## 21. Final Product Principle

The project should evolve according to one simple distinction:

- **V1**: Build and expose reliable capabilities.
- **V2**: Make an agent intelligently use those capabilities.
- **V3**: Experiment with whether specialized agents, JEV, and advanced
  analytics materially improve the system.

The project does not need to become a large multi-agent research platform to
be considered complete.

A measured, secure, deployed, well-documented V1 is already the primary
portfolio milestone.

## Canonical Rules

Use these sections as the authoritative source when a rule appears elsewhere
in the plan.

| Rule                                 | Source of truth                                       |
| ------------------------------------ | ------------------------------------------------------ |
| Baseline configuration               | Current Baseline Configuration                         |
| Evaluation discipline                | Retrieval Experiment Discipline                        |
| Failure handling                     | Failure Handling                                        |
| Memory boundary                      | Conversation and Memory                                 |
| MCP architecture                     | MCP Interface & Tool Exposure                           |
| Layering / separation of concerns    | Architectural Layering and Separation of Concerns       |
| V1 / V2 / V3 scope                   | Versioned Completion Targets                            |
| Embedding/index migration            | Embedding / Index Version Migration                     |

If duplicate wording elsewhere conflicts with a canonical section, the
canonical section wins.

## Immediate Execution Path

Stop planning and implement the evaluation baseline.

```text
CURRENT
RAG evaluation baseline
        ↓
Inspect actual current RAG implementation/configuration
        ↓
Document baseline configuration
        ↓
evals/questions.py
        ↓
evals/run_eval.py
        ↓
Run baseline through the real RAGChain
        ↓
Collect real retrieved contexts + generated answers
        ↓
Run RAGAS metrics
        ↓
Record baseline results
        ↓
Only then improve retrieval
```

Before writing or finalizing the evaluation runner, inspect the actual
current:

- RAGChain
- retrieval service
- source IDs
- request/response models
- chunking configuration
- embedding configuration
- n_results
- retrieved-document structure

The evaluation runner should call the same production code path rather than a
parallel mock interface.
