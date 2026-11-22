"""Admin router: run batch, view audit log, manage users."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, desc, select

from auth.dependencies import require_permission, require_role
from batch.processor import run_batch
from db.database import get_session
from db.models import AuditLog, BatchAnalysisRun, User

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.post("/run-batch")
def trigger_batch(
    _: User = Depends(require_permission("run:batch")),
    session: Session = Depends(get_session),
):
    """Trigger a full data processing run. Admin only."""
    try:
        run = run_batch(session)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch failed: {str(e)[:200]}",
        )
    return {
        "message":             "Batch complete",
        "run_at":              run.run_at.isoformat(),
        "total_addressable_inr": run.total_addressable_inr,
        "findings":            run.__dict__.get("_findings_count", 0),
        "stock_alerts":        run.__dict__.get("_stock_alerts_count", 0),
    }


@router.get("/batch-history")
def batch_history(
    limit: int = Query(default=10, le=50),
    _: User = Depends(require_permission("read:batch_results")),
    session: Session = Depends(get_session),
):
    runs = session.exec(
        select(BatchAnalysisRun).order_by(desc(BatchAnalysisRun.run_at)).limit(limit)
    ).all()
    return [
        {
            "id":                    r.id,
            "run_at":                r.run_at.isoformat(),
            "total_addressable_inr": r.total_addressable_inr,
            "duplicate_groups":      r.duplicate_groups,
            "high_risk_stockists":   r.high_risk_stockists,
        }
        for r in runs
    ]


@router.get("/audit-log")
def audit_log(
    limit: int = Query(default=50, le=200),
    _: User = Depends(require_permission("read:audit")),
    session: Session = Depends(get_session),
):
    logs = session.exec(
        select(AuditLog).order_by(desc(AuditLog.created_at)).limit(limit)
    ).all()
    return [
        {
            "id":         l.id,
            "username":   l.username,
            "action":     l.action,
            "endpoint":   l.endpoint,
            "success":    l.success,
            "detail":     l.detail,
            "created_at": l.created_at.isoformat(),
        }
        for l in logs
    ]


@router.get("/users")
def list_users(
    _: User = Depends(require_permission("manage:users")),
    session: Session = Depends(get_session),
):
    users = session.exec(select(User)).all()
    return [
        {
            "id":       u.id,
            "username": u.username,
            "email":    u.email,
            "role":     u.role.value,
            "cnf_code": u.cnf_code,
            "is_active": u.is_active,
        }
        for u in users
    ]
