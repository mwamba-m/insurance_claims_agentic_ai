from __future__ import annotations

from typing import Any, Literal, TypedDict

class ClaimWorkflowState(TypedDict, total=False):
    claim_id: str
    policy_id: str
    product_type: Literal["motor", "home"]
    fnol_text: str
    customer_segment: str
    claim_amount: float
    days_since_policy_start: int
    claims_last_12_months: int
    documents: list[str]

    claim_type: str
    urgency: str
    complexity: str
    incident_facts: dict[str, Any]
    triage_summary: dict[str, Any]

    retrieved_policy_clauses: list[dict[str, Any]]
    coverage_summary: str

    evidence_review: dict[str, Any]
    risk_score: float
    risk_level: str
    risk_flags: list[str]
    fraud_referral_required: bool

    handler_recommendation: dict[str, Any]
    human_approval_required: bool
    errors: list[str]
    fallback_reason: str
    final_status: str
