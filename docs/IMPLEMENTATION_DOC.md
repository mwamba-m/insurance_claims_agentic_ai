# Local Claims Agentic AI MVP - Engineering Implementation

## Process flow

```mermaid
sequenceDiagram
    participant User
    participant UI as Browser UI
    participant API as FastAPI
    participant Graph as LangGraph/Fallback Runner
    participant Triage as Claims Triage Agent
    participant RAG as Policy Coverage Agent
    participant Q as Qdrant
    participant Ev as Evidence Review Agent
    participant Risk as Risk Screening Agent
    participant Rec as Handler Recommendation
    participant Guard as Output Guardrails
    participant LS as LangSmith

    User->>UI: Select claim and run workflow
    UI->>API: GET /claims?limit=...
    API-->>UI: Claim options
    UI->>API: POST /claims/{id}/run
    API->>Graph: Invoke claim state
    Graph->>LS: Start trace
    Graph->>Triage: Summarise FNOL and classify
    Triage-->>Graph: Structured triage JSON
    Graph->>RAG: Build policy query
    RAG->>Q: Vector search with metadata filter
    Q-->>RAG: Policy chunks and citations
    RAG-->>Graph: Coverage summary
    Graph->>Ev: Review synthetic evidence docs
    Ev-->>Graph: Missing/conflicting info
    Graph->>Risk: Feature/rule scoring
    Risk-->>Graph: Risk level and flags
    Graph->>Rec: Generate handler recommendation
    Rec-->>Graph: Recommendation and human approval flag
    Graph->>Guard: Validate output guardrails
    Guard-->>Graph: Final status and approval flag
    Graph->>API: Final result
    API-->>UI: Agent, document, policy, risk and recommendation output
```

## Key design choices

- Groq is optional at runtime. If `GROQ_API_KEY` is missing, deterministic mock logic is used so the local MVP still runs.
- Qdrant is required for policy RAG search.
- Embeddings use a local hashing embedder to avoid Python 3.14 native dependency problems.
- LangGraph is attempted first. If your Python 3.14 environment has dependency issues, the app falls back to a simple graph runner with the same nodes.
- LangSmith decorators are optional. If configured, traces are sent to your LangSmith project.
- The browser UI is static HTML/CSS/JavaScript served by FastAPI from `app/static/index.html`.
- The UI visualizes the multi-agent architecture with agent-level outputs, document review details, policy retrieval details and raw JSON.

## Agents

1. Claims Triage Agent
   - Extracts claim type, urgency, complexity, incident facts and missing information.

2. Policy Coverage Agent
   - Searches Qdrant using product metadata filter.
   - Returns cited policy chunks and a coverage summary.

3. Evidence Review Agent
   - Reads generated synthetic evidence documents.
   - Highlights missing documents and conflicting dates.

4. Risk Screening Agent
   - Applies feature-based risk scoring and rules.
   - Flags high frequency, inflated cost, early policy claim, duplicate invoice, and date conflicts.

5. Handler Recommendation Agent
   - Produces final handler-facing recommendation.
   - Does not make final settlement decisions.

6. Output Guardrails
   - Blocks final claim decision language.
   - Requires human review for missing policy clauses or elevated risk.

## Browser UI

The main UI is available at:

```text
http://localhost:8000/
```

It uses:

- `GET /health`
- `GET /claims?limit=...`
- `POST /claims/{claim_id}/run`

The UI displays:

- workflow summary
- each agent involved and what it handled
- document workflow and extracted evidence fields
- policy retrieval and retrieved clause metadata
- recommendation, risk flags, missing information and raw response

## Evaluation

`python scripts/run_evaluation.py --limit 100` reports:

- claim type accuracy
- urgency accuracy
- average citations retrieved
- human approval rate
- risk level distribution
- sample case results
