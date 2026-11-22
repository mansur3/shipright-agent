"""
Check set runner. The check set is 20 real records, with the right answer agreed by hand from the raw rows
(see checks/check_set.csv and verification/08_check_set_sheet.md). This runner contains no rule of its own: it calls the one
claim checker (agent/claim_checks.py) and the mailbox intake (agent/email_intake.py), then compares with the agreed answer.

    python checks/run_checks.py            # prints X/Y right, every miss, and what happens to the rest of the register
    python checks/run_checks.py --json     # machine-readable

Exit status 0 only if every record is right.
"""
from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agent.claim_checks import ClaimInput, evaluate, evaluate_register_row
from agent.clean import get_clean, parse_date
from agent.email_intake import triage_register_email


def run_one(rec: dict) -> tuple[str, str, str]:
    """(decision, tier, reason) from the checker for one check-set record."""
    C = get_clean()
    kind = rec["kind"]
    if kind == "register":
        row = next(c for c in C.claims if c["claim_no"] == rec["source"])
        v = evaluate_register_row(row, C)
        return v.decision, v.tier, v.reason
    if kind == "synthetic":
        v = evaluate(ClaimInput(stockist=rec["stockist_code"], batch=rec["batch_no"], qty=float(rec["qty_claimed"]), claim_date=parse_date(rec["claim_date"]),
                                claim_type=rec["claim_type"], invoice_ref=rec["invoice_ref"], sku=rec["sku_code"]), C)
        return v.decision, v.tier, v.reason
    if kind == "email":
        import csv as _csv
        mail = next(r for r in _csv.DictReader(open(ROOT / "data" / "claim_emails.csv", encoding="utf-8")) if r["email_id"] == rec["source"])
        t = triage_register_email(mail)
        if t["intent"] == "status_request":
            return t["decision"], "INVALID", "; ".join(s.get("reason", "found") for s in t["statuses"])
        if t["intent"] in ("claim_incomplete", "not_a_claim"):
            return t["decision"], "INVALID", t.get("reason", t.get("route_to", ""))
        worst = sorted(t["lines"], key=lambda l: {"REJECT": 0, "NEEDS A PERSON": 1, "APPROVE": 2}[l["decision"]])[0]
        return worst["decision"], worst.get("tier", ""), worst.get("reason", "")
    raise ValueError(f"unknown kind {kind}")


def main(as_json: bool = False) -> int:
    with open(ROOT / "checks" / "check_set.csv", newline="", encoding="utf-8") as f:
        records = list(csv.DictReader(f))
    results = []
    for r in records:
        d, t, why = run_one(r)
        ok = d == r["expected_decision"] and (not r["expected_tier"] or t == r["expected_tier"])
        results.append({"check_id": r["check_id"], "kind": r["kind"], "source": r["source"], "expected": r["expected_decision"], "expected_tier": r["expected_tier"],
                        "actual": d, "actual_tier": t, "right": ok, "description": r["description"], "reason": why})
    right = sum(1 for x in results if x["right"])
    C = get_clean()
    rest = Counter(evaluate_register_row(c, C).decision for c in C.claims)
    summary = {"right": right, "total": len(results), "register_claims_replayed": len(C.claims),
               "what_happens_to_the_rest": {"APPROVE (recommended)": rest["APPROVE"], "REJECT (recommended)": rest["REJECT"], "NEEDS A PERSON": rest["NEEDS A PERSON"]}}
    if as_json:
        print(json.dumps({"summary": summary, "results": results}, indent=2))
    else:
        for x in results:
            print(f"  [{'PASS' if x['right'] else 'FAIL'}] {x['check_id']}: {x['actual']} ({x['actual_tier']}) -- {x['description'][:90]}")
        print("\n" + "=" * 64 + f"\n  {right}/{len(results)} check-set records right\n" + "=" * 64)
        for x in results:
            if not x["right"]:
                print(f"  MISS {x['check_id']}: expected {x['expected']} ({x['expected_tier']}), got {x['actual']} ({x['actual_tier']}): {x['reason'][:140]}")
        print(f"\n  The rest of the register ({len(C.claims)} claims replayed, each against the claims before it):")
        for k, v in summary["what_happens_to_the_rest"].items():
            print(f"    {k:24s} {v:5d}")
        print("  Every decision is a recommendation. A named person (Commercial Finance) decides what moves money.")
    return 0 if right == len(results) else 1


if __name__ == "__main__":
    sys.exit(main("--json" in sys.argv))
