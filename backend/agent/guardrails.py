"""
Agent guardrails — all checks are pure Python, no LLM call.

Guardrail layers
────────────────
INPUT  gate  : block malicious / off-topic queries before the LLM sees them
OUTPUT gate  : scrub internal references, hallucinated numbers, excessive length
TOOL   gate  : cap loop count, block unknown tool calls, validate tool args
COST   gate  : enforce token budget per session
AUDIT  trail : every guardrail decision is returned as metadata
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional


# ── Constants ─────────────────────────────────────────────────────────────────

MAX_QUESTION_LEN  = 800     # chars
MAX_ANSWER_LEN    = 4000    # chars — truncate before sending to client
MAX_TOOL_TRIPS    = 6       # hard cap on model↔tool loops
MAX_EVIDENCE_ROWS = 10      # cap evidence items returned to client

# Prompt injection markers
_INJECTION_PATTERNS = [
    re.compile(r"ignore (previous|above|prior|all)", re.I),
    re.compile(r"you are now", re.I),
    re.compile(r"system prompt", re.I),
    re.compile(r"<\s*system\s*>", re.I),
    re.compile(r"forget (your|all|previous)", re.I),
    re.compile(r"act as (a |an )?(different|new|evil|hacker)", re.I),
    re.compile(r"jailbreak", re.I),
    re.compile(r"DAN mode", re.I),
]

# Off-domain topics — this is a pharma supply chain tool, nothing else
_OFF_DOMAIN_PATTERNS = [
    re.compile(r"\b(recipe|weather|sport|stock (market|price)|crypto|bitcoin|password|hack|exploit)\b", re.I),
    re.compile(r"\b(write (?:me )?(?:code|a script|a program|python)|generate (image|picture|video))\b", re.I),
    re.compile(r"\b(personal (data|information) of|home address|phone number)\b", re.I),
    re.compile(r"\b(scrape (?:this|a) (?:website|site|url))\b", re.I),
]

# Patterns that must never appear in the output sent to the client
_OUTPUT_SCRUB = [
    re.compile(r"[A-Za-z]:\\[^\s\"',<>]{6,}"),          # Windows absolute path
    re.compile(r"/(?:home|usr|var|data|tmp)/[^\s\"']{4,}"),  # Unix path
    re.compile(r"(?i)\bdata[/\\][a-z_]+\.csv\b"),        # relative CSV ref
    re.compile(r"(?i)\bdb[/\\]sankalp\.db\b"),           # DB filename
    re.compile(r"(?i)\bagent[/\\][a-z_]+\.py\b"),        # source file
    re.compile(r"sqlite:///[^\s]+"),                     # connection string
    re.compile(r"\$2[ab]\$\d{2}\$[A-Za-z0-9./]{40,}"),  # bcrypt hash (any valid length)
    re.compile(r"(?i)secret[_\s]?key\s*[:=]\s*\S+"),    # secret key
    re.compile(r"(?i)api[_\s]?key\s*[:=]\s*\S+"),       # api key
]

# Hallucination risk: LLM-written numbers not preceded by a tool citation
# (we can't fix hallucination in pure Python, but we can flag suspicious patterns)
_HALLUCINATION_RISK = re.compile(
    r"(?<!\(source)(?<!\bfound\b)"       # not already cited
    r"\b(?:INR|Rs\.?|₹)\s*[\d,]+",      # bare INR amount
)


@dataclass
class GuardrailResult:
    allowed:  bool
    reason:   Optional[str] = None
    modified: Optional[str] = None      # sanitised version if content was changed
    flags:    list[str]     = field(default_factory=list)


# ── Input guardrails ──────────────────────────────────────────────────────────

def check_input(question: str) -> GuardrailResult:
    """
    Gate 1 — runs before the question reaches the LLM.
    Returns allowed=False + reason if the question should be blocked.
    """
    if not question or not question.strip():
        return GuardrailResult(allowed=False, reason="Empty question")

    q = question.strip()

    if len(q) > MAX_QUESTION_LEN:
        return GuardrailResult(
            allowed=False,
            reason=f"Question exceeds {MAX_QUESTION_LEN} character limit",
        )

    # Prompt injection
    for pat in _INJECTION_PATTERNS:
        if pat.search(q):
            return GuardrailResult(
                allowed=False,
                reason="Question contains disallowed instruction pattern",
                flags=["prompt_injection"],
            )

    # Off-domain
    for pat in _OFF_DOMAIN_PATTERNS:
        if pat.search(q):
            return GuardrailResult(
                allowed=False,
                reason="Question is outside the scope of this system (pharma supply chain only)",
                flags=["off_domain"],
            )

    return GuardrailResult(allowed=True)


# ── Output guardrails ─────────────────────────────────────────────────────────

def sanitise_output(answer: str, evidence: list[dict]) -> tuple[str, list[dict], list[str]]:
    """
    Gate 2 — runs on the LLM answer before it reaches the client.
    Returns (clean_answer, clean_evidence, flags_fired).
    """
    flags: list[str] = []

    # Scrub internal references
    clean = answer
    for pat in _OUTPUT_SCRUB:
        if pat.search(clean):
            flags.append("internal_ref_scrubbed")
            clean = pat.sub("[data]", clean)

    # Truncate overly long answers
    if len(clean) > MAX_ANSWER_LEN:
        clean = clean[:MAX_ANSWER_LEN] + "\n\n[Response truncated for length]"
        flags.append("output_truncated")

    # Flag if bare INR amounts appear without source citation
    if _HALLUCINATION_RISK.search(clean) and "data]" not in clean:
        # Don't block — but add a flag so the caller can add a caveat
        flags.append("unverified_number_risk")

    # Cap and scrub evidence
    clean_ev: list[dict] = []
    for ev in evidence[:MAX_EVIDENCE_ROWS]:
        tool_name = ev.get("tool", "unknown")
        raw       = str(ev.get("content", ""))
        # Scrub paths from evidence summaries
        for pat in _OUTPUT_SCRUB:
            raw = pat.sub("[data]", raw)
        clean_ev.append({"tool": tool_name, "summary": raw[:300]})

    return clean, clean_ev, flags


# ── Tool guardrails ───────────────────────────────────────────────────────────

ALLOWED_TOOLS = {
    "lookup_batch",
    "validate_claim",
    "get_at_risk_stock",
    "check_scheme_eligibility",
    "detect_quarter_spike",
    "get_fill_rate",
    "get_stockist_summary",
    "get_stock_cover",
    "get_dispatch_quality",
    "get_scheme_cap",
    "get_recovery_summary",
}


def check_tool_call(tool_name: str, args: dict) -> GuardrailResult:
    """
    Gate 3 — runs before each individual tool is executed.
    """
    if tool_name not in ALLOWED_TOOLS:
        return GuardrailResult(
            allowed=False,
            reason=f"Tool '{tool_name}' is not in the allowed tool registry",
            flags=["unknown_tool"],
        )

    # Validate argument types / lengths to prevent injection via tool args
    for k, v in args.items():
        if isinstance(v, str) and len(v) > 500:
            return GuardrailResult(
                allowed=False,
                reason=f"Tool argument '{k}' exceeds allowed length",
                flags=["arg_too_long"],
            )
        if isinstance(v, str):
            for pat in _INJECTION_PATTERNS:
                if pat.search(v):
                    return GuardrailResult(
                        allowed=False,
                        reason=f"Tool argument '{k}' contains injection pattern",
                        flags=["arg_injection"],
                    )

    return GuardrailResult(allowed=True)


# ── Trip budget ────────────────────────────────────────────────────────────────

def check_trip_budget(trips: int) -> GuardrailResult:
    if trips >= MAX_TOOL_TRIPS:
        return GuardrailResult(
            allowed=False,
            reason=f"Tool loop limit reached ({MAX_TOOL_TRIPS} trips)",
            flags=["trip_limit"],
        )
    return GuardrailResult(allowed=True)
