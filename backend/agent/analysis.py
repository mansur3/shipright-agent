"""
Measured analytics on the clean data. Pure Python, cached, no model.
Each function reproduces a finding in verification/05_findings_ledger.md and has a test pinning the ledger value.
"""
from __future__ import annotations

import bisect
from collections import Counter, defaultdict
from datetime import date, timedelta
from functools import lru_cache
from typing import Optional

import config as P
from agent.clean import CNF_CITY, CNF_CODES, fiscal_quarter, get_clean, quarter_end


def _pct(a: float, b: float) -> float:
    return round(100 * a / b, 1) if b else 0.0


# ── fill rate (ledger H18) ────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def fill_rates() -> list[dict]:
    """Per fiscal quarter and C&F. ordered_qty is counted once per (invoice, SKU) line.
    `paid_pct` counts invoiced packs only. `qbr_basis_pct` counts free scheme packs as supplied, which is how the QBR scorecard is built."""
    C = get_clean()
    acc: dict[tuple, dict] = {}
    for ln in C.lines.values():
        q = fiscal_quarter(ln["date"])
        for key in ((q, ln["cnf"]), (q, "ALL")):
            a = acc.setdefault(key, {"quarter": key[0], "cnf_code": key[1], "lines": 0, "ordered": 0.0, "invoiced": 0.0, "free": 0.0,
                                     "full_lines": 0, "zero_lines": 0, "unfilled_inr": 0.0})
            a["lines"] += 1
            a["ordered"] += ln["ordered"]
            a["invoiced"] += ln["invoiced"]
            a["free"] += ln["free"]
            a["full_lines"] += 1 if ln["invoiced"] >= ln["ordered"] - 1e-9 else 0
            a["zero_lines"] += 0 if ln["supplied"] else 1
            a["unfilled_inr"] += (ln["ordered"] - ln["invoiced"]) * ln["pts"]
    out = []
    for (q, c), a in sorted(acc.items()):
        a["paid_pct"] = _pct(a["invoiced"], a["ordered"])
        a["qbr_basis_pct"] = _pct(a["invoiced"] + a["free"], a["ordered"])
        a["full_lines_pct"] = _pct(a["full_lines"], a["lines"])
        a["zero_lines_pct"] = _pct(a["zero_lines"], a["lines"])
        a["unfilled_inr"] = round(a["unfilled_inr"], 0)
        a["cnf_city"] = CNF_CITY.get(c, "All")
        out.append(a)
    return out


# ── free goods against the 3% cap (H11) ───────────────────────────────────────

@lru_cache(maxsize=1)
def foc_by_quarter() -> list[dict]:
    C = get_clean()
    prim, free = defaultdict(float), defaultdict(float)
    for r in C.sales:
        q = fiscal_quarter(r["date"])
        prim[q] += r["value"]
        free[q] += r["free"] * r["pts"]
    out = []
    for q in sorted(prim):
        over = max(0.0, free[q] - P.SCHEME_FREE_CAP_PCT / 100 * prim[q])
        out.append({"quarter": q, "primary_inr": round(prim[q], 0), "free_inr": round(free[q], 0),
                    "foc_pct": round(100 * free[q] / prim[q], 2), "cap_pct": P.SCHEME_FREE_CAP_PCT,
                    "over_cap": free[q] > P.SCHEME_FREE_CAP_PCT / 100 * prim[q], "over_cap_inr": round(over, 0)})
    return out


# ── quarter phasing (H12) ─────────────────────────────────────────────────────

@lru_cache(maxsize=4)
def phasing(sku: str = "", cnf: str = "") -> list[dict]:
    C = get_clean()
    tot, last9, scheme9, month = defaultdict(float), defaultdict(float), defaultdict(float), defaultdict(float)
    for r in C.sales:
        if sku and r["sku"] != sku:
            continue
        if cnf and r["cnf"] != cnf:
            continue
        q = fiscal_quarter(r["date"])
        tot[q] += r["value"]
        month[(q, ((r["date"].month - 4) % 3) + 1)] += r["value"]
        if (quarter_end(r["date"]) - r["date"]).days <= P.SPIKE_LAST_DAYS - 1:
            last9[q] += r["value"]
            if r["scheme"]:
                scheme9[q] += r["value"]
    return [{"quarter": q, "total_inr": round(tot[q], 0), "month1_pct": _pct(month[(q, 1)], tot[q]), "month2_pct": _pct(month[(q, 2)], tot[q]),
             "month3_pct": _pct(month[(q, 3)], tot[q]), "last9d_pct": _pct(last9[q], tot[q]),
             "scheme_share_of_last9d_pct": _pct(scheme9[q], last9[q])} for q in sorted(tot)]


# ── scheme packs and later claims (H13, H14) ─────────────────────────────────

@lru_cache(maxsize=1)
def scheme_claim_rates() -> dict:
    """Claim rate of packs supplied under a quarter-end scheme against other packs.
    Only batch x stockist groups whose claim window had closed at the data end are used (no censoring)."""
    C = get_clean()
    end = max(r["date"] for r in C.sales)
    sup_s, sup_n = defaultdict(float), defaultdict(float)
    codes_of = defaultdict(Counter)
    for r in C.sales:
        if not r["batch"]:
            continue
        k = (r["stk"], r["batch"])
        (sup_s if r["scheme"] else sup_n)[k] += r["invoiced"] + r["free"]
        if r["scheme"]:
            codes_of[k][r["scheme"]] += r["invoiced"] + r["free"]
    claimed = defaultdict(float)
    for c in C.claims:
        if c["status"] in ("Credited", "Pending") and c["batch_in_master"]:
            claimed[(c["stk"], c["batch"])] += c["qty"]
    keys = [k for k in set(sup_s) | set(sup_n) if C.batches[k[1]]["exp"] + timedelta(days=90) <= end]

    def rate(ks):
        s = sum(sup_s.get(k, 0.0) + sup_n.get(k, 0.0) for k in ks)
        return round(100 * sum(claimed.get(k, 0.0) for k in ks) / s, 2) if s else 0.0

    no = [k for k in keys if sup_s.get(k, 0.0) == 0]
    some = [k for k in keys if sup_s.get(k, 0.0) > 0]

    def lsq(ks):
        sxx = syy = sxy = sxq = syq = 0.0
        for k in ks:
            s, n, q = sup_s.get(k, 0.0), sup_n.get(k, 0.0), claimed.get(k, 0.0)
            sxx += s * s; syy += n * n; sxy += s * n; sxq += s * q; syq += n * q
        det = sxx * syy - sxy * sxy
        return ((sxq * syy - syq * sxy) / det, (syq * sxx - sxq * sxy) / det)

    a, b = lsq(keys)
    ka = [k for k in keys if C.batches[k[1]]["sku"] in P.SCHEME_TIER_A_SKUS]
    aa, bb = lsq(ka)
    coh_s, coh_c = defaultdict(float), defaultdict(float)
    for k in keys:
        if codes_of.get(k):
            base = codes_of[k].most_common(1)[0][0][:-2]
            coh_s[base] += sup_s.get(k, 0.0)
            coh_c[base] += claimed.get(k, 0.0)
    cohorts = {k: round(100 * coh_c[k] / coh_s[k], 2) for k in sorted(coh_s) if coh_s[k] > 0}
    return {"groups_with_closed_window": len(keys), "rate_no_scheme_packs_pct": rate(no), "rate_with_scheme_packs_pct": rate(some),
            "scheme_pack_rate_pct": round(100 * a, 2), "other_pack_rate_pct": round(100 * b, 2),
            "multiple": round(a / b, 2) if b else None, "tier_a_scheme_pack_rate_pct": round(100 * aa, 2),
            "tier_a_other_pack_rate_pct": round(100 * bb, 2), "tier_a_multiple": round(aa / bb, 2) if bb else None,
            "cohort_rates_pct": cohorts, "cohort_low_pct": min(cohorts.values()), "cohort_high_pct": max(cohorts.values()),
            "cohort_mid_pct": round(sum(cohorts.values()) / len(cohorts), 2)}


def scheme_return_estimate(quarter: str) -> dict:
    """Expected claims still to come from the scheme packs of one fiscal quarter, at PTS. An estimate with a range, not a measurement."""
    C = get_clean()
    rates = scheme_claim_rates()
    val = 0.0
    packs = 0.0
    for r in C.sales:
        if r["scheme"] and r["batch"] and fiscal_quarter(r["date"]) == quarter:
            packs += r["invoiced"] + r["free"]
            val += (r["invoiced"] + r["free"]) * r["pts"]
    lo, hi, mid = rates["cohort_low_pct"], rates["cohort_high_pct"], rates["cohort_mid_pct"]
    return {"quarter": quarter, "scheme_packs": round(packs), "scheme_supply_inr": round(val), "expected_return_low_inr": round(val * lo / 100),
            "expected_return_mid_inr": round(val * mid / 100), "expected_return_high_inr": round(val * hi / 100),
            "basis": f"claim rate of earlier scheme cohorts, {lo}% to {hi}% of scheme packs (primary_sales + expiry_claims)", "kind": "estimate"}


# ── stock cover and allocation (H19, H20) ─────────────────────────────────────

def stock_cover(on: Optional[date] = None) -> dict:
    """Months of cover = stock on hand / avg_monthly_outward_packs (the extract's own figure), per C&F and SKU, at one month-end.
    Also lists SKUs a C&F has none of while other C&Fs hold spare stock, at PTS."""
    C = get_clean()
    d = on or C.snapshot_dates[-1]
    stock, outw = defaultdict(float), {}
    for (dd, c, s), q in C.stock.items():
        if dd == d:
            stock[(c, s)] = q
            outw[(c, s)] = C.outward[(dd, c, s)]
    nat_s = sum(stock.values())
    nat_o = sum(outw.values())
    by_cnf = []
    for c in CNF_CODES:
        s_tot = sum(v for (cc, s), v in stock.items() if cc == c)
        o_tot = sum(v for (cc, s), v in outw.items() if cc == c)
        zero = [s for s in C.skus if stock.get((c, s), 0.0) == 0.0]
        by_cnf.append({"cnf_code": c, "cnf_city": CNF_CITY[c], "stock_inr": round(sum(stock.get((c, s), 0.0) * C.pts(s) for s in C.skus)),
                       "cover_months": round(s_tot / o_tot, 1) if o_tot else None, "share_of_stock_pct": _pct(s_tot, nat_s),
                       "share_of_outward_pct": _pct(o_tot, nat_o), "skus_with_no_stock": len(zero)})
    net_cover = nat_s / nat_o if nat_o else 0
    over = under = 0.0
    spare_for_zero: dict[str, dict] = {}
    for c in CNF_CODES:
        for s in C.skus:
            have, need = stock.get((c, s), 0.0), net_cover * outw.get((c, s), 0.0)
            (over if have > need else None)
            if have > need:
                over += (have - need) * C.pts(s)
            else:
                under += (need - have) * C.pts(s)
    for c in CNF_CODES:
        for s in C.skus:
            if stock.get((c, s), 0.0) == 0.0 and outw.get((c, s), 0.0) > 0:
                spare = sum(max(0.0, stock.get((c2, s), 0.0) - P.COVER_FLOOR_MONTHS * outw.get((c2, s), 0.0)) for c2 in CNF_CODES if c2 != c)
                if spare > 0:
                    e = spare_for_zero.setdefault(c, {"cnf_city": CNF_CITY[c], "skus_lacking": 0, "spare_stock_elsewhere_inr": 0.0, "months_of_own_outward": []})
                    e["skus_lacking"] += 1
                    e["spare_stock_elsewhere_inr"] += spare * C.pts(s)
                    e["months_of_own_outward"].append(spare / outw[(c, s)])
    for c, e in spare_for_zero.items():
        m = sorted(e.pop("months_of_own_outward"))
        e["spare_stock_elsewhere_inr"] = round(e["spare_stock_elsewhere_inr"])
        e["spare_covers_months_of_this_cnfs_own_outward"] = round(m[len(m) // 2], 1)
    return {"as_of": d.isoformat(), "network_cover_months": round(net_cover, 1), "by_cnf": by_cnf,
            "stock_above_network_cover_inr": round(over), "stock_below_network_cover_inr": round(under),
            "cnfs_lacking_skus_that_other_cnfs_hold_spare": spare_for_zero,
            "source": "cnf_stock_snapshot.csv (rows with the same batch summed), sku_master.csv", "note": "cover uses the extract's avg_monthly_outward_packs"}


def unfilled_shortfall(months: int = 6) -> dict:
    """Shortage to one month of cover at the last `months` month-ends, split into what spare stock elsewhere could meet (allocation) and the rest."""
    C = get_clean()
    dates = C.snapshot_dates[-months:]
    alloc = rest = 0.0
    for d in dates:
        for s in C.skus:
            for c in CNF_CODES:
                o = C.outward.get((d, c, s), 0.0)
                if o <= 0:
                    continue
                need = max(0.0, P.COVER_FLOOR_MONTHS * o - C.stock.get((d, c, s), 0.0))
                if need <= 0:
                    continue
                spare = sum(max(0.0, C.stock.get((d, c2, s), 0.0) - P.COVER_FLOOR_MONTHS * C.outward.get((d, c2, s), 0.0)) for c2 in CNF_CODES if c2 != c)
                cov = min(need, spare)
                alloc += cov * C.pts(s)
                rest += (need - cov) * C.pts(s)
    return {"month_ends": [d.isoformat() for d in dates], "shortfall_inr": round(alloc + rest), "allocation_fixable_inr": round(alloc),
            "not_coverable_inr": round(rest), "allocation_fixable_pct": _pct(alloc, alloc + rest)}


# ── at-risk stock, latest snapshot only (H22) ─────────────────────────────────

def at_risk_stock(days: int = 180, cnf: str = "") -> dict:
    """Stock on hand at the LATEST month-end with expiry within `days`. Earlier snapshots are history, not stock on hand today."""
    C = get_clean()
    d = C.snapshot_dates[-1]
    rows = []
    for r in C.snapshots:
        if r["date"] != d or not r["batch"] or r["qty"] <= 0 or not r["exp"]:
            continue
        if cnf and r["cnf"] != cnf:
            continue
        left = (r["exp"] - d).days
        if left < 0 or left > days:
            continue
        months_left = left / 30.4
        sell = max(0.0, months_left - P.BLOCK_MONTHS) * r["outw"]
        older = sum(x["qty"] for x in C.snapshots if x["date"] == d and x["cnf"] == r["cnf"] and x["sku"] == r["sku"]
                    and x["batch"] and x["exp"] and x["exp"] < r["exp"])
        unsold = max(0.0, r["qty"] - max(0.0, sell - older))
        rows.append({"cnf_code": r["cnf"], "cnf_city": CNF_CITY[r["cnf"]], "sku_code": r["sku"], "product": C.skus[r["sku"]]["description"],
                     "batch_no": r["batch"], "expiry_date": r["exp"].isoformat(), "days_to_expiry": left, "qty_packs": r["qty"],
                     "pts_inr": C.pts(r["sku"]), "value_inr": round(r["qty"] * C.pts(r["sku"]), 2), "avg_monthly_outward": r["outw"],
                     "unsold_before_block_packs": round(unsold), "recommend_redistribute": unsold > 0.5 * r["qty"]})
    rows.sort(key=lambda x: x["days_to_expiry"])
    return {"as_of": d.isoformat(), "within_days": days, "batches": rows, "total_batches": len(rows),
            "total_value_inr": round(sum(x["value_inr"] for x in rows), 2),
            "source": "cnf_stock_snapshot.csv latest month-end only"}


# ── dispatch quality: FEFO and residual shelf life (H27, H29) ─────────────────

@lru_cache(maxsize=1)
def fefo_breaches() -> list[dict]:
    """A later-expiry batch was shipped while an older batch of the same SKU sat at the same C&F at both neighbouring month-ends
    (older by more than 90 days). Per C&F and fiscal quarter."""
    C = get_clean()
    dates = C.snapshot_dates
    held: dict[tuple, dict] = defaultdict(dict)
    for r in C.snapshots:
        if r["batch"] and r["qty"] > 0:
            held[(r["date"], r["cnf"], r["sku"])][r["batch"]] = r["qty"]
    cell = defaultdict(lambda: [0, 0, 0.0])
    for r in C.sales:
        if not r["batch"] or r["invoiced"] <= 0:
            continue
        i = bisect.bisect_right(dates, r["date"])
        if i == 0 or i >= len(dates):
            continue
        p, n = dates[i - 1], dates[i]
        if (n - p).days > 95:
            continue
        sp, sn = held.get((p, r["cnf"], r["sku"]), {}), held.get((n, r["cnf"], r["sku"]), {})
        shipped = C.batches[r["batch"]]["exp"]
        older = [b for b in sp if b in sn and C.batches[b]["exp"] < shipped - timedelta(days=90)]
        k = (r["cnf"], fiscal_quarter(r["date"]))
        cell[k][0] += 1
        if older:
            cell[k][1] += 1
            cell[k][2] += r["invoiced"] * r["pts"]
    return [{"cnf_code": c, "cnf_city": CNF_CITY[c], "quarter": q, "lines": v[0], "breach_lines": v[1], "breach_pct": _pct(v[1], v[0]),
             "shipped_out_of_order_inr": round(v[2])} for (c, q), v in sorted(cell.items(), key=lambda kv: (kv[0][1], kv[0][0]))]


@lru_cache(maxsize=1)
def short_dated_dispatch() -> dict:
    """Invoice rows dispatched with less than 60% of the SKU's shelf life left (policy 7.1)."""
    C = get_clean()
    rows = under = 0
    val = 0.0
    by_cnf = defaultdict(lambda: [0, 0])
    for r in C.sales:
        if not r["batch"]:
            continue
        b = C.batches[r["batch"]]
        rsl = (b["exp"] - r["date"]).days / (C.skus[r["sku"]]["shelf_months"] * 30.4375)
        rows += 1
        by_cnf[r["cnf"]][0] += 1
        if rsl < P.MIN_RSL_PCT:
            under += 1
            val += r["value"]
            by_cnf[r["cnf"]][1] += 1
    return {"rows": rows, "rows_under_60pct": under, "share_pct": _pct(under, rows), "value_inr": round(val),
            "by_cnf_pct": {c: _pct(v[1], v[0]) for c, v in sorted(by_cnf.items())}, "clause": "CO-POL-014 7.1 (p4)"}


# ── scheme gate for one stockist and SKU (policy 4.5, Annex B) ────────────────

@lru_cache(maxsize=1)
def _monthly_purchases() -> dict:
    C = get_clean()
    paid, free = defaultdict(float), defaultdict(float)
    for r in C.sales:
        k = (r["stk"], r["sku"], r["date"].year * 12 + r["date"].month - 1)
        paid[k] += r["invoiced"]
        free[k] += r["free"]
    return {"paid": paid, "free": free}


def scheme_gate(stockist: str, sku: str) -> dict:
    """What the extracts can and cannot say before a quarter-end scheme order is accepted from a stockist.
    There is no secondary data, so closing stock (4.5) cannot be known: the gate flags, the RSM confirms."""
    C = get_clean()
    stk, sk = stockist.strip().upper(), sku.strip().upper().replace("-", "")
    if stk not in C.stockists:
        return {"found": False, "stockist_code": stockist}
    if sk not in C.skus:
        return {"found": False, "sku_code": sku}
    m = _monthly_purchases()
    end = max(r["date"] for r in C.sales)
    e = end.year * 12 + end.month - 1
    recent = [e - i for i in range(3)]
    before = [e - 3 - i for i in range(9)]
    paid_recent = sum(m["paid"].get((stk, sk, x), 0.0) for x in recent)
    free_recent = sum(m["free"].get((stk, sk, x), 0.0) for x in recent)
    base = sum(m["paid"].get((stk, sk, x), 0.0) for x in before) / 9
    # three months of purchases at the normal rate is 3 x base; only what is taken above that adds stock to the stockist's godown
    added = (paid_recent + free_recent) / base - 3 if base else None
    rates = scheme_claim_rates()
    sup = claimed = 0.0
    for r in C.sales:
        if r["stk"] == stk and r["sku"] == sk and r["batch"] and r["scheme"]:
            b = C.batches[r["batch"]]
            if b["exp"] + timedelta(days=90) <= end:
                sup += r["invoiced"] + r["free"]
    for c in C.claims:
        if c["stk"] == stk and c["sku"] == sk and c["batch_in_master"] and c["status"] in ("Credited", "Pending") and C.batches[c["batch"]]["exp"] + timedelta(days=90) <= end:
            claimed += c["qty"]
    hist = round(100 * claimed / sup, 1) if sup else None
    reasons = []
    if base == 0:
        reasons.append("no purchases of this SKU in the 9 months before the last quarter: normal monthly purchase unknown")
    elif added > P.SCHEME_STOCK_NORM_MONTHS:
        reasons.append(f"the last 3 months of invoices are {added:.1f} months of normal purchase above this stockist's usual flow (stock norm {P.SCHEME_STOCK_NORM_MONTHS} months)")
    if hist is not None and hist > 2 * rates["scheme_pack_rate_pct"]:
        reasons.append(f"{hist}% of this stockist's earlier scheme packs of this SKU came back as claims, against {rates['scheme_pack_rate_pct']}% for all stockists")
    return {"found": True, "stockist_code": stk, "stockist_name": C.stockists[stk]["name"], "sku_code": sk, "product": C.skus[sk]["description"],
            "decision": "NEEDS RSM CONFIRMATION" if reasons else "NO FLAG FROM THE EXTRACTS", "eligible": None, "reasons": reasons,
            "normal_monthly_purchase_packs": round(base), "last_3_months_packs_paid_and_free": round(paid_recent + free_recent),
            "months_above_normal_flow": round(added, 1) if added is not None else None,
            "own_scheme_pack_claim_rate_pct": hist, "network_scheme_pack_claim_rate_pct": rates["scheme_pack_rate_pct"],
            "note": "No secondary sales exist, so closing stock cannot be measured (policy 4.5). The RSM confirms with the stockist before booking the order.",
            "clause": "CO-POL-014 4.5 (p3)", "source": "primary_sales.csv, expiry_claims.csv"}
