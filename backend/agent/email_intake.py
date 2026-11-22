"""
Claims mailbox intake. The mailbox is untrusted input (doc 1, section 5.7): anything a sender writes is data, never an instruction.

A formula reads the fields (batch, quantity, invoice) and the one claim checker decides. No model is involved, so a message that says
"pre-approved, skip checks" cannot change a verdict: those lines are removed before reading and the verdict is computed from the
structured fields only. Anything unclear (no batch, a unit in boxes, a batch typo, an unknown sender) goes to a person with the reason;
nothing is guessed. A model could read the messiest messages, but it would have to return the same fields and pass the same checks.
"""
from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Optional

import config as P
from agent.claim_checks import ClaimInput, PERSON, evaluate
from agent.clean import code, get_clean, parse_date

_BATCH = re.compile(r"\b([A-Z][0-9O]{7})\b")
_INVOICE = re.compile(r"\bINV[/-][A-Z]\d{2}[/-]\d{4}[/-]\d{6}\b", re.I)
_QTY_UNIT = re.compile(r"(\d[\d,]*)\s*(strips?|packs?|boxes|box|cartons?|bottles?|tubes?)\b", re.I)
_QTY_WORD = re.compile(r"\bqty[:\s]*(\d[\d,]*)", re.I)
_CLAIMNO = re.compile(r"\bCLM[- ]?\d{4}[- ]?\d{5}\b", re.I)
_INJECTION = re.compile(r"(system note|pre-?approved|approve (the )?full|skip (all )?(the )?checks|ignore (all |the )?(previous|above|prior)|for the ai|as an ai assistant|override)", re.I)
_RETURN_WORDS = re.compile(r"\b(expiry|expired|near expiry|take back|return|credit note|wapas)\b", re.I)
_OTHER_OWNERS = (
    (re.compile(r"\bMRP\b", re.I), "Regulatory Affairs mailbox (price and labelling queries)"),
    (re.compile(r"\bscheme\b", re.I), "Sales Operations (scheme circulars)"),
    (re.compile(r"transit|delay|damage|transport", re.I), "Regional Distribution Manager (transport and C&F service)"),
)


def _norm_invoice(s: str) -> str:
    s = s.upper().replace("-", "/")
    return s


def _status_lookup(claim_no: str) -> dict:
    C = get_clean()
    n = re.sub(r"[ ]", "-", claim_no.upper())
    n = re.sub(r"^CLM-?(\d{4})-?(\d{5})$", r"CLM-\1-\2", n)
    for c in C.claims:
        if c["claim_no"] == n:
            return {"found": True, "claim_no": n, "status": c["status"], "claim_date": c["cdate"].isoformat() if c["cdate"] else None,
                    "credit_note_date": c["cn_date"].isoformat() if c["cn_date"] else None,
                    "source": f"expiry_claims.csv line {c['_line']}"}
    return {"found": False, "claim_no": n, "decision": PERSON,
            "reason": "no such claim number in the register: ask the sender to confirm the number, do not assume it was lost"}


def _qty(line: str) -> tuple[Optional[float], list[str]]:
    flags: list[str] = []
    m = _QTY_UNIT.search(line)
    if m:
        unit = m.group(2).lower()
        if unit.startswith(("box", "carton")):
            flags.append("unit_not_packs")
        n = float(m.group(1).replace(",", ""))
        if re.search(r"\(\s*\d+\s*more", line, re.I) or "more found" in line.lower():
            flags.append("quantity_qualified_in_text")
        return n, flags
    m = _QTY_WORD.search(line)
    if m:
        return float(m.group(1).replace(",", "")), flags
    if "|" in line:
        cells = [c.strip() for c in line.split("|")]
        for c in cells:
            if re.fullmatch(r"\d{1,6}", c):
                return float(c), flags
    return None, flags


def _claim_type(received: date, expiry: date) -> str:
    return "Expired" if received > expiry else "Near expiry"


def triage_email(email_id: str, received: str, sender_stockist: str, subject: str, body: str) -> dict:
    """Read one mailbox message into structured claim lines, each checked by the one claim checker. Returns a plain dict."""
    C = get_clean()
    stk = code(sender_stockist)
    rec = parse_date(received)
    out: dict = {"email_id": email_id, "received": rec.isoformat() if rec else None, "stockist": stk or None, "flags": [], "lines": []}

    kept: list[str] = []
    for ln in body.splitlines():
        if _INJECTION.search(ln):
            out["flags"].append("instruction_in_message_ignored")
            continue
        kept.append(ln)
    text = "\n".join(kept)
    batch_lines = [ln for ln in kept if _BATCH.search(ln)]
    claim_nos = _CLAIMNO.findall(subject + "\n" + text)

    if not batch_lines and claim_nos:
        out["intent"] = "status_request"
        out["statuses"] = [_status_lookup(c) for c in claim_nos]
        out["decision"] = PERSON if any(not s["found"] for s in out["statuses"]) else "REPLY WITH STATUS"
        return out
    if not batch_lines:
        if _RETURN_WORDS.search(subject + "\n" + text):
            out["intent"] = "claim_incomplete"
            out["decision"] = PERSON
            out["reason"] = "the message asks for a return but gives no batch number: a claim needs SKU, batch, expiry, quantity and the original invoice (CO-POL-014 5.3)"
            out["clause"] = "CO-POL-014 5.3 (p3)"
            return out
        out["intent"] = "not_a_claim"
        owner = next((o for pat, o in _OTHER_OWNERS if pat.search(subject + "\n" + text)), "Commercial Operations shared mailbox")
        out["decision"] = "ROUTE"
        out["route_to"] = owner
        return out

    out["intent"] = "claim"
    seen: set = set()
    for ln in batch_lines:
        raw_batch = _BATCH.search(ln).group(1)
        batch = raw_batch
        line_flags: list[str] = []
        if batch not in C.batches and "O" in batch[1:]:
            fixed = batch[0] + batch[1:].replace("O", "0")
            if fixed in C.batches:
                line_flags.append("batch_typo_suggestion")
                out["lines"].append({"line": ln.strip()[:200], "batch_as_written": raw_batch, "suggested_batch": fixed, "decision": PERSON, "tier": "INVALID",
                                     "rule_ids": ["R_BATCH_TYPO"], "reason": f"batch '{raw_batch}' is not in the master; '{fixed}' is, with the letter O read as zero. Confirm with the sender before checking",
                                     "flags": line_flags})
                continue
        qty, qflags = _qty(ln)
        inv_m = _INVOICE.search(ln)
        inv = _norm_invoice(inv_m.group(0)) if inv_m else ""
        key = (batch, qty)
        if key in seen:
            out["lines"].append({"line": ln.strip()[:200], "batch": batch, "qty": qty, "decision": PERSON, "tier": "INVALID", "rule_ids": ["R_LINE_REPEATED"],
                                 "reason": "the same batch and quantity appear twice in one message", "flags": ["line_repeated_in_message"]})
            continue
        seen.add(key)
        if not stk:
            out["lines"].append({"line": ln.strip()[:200], "batch": batch, "qty": qty, "decision": PERSON, "tier": "INVALID", "rule_ids": ["R_SENDER"],
                                 "reason": "the sender is not matched to a stockist (personal address or unknown sender); the claimant must be confirmed first", "flags": ["sender_not_matched"]})
            continue
        if qty is None or qflags:
            why = "no quantity found in the line" if qty is None else "quantity is given in boxes or qualified in the text, so the pack count is unclear"
            out["lines"].append({"line": ln.strip()[:200], "batch": batch, "qty": qty, "decision": PERSON, "tier": "INVALID", "rule_ids": ["R_QUANTITY"],
                                 "reason": why, "flags": qflags or ["no_quantity"]})
            continue
        b = C.batches.get(batch)
        ctype = _claim_type(rec, b["exp"]) if b and rec else "Near expiry"
        v = evaluate(ClaimInput(stockist=stk, batch=batch, qty=qty, claim_date=rec, claim_type=ctype, invoice_ref=inv))
        d = v.as_dict()
        d.update({"line": ln.strip()[:200], "batch": batch, "qty": qty, "invoice_ref": inv or None, "claim_type_derived": ctype})
        out["lines"].append(d)

    decisions = [l["decision"] for l in out["lines"]]
    out["decision"] = "REJECT" if "REJECT" in decisions else PERSON if PERSON in decisions else "APPROVE"
    out["note"] = "Recommendations only. The message text never changes a verdict; only the structured fields do."
    return out


def triage_register_email(row: dict) -> dict:
    return triage_email(row["email_id"], row["received_date"], row["stockist_code_by_mailbox_rule"], row["subject"], row["body"])
