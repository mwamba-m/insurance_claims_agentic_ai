from __future__ import annotations

from typing import Any

from app.agents.state import ClaimWorkflowState
from app.llm import call_llm_json
from app.observability.tracing import traced

SYSTEM_PROMPT = """
You are a claims handler recommendation drafting assistant.
Draft handler-facing guidance only within the deterministic route supplied.
Do not make final claim acceptance, rejection, fraud, settlement, or policy-void decisions.
Do not say evidence is sufficient if evidence_status is incomplete.
Do not cite policy confidence if no policy citations are supplied.
If specialist_review_required is true, do not recommend normal progression.
Return strict JSON with recommendation_summary, rationale, supporting_evidence,
weakening_evidence, relevant_policy_clauses, customer_questions,
missing_documents_to_request, specialist_review_needed, specialist_review_reason,
and confidence.
All list fields must be arrays of plain human-readable strings, not objects.
"""

FORBIDDEN_FINAL_DECISION_TERMS = [
    "claim accepted",
    "claim rejected",
    "fraud confirmed",
    "policy void",
]


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _humanize_key(value: str) -> str:
    return value.replace("_", " ").strip()


def _format_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return _humanize_key(value)
    if isinstance(value, list):
        return ", ".join(filter(None, (_format_value(item) for item in value)))
    if isinstance(value, dict):
        parts = []
        for key, item in value.items():
            if item in (None, "", [], {}):
                continue
            parts.append(f"{_humanize_key(str(key))}: {_format_value(item)}")
        return "; ".join(parts)
    return str(value)


def _dict_to_sentence(item: dict[str, Any]) -> str:
    for key in ("summary", "question", "text", "sentence", "value"):
        if item.get(key):
            return _format_value(item[key])

    description = _format_value(item.get("description"))
    data = item.get("data")
    item_type = _format_value(item.get("type"))
    detail = _format_value(data)

    if description and detail:
        return f"{description}: {detail}."
    if description:
        return description + "."
    if item_type and detail:
        return f"{item_type}: {detail}."
    return _format_value(item)


def _as_text_list(value: Any, limit: int = 6) -> list[str]:
    items: list[str] = []
    for item in _as_list(value):
        if isinstance(item, dict):
            text = _dict_to_sentence(item)
        else:
            text = _format_value(item)
        text = text.strip()
        if text:
            items.append(text)
    return items[:limit]


def _has_final_decision_language(value: Any) -> bool:
    text = str(value).lower()
    return any(term in text for term in FORBIDDEN_FINAL_DECISION_TERMS)


def _confidence(value: Any, default: float = 0.7) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        if isinstance(value, str):
            lowered = value.lower().strip()
            if lowered == "high":
                return 0.85
            if lowered == "medium":
                return 0.7
            if lowered == "low":
                return 0.45
        return default


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "yes", "y", "1"}
    return bool(value)


def _deterministic_action(state: ClaimWorkflowState, missing: list[str], conflicts: list[dict]) -> tuple[str, str]:
    if state.get("fraud_referral_required"):
        return "fraud_or_specialist_review", "Escalate to fraud or specialist review."
    if conflicts:
        return "clarify_conflicting_evidence", "Request clarification on conflicting evidence before progressing."
    if missing:
        return "request_missing_evidence", "Request missing evidence from customer or third party."
    if state.get("coverage_summary") and state.get("retrieved_policy_clauses"):
        return "handler_review_with_policy_clauses", "Proceed with handler review using cited policy clauses."
    return "manual_review", "Manual review required."


def _top_policy_citations(state: ClaimWorkflowState) -> list[dict[str, Any]]:
    return [
        {
            "chunk_id": c.get("chunk_id"),
            "source_file": c.get("source_file"),
            "section": c.get("section"),
            "score": c.get("score"),
        }
        for c in state.get("retrieved_policy_clauses", [])[:3]
    ]


def _fallback_draft(
    state: ClaimWorkflowState,
    action: str,
    evidence_status: str,
    missing: list[str],
    conflicts: list[dict],
    citations: list[dict[str, Any]],
) -> dict[str, Any]:
    risk_flags = state.get("risk_flags", [])
    supporting_evidence = []
    if citations:
        supporting_evidence.append("Policy clauses were retrieved for handler review.")
    if state.get("coverage_summary"):
        supporting_evidence.append("A coverage summary is available for review against cited wording.")

    weakening_evidence = []
    if missing:
        weakening_evidence.append("Required evidence is missing: " + ", ".join(missing) + ".")
    if conflicts:
        weakening_evidence.append("Evidence conflicts were detected and need clarification.")
    if risk_flags:
        weakening_evidence.append("Risk flags are present: " + ", ".join(risk_flags) + ".")

    questions = []
    if conflicts:
        questions.append("Can the customer or third party confirm the correct incident date and explain the discrepancy?")
    if missing:
        questions.append("Can the customer provide the missing evidence before the claim progresses?")
    if not citations:
        questions.append("Can a handler confirm the applicable policy wording manually?")

    return {
        "recommendation_summary": action,
        "rationale": "The route is based on the deterministic workflow state: evidence status, retrieved policy context, and risk screening outputs.",
        "supporting_evidence": supporting_evidence,
        "weakening_evidence": weakening_evidence,
        "relevant_policy_clauses": [
            f"{c.get('source_file') or 'policy'} / {c.get('section') or c.get('chunk_id') or 'clause'}"
            for c in citations
        ],
        "customer_questions": questions,
        "missing_documents_to_request": missing if evidence_status == "incomplete" else [],
        "specialist_review_needed": bool(state.get("fraud_referral_required")),
        "specialist_review_reason": "Fraud or specialist referral is required by risk screening." if state.get("fraud_referral_required") else "",
        "confidence": 0.72,
        "ai_drafted": False,
    }


def _draft_recommendation(
    state: ClaimWorkflowState,
    route: str,
    action: str,
    evidence_status: str,
    missing: list[str],
    conflicts: list[dict],
    citations: list[dict[str, Any]],
) -> dict[str, Any]:
    fallback = _fallback_draft(state, action, evidence_status, missing, conflicts, citations)
    payload = {
        "deterministic_route": route,
        "allowed_recommended_action": action,
        "evidence_status": evidence_status,
        "specialist_review_required": bool(state.get("fraud_referral_required")),
        "missing_information": missing,
        "conflicts": conflicts,
        "coverage_summary": state.get("coverage_summary"),
        "policy_citations": citations,
        "risk_level": state.get("risk_level"),
        "risk_score": state.get("risk_score"),
        "risk_flags": state.get("risk_flags", []),
        "claim": {
            "claim_id": state.get("claim_id"),
            "claim_type": state.get("claim_type"),
            "product_type": state.get("product_type"),
            "urgency": state.get("urgency"),
            "complexity": state.get("complexity"),
            "claim_amount": state.get("claim_amount"),
            "incident_facts": state.get("incident_facts", {}),
        },
    }
    try:
        result = call_llm_json(SYSTEM_PROMPT, payload, task="recommendation")
    except Exception as exc:
        fallback["draft_error"] = str(exc)
        return fallback

    draft = {
        "recommendation_summary": str(result.get("recommendation_summary") or action),
        "rationale": str(result.get("rationale") or fallback["rationale"]),
        "supporting_evidence": _as_text_list(result.get("supporting_evidence")),
        "weakening_evidence": _as_text_list(result.get("weakening_evidence")),
        "relevant_policy_clauses": _as_text_list(result.get("relevant_policy_clauses")),
        "customer_questions": _as_text_list(result.get("customer_questions")),
        "missing_documents_to_request": _as_text_list(result.get("missing_documents_to_request")),
        "specialist_review_needed": _as_bool(result.get("specialist_review_needed")) or bool(state.get("fraud_referral_required")),
        "specialist_review_reason": str(result.get("specialist_review_reason") or fallback["specialist_review_reason"]),
        "confidence": _confidence(result.get("confidence")),
        "ai_drafted": True,
    }

    if _has_final_decision_language(draft):
        fallback["draft_error"] = "AI draft contained final decision language and was replaced with deterministic fallback."
        return fallback
    if evidence_status == "incomplete":
        draft["missing_documents_to_request"] = missing
    if not citations:
        draft["relevant_policy_clauses"] = []
    if state.get("fraud_referral_required"):
        draft["specialist_review_needed"] = True
    return draft


@traced("handler_recommendation_agent")
def recommendation_node(state: ClaimWorkflowState) -> ClaimWorkflowState:
    missing = state.get("evidence_review", {}).get("missing_information", [])
    conflicts = state.get("evidence_review", {}).get("conflicts", [])
    route, action = _deterministic_action(state, missing, conflicts)
    citations = _top_policy_citations(state)
    evidence_status = "incomplete" if missing or conflicts else "sufficient_for_initial_review"
    draft = _draft_recommendation(state, route, action, evidence_status, missing, conflicts, citations)

    state["handler_recommendation"] = {
        "claim_id": state["claim_id"],
        "claim_type": state.get("claim_type"),
        "urgency": state.get("urgency"),
        "complexity": state.get("complexity"),
        "coverage_summary": state.get("coverage_summary"),
        "top_policy_citations": citations,
        "evidence_status": evidence_status,
        "risk_level": state.get("risk_level"),
        "risk_score": state.get("risk_score"),
        "risk_flags": state.get("risk_flags", []),
        "deterministic_route": route,
        "recommended_action": action,
        "recommendation_summary": draft["recommendation_summary"],
        "rationale": draft["rationale"],
        "supporting_evidence": draft["supporting_evidence"],
        "weakening_evidence": draft["weakening_evidence"],
        "relevant_policy_clauses": draft["relevant_policy_clauses"],
        "customer_questions": draft["customer_questions"],
        "missing_documents_to_request": draft["missing_documents_to_request"],
        "specialist_review_needed": draft["specialist_review_needed"],
        "specialist_review_reason": draft["specialist_review_reason"],
        "recommendation_confidence": draft["confidence"],
        "ai_drafted": draft["ai_drafted"],
        "human_approval_required": state.get("human_approval_required", False),
    }
    if draft.get("draft_error"):
        state["handler_recommendation"]["draft_error"] = draft["draft_error"]
    state["final_status"] = "human_review_required" if state.get("human_approval_required") else "ready_for_handler_review"
    return state
