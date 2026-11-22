"""
Single clean data layer. Every tool, the batch and the claim checker read from here.

Cleaning rules (each one validated against the pack; see verification/04_data_quality.md):
  S1  drop exact repeated rows inside an (invoice, SKU) line in primary_sales
  S3  ordered_qty belongs to the (invoice, SKU) line, never summed across rows
  C1  claims: strip the hyphen in SKU codes (PFL-1501 -> PFL1501)
  C2  claims: INV-S02/... -> INV/S02/...
  C3  claims: drop a repeated claim number only if the content is identical
  C4  claims: blank claim value is derived as qty x PTS and flagged
  C5  claims on batches missing from batch_master are flagged pre_window (older than the extract)
  N1  snapshot: CFA codes without a hyphen (CFN02) become CF-N02
  N2  snapshot: rows sharing (date, CFA, SKU, batch) are separate pallets or bins and are summed
Cleaned totals tie to the QBR: primary sales by quarter, CFA inventory at PTS, free goods %.
"""
from __future__ import annotations

import csv
import re
from datetime import date, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

DATA = Path(__file__).resolve().parent.parent / "data"
DATE_FORMATS = ("%d-%m-%Y", "%Y-%m-%d", "%d-%b-%Y", "%b-%Y", "%d/%m/%Y")
CNF_CODES = ("CF-N01", "CF-N02", "CF-E01", "CF-W01", "CF-S01", "CF-S02")
CNF_CITY = {"CF-N01": "Gurugram", "CF-N02": "Lucknow", "CF-E01": "Kolkata",
            "CF-W01": "Bhiwandi", "CF-S01": "Chennai", "CF-S02": "Hyderabad"}


# ── primitives ────────────────────────────────────────────────────────────────

def parse_date(s: Any) -> date | None:
    s = (str(s) if s is not None else "").strip()
    if not s:
        return None
    for f in DATE_FORMATS:
        try:
            return datetime.strptime(s, f).date()
        except ValueError:
            pass
    return None


def month_end(d: date) -> date:
    y, m = (d.year + 1, 1) if d.month == 12 else (d.year, d.month + 1)
    return date.fromordinal(date(y, m, 1).toordinal() - 1)


def num(s: Any) -> float | None:
    s = (str(s) if s is not None else "").replace(",", "").strip()
    if s == "":
        return None
    try:
        return float(s)
    except ValueError:
        return None


def code(s: Any) -> str:
    return (str(s) if s is not None else "").strip().upper()


def norm_cnf(c: str) -> str:
    m = re.fullmatch(r"CF-?([NESW]\d\d)", code(c))
    return "CF-" + m.group(1) if m else code(c)


def norm_sku(s: str) -> str:
    return code(s).replace("-", "")


def norm_inv(s: Any) -> str:
    s = code(s).replace(" ", "")
    s = re.sub(r"^INV[-_]", "INV/", s)
    return re.sub(r"/{2,}", "/", s)


def fiscal_quarter(d: date) -> str:
    """FY starts in April. FY27 Q1 = Apr-Jun 2026."""
    fy = (d.year + (1 if d.month >= 4 else 0)) % 100
    return f"FY{fy:02d}Q{((d.month - 4) % 12) // 3 + 1}"


def quarter_end(d: date) -> date:
    last_month = [6, 9, 12][(d.month - 4) // 3] if d.month >= 4 else 3
    return month_end(date(d.year, last_month, 1))


def _read(name: str) -> list[dict]:
    with open(DATA / name, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for i, r in enumerate(rows):
        r["_line"] = i + 2          # line in the source file, header = line 1
    return rows


# ── the clean snapshot of the pack ───────────────────────────────────────────

class Clean:
    """Cleaned tables and ready-made indexes. Build once with get_clean()."""

    def __init__(self) -> None:
        self.log: dict[str, Any] = {}
        self._load()

    # -- masters ---------------------------------------------------------------
    def _load(self) -> None:
        self.skus: dict[str, dict] = {}
        for r in _read("sku_master.csv"):
            sk = norm_sku(r["sku_code"])
            self.skus[sk] = {"sku": sk, "description": r["product_description"], "pack": r["pack"],
                             "therapy_area": r["therapy_area"], "shelf_months": num(r["shelf_life_months"]),
                             "pts": num(r["pts_inr"]), "mrp": num(r["mrp_inr"]), "_line": r["_line"]}
        self.batches: dict[str, dict] = {}
        for r in _read("batch_master.csv"):
            b = code(r["batch_no"])
            self.batches[b] = {"batch": b, "sku": norm_sku(r["sku_code"]), "mfg": parse_date(r["mfg_date"]),
                               "exp": parse_date(r["expiry_date"]), "qty": num(r["batch_qty_packs"]), "_line": r["_line"]}
        self.stockists: dict[str, dict] = {}
        for r in _read("stockist_master.csv"):
            s = code(r["stockist_code"])
            self.stockists[s] = {"stk": s, "name": r["stockist_name"], "cnf": norm_cnf(r["cnf_code"]), "city": r["city"],
                                 "state": r["state"], "appointed": parse_date(r["appointed_on"]), "_line": r["_line"]}
        self._load_sales()
        self._load_claims()
        self._load_snapshots()

    # -- primary sales ---------------------------------------------------------
    def _load_sales(self) -> None:
        raw = _read("primary_sales.csv")
        seen: set = set()
        rows: list[dict] = []
        for r in raw:
            row = {"invoice_no": code(r["invoice_no"]), "date": parse_date(r["invoice_date"]), "cnf": norm_cnf(r["cnf_code"]),
                   "stk": code(r["stockist_code"]), "sku": norm_sku(r["sku_code"]), "batch": code(r["batch_no"]),
                   "ordered": num(r["ordered_qty"]), "invoiced": num(r["invoiced_qty"]) or 0.0, "free": num(r["free_qty"]) or 0.0,
                   "pts": num(r["pts_inr"]) or 0.0, "value": num(r["net_value_inr"]) or 0.0, "_line": r["_line"]}
            sc = code(r["scheme_code"])
            row["scheme"] = "" if sc in ("", "NA", "-") else sc
            k = (row["invoice_no"], row["sku"], row["date"], row["batch"], row["ordered"], row["invoiced"], row["free"],
                 row["pts"], row["value"], row["scheme"], row["stk"])
            if k in seen:
                continue
            seen.add(k)
            rows.append(row)
        self.log["sales_raw"] = len(raw)
        self.log["sales_exact_repeats_dropped"] = len(raw) - len(rows)
        self.sales = rows
        # (invoice, sku) lines: ordered once per line
        lines: dict[tuple[str, str], dict] = {}
        for r in rows:
            ln = lines.setdefault((r["invoice_no"], r["sku"]), {"invoice_no": r["invoice_no"], "sku": r["sku"], "ordered": None,
                                  "invoiced": 0.0, "free": 0.0, "cnf": r["cnf"], "stk": r["stk"], "date": r["date"], "pts": r["pts"], "supplied": False})
            if r["ordered"] is not None:
                ln["ordered"] = r["ordered"]
            ln["invoiced"] += r["invoiced"]
            ln["free"] += r["free"]
            if r["batch"]:
                ln["supplied"] = True
        self.lines = lines
        self.supply: dict[tuple[str, str], float] = {}
        self.first_invoice: dict[tuple[str, str], date] = {}
        self.invoice_date: dict[str, date] = {}
        self.invoice_line: dict[str, int] = {}
        self.invoice_batches: dict[str, set] = {}
        self.invoice_stockist: dict[str, str] = {}
        for r in rows:
            self.invoice_line.setdefault(r["invoice_no"], r["_line"])
            self.invoice_date.setdefault(r["invoice_no"], r["date"])
            self.invoice_stockist.setdefault(r["invoice_no"], r["stk"])
            if r["batch"]:
                k = (r["stk"], r["batch"])
                self.supply[k] = self.supply.get(k, 0.0) + r["invoiced"] + r["free"]
                self.invoice_batches.setdefault(r["invoice_no"], set()).add(r["batch"])
                if r["date"] and (k not in self.first_invoice or r["date"] < self.first_invoice[k]):
                    self.first_invoice[k] = r["date"]

    # -- claims ----------------------------------------------------------------
    def _load_claims(self) -> None:
        raw = _read("expiry_claims.csv")
        fields = ("claim_date", "stockist_code", "sku_code", "batch_no", "qty_claimed", "claim_value_inr", "claim_type",
                  "original_invoice_ref", "status", "credit_note_no", "credit_value_inr")
        seen: dict[str, tuple] = {}
        claims: list[dict] = []
        for r in raw:
            sku = norm_sku(r["sku_code"])
            row = {"claim_no": r["claim_no"].strip(), "cdate": parse_date(r["claim_date"]), "stk": code(r["stockist_code"]),
                   "cnf": norm_cnf(r["cnf_code"]), "sku": sku, "batch": code(r["batch_no"]), "exp_c": parse_date(r["expiry_date_as_claimed"]),
                   "qty": num(r["qty_claimed"]) or 0.0, "value": num(r["claim_value_inr"]), "type": r["claim_type"].strip(),
                   "inv": norm_inv(r["original_invoice_ref"]), "status": r["status"].strip(), "verified_by": r["verified_by"].strip(),
                   "cn": r["credit_note_no"].strip(), "cn_date": parse_date(r["credit_note_date"]), "credit": num(r["credit_value_inr"]),
                   "remarks": r["remarks"].strip(), "_line": r["_line"]}
            sig = tuple(r[f] for f in fields)
            if row["claim_no"] in seen and seen[row["claim_no"]] == sig:
                continue
            seen[row["claim_no"]] = sig
            claims.append(row)
        self.log["claims_raw"] = len(raw)
        self.log["claims_repeated_rows_dropped"] = len(raw) - len(claims)
        for r in claims:
            pts = self.skus.get(r["sku"], {}).get("pts") or 0.0
            r["value_derived"] = r["value"] is None
            r["value_eff"] = r["value"] if r["value"] is not None else r["qty"] * pts
            r["credit_eff"] = (r["credit"] or 0.0) if r["status"] == "Credited" else 0.0
            r["batch_in_master"] = r["batch"] in self.batches
            r["pre_window"] = not r["batch_in_master"]
            r["order"] = (r["cdate"] or date.min, r["_line"])
            r["inv_in_sales"] = bool(r["inv"]) and r["inv"] in self.invoice_date
        self.claims = claims
        self._credited_by_batch: dict[tuple[str, str], list[dict]] = {}
        self._pending_by_batch: dict[tuple[str, str], list[dict]] = {}
        for r in sorted(claims, key=lambda x: x["order"]):
            if r["status"] == "Credited":
                self._credited_by_batch.setdefault((r["stk"], r["batch"]), []).append(r)
            elif r["status"] == "Pending":
                self._pending_by_batch.setdefault((r["stk"], r["batch"]), []).append(r)

    def credited_before(self, stk: str, batch: str, before: tuple | None = None) -> list[dict]:
        """Credited claims on this stockist + batch, oldest first, optionally only those strictly before `before`."""
        v = self._credited_by_batch.get((code(stk), code(batch)), [])
        return [c for c in v if before is None or c["order"] < before]

    def pending_for(self, stk: str, batch: str) -> list[dict]:
        """Claims still pending on this stockist + batch. A new claim on the same batch risks a second credit."""
        return list(self._pending_by_batch.get((code(stk), code(batch)), []))

    # -- stock snapshots -------------------------------------------------------
    def _load_snapshots(self) -> None:
        raw = _read("cnf_stock_snapshot.csv")
        groups: dict[tuple, dict] = {}
        for r in raw:
            row = {"date": parse_date(r["snapshot_date"]), "cnf": norm_cnf(r["cnf_code"]), "sku": norm_sku(r["sku_code"]),
                   "batch": code(r["batch_no"]), "exp": parse_date(r["expiry_date"]), "qty": num(r["qty_on_hand_packs"]) or 0.0,
                   "outw": num(r["avg_monthly_outward_packs"]) or 0.0}
            k = (row["date"], row["cnf"], row["sku"], row["batch"])
            if k in groups:
                groups[k]["qty"] += row["qty"]
                groups[k]["n_rows"] += 1
            else:
                row["n_rows"] = 1
                groups[k] = row
        self.log["snapshot_raw"] = len(raw)
        self.log["snapshot_rows_summed"] = len(raw) - len(groups)
        self.snapshots = list(groups.values())
        self.snapshot_dates = sorted({r["date"] for r in self.snapshots})
        self.stock: dict[tuple, float] = {}
        self.outward: dict[tuple, float] = {}
        for r in self.snapshots:
            self.stock[(r["date"], r["cnf"], r["sku"])] = self.stock.get((r["date"], r["cnf"], r["sku"]), 0.0) + r["qty"]
            self.outward[(r["date"], r["cnf"], r["sku"])] = r["outw"]

    # -- convenience -----------------------------------------------------------
    def pts(self, sku: str) -> float:
        return self.skus.get(norm_sku(sku), {}).get("pts") or 0.0


@lru_cache(maxsize=1)
def get_clean() -> Clean:
    return Clean()
