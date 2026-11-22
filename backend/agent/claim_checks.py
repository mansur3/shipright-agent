"""
The one claim checker. The batch run, the validate_claim tool, /api/audit-claim, the check-set
runner and the claims graph all call evaluate(); nothing else implements these rules.

Pure Python, no model, no I/O beyond the cleaned data. Every verdict carries the rule ids, the
policy clause with page, and the file and line of every record it relied on. The verdict is a
recommendation: a named person (Controller, Commercial Finance) decides anything that moves money.

Evidence tiers (verification/05_findings_ledger.md section 4):
  T1  policy text breached: claimed more than was supplied (5.5); filed over 90 days after expiry (5.2)
  T2  probable breach: same stockist + batch + quantity credited before; outside the claim window (5.2)
  T3  needs a person: another credited claim on the batch within supply; no invoice reference (5.4)
  T4  cannot be checked from the extracts: batch older than the batch master
  CLEAN  every check passes
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Optional

import config as P
from agent.clean import Clean, code, get_clean, norm_inv, norm_sku

OWNER = "Neha Bansal (Controller, Commercial Finance)"
EXPIRY_TYPES = ("Near expiry", "Expired")
BED_TYPES = ("Breakage in transit", "Short supply")
ALL_TYPES = EXPIRY_TYPES + BED_TYPES

APPROVE, REJECT, PERSON = "APPROVE", "REJECT", "NEEDS A PERSON"
TIER_DECISION = {"T1": REJECT, "T2": REJECT, "T3": PERSON, "T4": PERSON, "INVALID": PERSON, "CLEAN": APPROVE}
TIER_SCORE = {"T1": 95, "T2": 80, "T3": 40, "T4": 30, "INVALID": 50, "CLEAN": 0}


@dataclass
class ClaimInput:
    stockist: str
    batch: str
    qty: float
    claim_date: Optional[date]
    claim_type: str
    invoice_ref: str = ""
    sku: str = ""
    expiry_claimed: Optional[date] = None
    order: Optional[tuple] = None        # (claim_date, source line) when replaying a register row


@dataclass
class Verdict:
    decision: str
    tier: str
    rule_ids: list[str]
    reasons: list[str]
    flags: list[str] = field(default_factory=list)
    checks_passed: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    clause: str = ""
    rupee_impact: float = 0.0
    excess_packs: float = 0.0
    risk_score: int = 0
    owner: str = OWNER

    @property
    def reason(self) -> str:
        return "; ".join(self.reasons) if self.reasons else "All checks passed"

    def as_dict(self) -> dict:
        return {"decision": self.decision, "tier": self.tier, "rule_id": self.rule_ids[0] if self.rule_ids else "R_ALL_PASSED",
                "rule_ids": self.rule_ids, "reason": self.reason, "flags": self.flags, "policy_clause": self.clause,
                "owner": self.owner, "rupee_impact": round(self.rupee_impact, 2), "excess_packs": self.excess_packs,
                "risk_score": self.risk_score, "checks_passed": self.checks_passed, "evidence": self.evidence,
                "note": "Recommendation only. A named person decides anything that moves money."}


def _verdict(tier: str, rule_ids: list[str], reasons: list[str], clause: str, flags: list[str], passed: list[str],
             evidence: list[str], impact: float = 0.0, excess: float = 0.0) -> Verdict:
    return Verdict(decision=TIER_DECISION[tier], tier=tier, rule_ids=rule_ids, reasons=reasons, flags=flags,
                   checks_passed=passed, evidence=evidence, clause=clause, rupee_impact=impact,
                   excess_packs=excess, risk_score=TIER_SCORE[tier])


def window_result(claim_type: str, d: date, expiry: Optional[date], invoice_date: Optional[date]) -> tuple[Optional[bool], str]:
    """(inside_window, message). None = cannot be tested (breakage or short supply without an invoice date)."""
    if claim_type == "Near expiry":
        lo, hi = expiry - timedelta(days=P.CLAIM_WINDOW_NE_DAYS), expiry
        if lo <= d <= hi:
            return True, "inside the near-expiry window (90 days before expiry to expiry)"
        return False, (f"filed {(lo - d).days} days before the near-expiry window opens" if d < lo
                       else f"filed {(d - hi).days} days after expiry; near-expiry window closed")
    if claim_type == "Expired":
        lo, hi = expiry, expiry + timedelta(days=P.CLAIM_WINDOW_POST_EXPIRY_DAYS)
        if lo <= d <= hi:
            return True, "inside the expired window (expiry to 90 days after)"
        return False, (f"filed {(lo - d).days} days before expiry" if d < lo
                       else f"filed {(d - hi).days} days after the 90-day post-expiry window")
    if claim_type in BED_TYPES:
        if invoice_date is None:
            return None, "7-day window from the invoice cannot be tested without the invoice date"
        gap = (d - invoice_date).days
        if 0 <= gap <= P.CLAIM_WINDOW_BED_DAYS:
            return True, f"inside the {P.CLAIM_WINDOW_BED_DAYS}-day window from the invoice ({gap} days)"
        return False, f"filed {gap} days after the invoice; the window is {P.CLAIM_WINDOW_BED_DAYS} days"
    return None, "unknown claim type"


def evaluate(ci: ClaimInput, clean: Optional[Clean] = None) -> Verdict:
    C = clean or get_clean()
    stk, bat = code(ci.stockist), code(ci.batch)
    inv = norm_inv(ci.invoice_ref)
    flags: list[str] = []
    passed: list[str] = []
    evidence: list[str] = []

    # ---- input and entity validity: anything we cannot read goes to a person, never a guess
    if ci.qty is None or ci.qty <= 0:
        return _verdict("INVALID", ["R_INPUT"], ["quantity must be above zero"], "CO-POL-014 5.3 (p3)", ["bad_quantity"], passed, evidence)
    if ci.claim_date is None:
        return _verdict("INVALID", ["R_INPUT"], ["claim date missing or not readable"], "CO-POL-014 5.3 (p3)", ["bad_date"], passed, evidence)
    if ci.claim_type not in ALL_TYPES:
        return _verdict("INVALID", ["R_INPUT"], [f"unknown claim type '{ci.claim_type}'"], "CO-POL-014 5.2 (p3)", ["bad_type"], passed, evidence)
    s = C.stockists.get(stk)
    if not s:
        return _verdict("INVALID", ["R_ENTITY"], [f"stockist {stk} is not in stockist_master"], "CO-POL-014 5.3 (p3)", ["unknown_stockist"], passed, evidence)
    passed.append(f"stockist {stk} found ({s['name']})")
    evidence.append(f"stockist_master.csv line {s['_line']}")

    b = C.batches.get(bat)
    pts = C.pts(norm_sku(ci.sku) if ci.sku else (b["sku"] if b else ""))
    impact = round(ci.qty * pts, 2)
    if b is None:
        return _verdict("T4", ["R_PRE_WINDOW"],
                        [f"batch {bat} is not in batch_master, which covers batches made from Oct 2023; this claim cannot be checked from the extracts and needs the archived invoice and batch record"],
                        "CO-POL-014 5.3, 5.5 (p3)", ["batch_not_in_master", "pre_window"], passed, evidence, impact)
    if ci.sku and norm_sku(ci.sku) != b["sku"]:
        return _verdict("INVALID", ["R_SKU_MISMATCH"], [f"batch {bat} is SKU {b['sku']}, claim says {norm_sku(ci.sku)}"],
                        "CO-POL-014 5.3 (p3)", ["sku_mismatch"], passed, evidence + [f"batch_master.csv line {b['_line']}"], impact)
    passed.append(f"batch {bat} found (SKU {b['sku']}, expiry {b['exp']})")
    evidence.append(f"batch_master.csv line {b['_line']}")
    pts = C.pts(b["sku"])
    impact = round(ci.qty * pts, 2)
    expiry = b["exp"]

    # ---- supply and earlier credited claims
    supply = C.supply.get((stk, bat), 0.0)
    prior = C.credited_before(stk, bat, ci.order)
    prior_qty = sum(p["qty"] for p in prior)
    evidence.append(f"primary_sales.csv: {supply:.0f} packs (paid + free) of batch {bat} invoiced to {stk}")
    for p in prior[:5]:
        evidence.append(f"expiry_claims.csv line {p['_line']}: {p['claim_no']} credited {p['qty']:.0f} packs, INR {p['credit_eff']:.2f}")

    # ---- window (invoice date comes from the invoice reference, not from the batch)
    inv_date = C.invoice_date.get(inv) if inv else None
    inside, wmsg = window_result(ci.claim_type, ci.claim_date, expiry, inv_date)
    if inv and inv in C.invoice_line:
        evidence.append(f"primary_sales.csv line {C.invoice_line[inv]}: invoice {inv} dated {inv_date}")

    over_supply = prior_qty + ci.qty > supply
    excess = max(0.0, prior_qty + ci.qty - max(supply, prior_qty)) if over_supply else 0.0
    late = ci.claim_type in EXPIRY_TYPES and (ci.claim_date - expiry).days > P.CLAIM_WINDOW_POST_EXPIRY_DAYS
    exact_repeat = any(p["qty"] == ci.qty for p in prior)
    outside = inside is False
    partial_repeat = bool(prior)
    inv_issue = ""
    if inv:
        if inv not in C.invoice_date:
            inv_issue = f"invoice {inv} is not in primary_sales"
        elif bat not in C.invoice_batches.get(inv, set()):
            inv_issue = f"batch {bat} is not on invoice {inv}"
        elif C.invoice_stockist.get(inv) != stk:
            inv_issue = f"invoice {inv} was billed to {C.invoice_stockist.get(inv)}, not {stk}"

    if over_supply: flags.append("over_supply")
    if late: flags.append("filed_over_90_days_after_expiry")
    if exact_repeat: flags.append("exact_repeat")
    if outside: flags.append("outside_window")
    if inside is None: flags.append("window_not_testable")
    if partial_repeat: flags.append("earlier_credit_on_batch")
    if inv_issue: flags.append("invoice_mismatch")
    if not inv: flags.append("no_invoice_ref")

    # ---- tier: first match wins; order is the ledger's
    if over_supply:
        why = (f"claim of {ci.qty:.0f} packs plus {prior_qty:.0f} already credited exceeds the {supply:.0f} packs invoiced to this stockist for the batch"
               if supply else f"batch {bat} was never invoiced to {stk}")
        return _verdict("T1", ["R_OVER_SUPPLY"], [why], "CO-POL-014 5.5 (p3)", flags, passed, evidence, impact, excess)
    if late:
        return _verdict("T1", ["R_LATE_AFTER_EXPIRY"], [wmsg, "claims more than 90 days after expiry are not accepted under any circumstances"],
                        "CO-POL-014 5.2 (p3)", flags, passed, evidence, impact)
    if exact_repeat:
        first = next(p for p in prior if p["qty"] == ci.qty)
        return _verdict("T2", ["R_EXACT_REPEAT"], [f"same stockist, batch and quantity already credited in {first['claim_no']} (INR {first['credit_eff']:.2f})"],
                        "CO-POL-014 5.6 step 3 (p4)", flags, passed, evidence, impact)
    if outside:
        return _verdict("T2", ["R_WINDOW"], [wmsg], "CO-POL-014 5.2 (p3)", flags, passed, evidence, impact)
    if inside:
        passed.append(wmsg)
    pending = C.pending_for(stk, bat) if ci.order is None else []
    if pending:
        flags.append("pending_claim_exists")
        p0 = pending[0]
        return _verdict("T3", ["R_PENDING_CLAIM"],
                        [f"claim {p0['claim_no']} on the same stockist and batch is still pending ({p0['qty']:.0f} packs); crediting both would pay twice"],
                        "CO-POL-014 5.6 step 3 (p4)", flags, passed, evidence + [f"expiry_claims.csv line {p0['_line']}: {p0['claim_no']} pending"], impact)
    if partial_repeat:
        return _verdict("T3", ["R_PARTIAL_REPEAT"],
                        [f"{len(prior)} earlier credited claim(s) on this batch for {prior_qty:.0f} packs; with this claim the total stays within the {supply:.0f} packs invoiced"],
                        "CO-POL-014 5.6 step 3 (p4)", flags, passed, evidence, impact)
    if inv_issue:
        return _verdict("T3", ["R_INVOICE_CHECK"], [inv_issue], "CO-POL-014 5.3 (p3)", flags, passed, evidence, impact)
    if not inv:
        return _verdict("T3", ["R_NO_INVOICE_REF"],
                        [f"no invoice reference; {supply:.0f} packs of this batch were invoiced to the stockist, so the claim can be checked on the ledger, but 5.4 needs the Area Manager's written approval"],
                        "CO-POL-014 5.4 (p3)", flags, passed, evidence, impact)
    passed.append(f"quantity within supply ({prior_qty + ci.qty:.0f} of {supply:.0f} packs)")
    passed.append(f"invoice {inv} found and matches stockist and batch")
    return _verdict("CLEAN", [], [], "CO-POL-014 5.1 to 5.7 (pp3-4)", flags, passed, evidence, impact)


def evaluate_register_row(row: dict, clean: Optional[Clean] = None) -> Verdict:
    """Replay a cleaned register claim against the claims that came before it."""
    ci = ClaimInput(stockist=row["stk"], batch=row["batch"], qty=row["qty"], claim_date=row["cdate"], claim_type=row["type"],
                    invoice_ref=row["inv"], sku=row["sku"], expiry_claimed=row["exp_c"], order=row["order"])
    return evaluate(ci, clean)
