"""
Production FastAPI entrypoint — Project Sankalp AI Platform.

On startup:
  1. Initialises SQLite (creates tables, seeds default users)
  2. Runs the full batch analysis (builds findings + stock alerts in DB)
  3. Serves RBAC-gated API + static frontend
"""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from sqlmodel import Session

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(name)s  %(message)s")
log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ───────────────────────────────────────────────────────────────
    from db.database import init_db, engine
    from batch.processor import run_batch

    log.info("Initialising database…")
    init_db()

    log.info("Running initial batch analysis…")
    with Session(engine) as session:
        try:
            run = run_batch(session)
            log.info(
                "Batch complete — INR %.0f addressable, %d findings",
                run.total_addressable_inr,
                run.__dict__.get("_findings_count", 0),
            )
        except Exception as exc:
            log.warning("Batch failed on startup (continuing): %s", exc)

    yield
    # ── Shutdown ──────────────────────────────────────────────────────────────
    log.info("Shutting down")


app = FastAPI(
    title="Sankalp AI — Pfizer Channel Intelligence",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url=None,
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# CORS: only the frontend origins listed in SANKALP_ALLOWED_ORIGINS (comma separated). The token is a bearer header, so no credentials.
_ORIGINS = [o.strip() for o in os.getenv("SANKALP_ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000,http://localhost:8000").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)


# ── Global error handler (never leak stack traces to client) ──────────────────
@app.exception_handler(Exception)
async def _unhandled(request: Request, exc: Exception):
    log.exception("Unhandled error on %s", request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal error occurred. Please contact support."},
    )


# ── Routers ───────────────────────────────────────────────────────────────────
from routers.auth      import router as auth_router
from routers.analytics import router as analytics_router
from routers.chat      import router as chat_router
from routers.admin     import router as admin_router
from routers.claims    import router as claims_router

from agent import tools as t
from auth.dependencies import require_permission
from auth.ratelimit import limit
from db.models import User

app.include_router(auth_router)
app.include_router(analytics_router)
app.include_router(chat_router)
app.include_router(admin_router)
app.include_router(claims_router)


# ── Health (public, minimal) ──────────────────────────────────────────────────
@app.get("/api/health")
def health():
    return {"ok": True}


# ── Claims Gatekeeper: deterministic check, no model. One implementation: agent/claim_checks.py ─────────────
from fastapi import Depends as _Depends, Query as Q
from pydantic import BaseModel as _BM, Field as _Field
from typing import Optional as _Opt


class _ClaimAuditReq(_BM):
    stockist_code: str = _Field(min_length=3, max_length=12)
    batch_no: str = _Field(min_length=3, max_length=20)
    qty_claimed: float = _Field(gt=0, le=10_000_000)
    claim_date: str = _Field(default="2026-09-30", max_length=12)
    claim_type: str = _Field(default="Near expiry", max_length=30)
    original_invoice_ref: _Opt[str] = _Field(default=None, max_length=40)
    has_am_ledger_approval: bool = False


@app.post("/api/audit-claim")
def audit_claim_direct(req: _ClaimAuditReq, _: User = _Depends(require_permission("write:validate_claim"))):
    """Check one claim against CO-POL-014. A recommendation for Commercial Finance, never a credit note."""
    import time as _time
    from agent.claim_checks import ClaimInput, evaluate
    from agent.clean import get_clean, parse_date

    _t0 = _time.perf_counter()
    C = get_clean()
    ci = ClaimInput(stockist=req.stockist_code, batch=req.batch_no, qty=req.qty_claimed, claim_date=parse_date(req.claim_date),
                    claim_type=req.claim_type.strip(), invoice_ref=req.original_invoice_ref or "")
    v = evaluate(ci, C)
    d = v.as_dict()
    if "no_invoice_ref" in v.flags and req.has_am_ledger_approval:
        d["reason"] += "; the caller says an Area Manager ledger approval exists: it is not in the extracts and must be attached by the person deciding"
    stk, bat = req.stockist_code.strip().upper(), req.batch_no.strip().upper()
    prior = C.credited_before(stk, bat)
    return {
        "latency_ms": round((_time.perf_counter() - _t0) * 1000, 1), "tools_called": ["claim_checks.evaluate"], "model_calls": 0,
        "verdict": {**d, "checks_failed": v.reasons},
        "evidence": {
            "records": v.evidence,
            "batch": ({"batch_no": bat, "sku_code": C.batches[bat]["sku"], "expiry_date": C.batches[bat]["exp"].isoformat()} if bat in C.batches else {"found": False}),
            "stockist": ({"stockist_code": stk, "stockist_name": C.stockists[stk]["name"]} if stk in C.stockists else {"found": False}),
            "billed_history": {"total_billed_packs": C.supply.get((stk, bat), 0.0)},
            "prior_claims": {"prior_claimed_packs": sum(p["qty"] for p in prior)},
        },
    }


class _SchemeReq(_BM):
    stockist_code: str = _Field(min_length=3, max_length=12)
    sku_code: str = _Field(min_length=3, max_length=12)
    proposed_order_qty: float = _Field(ge=0, le=10_000_000)
    scheme_foc_qty: float = _Field(default=0.0, ge=0, le=10_000_000)


@app.post("/api/evaluate-scheme")
def evaluate_scheme(req: _SchemeReq, _: User = _Depends(require_permission("write:scheme_check"))):
    """R6, policy 4.5: test a proposed scheme order against the stockist's normal flow. Pure code, no model call. BLOCK SCHEME is a
    recommendation resting on a proxy (no secondary data), which the RSM confirms; the National Sales Manager approves schemes."""
    import time as _time
    from agent import analysis

    _t0 = _time.perf_counter()
    g = analysis.scheme_gate(req.stockist_code, req.sku_code, req.proposed_order_qty, req.scheme_foc_qty)
    verdict_keys = ("found", "decision", "eligible", "reasons", "clause", "owner", "basis")
    return {
        "latency_ms": round((_time.perf_counter() - _t0) * 1000, 1), "tools_called": ["analysis.scheme_gate"], "model_calls": 0,
        "verdict": {k: g[k] for k in verdict_keys if k in g} if g.get("found") else g,
        "evidence": {k: v for k, v in g.items() if k not in verdict_keys},
    }


# ── Model question endpoint: authenticated, rate limited, scoped by role in the router ──────────
class _AskBody(_BM):
    question: str = _Field(min_length=3, max_length=1000)


@app.post("/api/ask")
def ask_agent(body: _AskBody, _: User = _Depends(require_permission("ask:ai")), __: None = _Depends(limit(10, 60, "ask"))):
    """Run a question through the LangGraph agent."""
    import time as _time
    try:
        t0 = _time.perf_counter()
        from agent.graph import run_question
        result = run_question(body.question)
        elapsed_ms = round((_time.perf_counter() - t0) * 1000, 1)
        import re as _re
        _scrub = [_re.compile(r"[A-Za-z]:\\[^\s\"']+"), _re.compile(r"(?i)data/[a-z_]+\.csv"), _re.compile(r"(?i)db/sankalp\.db"),
                  _re.compile(r"(?i)agent/[a-z_]+\.py"), _re.compile(r"sqlite:///[^\s]+")]
        ans = result.get("answer", "")
        for p in _scrub:
            ans = p.sub("[data]", ans)
        ev = []
        for e in result.get("evidence", []):
            txt = str(e.get("content", ""))
            for p in _scrub:
                txt = p.sub("[data]", txt)
            ev.append({"tool": e.get("tool", ""), "content": txt[:300]})
        return {"answer": ans, "evidence": ev, "model_calls": result.get("model_calls", 0), "latency_ms": elapsed_ms,
                "flags": result.get("flags", []), "blocked": result.get("blocked", False), "usage": result.get("usage")}
    except ValueError:
        return JSONResponse({"error": "AI service unavailable"}, status_code=503)
    except Exception as exc:
        log.warning("Agent error: %s", exc)
        return JSONResponse({"error": "Request failed"}, status_code=500)


# ── Structured tool endpoints: authenticated, role-checked ─────────────────────
@app.get("/api/at-risk-stock")
def at_risk(cnf_code: str = Q(default="", max_length=8), days: int = Q(default=90, ge=1, le=365), _: User = _Depends(require_permission("read:at_risk_all"))):
    return t.get_at_risk_stock.invoke({"cnf_code": cnf_code, "days_threshold": days})

@app.get("/api/fill-rate")
def fill_rate(cnf_code: str = Q(default="", max_length=8), _: User = _Depends(require_permission("read:fill_rate"))):
    return t.get_fill_rate.invoke({"cnf_code": cnf_code})

@app.get("/api/quarter-spike")
def quarter_spike(sku_code: str = Q(default="", max_length=10), cnf_code: str = Q(default="", max_length=8), _: User = _Depends(require_permission("read:spike"))):
    return t.detect_quarter_spike.invoke({"sku_code": sku_code, "cnf_code": cnf_code})

@app.get("/api/stockist/{stockist_code}")
def stockist(stockist_code: str, _: User = _Depends(require_permission("read:stockist_any"))):
    return t.get_stockist_summary.invoke({"stockist_code": stockist_code[:12]})

@app.get("/api/stock-cover")
def stock_cover(cnf_code: str = Q(default="", max_length=8), _: User = _Depends(require_permission("read:at_risk_all"))):
    return t.get_stock_cover.invoke({"cnf_code": cnf_code})

@app.get("/api/dispatch-quality")
def dispatch_quality(cnf_code: str = Q(default="", max_length=8), _: User = _Depends(require_permission("read:at_risk_all"))):
    return t.get_dispatch_quality.invoke({"cnf_code": cnf_code})

@app.get("/api/scheme-cap")
def scheme_cap(_: User = _Depends(require_permission("read:spike"))):
    return t.get_scheme_cap.invoke({})


# ── Static frontend ───────────────────────────────────────────────────────────
# The exported Next.js site lives in public/. On Vercel the CDN serves it; elsewhere the API serves it.
if not os.getenv("VERCEL") and (ROOT / "public").is_dir():
    from fastapi.staticfiles import StaticFiles
    app.mount("/", StaticFiles(directory=ROOT / "public", html=True), name="public")
