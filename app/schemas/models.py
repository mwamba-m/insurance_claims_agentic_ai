from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field

ProductType = Literal["motor", "home"]

class PolicySearchRequest(BaseModel):
    query: str
    product_type: ProductType | None = None
    top_k: int = Field(default=5, ge=1, le=20)

class ClaimRunResponse(BaseModel):
    claim_id: str
    status: str
    result: dict[str, Any]

class Claim(BaseModel):
    claim_id: str
    policy_id: str
    product_type: ProductType
    fnol_text: str
    customer_segment: str
    claim_amount: float
    days_since_policy_start: int
    claims_last_12_months: int
    documents: list[str] = []
