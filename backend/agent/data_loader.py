"""
Single point of data access.  All CSV reads go through here.
The LLM never touches this layer — only tools do.
"""
from __future__ import annotations

import csv
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

DATA = Path(__file__).resolve().parent.parent / "data"


def _parse_date(s: str) -> datetime | None:
    for fmt in ["%d-%m-%Y", "%Y-%m-%d", "%d-%b-%Y", "%b-%Y"]:
        try:
            return datetime.strptime(s.strip(), fmt)
        except ValueError:
            pass
    return None


def _num(s: str) -> float:
    try:
        return float(str(s).replace(",", "").strip())
    except (ValueError, AttributeError):
        return 0.0


# ── Loaders (cached for the lifetime of the process) ─────────────────────────

@lru_cache(maxsize=1)
def load_sku_master() -> dict[str, dict]:
    with open(DATA / "sku_master.csv", newline="", encoding="utf-8") as f:
        return {r["sku_code"].strip(): r for r in csv.DictReader(f)}


@lru_cache(maxsize=1)
def load_batch_master() -> dict[str, dict]:
    skus = load_sku_master()
    with open(DATA / "batch_master.csv", newline="", encoding="utf-8") as f:
        out: dict[str, dict] = {}
        for r in csv.DictReader(f):
            code = r["sku_code"].strip().upper()
            key = r["batch_no"].strip().upper()
            out[key] = {**skus.get(code, {}), **r, "sku_code": code}
    return out


@lru_cache(maxsize=1)
def load_stockist_master() -> dict[str, dict]:
    with open(DATA / "stockist_master.csv", newline="", encoding="utf-8") as f:
        return {r["stockist_code"].strip().upper(): r for r in csv.DictReader(f)}


@lru_cache(maxsize=1)
def load_primary_sales() -> list[dict]:
    with open(DATA / "primary_sales.csv", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


@lru_cache(maxsize=1)
def load_expiry_claims() -> list[dict]:
    with open(DATA / "expiry_claims.csv", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


@lru_cache(maxsize=1)
def load_cnf_snapshot() -> list[dict]:
    with open(DATA / "cnf_stock_snapshot.csv", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


@lru_cache(maxsize=1)
def load_claim_emails() -> list[dict]:
    with open(DATA / "claim_emails.csv", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


# ── Derived indices (also cached) ─────────────────────────────────────────────

@lru_cache(maxsize=1)
def invoiced_per_stockist_batch() -> dict[tuple[str, str], dict]:
    """
    Returns {(stockist_code_upper, batch_no_upper): {qty, value, dates, free_qty}}
    Used for claim validation (§5.5 quantity limit).
    """
    from collections import defaultdict
    idx: dict = defaultdict(lambda: {"qty": 0.0, "free_qty": 0.0, "value": 0.0, "dates": []})
    for r in load_primary_sales():
        k = (r["stockist_code"].strip().upper(), r["batch_no"].strip().upper())
        idx[k]["qty"] += _num(r["invoiced_qty"])
        idx[k]["free_qty"] += _num(r["free_qty"])
        idx[k]["value"] += _num(r["net_value_inr"])
        d = _parse_date(r["invoice_date"])
        if d:
            idx[k]["dates"].append(d)
    return dict(idx)


@lru_cache(maxsize=1)
def credited_claims_index() -> dict[tuple[str, str, str], list[dict]]:
    """
    Returns {(stockist_upper, batch_upper, sku_upper): [claim_rows]}
    for all Credited claims.  Used for duplicate detection.
    """
    from collections import defaultdict
    idx: dict = defaultdict(list)
    for r in load_expiry_claims():
        if r["status"].strip() == "Credited":
            k = (
                r["stockist_code"].strip().upper(),
                r["batch_no"].strip().upper(),
                r["sku_code"].strip().upper(),
            )
            idx[k].append(r)
    return dict(idx)


@lru_cache(maxsize=1)
def avg_monthly_purchase_per_stockist_sku(months: int = 3) -> dict[tuple[str, str], float]:
    """
    Average monthly qty invoiced per (stockist_upper, sku_upper) over last `months` months.
    Uses the most recent 3 calendar months in the sales data.
    """
    from collections import defaultdict

    sales = load_primary_sales()
    dates = [_parse_date(r["invoice_date"]) for r in sales if _parse_date(r["invoice_date"])]
    if not dates:
        return {}
    cutoff = max(dates)

    # find start of the period
    m = cutoff.month - months
    y = cutoff.year
    while m <= 0:
        m += 12
        y -= 1
    period_start = datetime(y, m, 1)

    idx: dict = defaultdict(float)
    for r in sales:
        d = _parse_date(r["invoice_date"])
        if not d or d < period_start:
            continue
        k = (r["stockist_code"].strip().upper(), r["sku_code"].strip().upper())
        idx[k] += _num(r["invoiced_qty"]) + _num(r["free_qty"])

    return {k: v / months for k, v in idx.items()}


# ── Convenience look-ups used by tools ────────────────────────────────────────

def batch_info(batch_no: str) -> dict:
    row = load_batch_master().get(batch_no.strip().upper())
    if not row:
        return {"found": False, "batch_no": batch_no}
    return {"found": True, **row}


def stockist_info(stockist_code: str) -> dict:
    row = load_stockist_master().get(stockist_code.strip().upper())
    if not row:
        return {"found": False, "stockist_code": stockist_code}
    return {"found": True, **row}
