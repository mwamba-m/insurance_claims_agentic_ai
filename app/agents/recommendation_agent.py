from __future__ import annotations

from app.agents.state import ClaimWorkflowState
from app.observability.tracing import traced

@traced("handler_recommendation_agent")
def recommendation_node(state: ClaimWorkflowState) -> ClaimWorkflowState:
    missing = state.get("evidence_review", {}).get("missing_information", [])
    conflicts = state.get("evidence_review", {}).get("conflicts", [])
    if state.get("fraud_referral_required"):
        action = "Escalate to fraud or specialist review."
    elif conflicts:
        action = "Request clarification on conflicting evidence before progressing."
    elif missing:
        action = "Request missing evidence from customer or third party."
    elif state.get("coverage_summary"):
        action = "Proceed with handler review using cited policy clauses."
    else:
        action = "Manual review required."

    state["handler_recommendation"] = {
        "claim_id": state["claim_id"],
        "claim_type": state.get("claim_type"),
        "urgency": state.get("urgency"),
        "complexity": state.get("complexity"),
        "coverage_summary": state.get("coverage_summary"),
        "top_policy_citations": [
            {
                "chunk_id": c.get("chunk_id"),
                "source_file": c.get("source_file"),
                "section": c.get("section"),
                "score": c.get("score"),
            }
            for c in state.get("retrieved_policy_clauses", [])[:3]
        ],
        "evidence_status": "incomplete" if missing or conflicts else "sufficient_for_initial_review",
        "risk_level": state.get("risk_level"),
        "risk_score": state.get("risk_score"),
        "risk_flags": state.get("risk_flags", []),
        "recommended_action": action,
        "human_approval_required": state.get("human_approval_required", False),
    }
    state["final_status"] = "human_review_required" if state.get("human_approval_required") else "ready_for_handler_review"
    return state
