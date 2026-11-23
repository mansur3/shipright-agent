"""
Tools the LangGraph agent can call. Every fact comes from the clean data layer and the one claim checker;
the model never writes a batch, date, quantity or amount that is not in a tool result.
Each result names its source so the answer can cite it.
"""
from __future__ import annotations

import re

from datetime import date, datetime

from langchain_core.tools import tool

import config as P
from agent import analysis
from agent.claim_checks import ClaimInput, evaluate
from agent.clean import CNF_CITY, fiscal_quarter, get_clean, parse_date

_REF = datetime.strptime(P.DATA_REF_DATE, "%Y-%m-%d").date()


# ── Tool 1: batch look-up ─────────────────────────────────────────────────────

@tool
def lookup_batch(batch_no: str) -> dict:
    """Look up a batch in the batch master: SKU, product, manufacturing and expiry date, PTS, shelf life, days to expiry.
    found=False means the batch is not in the master, which covers batches made from Oct 2023 only; say so and do not guess.
    Use whenever a question mentions a batch number."""
    C = get_clean()
    b = C.batches.get(batch_no.strip().upper())
    if not b:
        return {"found": False, "batch_no": batch_no, "note": "Not in batch_master, which covers batches made from Oct 2023. An older batch needs the archived record.", "source": "batch_master.csv"}
    s = C.skus[b["sku"]]
    left = (b["exp"] - _REF).days if b["exp"] else None
    return {"found": True, "batch_no": b["batch"], "sku_code": b["sku"], "product": s["description"], "therapy_area": s["therapy_area"],
            "mfg_date": b["mfg"].isoformat() if b["mfg"] else None, "expiry_date": b["exp"].isoformat() if b["exp"] else None,
            "shelf_life_months": s["shelf_months"], "pts_inr": s["pts"], "days_to_expiry": left,
            "expiry_status": "expired" if left is not None and left < 0 else "near_expiry" if left is not None and left <= 90 else "ok",
            "source": f"batch_master.csv line {b['_line']}, sku_master.csv line {s['_line']}"}


# ── Tool 2: claim validation (the one checker) ────────────────────────────────

def _clean_sku(raw: str) -> str:
    """A SKU is only used if it looks like one (PFL1102). Anything else the model passed by mistake is dropped and the batch's own SKU is used."""
    s = (raw or "").strip().upper().replace("-", "")
    return s if re.fullmatch(r"PFL\d{4}", s) else ""


def normalise_claim_type(raw: str) -> str:
    """Map how people write a claim type ('expiry', 'near-expiry', 'damaged') to the four types in the policy. Unknown text is left as it is, so the checker reports it."""
    s = (raw or "").strip().lower().replace("-", " ").replace("_", " ")
    if "near" in s:
        return "Near expiry"
    if "expir" in s:
        return "Expired"
    if "break" in s or "damag" in s or "transit" in s:
        return "Breakage in transit"
    if "short" in s:
        return "Short supply"
    return (raw or "").strip()


@tool
def validate_claim(stockist_code: str, batch_no: str, qty_claimed: float, claim_date: str, claim_type: str, invoice_ref: str = "", sku_code: str = "") -> dict:
    """Check an expiry, breakage or short-supply claim against CO-POL-014 v4.2: batch, claim window (breakage and short supply are measured from the
    invoice date), quantity against everything invoiced to that stockist for the batch (cumulative), earlier credited claims, invoice reference.
    Returns decision (APPROVE, REJECT or NEEDS A PERSON), evidence tier, rule ids, the policy clause, rupee impact and the file and line of every record used.
    The decision is a recommendation; Commercial Finance decides. sku_code is optional: leave it empty if the user did not give one. claim_type is one of: Near expiry, Expired, Breakage in transit, Short supply. Always call this before saying whether a claim is valid."""
    v = evaluate(ClaimInput(stockist=stockist_code, batch=batch_no, qty=qty_claimed, claim_date=parse_date(claim_date), claim_type=normalise_claim_type(claim_type),
                            invoice_ref=invoice_ref, sku=_clean_sku(sku_code)))
    d = v.as_dict()
    d["valid"] = v.tier == "CLEAN"
    d["recommended_action"] = f"{v.decision} (recommendation): {v.reason}"
    d["source"] = "batch_master.csv, primary_sales.csv, expiry_claims.csv, stockist_master.csv"
    return d


# ── Tool 3: at-risk stock ─────────────────────────────────────────────────────

@tool
def get_at_risk_stock(cnf_code: str = "", days_threshold: int = 90) -> dict:
    """Stock on hand at the latest month-end whose expiry is within days_threshold days, by C&F, at PTS, with whether it can sell before the 60-day block.
    An empty list is a real answer: it means nothing on hand today is that close to expiry. Earlier months are history, not stock on hand.
    The result also has freeze_watch: batches within 120 and 90 days of the 60-day dispatch freeze (180 and 150 days to expiry) and regional imbalance; quote its
    `message` for any question about the freeze. Use for expiring stock, inventory risk or batches to destroy."""
    r = analysis.at_risk_stock(int(days_threshold), cnf_code.strip().upper())
    if not r["batches"]:
        r["message"] = f"No stock on hand at {r['as_of']} expires within {days_threshold} days."
    r["freeze_watch"] = analysis.freeze_watch(cnf_code.strip().upper())   # R7: 120 and 90 days before the 60-day freeze, and regional imbalance
    return r


# ── Tool 4: scheme gate ───────────────────────────────────────────────────────

@tool
def check_scheme_eligibility(stockist_code: str, sku_code: str, proposed_order_qty: float | None = None, scheme_foc_qty: float = 0.0) -> dict:
    """Before a quarter-end scheme order is accepted: how many months of normal purchase the stockist took in the last 3 months, and how much of its earlier
    scheme packs of that SKU came back as claims. Cannot measure closing stock (no secondary data), so it flags for the RSM to confirm; never says 'eligible'.
    Pass proposed_order_qty (and scheme_foc_qty) to test a specific order: code returns BLOCK SCHEME when the order would add more than 2.5 months of
    normal purchase (policy 4.5), as a recommendation the RSM confirms. Use before accepting scheme orders from RSMs."""
    return analysis.scheme_gate(stockist_code, sku_code, proposed_order_qty, scheme_foc_qty)


# ── Tool 5: quarter phasing and scheme-driven returns ─────────────────────────

@tool
def detect_quarter_spike(sku_code: str = "", cnf_code: str = "") -> dict:
    """Share of each fiscal quarter's primary sales invoiced in the last 9 days, by month of the quarter, with the share on scheme-coded lines, and the expected
    claims still to come from the latest quarter's scheme packs (an estimate with a range from earlier cohorts). Use for demand patterns, scheme risk and returns to come."""
    sku = sku_code.strip().upper().replace("-", "")
    ph = analysis.phasing(sku, cnf_code.strip().upper())
    if not ph:
        return {"found": False, "sku_code": sku_code}
    rows = [{"quarter": p["quarter"], "total_inr": p["total_inr"], "last9d_inr": round(p["total_inr"] * p["last9d_pct"] / 100), "spike_pct": p["last9d_pct"],
             "scheme_pct": p["scheme_share_of_last9d_pct"], "month1_pct": p["month1_pct"], "month2_pct": p["month2_pct"], "month3_pct": p["month3_pct"]} for p in ph]
    recent = rows[-4:]
    avg = sum(p["spike_pct"] for p in recent) / len(recent)
    latest = rows[-1]
    est = analysis.scheme_return_estimate(latest["quarter"]) if not sku and not cnf_code else None
    risk = "HIGH" if avg >= P.SPIKE_HIGH_PCT else "MEDIUM" if avg >= P.SPIKE_MEDIUM_PCT else "LOW"
    return {"sku_code": sku or "ALL", "phasing_by_quarter": rows, "avg_spike_pct_last4q": round(avg, 1), "risk_level": risk,
            "latest_quarter": latest["quarter"], "latest_spike_pct": latest["spike_pct"], "baseline_spike_pct": P.SPIKE_BASELINE_PCT,
            "projected_expiry_return_inr": est["expected_return_mid_inr"] if est else None, "expected_return_range_inr": (
                {"low": est["expected_return_low_inr"], "high": est["expected_return_high_inr"], "basis": est["basis"], "kind": "estimate"} if est else None),
            "source": "primary_sales.csv (scheme_code, invoice_date); expiry_claims.csv for the return rate"}


# ── Tool 6: fill rate ─────────────────────────────────────────────────────────

@tool
def get_fill_rate(cnf_code: str = "") -> dict:
    """Fill rate by C&F and fiscal quarter: packs ordered against packs invoiced, ordered counted once per order line. 'paid' counts invoiced packs only;
    'qbr_basis' counts free scheme packs as supplied, which is how the QBR scorecard is built. Also the value ordered but not supplied at PTS.
    Use for supply availability, stock-outs and Lucknow or territory issues."""
    rows = analysis.fill_rates()
    c = cnf_code.strip().upper() or "ALL"
    q_last = sorted({r["quarter"] for r in rows})[-1]
    latest = [r for r in rows if r["quarter"] == q_last and r["cnf_code"] != "ALL" and (c == "ALL" or r["cnf_code"] == c)]
    by_cnf = [{"cnf_code": r["cnf_code"], "cnf_city": r["cnf_city"], "ordered_qty": r["ordered"], "invoiced_qty": r["invoiced"],
               "fill_rate_pct": r["paid_pct"], "qbr_basis_pct": r["qbr_basis_pct"], "unfilled_qty": r["ordered"] - r["invoiced"],
               "unfilled_inr": r["unfilled_inr"], "zero_supplied_lines_pct": r["zero_lines_pct"]} for r in latest]
    allr = next(r for r in rows if r["quarter"] == q_last and r["cnf_code"] == "ALL")
    return {"quarter": q_last, "by_cnf": by_cnf, "overall_fill_rate_pct": allr["paid_pct"], "overall_qbr_basis_pct": allr["qbr_basis_pct"],
            "trend_by_quarter": [{"quarter": r["quarter"], "paid_pct": r["paid_pct"], "qbr_basis_pct": r["qbr_basis_pct"], "unfilled_inr": r["unfilled_inr"]}
                                 for r in rows if r["cnf_code"] == c],
            "basis": "paid = invoiced / ordered; qbr_basis = (invoiced + free) / ordered", "source": "primary_sales.csv (repeated rows removed, ordered once per line)"}


# ── Tool 7: stockist overview ─────────────────────────────────────────────────

@tool
def get_stockist_summary(stockist_code: str) -> dict:
    """Stockist identity, total purchases, claims by evidence tier, and the claim-back rate. Use for a specific stockist's trading and claim behaviour."""
    C = get_clean()
    s = C.stockists.get(stockist_code.strip().upper())
    if not s:
        return {"found": False, "stockist_code": stockist_code}
    from agent.claim_checks import evaluate_register_row
    rows = [c for c in C.claims if c["stk"] == s["stk"]]
    tiers: dict[str, int] = {}
    for c in rows:
        t = evaluate_register_row(c, C).tier
        tiers[t] = tiers.get(t, 0) + 1
    inv_val = sum(r["value"] for r in C.sales if r["stk"] == s["stk"])
    claimed = sum(c["value_eff"] for c in rows)
    return {"found": True, "stockist_code": s["stk"], "stockist_name": s["name"], "city": s["city"], "state": s["state"], "cnf_code": s["cnf"],
            "total_invoiced_value_inr": round(inv_val), "total_claims": len(rows), "total_claimed_value_inr": round(claimed),
            "claim_value_pct_of_purchases": round(100 * claimed / inv_val, 1) if inv_val else 0, "claims_by_evidence_tier": tiers,
            "source": "primary_sales.csv, expiry_claims.csv, stockist_master.csv"}


# ── Tool 8: stock cover and allocation ────────────────────────────────────────

@tool
def get_stock_cover(cnf_code: str = "", sku_code: str = "") -> dict:
    """Months of stock cover (stock on hand / the extract's average monthly outward) per C&F at the latest month-end, share of national stock against share of
    outward volume, SKUs a C&F has none of while other C&Fs hold spare stock (at PTS), and how much of the shortage spare stock elsewhere could meet.
    Use for short-and-long questions, allocation, Lucknow or Kolkata stock."""
    r = analysis.stock_cover()
    sf = analysis.unfilled_shortfall(6)
    lack = r["cnfs_lacking_skus_that_other_cnfs_hold_spare"].get("CF-N02", {})
    by = {x["cnf_code"]: x for x in r["by_cnf"]}
    now = analysis.unfilled_shortfall(1)
    out = {**r, "shortage_split_last_6_month_ends": sf, "shortage_split_latest_month_end": now,
           "interpretation": (f"Latest month-end only ({now['month_ends'][-1]}): shortfall INR {now['shortfall_inr'] / 1e7:.1f} crore, of which INR {now['allocation_fixable_inr'] / 1e7:.1f} crore "
                              f"({now['allocation_fixable_pct']}%) could be met by reallocation. The six month-end total below counts a persistent gap once per month, so it is exposure over time, not one amount to recover. "
                              f"{sf['allocation_fixable_pct']}% of the shortfall at the last 6 month-ends (INR {sf['shortfall_inr'] / 1e7:.1f} crore) could be met by moving stock that other C&Fs hold "
                              f"above one month of their own outward (each spare pack counted once), so most of the shortage is an ALLOCATION problem; the other {100 - sf['allocation_fixable_pct']:.0f}% "
                              f"(INR {sf['not_coverable_inr'] / 1e7:.1f} crore) is stock the network does not have, which allocation cannot fix. "
                              f"Lucknow holds {by['CF-N02']['share_of_stock_pct']}% of national stock for {by['CF-N02']['share_of_outward_pct']}% of outward volume, with {by['CF-N02']['cover_months']} months of cover; "
                              f"Kolkata holds {by['CF-E01']['share_of_stock_pct']}% of stock for {by['CF-E01']['share_of_outward_pct']}% of outward, {by['CF-E01']['cover_months']} months of cover. "
                              f"Lucknow lacks {lack.get('skus_lacking', 0)} SKUs that the other C&Fs hold INR {lack.get('spare_stock_elsewhere_inr', 0) / 1e7:.1f} crore spare of."),
           "field_guide": "cnfs_lacking_skus_that_other_cnfs_hold_spare: the key is the C&F that LACKS the stock; spare_stock_elsewhere_inr is what the OTHER C&Fs hold."}
    if cnf_code:
        out["by_cnf"] = [x for x in out["by_cnf"] if x["cnf_code"] == cnf_code.strip().upper()]
    return out


# ── Tool 9: dispatch quality ──────────────────────────────────────────────────

@tool
def get_dispatch_quality(cnf_code: str = "") -> dict:
    """FEFO breaches by C&F and fiscal quarter (a later-expiry batch shipped while an older batch of the same SKU was on hand at the same C&F), and invoice rows
    dispatched with under 60% of shelf life left (policy 7.1). Use for FEFO, WMS, old lots, Hooghly or Kolkata, and short-dated dispatch."""
    f = analysis.fefo_breaches()
    c = cnf_code.strip().upper()
    if c:
        f = [r for r in f if r["cnf_code"] == c]
    e01 = [r for r in analysis.fefo_breaches() if r["cnf_code"] == "CF-E01"]
    others_max = max([r["breach_pct"] for r in analysis.fefo_breaches() if r["cnf_code"] != "CF-E01"] or [0])
    return {"interpretation": (f"FEFO breaches: Kolkata (CF-E01) {e01[-1]['breach_pct']}% of dispatch lines in {e01[-1]['quarter']} (0% until FY26Q3, after the February 2026 WMS change); the highest at any other C&F in any quarter is {others_max}%. "
                               "A breach means a later-expiry batch shipped while an older batch of the same SKU was on hand at that C&F."),
            "fefo_breaches_by_quarter": f, "short_dated_dispatch": analysis.short_dated_dispatch(),
            "source": "primary_sales.csv, cnf_stock_snapshot.csv, batch_master.csv"}


# ── Tool 10: free goods against the cap ───────────────────────────────────────

@tool
def get_scheme_cap() -> dict:
    """Free goods at PTS as a percentage of each quarter's primary sales against the 3% cap (CO-POL-014 4.4), value above the cap, and the claim rate of scheme packs
    against other packs. Use for scheme cost, cap exceptions, and whether schemes drive expiry returns."""
    rates = analysis.scheme_claim_rates()
    by = analysis.foc_by_quarter()
    over = [r["quarter"] for r in by if r["over_cap"]]
    return {"interpretation": (f"Free goods were above the 3% cap in {len(over)} quarters ({over[0]} to {over[-1]}); the latest quarter {by[-1]['quarter']} was {by[-1]['foc_pct']}%. "
                               f"Packs supplied under a quarter-end scheme came back as claims at {rates['scheme_pack_rate_pct']}% against {rates['other_pack_rate_pct']}% for other packs ({rates['multiple']}x); "
                               f"inside the ten tier-A SKUs alone {rates['tier_a_scheme_pack_rate_pct']}% vs {rates['tier_a_other_pack_rate_pct']}% ({rates['tier_a_multiple']}x). A measured association, not an experiment."),
            "free_goods_by_quarter": by, "scheme_pack_claim_rates": rates,
            "clause": "CO-POL-014 4.4 (p2)", "source": "primary_sales.csv, expiry_claims.csv"}


# ── Tool 11: how much can be claimed back ────────────────────────────────────

@tool
def get_recovery_summary(stockist_code: str = "") -> dict:
    """How much credited money broke a clear policy rule and can be claimed back (T1 policy text breached, T2 probable), how much pending money fails a rule today (hold), and how much needs a person or cannot be checked.
    With a stockist_code, the same for that stockist. Use for 'how much can we recover', 'who should we recover from', 'how much do we hold'."""
    from agent import recovery
    r = recovery.build()
    b = r["buckets"]
    out = {
        "interpretation": (f"INR {r['recover_inr']/1e5:.1f} lakh was credited against a clear policy rule over {r['window']} "
                           f"({b['recover_t1']['claims']} claims where policy text was breached, INR {b['recover_t1']['inr']/1e5:.1f} lakh; {b['recover_t2']['claims']} probable, INR {b['recover_t2']['inr']/1e5:.1f} lakh). "
                           f"{b['hold']['claims']} pending claims fail a rule today (INR {b['hold']['inr']/1e5:.1f} lakh): hold them. "
                           f"These are different kinds of money and are not added to the {b['review']['claims']} credited claims that need a person (INR {b['review']['inr']/1e5:.1f} lakh) or the {b['unverifiable']['claims']} that cannot be checked (INR {b['unverifiable']['inr']/1e5:.1f} lakh). "
                           "Recovery is decided by Commercial Finance."),
        "buckets": b, "recover_inr": r["recover_inr"], "recover_per_year_inr": r["recover_per_year_inr"], "window": r["window"],
        "clause": "CO-POL-014 5.2, 5.4, 5.5 (claim window, invoice, quantity)", "source": "expiry_claims.csv, primary_sales.csv, batch_master.csv",
    }
    code = stockist_code.strip().upper()
    if code:
        rows = [s for s in r["by_stockist"] if s["stockist_code"] == code]
        out["stockist"] = rows[0] if rows else {"stockist_code": code, "claims": 0, "recover_inr": 0.0, "note": "no credited claim against a clear rule"}
        out["stockist_claims"] = [c for c in r["claims"] if c["stockist_code"] == code][:15]
    else:
        out["top_stockists"] = [{k: s[k] for k in ("stockist_code", "stockist_name", "cnf", "claims", "recover_inr")} for s in r["by_stockist"][:10]]
    return out


TOOLS = [lookup_batch, validate_claim, get_at_risk_stock, check_scheme_eligibility, detect_quarter_spike, get_fill_rate, get_stockist_summary,
         get_stock_cover, get_dispatch_quality, get_scheme_cap, get_recovery_summary]
