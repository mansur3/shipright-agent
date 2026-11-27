"""
Claims AI Agent — LangGraph workflow for claim creation + status checking.

Two parallel workflows share a single entry point:

  START → classify_intent
    │
    ├─ create_claim ──────────────────────────────────────────────────────┐
    │    │                                                                │
    │    ▼                                                                │
    │  gather_info (parse message, extract fields)                        │
    │    │                                                                │
    │    ├─ missing fields → ask_user → END (wait for next turn)         │
    │    │                                                                │
    │    ▼ all fields present                                             │
    │  validate_guard (Pydantic + guardrail check)                        │
    │    │                                                                │
    │    ├─ validation failed → ask_user (error msg) → END               │
    │    │                                                                │
    │    ▼ valid                                                          │
    │  validate_against_data (lookup batch, qty check, duplicate check)  │
    │    │                                                                │
    │    ▼                                                                │
    │  compute_risk (apply ML signals)                                    │
    │    │                                                                │
    │    ▼                                                                │
    │  store_claim (persist to SQLite)                                    │
    │    │                                                                │
    │    ▼                                                                │
    │  respond (return claim_no + summary) → END                          │
    │                                                                     │
    ├─ check_status ──────────────────────────────────────────────────────┐
    │    │                                                                │
    │    ▼                                                                │
    │  lookup_user_claims (query DB for this user's claims)               │
    │    │                                                                │
    │    ▼                                                                │
    │  format_status → respond → END                                       │
    │                                                                     │
    └─ recovery_check ───────────────────────────────────────────────────┐
         │                                                                │
         ▼                                                                │
       compute_recovery (query batch run + user claims)                  │
         │                                                                │
         ▼                                                                │
       respond_benchmark → END                                            │
                                                                          │

The LLM is used ONLY for intent classification and natural-language response
generation. All data operations (validation, storage, lookup) are pure Python.

State carries the accumulated claim fields across turns so the agent can
ask for missing information one field at a time.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Annotated, Optional, TypedDict

from langchain_core.messages import (
    AIMessage,
    AnyMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from pydantic import ValidationError
from sqlmodel import Session, desc, select

from agent.claim_schemas import (
    ClaimCreate,
    ClaimStatusEnum,
    ClaimTypeEnum,
    IntentEnum,
)
from agent.guardrails import check_input
from agent.llm import get_llm
from db.database import engine
from db.models import (
    BatchAnalysisRun,
    ChatMessage,
    ChatSession,
    ClaimFinding,
    UserClaim,
)

log = logging.getLogger(__name__)

NL = chr(10)

MAX_TRIPS = 12

# ── Required fields for claim creation, in order of asking ────────────────────
CLAIM_FIELDS = [
    ("stockist_code", "stockist code", "e.g. STK0054"),
    ("batch_no",      "batch number",  "e.g. K2310267"),
    ("sku_code",      "SKU code",      "e.g. PFL1102"),
    ("qty_claimed",   "quantity",      "number of packs, e.g. 50"),
    ("claim_date",    "claim date",    "dd-mm-yyyy format"),
    ("claim_type",    "claim type",    "Near expiry / Expired / Breakage in transit / Short supply"),
]


# ── State ─────────────────────────────────────────────────────────────────────

class ClaimsState(TypedDict):
    messages:        Annotated[list[AnyMessage], add_messages]
    intent:          str
    claim_data:      dict
    missing_fields:  list[str]
    username:        str
    session_id:      str
    claim_no:        Optional[str]
    error:           Optional[str]
    trip_count:      int
    status_result:   Optional[dict]
    recovery_result: Optional[dict]


# ── Node 1: classify_intent ──────────────────────────────────────────────────

_INTENT_SYSTEM = """You classify user intent for a claims assistant. \
Respond with ONLY one word: create_claim, check_status, recovery_check, or general.
- create_claim: user wants to file a new expiry/breakage/short-supply claim
- check_status: user wants to see the status of their submitted claims
- recovery_check: user (typically CFO) wants to see money recovered / recoverable
- general: anything else
"""


def classify_intent(state: ClaimsState) -> dict:
    """Use LLM to classify what the user wants to do."""
    last = state["messages"][-1].content if state["messages"] else ""

    # Input guardrail
    guard = check_input(str(last))
    if not guard.allowed:
        return {
            "intent": "general",
            "error": guard.reason,
        }

    # Quick keyword check first (cheaper than LLM)
    q = str(last).lower()
    # In the middle of filing a claim, the next message continues it unless it clearly asks for something else
    if state.get("intent") == "create_claim" and not any(w in q for w in ["status", "track", "recover", "benchmark", "how much", "cancel"]):
        return {"intent": "create_claim"}
    if any(w in q for w in ["create", "file", "submit", "new claim", "log a claim"]):
        return {"intent": "create_claim"}
    if any(w in q for w in ["status", "track", "my claim", "where is", "check my"]):
        return {"intent": "check_status"}
    if any(w in q for w in ["recover", "benchmark", "how much", "money", "savings"]):
        return {"intent": "recovery_check"}

    # Fallback to LLM classification
    try:
        llm = get_llm()
        reply = llm.invoke([
            SystemMessage(_INTENT_SYSTEM),
            HumanMessage(str(last)[:500]),
        ])
        intent_str = reply.content.strip().lower().replace(" ", "").replace("-", "_")
        if intent_str in ["create_claim", "check_status", "recovery_check"]:
            return {"intent": intent_str}
    except Exception:
        pass

    return {"intent": "general"}


def route_intent(state: ClaimsState) -> str:
    """Route to the appropriate workflow based on intent."""
    if state.get("error"):
        return "respond_error"
    intent = state.get("intent", "general")
    if intent == "create_claim":
        return "gather_info"
    elif intent == "check_status":
        return "lookup_claims"
    elif intent == "recovery_check":
        return "compute_recovery"
    return "respond_general"


# ── Node 2: gather_info (extract claim fields from user message) ─────────────

# Regex patterns to extract fields from free text
_PATTERNS = {
    "stockist_code": re.compile(r"\b(STK\d{3,4})\b", re.I),
    "batch_no":      re.compile(r"\b([A-Z]\d{7})\b", re.I),
    "sku_code":      re.compile(r"\b(PFL\d{4})\b", re.I),
    "qty_claimed":   re.compile(r"(\d+)\s*(?:strips?|packs?|units?|qty|quantity)", re.I),
    "claim_date":    re.compile(r"(\d{1,2}-\d{1,2}-\d{4})"),
    "invoice_ref":   re.compile(r"\b(INV/[A-Z0-9/]+)\b", re.I),
}
_CLAIM_TYPE_MAP = {
    "near expir": "Near expiry",
    "expired": "Expired",
    "breakage": "Breakage in transit",
    "transit": "Breakage in transit",
    "short supply": "Short supply",
    "short": "Short supply",
}


def extract_fields(user_msg: str, data: dict) -> dict:
    """Read claim fields out of one message; fields already known are kept. Pure Python, no model."""
    data = dict(data)
    for field_name, pattern in _PATTERNS.items():
        if not data.get(field_name):
            match = pattern.search(user_msg)
            if match:
                val = match.group(1).strip()
                if field_name not in ("qty_claimed", "claim_date"):
                    val = val.upper()
                if field_name == "qty_claimed":
                    try:
                        val = float(val)
                    except ValueError:
                        continue
                data[field_name] = val
    if not data.get("claim_type"):
        for keyword, claim_type in _CLAIM_TYPE_MAP.items():
            if keyword in user_msg.lower():
                data["claim_type"] = claim_type
                break
    return data


def gather_info(state: ClaimsState) -> dict:
    """Parse the user's message for claim fields and determine what's missing."""
    user_msg = str(state["messages"][-1].content) if state["messages"] else ""
    data = extract_fields(user_msg, state.get("claim_data", {}))
    required = [f[0] for f in CLAIM_FIELDS]
    missing = [f for f in required if not data.get(f)]
    return {"claim_data": data, "missing_fields": missing}


def route_after_gather(state: ClaimsState) -> str:
    """If fields are missing, ask. If all present, validate."""
    if state.get("missing_fields"):
        return "ask_user"
    return "validate_guard"


# ── Node 3: ask_user (ask for the next missing field) ────────────────────────

def ask_user(state: ClaimsState) -> dict:
    """Ask for every missing field in one message, with an example each. The model words it later; the facts come from here."""
    missing = state.get("missing_fields", [])
    if not missing:
        return {"messages": [AIMessage(content="I have all the information needed.")]}
    info = {f[0]: (f[1], f[2]) for f in CLAIM_FIELDS}
    already = {k: v for k, v in state.get("claim_data", {}).items() if v}
    lines = ["To file your claim I still need:"]
    lines += [f"- **{info[f][0]}** ({info[f][1]})" for f in missing if f in info]
    if already:
        lines.append("So far I have: " + ", ".join(f"{info[k][0] if k in info else k} {v}" for k, v in already.items()))
    lines.append("An invoice reference (INV/...) is optional but helps. You can send everything in one message.")
    return {"messages": [AIMessage(content=NL.join(lines))], "trip_count": state.get("trip_count", 0) + 1}


# ── Node 4: validate_guard (Pydantic validation + guardrail) ──────────────────

def validate_guard(state: ClaimsState) -> dict:
    """Validate all collected fields using Pydantic ClaimCreate schema."""
    data = state.get("claim_data", {})
    try:
        claim = ClaimCreate(**data)
        return {"claim_data": claim.model_dump(), "error": None}
    except ValidationError as e:
        errors = []
        for err in e.errors():
            loc = ".".join(str(x) for x in err["loc"])
            errors.append(f"{loc}: {err['msg']}")
        return {"error": "Validation failed: " + "; ".join(errors)}
    except Exception as e:
        return {"error": f"Validation error: {str(e)[:200]}"}


def route_after_validate(state: ClaimsState) -> str:
    if state.get("error"):
        return "ask_user_error"
    return "validate_against_data"


# ── Node 5: ask_user_error (tell user about validation error) ─────────────────

def ask_user_error(state: ClaimsState) -> dict:
    """Inform user of validation errors and ask them to correct."""
    msg = AIMessage(content=f"⚠ There was an issue with your claim:\n\n{state['error']}\n\nPlease provide the correct value and I'll try again.")
    return {
        "messages": [msg],
        "error": None,  # reset so we can retry
        "claim_data": {},  # reset partial data
        "missing_fields": [f[0] for f in CLAIM_FIELDS],  # restart gathering
        "trip_count": state.get("trip_count", 0) + 1,
    }


# ── Node 6: validate_against_data (lookup batch, qty check, duplicate) ────────

def validate_against_data(state: ClaimsState) -> dict:
    """Cross-check the claim with the one claim checker (agent/claim_checks.py). No rule is implemented here."""
    from agent.claim_checks import ClaimInput, evaluate
    from agent.clean import get_clean, parse_date

    data = state.get("claim_data", {})
    v = evaluate(ClaimInput(stockist=data["stockist_code"], batch=data["batch_no"], qty=data["qty_claimed"],
                            claim_date=parse_date(data["claim_date"]), claim_type=data["claim_type"],
                            invoice_ref=data.get("invoice_ref", ""), sku=data.get("sku_code", "")))
    C = get_clean()
    batch = C.batches.get(data["batch_no"].strip().upper())
    data["risk_score"] = v.risk_score
    data["risk_flags"] = v.flags
    data["claim_value_inr"] = v.rupee_impact
    # rupees not credited if the recommendation is followed; only a REJECT recommendation counts
    data["recovery_amount_inr"] = v.rupee_impact if v.decision == "REJECT" else 0.0
    data["invoiced_qty"] = C.supply.get((data["stockist_code"].strip().upper(), data["batch_no"].strip().upper()), 0.0)
    data["recommended_action"] = f"{v.decision} (recommendation): {v.reason}"
    data["batch_valid"] = batch is not None
    data["batch_expiry"] = batch["exp"].isoformat() if batch and batch["exp"] else None
    data["verdict"] = v.as_dict()
    return {"claim_data": data}


def _parse_date(s: str) -> datetime | None:
    for fmt in ["%d-%m-%Y", "%Y-%m-%d", "%d-%b-%Y"]:
        try:
            return datetime.strptime(str(s).strip(), fmt)
        except ValueError:
            pass
    return None


# ── Node 7: store_claim (persist to SQLite) ──────────────────────────────────

def store_claim(state: ClaimsState) -> dict:
    """Save the validated claim to SQLite."""
    data = state.get("claim_data", {})
    username = state.get("username", "unknown")

    # Generate claim number
    now = datetime.now(timezone.utc)
    claim_no = f"CLM-USER-{now.strftime('%Y%m%d%H%M%S')}-{username[:3].upper()}"

    with Session(engine) as session:
        claim = UserClaim(
            claim_no=claim_no,
            submitted_by=username,
            stockist_code=data.get("stockist_code", ""),
            batch_no=data.get("batch_no", ""),
            sku_code=data.get("sku_code", ""),
            qty_claimed=data.get("qty_claimed", 0.0),
            claim_date=data.get("claim_date", ""),
            claim_type=data.get("claim_type", ""),
            invoice_ref=data.get("invoice_ref", ""),
            status="Submitted",
            risk_score=data.get("risk_score", 0),
            risk_flags=",".join(data.get("risk_flags", [])),
            claim_value_inr=data.get("claim_value_inr", 0.0),
            recovery_amount_inr=data.get("recovery_amount_inr", 0.0),
        )
        session.add(claim)
        session.commit()
        session.refresh(claim)

    return {"claim_no": claim_no}


# ── Node 8: respond (return claim summary to user) ────────────────────────────

def respond(state: ClaimsState) -> dict:
    """Generate the response summarising the created claim."""
    data = state.get("claim_data", {})
    claim_no = state.get("claim_no", "")

    risk = data.get("risk_score", 0)
    risk_label = "HIGH" if risk >= 50 else "MEDIUM" if risk >= 25 else "LOW"

    parts = [
        f"✅ Claim created successfully!",
        f"",
        f"**Claim Number:** {claim_no}",
        f"**Status:** Submitted",
        f"**Risk Score:** {risk}/100 ({risk_label})",
        f"**Claim Value:** ₹{data.get('claim_value_inr', 0):,.0f}",
        f"**Potential Recovery:** ₹{data.get('recovery_amount_inr', 0):,.0f}",
        f"**Recommended Action:** {data.get('recommended_action', 'N/A')}",
    ]

    if data.get("risk_flags"):
        parts.append(f"**Flags:** {', '.join(data['risk_flags'])}")

    if data.get("batch_expiry"):
        parts.append(f"**Batch Expiry:** {data['batch_expiry']}")

    parts.append(f"\nYou can track this claim under **My Claims** in the sidebar.")

    msg = AIMessage(content="\n".join(parts))
    return {"messages": [msg]}


# ── Node 9: lookup_claims (check_status workflow) ─────────────────────────────

def lookup_claims(state: ClaimsState) -> dict:
    """Query SQLite for all claims submitted by this user."""
    username = state.get("username", "unknown")

    with Session(engine) as session:
        claims = session.exec(
            select(UserClaim)
            .where(UserClaim.submitted_by == username)
            .order_by(desc(UserClaim.created_at))
        ).all()

    claim_items = []
    total_value = 0.0
    for c in claims:
        total_value += c.claim_value_inr
        claim_items.append({
            "claim_no": c.claim_no,
            "status": c.status,
            "risk_score": c.risk_score,
            "claim_value_inr": c.claim_value_inr,
            "recovery_amount_inr": c.recovery_amount_inr,
            "claim_type": c.claim_type,
            "batch_no": c.batch_no,
            "stockist_code": c.stockist_code,
            "created_at": c.created_at.isoformat() if c.created_at else "",
        })

    return {"status_result": {"claims": claim_items, "total": len(claims), "total_value_inr": total_value}}


# ── Node 10: format_status ────────────────────────────────────────────────────

def format_status(state: ClaimsState) -> dict:
    """Format the user's claims as a readable response."""
    result = state.get("status_result", {})
    claims = result.get("claims", [])

    if not claims:
        msg = AIMessage(content="You have no claims on file yet. Would you like to create one? Just say 'I want to file a claim'.")
        return {"messages": [msg]}

    parts = [f"📋 **Your Claims ({len(claims)} total, ₹{result.get('total_value_inr', 0):,.0f} total value)**\n"]
    for c in claims[:20]:
        parts.append(
            f"• **{c['claim_no']}** — {c['status']} | Risk: {c['risk_score']} | "
            f"₹{c['claim_value_inr']:,.0f} | Recovery: ₹{c['recovery_amount_inr']:,.0f} | "
            f"{c['claim_type']} | Batch: {c['batch_no']} | Stockist: {c['stockist_code']}"
        )
    if len(claims) > 20:
        parts.append(f"\n...and {len(claims) - 20} more (see My Claims tab for full list)")

    msg = AIMessage(content="\n".join(parts))
    return {"messages": [msg]}


# ── Node 11: compute_recovery (recovery_check workflow) ───────────────────────

def compute_recovery(state: ClaimsState) -> dict:
    """Compute the recovery benchmark from batch analysis + user claims."""
    with Session(engine) as session:
        # Latest batch run
        run = session.exec(
            select(BatchAnalysisRun).order_by(desc(BatchAnalysisRun.run_at))
        ).first()

        # User-submitted claims
        all_user_claims = session.exec(select(UserClaim)).all()
        pending = [c for c in all_user_claims if c.status in ("Submitted", "Under Review")]
        approved = [c for c in all_user_claims if c.status in ("Approved", "Credited")]

        pending_val = sum(c.claim_value_inr for c in pending)
        approved_val = sum(c.recovery_amount_inr for c in approved)

    # One source for every recovery figure: agent/recovery.py (the claim checker over the register). Kinds are kept apart.
    from agent import recovery as _rec
    r = _rec.build()
    b = r["buckets"]
    recovery = {
        "recover_inr": r["recover_inr"], "recover_claims": r["recover_claims"], "recover_per_year_inr": r["recover_per_year_inr"],
        "recover_t1_inr": b["recover_t1"]["inr"], "recover_t1_claims": b["recover_t1"]["claims"],
        "recover_t2_inr": b["recover_t2"]["inr"], "recover_t2_claims": b["recover_t2"]["claims"],
        "hold_inr": b["hold"]["inr"], "hold_claims": b["hold"]["claims"],
        "review_inr": b["review"]["inr"], "review_claims": b["review"]["claims"],
        "unverifiable_inr": b["unverifiable"]["inr"], "unverifiable_claims": b["unverifiable"]["claims"],
        "user_claims_pending": len(pending),
        "user_claims_pending_value_inr": pending_val,
        "user_claims_submitted": len(all_user_claims),
        "user_claims_approved_inr": approved_val,
    }

    return {"recovery_result": recovery}


# ── Node 12: respond_benchmark ────────────────────────────────────────────────

def respond_benchmark(state: ClaimsState) -> dict:
    """Format the recovery benchmark for the CFO."""
    r = state.get("recovery_result", {})

    lakh = lambda v: f"INR {v / 1e5:,.1f} lakh"
    parts = [
        "## Money we can claim back\n",
        f"**{lakh(r.get('recover_inr', 0))}** was credited against a clear policy rule in the last 30 months "
        f"({r.get('recover_claims', 0)} claims, about {lakh(r.get('recover_per_year_inr', 0))} a year).",
        f"- Policy text breached (strongest case): {r.get('recover_t1_claims', 0)} claims, {lakh(r.get('recover_t1_inr', 0))}",
        f"- Probable breach (repeats, out of window): {r.get('recover_t2_claims', 0)} claims, {lakh(r.get('recover_t2_inr', 0))}",
        "",
        "## Different kinds of money (not added to the above)\n",
        f"- **Hold now:** {r.get('hold_claims', 0)} pending claims fail a rule today, {lakh(r.get('hold_inr', 0))}",
        f"- **Needs a person:** {r.get('review_claims', 0)} credited claims, {lakh(r.get('review_inr', 0))}",
        f"- **Cannot be checked:** {r.get('unverifiable_claims', 0)} claims on batches older than the data, {lakh(r.get('unverifiable_inr', 0))}",
        "",
        "## Claims filed through this assistant\n",
        f"- Submitted: {r.get('user_claims_submitted', 0)}",
        f"- Pending review: {r.get('user_claims_pending', 0)} (INR {r.get('user_claims_pending_value_inr', 0):,.0f})",
        "",
        "Commercial Finance decides what to recover. Nothing moves automatically.",
    ]

    msg = AIMessage(content="\n".join(parts))
    return {"messages": [msg]}


# ── Node 13: respond_general ───────────────────────────────────────────────────

def respond_general(state: ClaimsState) -> dict:
    """Handle off-domain or unrecognized intents."""
    msg = AIMessage(content=(
        "I'm the Sankalp Claims Assistant. I can help you with:\n\n"
        "1. **Create a claim** — file a new expiry, breakage, or short-supply claim\n"
        "2. **Check status** — see the status of your submitted claims\n"
        "3. **Recovery benchmark** — see how much money has been recovered (CFO view)\n\n"
        "What would you like to do?"
    ))
    return {"messages": [msg]}


# ── Node 14: respond_error ────────────────────────────────────────────────────

def respond_error(state: ClaimsState) -> dict:
    """Handle guardrail blocks."""
    msg = AIMessage(content=f"I cannot process this request: {state.get('error', 'blocked')}. Please try a valid claim-related question.")
    return {"messages": [msg]}


# ── Build graph ───────────────────────────────────────────────────────────────

builder = StateGraph(ClaimsState)

# Add all nodes
builder.add_node("classify_intent",      classify_intent)
builder.add_node("gather_info",          gather_info)
builder.add_node("ask_user",             ask_user)
builder.add_node("validate_guard",       validate_guard)
builder.add_node("ask_user_error",      ask_user_error)
builder.add_node("validate_against_data", validate_against_data)
builder.add_node("store_claim",          store_claim)
builder.add_node("respond",              respond)
builder.add_node("lookup_claims",        lookup_claims)
builder.add_node("format_status",        format_status)
builder.add_node("compute_recovery",     compute_recovery)
builder.add_node("respond_benchmark",    respond_benchmark)
builder.add_node("respond_general",      respond_general)
builder.add_node("respond_error",        respond_error)

# Edges: START → classify_intent
builder.add_edge(START, "classify_intent")

# classify_intent → route to workflow
builder.add_conditional_edges("classify_intent", route_intent, {
    "gather_info":       "gather_info",
    "lookup_claims":     "lookup_claims",
    "compute_recovery":  "compute_recovery",
    "respond_general":   "respond_general",
    "respond_error":     "respond_error",
})

# ── Workflow A: create_claim ──────────────────────────────────────────────────
builder.add_conditional_edges("gather_info", route_after_gather, {
    "ask_user":       "ask_user",
    "validate_guard": "validate_guard",
})
builder.add_edge("ask_user", END)
builder.add_conditional_edges("validate_guard", route_after_validate, {
    "ask_user_error":         "ask_user_error",
    "validate_against_data":  "validate_against_data",
})
builder.add_edge("ask_user_error", END)
builder.add_edge("validate_against_data", "store_claim")
builder.add_edge("store_claim", "respond")
builder.add_edge("respond", END)

# ── Workflow B: check_status ──────────────────────────────────────────────────
builder.add_edge("lookup_claims", "format_status")
builder.add_edge("format_status", END)

# ── Workflow C: recovery_check ────────────────────────────────────────────────
builder.add_edge("compute_recovery", "respond_benchmark")
builder.add_edge("respond_benchmark", END)

# ── Terminal nodes ────────────────────────────────────────────────────────────
builder.add_edge("respond_general", END)
builder.add_edge("respond_error", END)

claims_graph = builder.compile()


# ── Public entry point ───────────────────────────────────────────────────────

def run_claims_agent(question: str, username: str, session_id: str) -> dict:
    """
    Run the claims agent for one user turn.
    Returns: answer, intent, claim_no (if created), status_result (if checked),
    recovery_result (if requested), error (if any).
    """
    prior_intent, draft = _load_draft(session_id)
    initial: ClaimsState = {
        "messages":        [HumanMessage(question)],
        "intent":          prior_intent,
        "claim_data":      draft,
        "missing_fields":  [],
        "username":        username,
        "session_id":      session_id,
        "claim_no":        None,
        "error":           None,
        "trip_count":      0,
        "status_result":   None,
        "recovery_result": None,
    }
    final = claims_graph.invoke(initial)

    draft_answer = final["messages"][-1].content if final["messages"] else ""
    # Code produced every fact above; the model only words it for the user, and is dropped if it changes a number.
    answer, model_used = _polish(question, draft_answer)

    # Save chat messages to DB
    done = bool(final.get("claim_no"))
    restart = done or draft_answer.startswith("⚠")   # claim filed, or a validation error cleared the draft: start the next claim fresh
    _save_chat(session_id, username, question, answer, "general" if done else final.get("intent", ""), created=restart)

    return {
        "model_worded":    model_used,
        "answer":          answer,
        "intent":          final.get("intent", "general"),
        "claim_no":        final.get("claim_no"),
        "status_result":   final.get("status_result"),
        "recovery_result": final.get("recovery_result"),
        "error":           final.get("error"),
    }


def _load_draft(session_id: str) -> tuple[str, dict]:
    """Rebuild a half-filed claim from this session's earlier messages (stateless, so it works on any server instance).
    Returns the session's last intent and the claim fields read from user messages since the last claim was created."""
    with Session(engine) as session:
        cs = session.exec(select(ChatSession).where(ChatSession.session_id == session_id)).first()
        if not cs:
            return "", {}
        rows = session.exec(select(ChatMessage).where(ChatMessage.session_id == session_id).order_by(ChatMessage.id)).all()
    draft: dict = {}
    for r in rows:
        if r.role == "ai" and r.tool_used == "claim_created":
            draft = {}
        elif r.role == "user":
            draft = extract_fields(r.content, draft)
    return cs.intent if cs.intent == "create_claim" else "", draft


_POLISH_SYSTEM = (
    "You are the Sankalp Claims Assistant for a pharma distribution company. Rewrite the DRAFT reply so it reads clearly for a busy colleague: "
    "short sentences, plain English, light markdown (bold labels, short bullet lists, a small table only if it helps). "
    "Keep every number, rupee amount, code, claim number, date and policy clause exactly as in the draft. "
    "Do not add facts, promises, advice or numbers that are not in the draft. If the draft asks for information, ask for exactly that. "
    "Stay under 180 words. Reply with the message only."
)


def _numbers(s: str) -> set[str]:
    return set(re.findall(r"\d[\d,.]*\d|\d", s))


def _polish(question: str, draft: str) -> tuple[str, bool]:
    """Ask the model to word the draft. Falls back to the draft if the model is unavailable or changes any figure."""
    if not draft.strip():
        return draft, False
    try:
        out = get_llm().invoke([SystemMessage(_POLISH_SYSTEM), HumanMessage(f"User said: {question[:400]}{NL}{NL}DRAFT:{NL}{draft}")]).content
        out = str(out).strip()
    except Exception as e:  # missing key, network, rate limit: the draft is already a correct, readable answer
        log.warning("Reply wording skipped: %s", type(e).__name__)
        return draft, False
    if not out or not _numbers(draft) <= _numbers(out):
        return draft, False
    added = _numbers(out) - _numbers(draft)
    if any(len(x) > 1 for x in added):   # a new figure (not just a list number like 1 or 2) means the model added a fact
        return draft, False
    return out, True


def _save_chat(session_id: str, username: str, question: str, answer: str, intent: str, created: bool = False):
    """Persist chat messages to SQLite for per-user history."""
    now = datetime.now(timezone.utc)
    with Session(engine) as session:
        # Create or update session
        existing = session.exec(
            select(ChatSession).where(ChatSession.session_id == session_id)
        ).first()
        if not existing:
            session.add(ChatSession(
                session_id=session_id,
                user_username=username,
                intent=intent,
                created_at=now,
                last_activity=now,
            ))
        else:
            existing.last_activity = now
            if intent:
                existing.intent = intent
            session.add(existing)

        # Save user message
        session.add(ChatMessage(
            session_id=session_id,
            role="user",
            content=question[:2000],
        ))
        # Save AI response
        session.add(ChatMessage(
            session_id=session_id,
            role="ai",
            content=answer[:2000],
            tool_used="claim_created" if created else "",
        ))
        session.commit()
