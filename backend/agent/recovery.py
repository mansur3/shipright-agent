"""
Recovery view: how much credited money broke a clear rule and can be claimed back, how much pending money should be held,
and what needs a person. Built from the one claim checker; nothing here is a new rule.

Rupee kinds stay apart (never added): recover (cash already credited, clear rule broken), hold (pending claims that fail a rule today),
review (credited, needs a person), unverifiable (credited on batches older than the extracts).
Recovering money is a decision for a named person (Commercial Finance); this module only lists it with the evidence.
"""
from __future__ import annotations

from collections import defaultdict
from functools import lru_cache

from agent.claim_checks import evaluate_register_row
from agent.clean import get_clean


def _row(c: dict, v, amount: float, bucket: str, name: str) -> dict:
    return {
        "claim_no": c["claim_no"], "stockist_code": c["stk"], "stockist_name": name, "batch_no": c["batch"], "sku_code": c["sku"],
        "claim_type": c["type"], "claim_date": c["cdate"].isoformat() if c["cdate"] else None, "status": c["status"],
        "credited_inr": round(c["credit_eff"], 2) if c["status"] == "Credited" else 0.0, "amount_inr": round(amount, 2),
        "bucket": bucket, "tier": v.tier, "rule_id": v.rule_ids[0] if v.rule_ids else "", "clause": v.clause, "reason": v.reason,
        "decision": v.decision,
    }


@lru_cache(maxsize=1)
def build() -> dict:
    C = get_clean()
    claims: list[dict] = []
    buckets = {k: {"claims": 0, "inr": 0.0} for k in ("recover_t1", "recover_t2", "hold", "review", "unverifiable")}
    stk = defaultdict(lambda: {"claims": 0, "recover_inr": 0.0, "credited_inr": 0.0})

    for c in C.claims:
        v = evaluate_register_row(c, C)
        name = C.stockists.get(c["stk"], {}).get("name", "")
        pts = C.pts(c["sku"])
        if c["status"] == "Credited":
            stk[c["stk"]]["credited_inr"] += c["credit_eff"]
            if v.tier in ("T1", "T2"):
                # a late claim is recoverable in full; an over-supply claim only for the packs above supply
                over = v.rule_ids and v.rule_ids[0] == "R_OVER_SUPPLY"
                amt = v.excess_packs * pts if over else c["credit_eff"]
                key = "recover_t1" if v.tier == "T1" else "recover_t2"
                buckets[key]["claims"] += 1
                buckets[key]["inr"] += amt
                stk[c["stk"]]["claims"] += 1
                stk[c["stk"]]["recover_inr"] += amt
                claims.append(_row(c, v, amt, key, name))
            elif v.tier == "T3":
                buckets["review"]["claims"] += 1
                buckets["review"]["inr"] += c["credit_eff"]
            elif v.tier == "T4":
                buckets["unverifiable"]["claims"] += 1
                buckets["unverifiable"]["inr"] += c["credit_eff"]
        elif c["status"] == "Pending" and v.tier in ("T1", "T2"):
            buckets["hold"]["claims"] += 1
            buckets["hold"]["inr"] += c["value_eff"]
            claims.append(_row(c, v, c["value_eff"], "hold", name))

    by_stockist = sorted(
        ({"stockist_code": s, "stockist_name": C.stockists.get(s, {}).get("name", ""), "cnf": C.stockists.get(s, {}).get("cnf", ""), **a,
          "recover_inr": round(a["recover_inr"], 2), "credited_inr": round(a["credited_inr"], 2)}
         for s, a in stk.items() if a["claims"]),
        key=lambda r: -r["recover_inr"],
    )
    claims.sort(key=lambda r: -r["amount_inr"])
    for b in buckets.values():
        b["inr"] = round(b["inr"], 2)
    recover_inr = round(buckets["recover_t1"]["inr"] + buckets["recover_t2"]["inr"], 2)  # T1 and T2 are both cash credited against a rule
    return {
        "buckets": buckets,
        "recover_inr": recover_inr,
        "recover_claims": buckets["recover_t1"]["claims"] + buckets["recover_t2"]["claims"],
        "recover_per_year_inr": round(recover_inr / 2.5, 2),   # 30 months of register = 2.5 years
        "by_stockist": by_stockist,
        "claims": claims,
        "window": "Apr 2024 to Sep 2026 (30 months)",
        "basis": "Every claim replayed against the claims before it by agent/claim_checks.py. T1 = policy text breached, T2 = probable breach.",
    }
