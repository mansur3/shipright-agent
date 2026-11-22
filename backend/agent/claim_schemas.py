"""
Pydantic schemas for the claims AI agent.
These enforce type safety at every boundary — the LLM cannot create
a claim with wrong types or missing required fields.
"""
from __future__ import annotations

from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


# ── Claim Types ──────────────────────────────────────────────────────────────

class ClaimTypeEnum(str, Enum):
    near_expiry        = "Near expiry"
    expired            = "Expired"
    breakage_in_transit = "Breakage in transit"
    short_supply       = "Short supply"


class ClaimStatusEnum(str, Enum):
    submitted     = "Submitted"
    under_review  = "Under Review"
    approved      = "Approved"
    rejected      = "Rejected"
    credited      = "Credited"


# ── Claim Creation Schema ─────────────────────────────────────────────────────

class ClaimCreate(BaseModel):
    """All fields required to create a valid claim."""
    stockist_code: str = Field(min_length=2, max_length=20, description="Stockist code e.g. STK0054")
    batch_no:      str = Field(min_length=2, max_length=20, description="Batch number e.g. K2310267")
    sku_code:      str = Field(min_length=2, max_length=20, description="SKU code e.g. PFL1102")
    qty_claimed:   float = Field(gt=0, description="Quantity claimed in packs")
    claim_date:    str = Field(description="Claim date in dd-mm-yyyy format")
    claim_type:    ClaimTypeEnum
    invoice_ref:   str = Field(default="", max_length=100, description="Original invoice ref if available")

    @field_validator("stockist_code", "batch_no", "sku_code")
    @classmethod
    def no_injection(cls, v: str) -> str:
        for pattern in ["ignore", "system", "prompt", "jailbreak", "DAN"]:
            if pattern.lower() in v.lower():
                raise ValueError(f"Field contains disallowed content")
        return v.strip().upper()

    @field_validator("claim_date")
    @classmethod
    def validate_date_format(cls, v: str) -> str:
        from datetime import datetime
        for fmt in ["%d-%m-%Y", "%Y-%m-%d"]:
            try:
                datetime.strptime(v.strip(), fmt)
                return v.strip()
            except ValueError:
                pass
        raise ValueError("Date must be dd-mm-yyyy format")


# ── Claim Response Schema ────────────────────────────────────────────────────

class ClaimResponse(BaseModel):
    claim_no:           str
    status:             ClaimStatusEnum
    risk_score:         int
    risk_flags:         list[str] = []
    claim_value_inr:    float
    recovery_amount_inr: float
    batch_valid:        bool
    batch_expiry:       Optional[str] = None
    invoiced_qty:       float
    recommended_action:  str


# ── Intent Classification ─────────────────────────────────────────────────────

class IntentEnum(str, Enum):
    create_claim   = "create_claim"
    check_status   = "check_status"
    recovery_check = "recovery_check"
    general        = "general"


class IntentResult(BaseModel):
    intent: IntentEnum
    confidence: float = Field(ge=0, le=1)


# ── Status Check Response ────────────────────────────────────────────────────

class ClaimStatusItem(BaseModel):
    claim_no:           str
    status:             str
    risk_score:         int
    claim_value_inr:    float
    recovery_amount_inr: float
    claim_type:         str
    batch_no:           str
    stockist_code:      str
    created_at:         str


class StatusResponse(BaseModel):
    claims:     list[ClaimStatusItem]
    total:      int
    total_value_inr: float


# ── Recovery Benchmark ───────────────────────────────────────────────────────

class RecoveryBenchmark(BaseModel):
    """CFO-facing benchmark: how much recovered vs how much recoverable."""
    # Already recovered (credited claims from batch analysis)
    recovered_inr:       float
    recoverable_now_inr: float     # duplicates + zero-match
    at_risk_inr:         float     # inventory at risk 0-90d
    projected_future_inr: float    # from scheme spike
    total_addressable_inr: float
    user_claims_pending: int
    user_claims_value_inr: float
    # Dynamic from user-submitted claims
    user_claims_submitted: int
    user_claims_approved_inr: float
