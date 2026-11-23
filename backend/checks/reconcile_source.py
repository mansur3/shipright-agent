"""
Independent source-to-metric reconciliation.

Re-computes key figures straight from the original CSVs in data-pack/data using only the standard library (it does NOT import
agent.clean, agent.analysis or agent.recovery to calculate), then compares them with what the application reports.
A row is OK when the two agree. Disagreements are reported, never hidden or adjusted.

Run:  python -m checks.reconcile_source        (from backend/)
"""
from __future__ import annotations

import csv
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data"      # backend/data is a copy of data-pack/data
FORMATS = ("%d-%m-%Y", "%Y-%m-%d", "%d-%b-%Y")


def pdate(s: str) -> date | None:
    s = (s or "").strip()
    for f in FORMATS:
        try:
            return datetime.strptime(s, f).date()
        except ValueError:
            continue
    return None


def num(s: str) -> float:
    s = (s or "").replace(",", "").strip()
    try:
        return float(s)
    except ValueError:
        return 0.0


CODE_FIELDS = ("stockist_code", "cnf_code", "sku_code", "batch_no")


def rows(name: str) -> list[dict]:
    """Rows as in the file, except code fields are trimmed and upper-cased and blank, '-' and 'NA' scheme codes are one value: the raw files carry 'stk0039' and 'STK0039 ' for one stockist."""
    with open(DATA / name, newline="", encoding="utf-8-sig") as f:
        out = []
        for r in csv.DictReader(f):
            r = {k: (v or "").strip() for k, v in r.items()}
            for k in CODE_FIELDS:
                if k in r:
                    r[k] = r[k].upper()
            if "scheme_code" in r and r["scheme_code"].upper() in ("", "-", "NA", "N/A"):
                r["scheme_code"] = "NA"   # blank, '-' and 'NA' all mean no scheme
            out.append(r)
        return out


def fy_quarter(d: date) -> str:
    """Indian fiscal year (Apr to Mar): FY25 = Apr 2024 to Mar 2025. Quarter 1 = Apr to Jun."""
    fy = d.year + 1 if d.month >= 4 else d.year
    q = ((d.month - 4) % 12) // 3 + 1
    return f"FY{str(fy)[2:]}Q{q}"


def compute() -> list[dict]:
    out: list[dict] = []

    def add(name: str, independent, app, tol: float = 0.0, note: str = "") -> None:
        ok = abs(independent - app) <= tol if isinstance(independent, (int, float)) else independent == app
        out.append({"check": name, "independent": independent, "application": app, "ok": bool(ok), "note": note})

    from agent import analysis, recovery
    from agent.clean import get_clean
    C = get_clean()

    sales_raw = rows("primary_sales.csv")
    claims_raw = rows("expiry_claims.csv")
    batches = {r["batch_no"]: r for r in rows("batch_master.csv")}
    skus = {r["sku_code"]: r for r in rows("sku_master.csv")}

    # 1. repeats
    seen, sales = set(), []
    for r in sales_raw:
        k = tuple(r.values())
        if k in seen:
            continue
        seen.add(k)
        sales.append(r)
    add("primary_sales rows after removing exact repeats", len(sales), len(C.sales), note=f"raw {len(sales_raw)}; {len(sales_raw) - len(sales)} exact repeats")
    seen, claims = set(), []
    for r in claims_raw:
        k = tuple(r.values())
        if k in seen:
            continue
        seen.add(k)
        claims.append(r)
    add("expiry_claims rows after removing identical repeats", len(claims), len(C.claims), note=f"raw {len(claims_raw)}")

    # 2. primary sales by quarter (at PTS) and the 3% cap
    prim, free = defaultdict(float), defaultdict(float)
    for r in sales:
        q = fy_quarter(pdate(r["invoice_date"]))
        pts = num(r["pts_inr"])
        prim[q] += num(r["invoiced_qty"]) * pts
        free[q] += num(r["free_qty"]) * pts
    app_foc = {x["quarter"]: x for x in analysis.foc_by_quarter()}
    for q in sorted(app_foc):
        add(f"primary sales {q} (INR, at PTS)", round(prim[q]), round(app_foc[q]["primary_inr"]), tol=1)
    over = {q: max(0.0, free[q] - 0.03 * prim[q]) for q in prim}
    last4 = sorted(prim)[-4:]
    add("free goods above 3% cap, last 4 quarters (INR)", round(sum(over[q] for q in last4)), round(sum(app_foc[q]["over_cap_inr"] for q in last4)), tol=5)
    add("free goods above 3% cap, all quarters (INR)", round(sum(over.values())), round(sum(x["over_cap_inr"] for x in app_foc.values())), tol=10)

    # 3. claims register
    cr = [r for r in claims if r["status"].strip() == "Credited"]
    pend = [r for r in claims if r["status"].strip() == "Pending"]
    add("credited claims (count)", len(cr), sum(1 for c in C.claims if c["status"] == "Credited"))
    add("credited value as stated in the file (INR)", round(sum(num(r["credit_value_inr"]) for r in cr)),
        round(sum(c["credit_eff"] for c in C.claims if c["status"] == "Credited")), tol=1000,
        note="the application fills a blank credit value from the claim value; a small gap is that fill")
    add("pending claims (count)", len(pend), sum(1 for c in C.claims if c["status"] == "Pending"))

    # 4. late claims: credited more than 90 days after batch expiry (CO-POL-014 5.2), recomputed from the batch master only
    late_inr, n_late = 0.0, 0
    for r in cr:
        bm = batches.get(r["batch_no"])
        cd = pdate(r["claim_date"])
        if bm and cd and cd > pdate(bm["expiry_date"]) + timedelta(days=90):
            late_inr += num(r["credit_value_inr"])
            n_late += 1
    rec = recovery.build()
    app_late = [c for c in rec["claims"] if c["status"] == "Credited" and c["rule_id"] == "R_LATE_AFTER_EXPIRY"]
    app_late_inr = sum(c["amount_inr"] for c in app_late)
    add("claims credited over 90 days after batch expiry (count)", n_late, len(app_late), tol=3, note="application tier T1 rule R_LATE_AFTER_EXPIRY; tolerance 3 claims")
    add("claims credited over 90 days after batch expiry (INR)", round(late_inr), round(app_late_inr), tol=0.05 * app_late_inr, note="tolerance 5%; the application replays claims in date order and applies the quantity rule first")

    # 5. recovery bucket arithmetic
    b = rec["buckets"]
    add("T1 + T2 equals recover_inr", round(b["recover_t1"]["inr"] + b["recover_t2"]["inr"], 2), rec["recover_inr"], tol=0.01)
    add("by-stockist rows sum to recover_inr", round(sum(s["recover_inr"] for s in rec["by_stockist"]), 2), rec["recover_inr"], tol=1)

    # 6. ordered but not invoiced (all quarters), at PTS
    unf = defaultdict(float)
    for r in sales:
        unf[fy_quarter(pdate(r["invoice_date"]))] += max(0.0, num(r["ordered_qty"]) - num(r["invoiced_qty"])) * num(r["pts_inr"])
    out.append({"check": "ordered minus invoiced, last 4 quarters (INR crore, at PTS)", "independent": round(sum(unf[q] for q in last4) / 1e7, 2),
                "application": "not computed in the application", "ok": True, "note": "ledger quotes INR 39.9 crore (ceiling, order padding possible); reported for reference, not an opportunity"})

    # 7. PTS consistency
    bad = sum(1 for r in sales if abs(num(r["pts_inr"]) - num(skus[r["sku_code"]]["pts_inr"])) > 0.005)
    add("invoice lines whose PTS differs from sku_master", bad, 0)
    return out


def main() -> int:
    res = compute()
    for r in res:
        flag = "OK  " if r["ok"] else "DIFF"
        print(f"  {flag} {r['check']}: independent={r['independent']} application={r['application']}" + (f"  [{r['note']}]" if r["note"] else ""))
    bad = [r for r in res if not r["ok"]]
    print(f"\n  {len(res) - len(bad)}/{len(res)} reconciliations agree")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
