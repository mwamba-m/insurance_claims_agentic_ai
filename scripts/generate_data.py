from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from datetime import date, timedelta

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CLAIMS = DATA / "claims" / "synthetic_claims.jsonl"
DOCS = DATA / "documents" / "synthetic_documents.jsonl"
POLICIES = DATA / "policies"

random.seed(42)

MOTOR_FNOL = [
    "Customer reports being hit from behind while stationary at traffic lights on {d}. No injuries reported. Third party stopped but insurer details not yet provided. Repair estimate is £{amt}.",
    "Policyholder collided with a parked vehicle on {d}. Vehicle is driveable. Photos uploaded and repair invoice expected. Estimated damage £{amt}.",
    "Customer reports motorway incident on {d} with possible whiplash injury and third party involvement. Vehicle recovered. Estimated cost £{amt}.",
    "Windscreen damage reported after stone impact on {d}. No third party, no injury. Estimated cost £{amt}.",
]
HOME_FNOL = [
    "Customer reports escape of water from bathroom pipe on {d}. Damage to ceiling and flooring. Contractor estimate is £{amt}.",
    "Storm damage reported to roof tiles and guttering on {d}. Photos available. Estimated repair cost £{amt}.",
    "Customer reports burglary at home on {d}. Items stolen and police reference pending. Estimated loss £{amt}.",
    "Accidental damage to kitchen worktop reported on {d}. Customer submitted loss report. Estimated amount £{amt}.",
]


def write_policies() -> None:
    POLICIES.mkdir(parents=True, exist_ok=True)
    (POLICIES / "motor_policy.md").write_text("""# Motor Insurance Policy Wording 2026

## Accidental Damage
We will cover accidental damage to the insured vehicle caused by collision, impact, malicious damage, fire, theft or attempted theft, subject to the policy excess and the terms of this policy. The policyholder must provide reasonable evidence of the incident and repair cost.

## Third Party Liability
We will cover legal liability for injury or damage to third parties arising from use of the insured vehicle where the policyholder is legally responsible. Claims involving injury, disputed liability, or multiple parties must be reviewed by a handler.

## Windscreen Cover
We will cover repair or replacement of damaged windscreen glass subject to the windscreen excess shown in the schedule. No claims discount may be unaffected where an approved repairer is used.

## Motor Exclusions
We will not cover wear and tear, mechanical breakdown, deliberate damage by the policyholder, driving under the influence, use outside policy terms, or loss where required evidence is not supplied.

## Motor Excess Rules
The policy excess applies to accidental damage claims. Additional young driver or inexperienced driver excess may apply. Handler should confirm the schedule before settlement.

## Evidence Conditions
The policyholder must provide invoices, photos, third-party details where relevant, and any police reference where the incident involves theft, injury, malicious damage, or legal dispute.
""", encoding="utf-8")

    (POLICIES / "home_policy.md").write_text("""# Home Insurance Policy Wording 2026

## Escape of Water
We will cover sudden and unexpected damage caused by escape of water from fixed domestic water or heating installations. Cover is subject to policy excess, maintenance conditions, and evidence of the cause of damage.

## Escape of Water Exclusions
We will not cover gradual leakage, wear and tear, defective workmanship, lack of maintenance, or damage that happened before the policy started. Claims with signs of long-term water damage require handler review.

## Storm Damage
We will cover storm damage to the buildings where there is evidence of storm conditions and direct physical damage. The customer should provide photographs, repair estimates, and where available weather evidence.

## Theft and Burglary
We will cover theft following forcible or violent entry subject to policy limits and exclusions. The policyholder must provide a police reference and evidence of ownership for high-value items.

## Accidental Damage
Where accidental damage cover is selected, we will cover sudden accidental physical damage to buildings or contents, subject to exclusions and policy limits.

## Home Exclusions
We will not cover wear and tear, gradual deterioration, faulty workmanship, pre-existing damage, or damage caused deliberately by the policyholder or household members.

## Home Excess Rules
The policy excess applies to buildings and contents claims. Escape of water may have a higher excess shown in the schedule. Handler should confirm the applicable excess.

## Evidence Conditions
The policyholder must provide a loss description, photographs where available, invoices or contractor estimates, police references for theft, and any third-party report relevant to the claim.
""", encoding="utf-8")


def claim_type_from_text(product: str, text: str) -> str:
    low = text.lower()
    if product == "motor":
        return "motor_injury" if "injury" in low or "whiplash" in low else "motor_accident" if "windscreen" not in low else "motor_windscreen"
    if "escape of water" in low:
        return "home_escape_of_water"
    if "storm" in low:
        return "home_storm_damage"
    if "burglary" in low or "stolen" in low:
        return "home_theft"
    return "home_accidental_damage"


def urgency_from(amount: float, ctype: str) -> str:
    if "injury" in ctype or amount > 7000:
        return "high"
    if amount > 2000:
        return "medium"
    return "low"


def generate(records: int) -> None:
    write_policies()
    CLAIMS.parent.mkdir(parents=True, exist_ok=True)
    DOCS.parent.mkdir(parents=True, exist_ok=True)
    today = date(2026, 5, 26)
    seen_refs: list[str] = []

    with CLAIMS.open("w", encoding="utf-8") as cf, DOCS.open("w", encoding="utf-8") as df:
        for i in range(1, records + 1):
            product = "motor" if random.random() < 0.55 else "home"
            amount = round(random.lognormvariate(7.2, 0.65), 2)
            amount = max(120.0, min(amount, 15000.0))
            d = today - timedelta(days=random.randint(1, 365))
            template = random.choice(MOTOR_FNOL if product == "motor" else HOME_FNOL)
            text = template.format(d=d.isoformat(), amt=f"{amount:,.2f}")
            ctype = claim_type_from_text(product, text)
            urgency = urgency_from(amount, ctype)
            claim_id = f"CLM-{i:06d}"
            policy_id = f"{'MOTOR' if product == 'motor' else 'HOME'}-2026-{random.randint(1,999):03d}"
            days_since_start = random.randint(1, 1500)
            if random.random() < 0.04:
                days_since_start = random.randint(1, 25)
            claims_12m = random.choices([0, 1, 2, 3, 4, 5], weights=[55, 25, 10, 5, 3, 2])[0]
            docs = []
            for doc_type in ["invoice", "loss_report", "photo"]:
                if random.random() < (0.82 if doc_type == "invoice" else 0.65):
                    doc_id = f"DOC-{claim_id}-{doc_type}"
                    docs.append(doc_id)
                    duplicate = random.random() < 0.015 and seen_refs
                    ref = random.choice(seen_refs) if duplicate else f"INV-{random.randint(100000,999999)}"
                    if doc_type == "invoice":
                        seen_refs.append(ref)
                    incident_date = d.isoformat()
                    if random.random() < 0.035:
                        incident_date = (d - timedelta(days=random.randint(1, 7))).isoformat()
                    df.write(json.dumps({
                        "document_id": doc_id,
                        "claim_id": claim_id,
                        "document_type": doc_type,
                        "reference": ref,
                        "amount": amount if doc_type == "invoice" else None,
                        "incident_date": incident_date,
                        "fnol_incident_date": d.isoformat(),
                        "text": f"{doc_type} for {claim_id} reference {ref} amount {amount}",
                    }) + "\n")
            risk_flags = []
            if len(seen_refs) > 1 and random.random() < 0.01:
                risk_flags.append("duplicate_invoice_reference")
            row = {
                "claim_id": claim_id,
                "policy_id": policy_id,
                "product_type": product,
                "fnol_text": text,
                "customer_segment": random.choice(["standard", "premium", "vulnerable", "commercial" ]),
                "claim_amount": amount,
                "days_since_policy_start": days_since_start,
                "claims_last_12_months": claims_12m,
                "documents": docs,
                "risk_flags": risk_flags,
                "expected": {"claim_type": ctype, "urgency": urgency},
            }
            cf.write(json.dumps(row) + "\n")
    print(f"Generated {records} claims at {CLAIMS}")
    print(f"Generated documents at {DOCS}")
    print(f"Generated policy docs at {POLICIES}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--records", type=int, default=10000)
    args = parser.parse_args()
    generate(min(args.records, 10000))
