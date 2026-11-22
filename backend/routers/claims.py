"""
Claims router — AI-driven claim creation, status checking, auditor review, CFO benchmark.

Endpoints:
  POST /api/claims/chat           — multi-turn AI agent (create + status + recovery)
  GET  /api/claims/my              — current user's claims only
  GET  /api/claims/all             — all claims (auditor / CFO / admin only)
  POST /api/claims/{id}/review     — auditor reviews a claim (approve/reject/credit)
  GET  /api/claims/benchmark       — CFO recovery benchmark table
  GET  /api/claims/chat-history     — per-user chat history
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, status
from pydantic import BaseModel
from sqlmodel import Session, desc, select

from agent.claims_graph import run_claims_agent
from auth.dependencies import get_current_user, require_permission
from db.database import get_session
from db.models import (
    BatchAnalysisRun,
    ChatMessage,
    ChatSession,
    UserClaim,
    User,
)

router = APIRouter(prefix="/api/claims", tags=["claims"])


# ── Chat with the claims AI agent ─────────────────────────────────────────────

class ClaimsChatBody(BaseModel):
    message: str
    session_id: str = ""   # empty = new session


@router.post("/chat")
def claims_chat(
    body: ClaimsChatBody,
    request: Request,
    user: User = Depends(get_current_user),
):
    """Multi-turn conversational AI for claim creation, status, and recovery."""
    if len(body.message.strip()) < 3:
        raise HTTPException(status_code=422, detail="Message too short")
    if len(body.message) > 800:
        raise HTTPException(status_code=422, detail="Message too long (max 800 chars)")

    session_id = body.session_id or f"sess-{uuid.uuid4().hex[:12]}"

    try:
        result = run_claims_agent(
            question=body.message,
            username=user.username,
            session_id=session_id,
        )
    except Exception:
        # Wording the reply is optional (the agent falls back to its own text), so a failure here is a code or data problem, not "AI unavailable".
        logging.getLogger(__name__).exception("claims chat failed")
        raise HTTPException(status_code=500, detail="Could not process that message. Please try again, or rephrase it.")

    return {
        "answer":         result.get("answer", ""),
        "intent":         result.get("intent", "general"),
        "claim_no":       result.get("claim_no"),
        "session_id":     session_id,
        "status_result":  result.get("status_result"),
        "recovery_result": result.get("recovery_result"),
    }


# ── My claims (current user only) ────────────────────────────────────────────

@router.get("/my")
def my_claims(
    status_filter: str = Query(default=""),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Return only the current user's submitted claims."""
    q = select(UserClaim).where(UserClaim.submitted_by == user.username)
    if status_filter:
        q = q.where(UserClaim.status == status_filter)
    q = q.order_by(desc(UserClaim.created_at))
    claims = session.exec(q).all()

    total_value = sum(c.claim_value_inr for c in claims)
    total_recovery = sum(c.recovery_amount_inr for c in claims)

    return {
        "claims": [
            {
                "id":                  c.id,
                "claim_no":            c.claim_no,
                "status":              c.status,
                "stockist_code":       c.stockist_code,
                "batch_no":            c.batch_no,
                "sku_code":            c.sku_code,
                "qty_claimed":         c.qty_claimed,
                "claim_date":          c.claim_date,
                "claim_type":          c.claim_type,
                "invoice_ref":         c.invoice_ref,
                "risk_score":          c.risk_score,
                "risk_flags":          c.risk_flags.split(",") if c.risk_flags else [],
                "claim_value_inr":     c.claim_value_inr,
                "recovery_amount_inr": c.recovery_amount_inr,
                "auditor_username":    c.auditor_username,
                "auditor_notes":       c.auditor_notes,
                "created_at":          c.created_at.isoformat() if c.created_at else "",
                "updated_at":           c.updated_at.isoformat() if c.updated_at else "",
                "resolved_at":          c.resolved_at,
            }
            for c in claims
        ],
        "total": len(claims),
        "total_claim_value_inr": total_value,
        "total_recovery_inr": total_recovery,
    }


# ── All claims (auditor / CFO / admin only) ───────────────────────────────────

@router.get("/all")
def all_claims(
    status_filter: str = Query(default=""),
    submitted_by: str = Query(default=""),
    min_risk: int = Query(default=0, ge=0, le=100),
    limit: int = Query(default=100, le=500),
    user: User = Depends(require_permission("read:claims")),
    session: Session = Depends(get_session),
):
    """Return all user-submitted claims for audit / review. Claims Finance, CFO, Admin."""
    q = select(UserClaim)
    if status_filter:
        q = q.where(UserClaim.status == status_filter)
    if submitted_by:
        q = q.where(UserClaim.submitted_by == submitted_by)
    if min_risk > 0:
        q = q.where(UserClaim.risk_score >= min_risk)
    q = q.order_by(desc(UserClaim.created_at)).limit(limit)
    claims = session.exec(q).all()

    return {
        "claims": [
            {
                "id":                  c.id,
                "claim_no":            c.claim_no,
                "submitted_by":        c.submitted_by,
                "status":              c.status,
                "stockist_code":       c.stockist_code,
                "batch_no":            c.batch_no,
                "sku_code":            c.sku_code,
                "qty_claimed":         c.qty_claimed,
                "claim_type":          c.claim_type,
                "risk_score":          c.risk_score,
                "risk_flags":          c.risk_flags.split(",") if c.risk_flags else [],
                "claim_value_inr":     c.claim_value_inr,
                "recovery_amount_inr": c.recovery_amount_inr,
                "auditor_username":    c.auditor_username,
                "auditor_notes":       c.auditor_notes,
                "created_at":          c.created_at.isoformat() if c.created_at else "",
            }
            for c in claims
        ],
        "total": len(claims),
    }


# ── Auditor review (approve / reject / credit) ───────────────────────────────

class ReviewBody(BaseModel):
    decision: str           # "Approved" | "Rejected" | "Credited" | "Under Review"
    notes: str = ""


@router.post("/{claim_id}/review")
def review_claim(
    claim_id: int,
    body: ReviewBody,
    user: User = Depends(require_permission("write:validate_claim")),
    session: Session = Depends(get_session),
):
    """Auditor reviews a user-submitted claim."""
    claim = session.get(UserClaim, claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    valid_decisions = ["Approved", "Rejected", "Credited", "Under Review"]
    if body.decision not in valid_decisions:
        raise HTTPException(status_code=422, detail=f"Decision must be one of: {', '.join(valid_decisions)}")

    claim.status = body.decision
    claim.auditor_username = user.username
    claim.auditor_notes = body.notes[:500]
    claim.updated_at = datetime.now(timezone.utc)
    if body.decision in ("Approved", "Rejected", "Credited"):
        claim.resolved_at = datetime.now(timezone.utc).isoformat()

    session.add(claim)
    session.commit()
    session.refresh(claim)

    return {
        "claim_no":       claim.claim_no,
        "status":         claim.status,
        "reviewed_by":    user.username,
        "recovery_inr":   claim.recovery_amount_inr if body.decision == "Rejected" else 0.0,
    }


# ── CFO Recovery Benchmark ────────────────────────────────────────────────────

@router.get("/benchmark")
def recovery_benchmark(
    user: User = Depends(require_permission("read:report")),
    session: Session = Depends(get_session),
):
    """
    CFO-facing benchmark: how much recovered vs how much recoverable.
    Combines batch-analysis findings with user-submitted claim data.
    """
    # Latest batch run
    run = session.exec(
        select(BatchAnalysisRun).order_by(desc(BatchAnalysisRun.run_at))
    ).first()

    # User-submitted claims
    all_user_claims = session.exec(select(UserClaim)).all()
    submitted = len(all_user_claims)
    pending = [c for c in all_user_claims if c.status in ("Submitted", "Under Review")]
    approved = [c for c in all_user_claims if c.status == "Approved"]
    rejected = [c for c in all_user_claims if c.status == "Rejected"]
    credited = [c for c in all_user_claims if c.status == "Credited"]

    return {
        "batch_analysis": {
            "duplicate_excess_inr":  run.duplicate_excess_inr if run else 0,
            "zero_invoice_inr":      run.zero_invoice_inr if run else 0,
            "qty_overclaim_inr":    run.qty_overclaim_inr if run else 0,
            "at_risk_30d_inr":       run.at_risk_30d_inr if run else 0,
            "at_risk_60d_inr":       run.at_risk_60d_inr if run else 0,
            "at_risk_90d_inr":       run.at_risk_90d_inr if run else 0,
            "total_addressable_inr": run.total_addressable_inr if run else 0,
        } if run else None,
        "user_claims": {
            "total_submitted":   submitted,
            "pending":           len(pending),
            "pending_value_inr": sum(c.claim_value_inr for c in pending),
            "approved":          len(approved),
            "approved_value_inr": sum(c.claim_value_inr for c in approved),
            "rejected":          len(rejected),
            "rejected_value_inr": sum(c.claim_value_inr for c in rejected),
            "credited":          len(credited),
            "credited_value_inr": sum(c.claim_value_inr for c in credited),
            "recovery_from_blocks_inr": sum(c.recovery_amount_inr for c in rejected),
            "recovery_from_reviews_inr": sum(c.recovery_amount_inr for c in pending),
        },
        "benchmark": {
            # Each figure is one kind of rupee. Nothing here is added to anything else and nothing is multiplied by an assumed factor.
            "recovered_inr":        sum(c.recovery_amount_inr for c in rejected),                  # only what users actually stopped through this tool
            "recoverable_now_inr":  run.pending_suspicious_inr if run else 0,                      # pending claims failing a clear rule today: hold before credit
            "at_risk_inr":          run.at_risk_90d_inr if run else 0,                             # stock on hand at the latest month-end expiring within 90 days
            "total_addressable_inr": run.total_addressable_inr if run else 0,                      # credited against clear rules, Apr 2024 to Sep 2026 (30 months)
            "projected_annual_inr":  (run.total_addressable_inr / 2.5) if run else 0,              # the same, per year (30 months = 2.5 years)
            "unverifiable_inr":     run.zero_invoice_inr if run else 0,                            # credited on batches older than the extracts: cannot be checked
        },
    }


# ── Per-user chat history ─────────────────────────────────────────────────────

@router.get("/chat-history")
def chat_history(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Return the current user's chat sessions and messages."""
    sessions = session.exec(
        select(ChatSession)
        .where(ChatSession.user_username == user.username)
        .order_by(desc(ChatSession.last_activity))
    ).all()

    result = []
    for s in sessions:
        messages = session.exec(
            select(ChatMessage)
            .where(ChatMessage.session_id == s.session_id)
            .order_by(ChatMessage.id)
        ).all()
        result.append({
            "session_id":    s.session_id,
            "intent":         s.intent,
            "created_at":     s.created_at.isoformat() if s.created_at else "",
            "last_activity":  s.last_activity.isoformat() if s.last_activity else "",
            "messages": [
                {"role": m.role, "content": m.content, "created_at": m.created_at.isoformat() if m.created_at else ""}
                for m in messages
            ],
        })

    return {"sessions": result}
