"""
Batch processor: runs every claim through the one claim checker and persists the result.

All numbers come from the clean data layer and the claim checker. The model is never invoked here.
Rupee kinds are never added together: credited cash, unverifiable claims, stock at risk and revenue are separate figures.
"""
from __future__ import annotations

import logging
from collections import defaultdict

from sqlmodel import Session

from agent import analysis
from agent.claim_checks import evaluate_register_row
from agent.clean import get_clean
from db.models import BatchAnalysisRun, ClaimFinding, RiskLevel, StockAlert, StockistRiskProfile

log = logging.getLogger(__name__)


def _level(score: int) -> RiskLevel:
    return RiskLevel.high if score >= 50 else RiskLevel.medium if score >= 25 else RiskLevel.low


def run_batch(session: Session) -> BatchAnalysisRun:
    """Score every claim, build stock alerts and stockist profiles, and store one BatchAnalysisRun."""
    C = get_clean()
    log.info("Batch run started")

    findings: list[ClaimFinding] = []
    tier_n: dict[str, int] = defaultdict(int)
    tier_v: dict[str, float] = defaultdict(float)
    repeat_value = 0.0
    repeat_groups: set = set()
    excess_value = 0.0
    pending_t12 = 0
    pending_t12_value = 0.0
    stk = defaultdict(lambda: {"credit": 0.0, "claims": 0, "clear": 0.0, "clear_n": 0, "repeat": 0.0, "unverifiable": 0.0, "value": 0.0})

    for c in C.claims:
        v = evaluate_register_row(c, C)
        credited = c["status"] == "Credited"
        pts = C.pts(c["sku"])
        excess = v.excess_packs * pts if "over_supply" in v.flags else 0.0
        if credited:
            # T1 counts the credit of a late claim in full, but only the packs above supply for an over-supply claim
            val = excess if v.rule_ids and v.rule_ids[0] == "R_OVER_SUPPLY" else c["credit_eff"]
            tier_n[v.tier] += 1
            tier_v[v.tier] += val
            if "exact_repeat" in v.flags:
                repeat_value += c["credit_eff"]
                repeat_groups.add((c["stk"], c["batch"], c["qty"]))
            if "over_supply" in v.flags:
                excess_value += excess
            s = stk[c["stk"]]
            s["credit"] += c["credit_eff"]
            if v.tier in ("T1", "T2"):
                s["clear"] += val
                s["clear_n"] += 1
            if "exact_repeat" in v.flags:
                s["repeat"] += c["credit_eff"]
            if v.tier == "T4":
                s["unverifiable"] += c["credit_eff"]
        elif c["status"] == "Pending" and v.tier in ("T1", "T2"):
            pending_t12 += 1
            pending_t12_value += c["value_eff"]
        stk[c["stk"]]["claims"] += 1
        stk[c["stk"]]["value"] += c["value_eff"]
        findings.append(ClaimFinding(
            claim_no=c["claim_no"], stockist_code=c["stk"], batch_no=c["batch"], sku_code=c["sku"], claim_type=c["type"],
            claim_date=c["cdate"].isoformat() if c["cdate"] else None, claim_value_inr=c["value_eff"], status=c["status"],
            risk_score=v.risk_score, risk_level=_level(v.risk_score), signals=",".join([v.tier] + v.flags),
            has_invoice=bool(c["inv"]), invoiced_qty=C.supply.get((c["stk"], c["batch"]), 0.0), claimed_qty=c["qty"],
            recommended_action=f"{v.decision} (recommendation) - {v.rule_ids[0] if v.rule_ids else 'all checks passed'}: {v.reason}"[:300],
        ))

    # ── stock: latest month-end only; 365-day horizon so the early-warning view has something to show ──
    horizon = analysis.at_risk_stock(365)
    alerts = [StockAlert(cnf_code=b["cnf_code"], cnf_city=b["cnf_city"], sku_code=b["sku_code"], product=b["product"], batch_no=b["batch_no"],
                         expiry_date=b["expiry_date"], days_to_expiry=b["days_to_expiry"], qty_packs=b["qty_packs"], pts_inr=b["pts_inr"],
                         value_inr=b["value_inr"], avg_monthly_outward=b["avg_monthly_outward"], recommend_redistribute=b["recommend_redistribute"])
              for b in horizon["batches"]]
    at_risk = {h: analysis.at_risk_stock(h)["total_value_inr"] for h in (30, 60, 90, 180)}

    # ── stockist profiles: how much of each stockist's credited value broke a clear rule ──
    prim = defaultdict(float)
    for r in C.sales:
        prim[r["stk"]] += r["value"]
    profiles: list[StockistRiskProfile] = []
    for s, a in stk.items():
        share = a["clear"] / a["credit"] if a["credit"] else 0.0
        score = min(100, round(200 * share))
        sigs = [f"clear_breaches:{a['clear_n']}"] if a["clear_n"] else []
        if a["repeat"]:
            sigs.append("repeat_credits")
        if a["unverifiable"]:
            sigs.append("unverifiable_credits")
        info = C.stockists.get(s, {})
        profiles.append(StockistRiskProfile(
            stockist_code=s, stockist_name=info.get("name", ""), cnf_code=info.get("cnf", ""), risk_score=score,
            claim_rate_pct=round(100 * a["value"] / max(prim.get(s, 0.0), 1.0), 2), total_claim_inr=a["value"],
            zero_inv_inr=a["unverifiable"], dup_credit_inr=a["repeat"], signals=",".join(sigs)))

    clear = tier_v["T1"] + tier_v["T2"]
    run = BatchAnalysisRun(
        total_claims=len(C.claims), total_sales_rows=len(C.sales), total_cnf_rows=len(C.snapshots),
        duplicate_groups=len(repeat_groups), duplicate_excess_inr=round(repeat_value, 2),
        zero_invoice_inr=round(tier_v["T4"], 2), qty_overclaim_inr=round(excess_value, 2),
        pending_suspicious_inr=round(pending_t12_value, 2),
        at_risk_30d_inr=round(at_risk[30], 2), at_risk_60d_inr=round(at_risk[60], 2),
        at_risk_90d_inr=round(at_risk[90], 2), at_risk_180d_inr=round(at_risk[180], 2),
        total_addressable_inr=round(clear, 2), high_risk_stockists=sum(1 for p in profiles if p.risk_score >= 50),
        t1_claims=tier_n["T1"], t1_inr=round(tier_v["T1"], 2), t2_claims=tier_n["T2"], t2_inr=round(tier_v["T2"], 2),
        t3_claims=tier_n["T3"], t3_inr=round(tier_v["T3"], 2), t4_claims=tier_n["T4"], t4_inr=round(tier_v["T4"], 2),
        pending_t12_claims=pending_t12,
    )
    session.add(run)
    session.flush()
    for f in findings:
        f.run_id = run.id
        session.add(f)
    for a in alerts:
        a.run_id = run.id
        session.add(a)
    for p in profiles:
        p.run_id = run.id
        session.add(p)
    session.commit()
    session.refresh(run)
    log.info("Batch complete: %d findings, %d alerts, clear breaches INR %.0f", len(findings), len(alerts), clear)
    run.__dict__["_findings_count"] = len(findings)
    run.__dict__["_stock_alerts_count"] = len(alerts)
    return run
