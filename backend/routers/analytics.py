"""
Analytics router — RBAC-gated read endpoints served from SQLite.
No internal paths, file names, or DB structure are exposed to the client.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, desc, select

from auth.dependencies import get_current_user, require_permission
from db.database import get_session
from db.models import (
    BatchAnalysisRun,
    ClaimFinding,
    StockAlert,
    StockistRiskProfile,
    User,
)

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


# ── Latest batch summary (CFO / SC / Claims / Admin) ─────────────────────────
@router.get("/summary")
def get_summary(
    _: User = Depends(require_permission("read:dashboard")),
    session: Session = Depends(get_session),
):
    run = session.exec(
        select(BatchAnalysisRun).order_by(desc(BatchAnalysisRun.run_at))
    ).first()
    if not run:
        return {"message": "No batch run found. Run /api/admin/run-batch first."}
    return {
        "run_at":               run.run_at.isoformat(),
        "total_claims":         run.total_claims,
        "total_sales_rows":     run.total_sales_rows,
        "duplicate_groups":     run.duplicate_groups,
        "duplicate_excess_inr": run.duplicate_excess_inr,
        "zero_invoice_inr":     run.zero_invoice_inr,
        "qty_overclaim_inr":    run.qty_overclaim_inr,
        "pending_suspicious_inr": run.pending_suspicious_inr,
        "at_risk_30d_inr":      run.at_risk_30d_inr,
        "at_risk_60d_inr":      run.at_risk_60d_inr,
        "at_risk_90d_inr":      run.at_risk_90d_inr,
        "at_risk_180d_inr":     run.at_risk_180d_inr,
        "total_addressable_inr": run.total_addressable_inr,
        "high_risk_stockists":  run.high_risk_stockists,
        # evidence tiers: never added together with stock or revenue
        "clear_breach_inr":     run.t1_inr + run.t2_inr,
        "t1_claims": run.t1_claims, "t1_inr": run.t1_inr,
        "t2_claims": run.t2_claims, "t2_inr": run.t2_inr,
        "t3_claims": run.t3_claims, "t3_inr": run.t3_inr,
        "t4_claims": run.t4_claims, "t4_inr": run.t4_inr,
        "pending_t12_claims": run.pending_t12_claims,
        "meaning": {
            "total_addressable_inr": "credited against clear policy rules (T1 + T2) over Apr 2024 to Sep 2026; not annual, not stock, not unverifiable",
            "zero_invoice_inr": "credited on batches older than the extracts; cannot be checked, not shown invalid",
            "duplicate_excess_inr": "credited again for the same stockist, batch and quantity",
            "at_risk_180d_inr": "stock on hand at the latest month-end expiring within the horizon",
        },
    }


# ── Claim findings (Claims Finance / CFO / Admin) ─────────────────────────────
@router.get("/claim-findings")
def get_claim_findings(
    risk_level: str = Query(default="", description="LOW, MEDIUM, HIGH"),
    status: str = Query(default=""),
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0),
    _: User = Depends(require_permission("read:claims")),
    session: Session = Depends(get_session),
):
    run = session.exec(
        select(BatchAnalysisRun).order_by(desc(BatchAnalysisRun.run_at))
    ).first()
    if not run:
        return {"findings": [], "total": 0}

    q = select(ClaimFinding).where(ClaimFinding.run_id == run.id)
    if risk_level:
        q = q.where(ClaimFinding.risk_level == risk_level.upper())
    if status:
        q = q.where(ClaimFinding.status == status)
    q = q.order_by(desc(ClaimFinding.risk_score)).offset(offset).limit(limit)
    findings = session.exec(q).all()
    return {
        "findings": [
            {
                "claim_no":          f.claim_no,
                "stockist_code":     f.stockist_code,
                "batch_no":          f.batch_no,
                "sku_code":          f.sku_code,
                "claim_type":        f.claim_type,
                "claim_date":        f.claim_date,
                "claim_value_inr":   f.claim_value_inr,
                "status":            f.status,
                "risk_score":        f.risk_score,
                "risk_level":        f.risk_level,
                "signals":           f.signals.split(",") if f.signals else [],
                "has_invoice":       f.has_invoice,
                "invoiced_qty":      f.invoiced_qty,
                "claimed_qty":       f.claimed_qty,
                "recommended_action": f.recommended_action,
            }
            for f in findings
        ],
        "total": len(findings),
        "run_at": run.run_at.isoformat(),
    }


# ── At-risk stock (Supply / CFO / Admin, CNF-scoped for cnf_agent) ────────────
@router.get("/at-risk-stock")
def get_at_risk(
    days: int = Query(default=90, ge=1, le=365),
    cnf_code: str = Query(default=""),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    # Role-based scope: cnf_agent sees only their CNF
    from auth.dependencies import PERMISSIONS
    role = user.role.value
    if role not in PERMISSIONS.get("read:at_risk_all", set()):
        if role in PERMISSIONS.get("read:at_risk_own_cnf", set()):
            if user.cnf_code:
                cnf_code = user.cnf_code
            else:
                return {"batches": [], "total_value_inr": 0}
        else:
            from fastapi import HTTPException, status as st
            raise HTTPException(status_code=st.HTTP_403_FORBIDDEN, detail="Access denied")

    run = session.exec(
        select(BatchAnalysisRun).order_by(desc(BatchAnalysisRun.run_at))
    ).first()
    if not run:
        return {"batches": [], "total_value_inr": 0}

    q = select(StockAlert).where(
        StockAlert.run_id == run.id,
        StockAlert.days_to_expiry <= days,
        StockAlert.days_to_expiry >= 0,
    )
    if cnf_code:
        q = q.where(StockAlert.cnf_code == cnf_code.upper())
    q = q.order_by(StockAlert.days_to_expiry)
    alerts = session.exec(q).all()

    total_value = sum(a.value_inr for a in alerts)
    by_therapy: dict[str, float] = {}
    for a in alerts:
        ta = a.sku_code[:5]  # simplified; real impl joins sku_master
        by_therapy[ta] = by_therapy.get(ta, 0) + a.value_inr

    return {
        "batches": [
            {
                "cnf_code":           a.cnf_code,
                "cnf_city":           a.cnf_city,
                "sku_code":           a.sku_code,
                "product":            a.product,
                "batch_no":           a.batch_no,
                "expiry_date":        a.expiry_date,
                "days_to_expiry":     a.days_to_expiry,
                "qty_packs":          a.qty_packs,
                "value_inr":          a.value_inr,
                "recommend_redistribute": a.recommend_redistribute,
            }
            for a in alerts
        ],
        "total_batches": len(alerts),
        "total_value_inr": total_value,
        "run_at": run.run_at.isoformat(),
    }


# ── Stockist risk (Sales RSM sees only their stockists) ────────────────────────
@router.get("/stockist-risk")
def get_stockist_risk(
    min_score: int = Query(default=25),
    limit: int = Query(default=50, le=200),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    from auth.dependencies import PERMISSIONS
    role = user.role.value
    can_see_all = role in PERMISSIONS.get("read:stockist_any", set())
    can_see_own = role in PERMISSIONS.get("read:stockist_own", set())

    if not can_see_all and not can_see_own:
        from fastapi import HTTPException, status as st
        raise HTTPException(status_code=st.HTTP_403_FORBIDDEN, detail="Access denied")

    run = session.exec(
        select(BatchAnalysisRun).order_by(desc(BatchAnalysisRun.run_at))
    ).first()
    if not run:
        return {"profiles": []}

    q = select(StockistRiskProfile).where(
        StockistRiskProfile.run_id == run.id,
        StockistRiskProfile.risk_score >= min_score,
    ).order_by(desc(StockistRiskProfile.risk_score)).limit(limit)

    if can_see_own and user.cnf_code:
        q = q.where(StockistRiskProfile.cnf_code == user.cnf_code)

    profiles = session.exec(q).all()
    return {
        "profiles": [
            {
                "stockist_code":  p.stockist_code,
                "stockist_name":  p.stockist_name,
                "cnf_code":       p.cnf_code,
                "risk_score":     p.risk_score,
                "claim_rate_pct": p.claim_rate_pct,
                "total_claim_inr": p.total_claim_inr,
                "zero_inv_inr":   p.zero_inv_inr,
                "dup_credit_inr": p.dup_credit_inr,
                "signals":        p.signals.split(",") if p.signals else [],
            }
            for p in profiles
        ],
        "run_at": run.run_at.isoformat(),
    }


# ── Recovery: what can be claimed back, held, or needs a person ───────────────
@router.get("/recovery")
def get_recovery(_: User = Depends(require_permission("read:dashboard"))):
    from agent import recovery
    r = recovery.build()
    return {k: r[k] for k in ("buckets", "recover_inr", "recover_claims", "recover_per_year_inr", "window", "basis")} | {"by_stockist": r["by_stockist"][:20]}


@router.get("/recovery/claims")
def get_recovery_claims(
    bucket: str = Query(default="", description="recover_t1, recover_t2 or hold"),
    limit: int = Query(default=1000, le=2000),
    _: User = Depends(require_permission("read:claims")),
):
    from agent import recovery
    rows = [c for c in recovery.build()["claims"] if not bucket or c["bucket"] == bucket]
    return {"claims": rows[:limit], "total": len(rows)}
