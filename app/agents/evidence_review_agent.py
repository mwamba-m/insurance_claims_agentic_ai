from __future__ import annotations

from app.agents.state import ClaimWorkflowState
from app.data_store import get_documents_for_claim
from app.observability.tracing import traced

@traced("evidence_review_agent")
def evidence_review_node(state: ClaimWorkflowState) -> ClaimWorkflowState:
    docs = get_documents_for_claim(state["claim_id"])
    missing: list[str] = []
    conflicts: list[dict] = []
    extracted = []

    required = ["invoice", "photo", "loss_report"]
    doc_types = {d.get("document_type") for d in docs}
    for req in required:
        if req not in doc_types:
            missing.append(req)

    for d in docs:
        extracted.append({
            "document_id": d.get("document_id"),
            "document_type": d.get("document_type"),
            "amount": d.get("amount"),
            "reference": d.get("reference"),
            "incident_date": d.get("incident_date"),
        })
        if d.get("incident_date") and d.get("incident_date") != d.get("fnol_incident_date"):
            conflicts.append({
                "field": "incident_date",
                "document_value": d.get("incident_date"),
                "fnol_value": d.get("fnol_incident_date"),
                "source": d.get("document_id"),
            })

    state["evidence_review"] = {
        "documents_reviewed": len(docs),
        "document_types": sorted(list(doc_types)),
        "extracted": extracted[:10],
        "missing_information": missing,
        "conflicts": conflicts,
        "critical_conflicts": bool(conflicts),
        "confidence": 0.8 if docs else 0.4,
    }
    if missing or conflicts:
        state["human_approval_required"] = True
    return state
