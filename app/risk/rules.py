from __future__ import annotations


def build_features(state: dict) -> dict:
    amount = float(state.get("claim_amount", 0))
    product = state.get("product_type", "motor")
    claim_type = state.get("claim_type", "")
    baseline = 1200.0 if product == "motor" else 1800.0
    if "escape_of_water" in claim_type:
        baseline = 2200.0
    if "theft" in claim_type:
        baseline = 3000.0
    evidence = state.get("evidence_review", {})
    duplicate_reference = any("duplicate" in f for f in state.get("risk_flags", []))
    return {
        "claim_amount": amount,
        "expected_amount": baseline,
        "amount_to_expected_ratio": amount / baseline if baseline else 0,
        "days_since_policy_start": int(state.get("days_since_policy_start", 9999)),
        "claims_last_12_months": int(state.get("claims_last_12_months", 0)),
        "incident_date_conflict": bool(evidence.get("conflicts")),
        "duplicate_invoice_reference": duplicate_reference,
    }


def apply_rules(features: dict) -> list[str]:
    flags: list[str] = []
    if features["amount_to_expected_ratio"] >= 2.5:
        flags.append("inflated_cost_indicator")
    if features["days_since_policy_start"] <= 30:
        flags.append("early_policy_claim")
    if features["claims_last_12_months"] >= 3:
        flags.append("high_claim_frequency")
    if features["duplicate_invoice_reference"]:
        flags.append("duplicate_invoice_reference")
    if features["incident_date_conflict"]:
        flags.append("incident_date_conflict")
    return flags


def score_risk(features: dict, flags: list[str]) -> float:
    score = 0.0
    weights = {
        "inflated_cost_indicator": 0.25,
        "early_policy_claim": 0.20,
        "high_claim_frequency": 0.20,
        "duplicate_invoice_reference": 0.30,
        "incident_date_conflict": 0.15,
    }
    for flag in flags:
        score += weights.get(flag, 0.1)
    return min(score, 1.0)


def risk_level(score: float) -> str:
    if score >= 0.75:
        return "high"
    if score >= 0.45:
        return "medium"
    return "low"
