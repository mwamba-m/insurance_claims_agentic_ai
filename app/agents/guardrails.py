from __future__ import annotations

from app.agents.state import ClaimWorkflowState
from app.observability.tracing import traced

FORBIDDEN_FINAL_DECISIONS = ["claim accepted", "claim rejected", "fraud confirmed", "policy void"]

@traced("output_guardrails")
def guardrail_node(state: ClaimWorkflowState) -> ClaimWorkflowState:
    text = str(state.get("handler_recommendation", {})).lower()
    if any(term in text for term in FORBIDDEN_FINAL_DECISIONS):
        state["human_approval_required"] = True
        state["fallback_reason"] = "Guardrail blocked final decision language"
    if not state.get("retrieved_policy_clauses"):
        state["human_approval_required"] = True
    if state.get("risk_level") in {"medium", "high"}:
        state["human_approval_required"] = True
    state["final_status"] = "human_review_required" if state.get("human_approval_required") else "ready_for_handler_review"
    return state
