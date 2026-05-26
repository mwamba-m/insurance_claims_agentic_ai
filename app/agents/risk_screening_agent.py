from __future__ import annotations

from app.agents.state import ClaimWorkflowState
from app.observability.tracing import traced
from app.risk.rules import apply_rules, build_features, risk_level, score_risk

@traced("risk_screening_agent")
def risk_screening_node(state: ClaimWorkflowState) -> ClaimWorkflowState:
    existing = state.get("risk_flags", [])
    features = build_features(state)
    flags = sorted(set(existing + apply_rules(features)))
    score = score_risk(features, flags)
    level = risk_level(score)
    state["risk_flags"] = flags
    state["risk_score"] = score
    state["risk_level"] = level
    state["fraud_referral_required"] = level == "high" or "duplicate_invoice_reference" in flags
    if state["fraud_referral_required"]:
        state["human_approval_required"] = True
    return state
