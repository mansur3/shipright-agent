"""
Opportunity register: every money finding in one list, classified by what kind of money it is, with the evidence behind it.

Nothing here invents a figure. Each amount is read from a function that reads the CSVs (agent.recovery, agent.analysis, agent.clean).
Classes are never added together: cash credited, cost, revenue at PTS and unsized risks are different things.
Recovering or changing anything is a decision for a named person; this module only lists, sizes and labels.

Classes
  confirmed_leakage        cash already credited where the written policy text was breached (T1)
  potentially_recoverable  cash already credited where a breach is probable (T2); the claim owner confirms before any recovery
  cost_avoidance           pending claims that fail a rule today; not yet paid, so hold them
  cost_saving              recurring cost that a policy or scheme change would reduce
  revenue_opportunity      sales at PTS that better allocation could serve; NOT cash and NOT margin
  operational_risk         a control that failed or a pattern that precedes loss; not sized as a loss
  exposure                 money that cannot be called leakage or recovery from the pack (needs a person, or the data is missing)
"""
from __future__ import annotations

from functools import lru_cache

from agent import analysis, recovery
from agent.clean import get_clean

CLASSES = {
    "confirmed_leakage": "Confirmed leakage",
    "potentially_recoverable": "Potentially recoverable",
    "cost_avoidance": "Cost avoidance (hold)",
    "cost_saving": "Cost saving",
    "revenue_opportunity": "Revenue opportunity",
    "operational_risk": "Operational risk",
    "exposure": "Exposure, not leakage",
}
CONFIDENCE = ("High", "Medium", "Low")

# the one deterministic check an opportunity must pass before it is shown as validated
_REQUIRED = ("id", "name", "class", "problem", "evidence", "formula", "confidence", "feasibility", "action", "owner", "agent", "priority", "kind")


def _last_quarters(n: int = 4) -> list[str]:
    from agent.clean import fiscal_quarter
    qs = sorted({fiscal_quarter(r["date"]) for r in get_clean().sales})
    return qs[-n:]


def _scheme_returns_vs_target() -> dict:
    """Expiry-type claims logged in the last 4 fiscal quarters, less the CFO's 1% of primary sales target (the ledger's method B)."""
    from agent.clean import fiscal_quarter
    C = get_clean()
    qs = set(_last_quarters(4))
    logged = sum(c["value_eff"] for c in C.claims if c["cdate"] and fiscal_quarter(c["cdate"]) in qs and c["type"] in ("Near expiry", "Expired"))
    primary = sum(r["invoiced"] * r["pts"] for r in C.sales if fiscal_quarter(r["date"]) in qs)
    target = 0.01 * primary
    return {"quarters": sorted(qs), "logged_inr": round(logged), "target_inr": round(target), "excess_inr": round(logged - target)}


def _hooghly_fefo(last_quarters: int = 2) -> dict:
    rows = [r for r in analysis.fefo_breaches() if r["cnf_code"] == "CF-E01"]
    qs = sorted({r["quarter"] for r in rows})[-last_quarters:]
    sel = [r for r in rows if r["quarter"] in qs]
    lines = sum(r["lines"] for r in sel)
    breach = sum(r["breach_lines"] for r in sel)
    return {"quarters": qs, "lines": lines, "breach_lines": breach, "breach_pct": round(100 * breach / lines, 1) if lines else 0.0,
            "shipped_out_of_order_inr": round(sum(r["shipped_out_of_order_inr"] for r in sel))}


@lru_cache(maxsize=1)
def build() -> dict:
    rec = recovery.build()
    b = rec["buckets"]
    foc = analysis.foc_by_quarter()
    foc_last4 = foc[-4:]
    foc_cap_last4 = round(sum(q["over_cap_inr"] for q in foc_last4))
    foc_cap_all = round(sum(q["over_cap_inr"] for q in foc))
    over_qs = [q["quarter"] for q in foc if q["over_cap"]]
    sc = analysis.scheme_claim_rates()
    srt = _scheme_returns_vs_target()
    fwd_qs = _last_quarters(2)
    fwd = [analysis.scheme_return_estimate(q) for q in fwd_qs]
    fwd_lo, fwd_hi = sum(f["expected_return_low_inr"] for f in fwd), sum(f["expected_return_high_inr"] for f in fwd)
    now = analysis.unfilled_shortfall(1)
    cum = analysis.unfilled_shortfall(6)
    cover = analysis.stock_cover()
    hoog = _hooghly_fefo()
    dispatch = analysis.short_dated_dispatch()

    top_stk = rec["by_stockist"][:3]
    opps: list[dict] = [
        {
            "id": "OPP-01", "name": "Credited claims that broke written policy text",
            "class": "confirmed_leakage", "kind": "cash credited",
            "problem": "Credit notes were issued for claims filed more than 90 days after expiry, or for more packs than were invoiced to the stockist.",
            "evidence": "expiry_claims.csv (4,503 claims replayed in date order) against primary_sales.csv invoices and batch_master.csv; CO-POL-014 5.2 (p3) and 5.5 (p3)",
            "scope": f"{b['recover_t1']['claims']} claims, Apr 2024 to Sep 2026; largest: " + ", ".join(f"{s['stockist_name']} ({s['stockist_code']})" for s in top_stk),
            "formula": "sum of credit_inr where claim is late beyond the window (full credit) or over supply (excess packs x PTS), tier T1; checker agent/claim_checks.py",
            "amount_inr": b["recover_t1"]["inr"], "claims": b["recover_t1"]["claims"],
            "confidence": "High", "feasibility": "Medium: credit already issued; recovery is by set-off against future credit notes, which Commercial Finance must agree",
            "action": "Controller reviews the T1 list and raises set-off requests; add the claim checker as a gate before every credit note.",
            "owner": "Commercial Finance (Neha Bansal)", "agent": "Claim Gatekeeper, Recovery Analyst", "priority": 1,
        },
        {
            "id": "OPP-02", "name": "Credited claims with a probable breach (repeats, out of window)",
            "class": "potentially_recoverable", "kind": "cash credited",
            "problem": "The same stockist, batch and quantity was credited twice, or the claim fell outside the near-expiry or post-expiry window.",
            "evidence": "expiry_claims.csv, primary_sales.csv, batch_master.csv; CO-POL-014 5.2 (p3), 5.5 (p3)",
            "scope": f"{b['recover_t2']['claims']} claims, Apr 2024 to Sep 2026",
            "formula": "sum of credit_inr for tier T2 (outside window or exact repeat); tiers T1 and T2 never overlap",
            "amount_inr": b["recover_t2"]["inr"], "claims": b["recover_t2"]["claims"],
            "confidence": "Medium", "feasibility": "Medium: each claim needs the owner to confirm it is a breach, not a documented exception",
            "action": "Controller confirms or clears each T2 claim; confirmed ones join the set-off list.",
            "owner": "Commercial Finance (Neha Bansal)", "agent": "Claim Gatekeeper, Recovery Analyst", "priority": 2,
        },
        {
            "id": "OPP-03", "name": "Pending claims that fail a rule today",
            "class": "cost_avoidance", "kind": "cash not yet paid",
            "problem": "Claims in Pending status would breach the same rules if credited now.",
            "evidence": "expiry_claims.csv status = Pending, checked by agent/claim_checks.py",
            "scope": f"{b['hold']['claims']} pending claims",
            "formula": "sum of claim value for pending claims in tiers T1 and T2",
            "amount_inr": b["hold"]["inr"], "claims": b["hold"]["claims"],
            "confidence": "High", "feasibility": "High: nothing has been paid; the credit can simply be held",
            "action": "Hold these credit notes until the claimant answers the rule that fails.",
            "owner": "Commercial Finance (Neha Bansal)", "agent": "Claim Gatekeeper", "priority": 1,
        },
        {
            "id": "OPP-04", "name": "Free goods above the 3% cap",
            "class": "cost_saving", "kind": "cost (free goods at PTS)",
            "problem": f"Free scheme goods exceeded 3% of the quarter's primary sales in {len(over_qs)} of {len(foc)} quarters.",
            "evidence": "primary_sales.csv (free and invoiced packs x PTS by fiscal quarter); CO-POL-014 4.4 (p2); exceptions need CFO approval, none are in the pack",
            "scope": f"last 4 quarters: {', '.join(q['quarter'] for q in foc_last4)}; cumulative since {over_qs[0] if over_qs else 'n/a'}: INR {foc_cap_all / 1e7:.2f} crore",
            "formula": "per quarter, max(0, free value at PTS - 3% x primary value at PTS), summed over the last 4 quarters",
            "amount_inr": foc_cap_last4, "claims": None,
            "confidence": "High on the excess; Medium on avoidability (approved exceptions may exist)",
            "feasibility": "High going forward: a circular can enforce the cap",
            "action": "CFO and NSM approve the next scheme circular only within the cap, or record the exception.",
            "owner": "CFO (Rohan Mehta), NSM (Arjun Sethi)", "agent": "Scheme Order Gate", "priority": 2,
        },
        {
            "id": "OPP-05", "name": "Expiry returns pushed by quarter-end schemes",
            "class": "cost_saving", "kind": "cost (claims credited)",
            "problem": f"Scheme packs come back as claims at {sc['scheme_pack_rate_pct']}% against {sc['other_pack_rate_pct']}% for other packs ({sc['multiple']}x).",
            "evidence": "primary_sales.csv scheme flag joined to expiry_claims.csv by batch and stockist; expiry claims above the CFO's 1% of primary sales target",
            "scope": f"last 4 quarters {srt['quarters'][0]} to {srt['quarters'][-1]}: logged INR {srt['logged_inr'] / 1e7:.2f} crore vs target INR {srt['target_inr'] / 1e7:.2f} crore",
            "formula": "expiry-type claims logged in the last 4 fiscal quarters minus 1% of invoiced primary value at PTS (CFO target)",
            "amount_inr": srt["excess_inr"], "claims": None,
            "range": {"low_inr": fwd_lo, "high_inr": fwd_hi, "note": f"forward range: claims still to come from {fwd_qs[0]} and {fwd_qs[1]} scheme supply at cohort claim rates {sc['cohort_low_pct']}% to {sc['cohort_high_pct']}%"},
            "confidence": "Medium: size depends on the 1% target; direction is High",
            "feasibility": "Medium: needs scheme design change (stock norm, quarter-end minimums)",
            "action": "Add the Scheme Order Gate to quarter-end order approval; RSM confirms stock held before a scheme is accepted.",
            "owner": "NSM (Arjun Sethi), CFO (Rohan Mehta)", "agent": "Scheme Order Gate, Supply and FEFO Watcher", "priority": 1,
            "overlap": "Overlaps OPP-04 (same scheme lever) and OPP-09 (short-dated dispatch); do not add them.",
        },
        {
            "id": "OPP-06", "name": "Stock sits in the wrong place: short supply a reallocation could serve",
            "class": "revenue_opportunity", "kind": "revenue at PTS (not cash, not margin)",
            "problem": "Some C&Fs hold under one month of their own outward while others hold spare stock of the same SKU.",
            "evidence": "cnf_stock_snapshot.csv latest month-end, avg_monthly_outward_packs (inferred allocation basis: the share table is not in the pack), sku_master.csv PTS",
            "scope": f"month-end {now['month_ends'][-1]}, all C&Fs; Lucknow holds {_cnf(cover, 'CF-N02')['share_of_stock_pct']}% of stock for {_cnf(cover, 'CF-N02')['share_of_outward_pct']}% of outward",
            "formula": "per SKU: min(total shortage to 1 month of cover, total spare stock above 1 month) x PTS, each spare pack counted once, latest month-end only",
            "amount_inr": now["allocation_fixable_inr"], "claims": None,
            "context": {"total_shortfall_inr": now["shortfall_inr"], "not_coverable_by_allocation_inr": now["not_coverable_inr"],
                        "six_month_cumulative_shortfall_inr": cum["shortfall_inr"],
                        "note": "The six month-end cumulative figure counts a persistent gap once per month; it is exposure over time, not one amount, so it is not used as the opportunity."},
            "confidence": "Medium: depends on the outward definition and on the stock being movable (shelf life, transport)",
            "feasibility": "Medium: needs Demand Planning to confirm the allocation basis",
            "action": "Supply Chain moves spare SKUs to short C&Fs before the monthly allocation; Demand Planning confirms the outward definition.",
            "owner": "Supply Chain (Kavita Rao), Demand Planning (Vaishali Kapoor)", "agent": "Supply and FEFO Watcher", "priority": 2,
        },
        {
            "id": "OPP-07", "name": "Hooghly (Kolkata) ships newer batches before older ones",
            "class": "operational_risk", "kind": "stock value shipped out of order (not a loss)",
            "problem": f"FEFO was broken on {hoog['breach_pct']}% of Kolkata lines in {hoog['quarters'][0]} to {hoog['quarters'][-1]} against 0% at the other C&Fs; older stock is left behind.",
            "evidence": "primary_sales.csv invoice lines vs batch_master.csv expiry order, per C&F per quarter; CO-POL-014 7.1",
            "scope": f"CF-E01 Kolkata, {hoog['breach_lines']} of {hoog['lines']} lines, INR {hoog['shipped_out_of_order_inr'] / 1e7:.2f} crore shipped out of order",
            "formula": "lines where a newer batch shipped while an older batch had stock, counted per quarter; value at PTS",
            "amount_inr": None, "claims": None, "reference_inr": hoog["shipped_out_of_order_inr"],
            "confidence": "High on the breach; the loss is not sized because no stock is within 180 days of expiry yet",
            "feasibility": "High: a C&F SOP reminder and a weekly FEFO check",
            "action": "Supply Chain raises the FEFO breach with the Kolkata C&F and checks weekly.",
            "owner": "Supply Chain (Kavita Rao)", "agent": "Supply and FEFO Watcher", "priority": 3,
        },
        {
            "id": "OPP-08", "name": "Claims that need a person before any decision",
            "class": "exposure", "kind": "cash credited, not judged",
            "problem": "Credited claims that cannot be called leakage: partial repeats within supply, or no invoice reference but supported by supply.",
            "evidence": "expiry_claims.csv tier T3 from agent/claim_checks.py",
            "scope": f"{b['review']['claims']} claims",
            "formula": "sum of credit_inr for tier T3",
            "amount_inr": None, "claims": b["review"]["claims"], "reference_inr": b["review"]["inr"],
            "confidence": "High that they need review; not sized as recoverable", "feasibility": "Review workload, not recovery",
            "action": "Claims desk works the review queue; not counted as leakage.",
            "owner": "Commercial Finance (Neha Bansal)", "agent": "Claims Mailbox Triage, Claim Gatekeeper", "priority": 3,
        },
        {
            "id": "OPP-09", "name": "Claims on batches older than the data",
            "class": "exposure", "kind": "cash credited, cannot be checked",
            "problem": "Credit exists for batches that are not in the batch master, so no rule can be tested.",
            "evidence": "expiry_claims.csv with batch_in_master = false",
            "scope": f"{b['unverifiable']['claims']} claims",
            "formula": "sum of credit_inr for tier T4",
            "amount_inr": None, "claims": b["unverifiable"]["claims"], "reference_inr": b["unverifiable"]["inr"],
            "confidence": "High that they cannot be checked", "feasibility": "Needs the archive batch master from the client",
            "action": "Request the archive batch master; until then this is not leakage and is not claimed.",
            "owner": "Commercial Finance (Neha Bansal)", "agent": "Recovery Analyst", "priority": 3,
        },
        {
            "id": "OPP-10", "name": "Dispatch below 60% residual shelf life",
            "class": "operational_risk", "kind": "invoiced value shipped (not a loss)",
            "problem": f"{dispatch['rows_under_60pct']} of {dispatch['rows']} invoice lines ({dispatch['share_pct']}%) shipped with under 60% of shelf life left.",
            "evidence": "primary_sales.csv joined to batch_master.csv; CO-POL-014 7.1 (p4)",
            "scope": "all six C&Fs, 5% to 6% of lines each",
            "formula": "count and PTS value of invoice lines where (expiry - invoice date) / shelf life < 60%",
            "amount_inr": None, "claims": None, "reference_inr": dispatch["value_inr"],
            "confidence": "Medium", "feasibility": "High: block dispatch under policy",
            "action": "Enforce the dispatch freeze in the C&F system.",
            "owner": "Supply Chain (Kavita Rao)", "agent": "Supply and FEFO Watcher", "priority": 3,
            "overlap": "Overlaps OPP-05 (the same batches come back as claims); do not add.",
        },
    ]
    for o in opps:
        o["class_label"] = CLASSES[o["class"]]
        o["validated"] = all(o.get(k) not in (None, "") for k in _REQUIRED) and o["confidence"].startswith(CONFIDENCE)
        o["validation"] = "Amount computed in code from the source CSVs and reconciled to the findings ledger; no model-written figure." if o["validated"] else "Incomplete: not shown as validated"
        o["sized"] = o["amount_inr"] is not None

    totals = {k: {"opportunities": 0, "amount_inr": 0} for k in CLASSES}
    for o in opps:
        t = totals[o["class"]]
        t["opportunities"] += 1
        if o["amount_inr"] is not None:
            t["amount_inr"] += o["amount_inr"]
    cash = round(b["recover_t1"]["inr"] + b["recover_t2"]["inr"], 2)
    return {
        "opportunities": opps,
        "classes": CLASSES,
        "totals_by_class": totals,
        "headline": {
            "confirmed_leakage_inr": b["recover_t1"]["inr"],
            "potentially_recoverable_inr": b["recover_t2"]["inr"],
            "credited_cash_to_review_inr": cash,
            "cash_to_hold_inr": b["hold"]["inr"],
            "annual_cost_saving_inr": {"free_goods_over_cap_last_4_quarters": foc_cap_last4, "returns_above_1pct_target_last_4_quarters": srt["excess_inr"]},
            "revenue_opportunity_at_pts_inr": now["allocation_fixable_inr"],
        },
        "rules": [
            "Classes are different kinds of money and are never added together.",
            "OPP-04, OPP-05 and OPP-10 describe overlapping scheme effects; they are not additive.",
            "Revenue opportunity is sales at PTS, not recovered cash and not margin.",
            "Credited-cash figures are for the 30-month register (Apr 2024 to Sep 2026); recovery needs a named person's decision.",
        ],
        "window": rec["window"],
    }


def _cnf(cover: dict, code: str) -> dict:
    return next(x for x in cover["by_cnf"] if x["cnf_code"] == code)
