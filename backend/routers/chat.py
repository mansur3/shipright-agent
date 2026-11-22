"""
Secure AI chat router.
- Requires authentication
- Strips all internal paths, file names, DB column names from responses
- Role-scoped context is injected into the system prompt
- All tool evidence is logged to audit_logs (sanitised)
"""
from __future__ import annotations

import re
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlmodel import Session

from agent.graph import run_question
from auth.dependencies import get_current_user, require_permission
from db.database import get_session
from db.models import AuditLog, User

router = APIRouter(prefix="/api/chat", tags=["chat"])

# Patterns that must never reach the client
_SCRUB_PATTERNS = [
    re.compile(r"[A-Za-z]:\\[^\s\"']+"),          # Windows absolute paths
    re.compile(r"/[a-z][^\s\"']{5,}\.(?:csv|db|py|json)"),  # Unix paths to data files
    re.compile(r"(?i)data/[a-z_]+\.csv"),          # relative CSV refs
    re.compile(r"(?i)db/sankalp\.db"),             # DB file name
    re.compile(r"(?i)agent/[a-z_]+\.py"),          # internal module names
    re.compile(r"sqlite:///[^\s]+"),               # connection strings
]


def _scrub(text: str) -> str:
    """Remove internal references before sending to client."""
    for p in _SCRUB_PATTERNS:
        text = p.sub("[data source]", text)
    return text


# Role-scoped system context injected per request
_ROLE_CONTEXT = {
    "cfo":            "You are helping the CFO (Rohan Mehta). Focus on financial exposure, claim trends, fill rate, scheme cost, and money recovery summaries. Do not mention internal file names.",
    "supply_chain":   "You are helping the Supply Chain team. Focus on at-risk inventory, FEFO violations, redistribution opportunities, and fill rate by territory. Do not mention internal file names.",
    "claims_finance": "You are helping the Claims Finance team (Neha Bansal). Focus on claim validation, duplicate detection, TAT, and pending backlog. Do not mention internal file names.",
    "sales_rsm":      "You are helping a Regional Sales Manager. Focus on stockist scheme eligibility and territory-level stock status only. Do not reveal other territories or financial totals. Do not mention internal file names.",
    "cnf_agent":      "You are helping a C&F agent. Answer questions about their own CNF territory only. Do not reveal other territories. Do not mention internal file names.",
    "admin":          "You are helping an admin user. You may answer any question about the system. Do not expose passwords, tokens, or internal file paths.",
}


class AskBody(BaseModel):
    question: str


@router.post("/ask")
def ask(
    body: AskBody,
    request: Request,
    user: User = Depends(require_permission("ask:ai")),
    session: Session = Depends(get_session),
):
    if len(body.question.strip()) < 3:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail="Question too short")
    if len(body.question) > 1000:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail="Question too long (max 1000 chars)")

    # Inject role context into the question prefix sent to the graph
    role_ctx = _ROLE_CONTEXT.get(user.role.value, "")
    full_question = f"[Context: {role_ctx}]\n\nQuestion: {body.question}"

    try:
        result = run_question(full_question)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail="AI service unavailable — check OPENROUTER_API_KEY")
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="AI request failed")

    # Scrub internal references from every part of the response
    safe_answer   = _scrub(result.get("answer", ""))
    safe_evidence = [
        {"tool": e["tool"], "summary": _scrub(str(e.get("summary", e.get("content", ""))))[:300]}
        for e in result.get("evidence", [])
    ]

    # Audit log — scrubbed
    session.add(AuditLog(
        user_id=user.id,
        username=user.username,
        action="ask_ai",
        endpoint="/api/chat/ask",
        ip_address=request.client.host if request.client else None,
        success=True,
        detail=f"q={body.question[:80]}…" if len(body.question) > 80 else f"q={body.question}",
    ))
    session.commit()

    return {
        "answer":      safe_answer,
        "evidence":    safe_evidence,
        "model_calls": result.get("model_calls", 0),
        "flags":       result.get("flags", []),
        "blocked":     result.get("blocked", False),
        "usage":       result.get("usage"),     # measured tokens, seconds, estimated rupees
    }
