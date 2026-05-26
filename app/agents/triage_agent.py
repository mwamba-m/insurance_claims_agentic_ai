from __future__ import annotations

from app.agents.state import ClaimWorkflowState
from app.llm import call_llm_json
from app.observability.tracing import traced

SYSTEM_PROMPT = """
You are a claims triage assistant for motor and home insurance.
Use only the FNOL and structured claim fields provided.
Do not make final claim decisions.
Return strict JSON with claim_type, incident_summary, incident_facts,
urgency, complexity, missing_information, evidence_required, and confidence.
"""

@traced("claims_triage_agent")
def triage_node(state: ClaimWorkflowState) -> ClaimWorkflowState:
    result = call_llm_json(SYSTEM_PROMPT, dict(state), task="triage")
    state["claim_type"] = result.get("claim_type", "unknown")
    state["urgency"] = result.get("urgency", "medium")
    state["complexity"] = result.get("complexity", "standard")
    state["incident_facts"] = result.get("incident_facts", {})
    state["triage_summary"] = result
    if result.get("confidence", 0) < 0.65:
        state["human_approval_required"] = True
        state["fallback_reason"] = "Low confidence triage"
    return state
