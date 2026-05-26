from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from app.config import QDRANT_COLLECTION, QDRANT_URL, USE_GROQ, LANGSMITH_PROJECT
from app.data_store import get_claim, list_claims
from app.schemas.models import ClaimRunResponse, PolicySearchRequest
from app.agents.workflow import run_claim_workflow
from app.rag.qdrant_store import search_policy, ensure_collection
from app.evaluation.metrics import evaluate_cases

app = FastAPI(title="Claims Agentic AI MVP", version="0.1.0")
STATIC_DIR = Path(__file__).parent / "static"

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/", include_in_schema=False)
def claim_ui() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")

@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "use_groq": USE_GROQ,
        "qdrant_url": QDRANT_URL,
        "qdrant_collection": QDRANT_COLLECTION,
        "langsmith_project": LANGSMITH_PROJECT,
    }

@app.get("/claims")
def claims(limit: int = 20) -> list[dict]:
    return list_claims(limit=limit)

@app.get("/claims/{claim_id}")
def claim_detail(claim_id: str) -> dict:
    claim = get_claim(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found. Run scripts/generate_data.py first.")
    return claim

@app.post("/claims/{claim_id}/run", response_model=ClaimRunResponse)
def run_claim(claim_id: str) -> ClaimRunResponse:
    claim = get_claim(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found. Run scripts/generate_data.py first.")
    result = run_claim_workflow(claim)
    return ClaimRunResponse(claim_id=claim_id, status=result.get("final_status", "completed"), result=result)

@app.post("/policies/search")
def policy_search(req: PolicySearchRequest) -> dict:
    results = search_policy(req.query, req.product_type, req.top_k)
    return {"query": req.query, "results": results}

@app.post("/policies/ensure-collection")
def ensure_policy_collection() -> dict:
    ensure_collection()
    return {"status": "ok", "collection": QDRANT_COLLECTION}

@app.post("/evaluate")
def evaluate(limit: int = 100) -> dict:
    return evaluate_cases(limit=limit)
