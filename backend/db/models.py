"""
SQLite database models using SQLModel.
All tables are created on startup via init_db().
"""
from __future__ import annotations

import enum
from datetime import datetime, timezone
from typing import Optional

def _now() -> datetime:
    return datetime.now(timezone.utc)

from sqlmodel import Field, SQLModel


# ── Enums ─────────────────────────────────────────────────────────────────────

class RoleEnum(str, enum.Enum):
    cfo            = "cfo"
    supply_chain   = "supply_chain"
    claims_finance = "claims_finance"
    sales_rsm      = "sales_rsm"
    cnf_agent      = "cnf_agent"
    admin          = "admin"


class ClaimStatus(str, enum.Enum):
    pending  = "Pending"
    credited = "Credited"
    rejected = "Rejected"


class RiskLevel(str, enum.Enum):
    low    = "LOW"
    medium = "MEDIUM"
    high   = "HIGH"


# ── Users & Auth ──────────────────────────────────────────────────────────────

class User(SQLModel, table=True):
    __tablename__ = "users"
    id:            Optional[int] = Field(default=None, primary_key=True)
    username:      str           = Field(index=True, unique=True)
    email:         str           = Field(index=True, unique=True)
    hashed_password: str
    role:          RoleEnum      = Field(default=RoleEnum.sales_rsm)
    cnf_code:      Optional[str] = Field(default=None)   # scope for cnf_agent
    is_active:     bool          = Field(default=True)
    created_at:    datetime      = Field(default_factory=_now)


class RefreshToken(SQLModel, table=True):
    __tablename__ = "refresh_tokens"
    id:         Optional[int] = Field(default=None, primary_key=True)
    user_id:    int           = Field(foreign_key="users.id", index=True)
    token:      str           = Field(index=True, unique=True)
    revoked:    bool          = Field(default=False)
    created_at: datetime      = Field(default_factory=_now)
    expires_at: datetime


# ── Batch Analysis Results ─────────────────────────────────────────────────────

class BatchAnalysisRun(SQLModel, table=True):
    """One complete batch processing run over all CSV data."""
    __tablename__ = "batch_runs"
    id:                 Optional[int] = Field(default=None, primary_key=True)
    run_at:             datetime      = Field(default_factory=_now)
    total_claims:       int
    total_sales_rows:   int
    total_cnf_rows:     int
    duplicate_groups:   int
    duplicate_excess_inr:   float
    zero_invoice_inr:   float
    qty_overclaim_inr:  float
    pending_suspicious_inr: float
    at_risk_30d_inr:    float
    at_risk_60d_inr:    float
    at_risk_90d_inr:    float
    at_risk_180d_inr:   float
    total_addressable_inr: float      # now: credited against clear policy rules (T1 + T2), 30 months. Never adds stock or unverifiable claims.
    high_risk_stockists: int
    # Evidence tiers (agent/claim_checks.py). Defaults let an older database be upgraded in place.
    t1_claims:  int   = 0
    t1_inr:     float = 0.0           # filed over 90 days after expiry (whole credit) + packs above supply (excess only)
    t2_claims:  int   = 0
    t2_inr:     float = 0.0           # exact repeats and claims outside their window
    t3_claims:  int   = 0
    t3_inr:     float = 0.0           # needs a person: partial repeats, no invoice reference
    t4_claims:  int   = 0
    t4_inr:     float = 0.0           # cannot be checked from the extracts (batch older than the batch master)
    pending_t12_claims: int = 0       # pending claims that fail a clear rule today


class ClaimFinding(SQLModel, table=True):
    """One anomalous claim identified during a batch run."""
    __tablename__ = "claim_findings"
    id:             Optional[int] = Field(default=None, primary_key=True)
    run_id:         int           = Field(foreign_key="batch_runs.id", index=True)
    claim_no:       str           = Field(index=True)
    stockist_code:  str           = Field(index=True)
    batch_no:       str
    sku_code:       str
    claim_type:     str
    claim_date:     Optional[str]
    claim_value_inr: float
    status:         str
    risk_score:     int
    risk_level:     RiskLevel
    signals:        str           # comma-separated signal names
    has_invoice:    bool
    invoiced_qty:   float
    claimed_qty:    float
    recommended_action: str
    created_at:     datetime = Field(default_factory=_now)


class StockAlert(SQLModel, table=True):
    """One at-risk batch identified during a batch run."""
    __tablename__ = "stock_alerts"
    id:              Optional[int] = Field(default=None, primary_key=True)
    run_id:          int           = Field(foreign_key="batch_runs.id", index=True)
    cnf_code:        str           = Field(index=True)
    cnf_city:        Optional[str]
    sku_code:        str
    product:         str
    batch_no:        str
    expiry_date:     str
    days_to_expiry:  int
    qty_packs:       float
    pts_inr:         float
    value_inr:       float
    avg_monthly_outward: float
    recommend_redistribute: bool
    created_at:      datetime = Field(default_factory=_now)


class StockistRiskProfile(SQLModel, table=True):
    """Stockist-level risk profile refreshed each batch run."""
    __tablename__ = "stockist_risk"
    id:               Optional[int] = Field(default=None, primary_key=True)
    run_id:           int           = Field(foreign_key="batch_runs.id", index=True)
    stockist_code:    str           = Field(index=True)
    stockist_name:    Optional[str]
    cnf_code:         Optional[str]
    risk_score:       int
    claim_rate_pct:   float
    total_claim_inr:  float
    zero_inv_inr:     float
    dup_credit_inr:   float
    signals:          str
    created_at:       datetime = Field(default_factory=_now)


# ── Audit Log ─────────────────────────────────────────────────────────────────

class AuditLog(SQLModel, table=True):
    __tablename__ = "audit_logs"
    id:          Optional[int] = Field(default=None, primary_key=True)
    user_id:     Optional[int] = Field(default=None, foreign_key="users.id", index=True)
    username:    str
    action:      str           # e.g. "validate_claim", "ask_ai", "login"
    endpoint:    str
    ip_address:  Optional[str]
    success:     bool
    detail:      Optional[str] # sanitised — no internal paths
    created_at:  datetime = Field(default_factory=_now)


# ── User-Submitted Claims (AI agent creates these) ────────────────────────────

class UserClaim(SQLModel, table=True):
    """A claim created through the AI agent by an authenticated user."""
    __tablename__ = "user_claims"
    id:               Optional[int] = Field(default=None, primary_key=True)
    claim_no:         str  = Field(index=True, unique=True)
    submitted_by:     str  = Field(index=True)   # username
    stockist_code:    str
    batch_no:         str
    sku_code:         str
    qty_claimed:      float
    claim_date:       str
    claim_type:       str
    invoice_ref:      str  = ""
    status:           str  = Field(default="Submitted", index=True)
    # Submitted → Under Review → Approved / Rejected → Credited
    risk_score:       int  = 0
    risk_flags:       str  = ""
    claim_value_inr:  float = 0.0
    recovery_amount_inr: float = 0.0
    auditor_username: Optional[str] = None
    auditor_notes:    Optional[str] = None
    created_at:       datetime = Field(default_factory=_now)
    updated_at:       datetime = Field(default_factory=_now)
    resolved_at:      Optional[str] = None


# ── Per-User Chat History ──────────────────────────────────────────────────────

class ChatSession(SQLModel, table=True):
    __tablename__ = "chat_sessions"
    id:            Optional[int] = Field(default=None, primary_key=True)
    session_id:    str = Field(index=True, unique=True)
    user_username: str = Field(index=True)
    intent:        str = ""    # "create_claim" | "check_status" | "recovery_check"
    created_at:    datetime = Field(default_factory=_now)
    last_activity: datetime = Field(default_factory=_now)


class ChatMessage(SQLModel, table=True):
    __tablename__ = "chat_messages"
    id:          Optional[int] = Field(default=None, primary_key=True)
    session_id:  str = Field(index=True)
    role:        str   # "user" | "ai" | "system"
    content:     str
    tool_used:   str  = ""
    created_at:  datetime = Field(default_factory=_now)
