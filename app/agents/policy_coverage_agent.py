from __future__ import annotations

from app.agents.state import ClaimWorkflowState
from app.llm import call_llm_json
from app.observability.tracing import traced
from app.rag.qdrant_store import search_policy

SYSTEM_PROMPT = """
You are a policy coverage assistant for insurance claim handlers.
Use only the retrieved policy clauses supplied in the user payload.
Do not make a final coverage or settlement decision.
Return JSON with coverage_summary, key_conditions, exclusions, excess_notes, confidence.
"""


def build_query(state: ClaimWorkflowState) -> str:
    facts = state.get("incident_facts", {})
    return " ".join([
        state.get("product_type", ""),
        state.get("claim_type", ""),
        facts.get("loss_cause", ""),
        state.get("fnol_text", ""),
        "coverage exclusions excess conditions claims guidance",
    ])

@traced("policy_coverage_agent")
def policy_coverage_node(state: ClaimWorkflowState) -> ClaimWorkflowState:
    query = build_query(state)
    clauses = search_policy(query=query, product_type=state.get("product_type"), top_k=6)
    state["retrieved_policy_clauses"] = clauses
    if not clauses:
        state["human_approval_required"] = True
        state["fallback_reason"] = "No policy clauses retrieved"
        state["coverage_summary"] = "Policy lookup inconclusive. Handler review required."
        return state
    payload = {"claim": dict(state), "retrieved_clauses": clauses}
    result = call_llm_json(SYSTEM_PROMPT, payload, task="coverage")
    state["coverage_summary"] = result.get("coverage_summary", "Coverage requires handler review using cited clauses.")
    if result.get("confidence", 0) < 0.65:
        state["human_approval_required"] = True
        state["fallback_reason"] = "Low confidence coverage summary"
    return state
