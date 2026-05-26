from __future__ import annotations

from collections import Counter
from app.data_store import list_claims
from app.agents.workflow import run_claim_workflow


def evaluate_cases(limit: int = 100) -> dict:
    claims = list_claims(limit=limit)
    results = []
    for claim in claims:
        out = run_claim_workflow(claim)
        expected = claim.get("expected", {})
        results.append({
            "claim_id": claim["claim_id"],
            "expected_claim_type": expected.get("claim_type"),
            "actual_claim_type": out.get("claim_type"),
            "claim_type_match": expected.get("claim_type") == out.get("claim_type"),
            "expected_urgency": expected.get("urgency"),
            "actual_urgency": out.get("urgency"),
            "urgency_match": expected.get("urgency") == out.get("urgency"),
            "citations_count": len(out.get("retrieved_policy_clauses", [])),
            "human_approval_required": out.get("human_approval_required", False),
            "risk_level": out.get("risk_level"),
            "errors": out.get("errors", []),
        })
    n = len(results) or 1
    risk_counts = Counter(r["risk_level"] for r in results)
    return {
        "cases_evaluated": len(results),
        "claim_type_accuracy": sum(r["claim_type_match"] for r in results) / n,
        "urgency_accuracy": sum(r["urgency_match"] for r in results) / n,
        "average_citations": sum(r["citations_count"] for r in results) / n,
        "human_approval_rate": sum(r["human_approval_required"] for r in results) / n,
        "risk_level_counts": dict(risk_counts),
        "sample_results": results[:10],
    }
