from __future__ import annotations

from app.agents.state import ClaimWorkflowState
from app.agents.triage_agent import triage_node
from app.agents.policy_coverage_agent import policy_coverage_node
from app.agents.evidence_review_agent import evidence_review_node
from app.agents.risk_screening_agent import risk_screening_node
from app.agents.recommendation_agent import recommendation_node
from app.agents.guardrails import guardrail_node


def _fallback_run(state: ClaimWorkflowState) -> ClaimWorkflowState:
    state.setdefault("errors", [])
    state.setdefault("risk_flags", [])
    state.setdefault("human_approval_required", False)

    for node in [triage_node, policy_coverage_node, evidence_review_node, risk_screening_node, recommendation_node, guardrail_node]:
        try:
            state = node(state)
        except Exception as exc:
            state.setdefault("errors", []).append(f"{node.__name__}: {exc}")
            state["human_approval_required"] = True
            state["fallback_reason"] = f"Agent failure in {node.__name__}"
            break
    if "handler_recommendation" not in state:
        state = recommendation_node(state)
    state = guardrail_node(state)
    return state


def build_graph():
    try:
        from langgraph.graph import END, START, StateGraph

        def after_triage(state: ClaimWorkflowState) -> str:
            if state.get("urgency") == "high" or state.get("complexity") == "complex":
                # still continue through coverage/evidence for context, but mark human approval
                state["human_approval_required"] = True
            return "policy_coverage"

        def after_coverage(state: ClaimWorkflowState) -> str:
            return "evidence_review"

        def after_evidence(state: ClaimWorkflowState) -> str:
            return "risk_screening"

        def after_risk(state: ClaimWorkflowState) -> str:
            return "recommendation"

        builder = StateGraph(ClaimWorkflowState)
        builder.add_node("triage", triage_node)
        builder.add_node("policy_coverage", policy_coverage_node)
        builder.add_node("evidence_review", evidence_review_node)
        builder.add_node("risk_screening", risk_screening_node)
        builder.add_node("recommendation", recommendation_node)
        builder.add_node("guardrails", guardrail_node)

        builder.add_edge(START, "triage")
        builder.add_conditional_edges("triage", after_triage, {"policy_coverage": "policy_coverage"})
        builder.add_conditional_edges("policy_coverage", after_coverage, {"evidence_review": "evidence_review"})
        builder.add_conditional_edges("evidence_review", after_evidence, {"risk_screening": "risk_screening"})
        builder.add_conditional_edges("risk_screening", after_risk, {"recommendation": "recommendation"})
        builder.add_edge("recommendation", "guardrails")
        builder.add_edge("guardrails", END)
        return builder.compile()
    except Exception:
        return None

_graph = build_graph()


def run_claim_workflow(claim: dict) -> dict:
    state: ClaimWorkflowState = ClaimWorkflowState(**claim)
    state.setdefault("errors", [])
    state.setdefault("risk_flags", [])
    state.setdefault("human_approval_required", False)
    if _graph is not None:
        try:
            return dict(_graph.invoke(state))
        except Exception as exc:
            state["errors"].append(f"LangGraph runtime failed; fallback runner used: {exc}")
            return dict(_fallback_run(state))
    return dict(_fallback_run(state))
