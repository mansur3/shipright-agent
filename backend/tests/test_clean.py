"""
Clean data layer. Every expected number below was produced by verification/a4_dq_final.py
and ties to the Q1 FY27 QBR (docs/ledger: verification/04_data_quality.md).
"""
from collections import defaultdict
from datetime import date

import pytest

from agent.clean import fiscal_quarter, get_clean, norm_cnf, norm_inv, norm_sku, parse_date, quarter_end

C = get_clean()


class TestPrimitives:
    def test_three_date_formats(self):
        assert parse_date("18-04-2024") == date(2024, 4, 18)
        assert parse_date("2024-04-18") == date(2024, 4, 18)
        assert parse_date("18-Apr-2024") == date(2024, 4, 18)
        assert parse_date("") is None and parse_date("garbage") is None

    def test_code_normalisers(self):
        assert norm_sku("PFL-1501") == "PFL1501" and norm_sku(" pfl1501 ") == "PFL1501"
        assert norm_inv("INV-S02/2404/002127") == "INV/S02/2404/002127"
        assert norm_cnf("CFN02") == "CF-N02" and norm_cnf("cf-e01") == "CF-E01"

    def test_fiscal_quarter(self):
        assert fiscal_quarter(date(2026, 6, 30)) == "FY27Q1"
        assert fiscal_quarter(date(2026, 1, 15)) == "FY26Q4"
        assert fiscal_quarter(date(2024, 4, 1)) == "FY25Q1"
        assert quarter_end(date(2026, 5, 3)) == date(2026, 6, 30)
        assert quarter_end(date(2026, 2, 3)) == date(2026, 3, 31)
        assert quarter_end(date(2025, 11, 3)) == date(2025, 12, 31)


class TestRowCounts:
    def test_sales_repeats_dropped(self):
        assert C.log["sales_raw"] == 93809
        assert len(C.sales) == 93063 and C.log["sales_exact_repeats_dropped"] == 746

    def test_claim_repeats_dropped(self):
        assert C.log["claims_raw"] == 4526 and len(C.claims) == 4503
        assert len({c["claim_no"] for c in C.claims}) == 4503

    def test_snapshot_rows_summed(self):
        assert C.log["snapshot_raw"] == 5015 and len(C.snapshots) == 4163

    def test_masters(self):
        assert len(C.skus) == 36 and len(C.batches) == 663 and len(C.stockists) == 156


class TestCodesAreClean:
    def test_all_claim_skus_valid(self):
        assert all(c["sku"] in C.skus for c in C.claims)

    def test_all_cnf_codes_valid(self):
        valid = {"CF-N01", "CF-N02", "CF-E01", "CF-W01", "CF-S01", "CF-S02"}
        assert all(r["cnf"] in valid for r in C.sales)
        assert all(r["cnf"] in valid for r in C.snapshots)
        assert all(c["cnf"] in valid for c in C.claims)

    def test_hyphenated_invoice_refs_resolve(self):
        assert sum(1 for c in C.claims if c["inv_in_sales"]) == 2856


class TestLinesAndOrdered:
    def test_ordered_is_per_line_not_summed(self):
        assert all(ln["ordered"] is not None for ln in C.lines.values())
        assert all(ln["invoiced"] <= ln["ordered"] + 1e-9 for ln in C.lines.values())

    def test_blank_batch_lines_are_unsupplied(self):
        blank = [r for r in C.sales if not r["batch"]]
        assert len(blank) == 2628
        assert all(r["invoiced"] == 0 and r["free"] == 0 for r in blank)


class TestClaimsFlags:
    def test_pre_window_count(self):
        assert sum(1 for c in C.claims if c["pre_window"]) == 971
        assert all(c["status"] == "Credited" for c in C.claims if c["pre_window"])

    def test_blank_value_is_derived_from_pts(self):
        derived = [c for c in C.claims if c["value_derived"]]
        assert len(derived) == 135
        assert all(abs(c["value_eff"] - c["qty"] * C.pts(c["sku"])) < 1e-6 for c in derived)


class TestTiesToQBR:
    """The cleaning rules are right only if Finance's own scorecard reproduces."""

    def test_primary_sales_by_quarter(self):
        by = defaultdict(float)
        for r in C.sales:
            by[fiscal_quarter(r["date"])] += r["value"]
        expect = {"FY26Q1": 52.52, "FY26Q2": 51.84, "FY26Q3": 50.42, "FY26Q4": 49.37, "FY27Q1": 51.36}
        for q, cr in expect.items():
            assert round(by[q] / 1e7, 2) == cr

    def test_free_goods_percent_by_quarter(self):
        prim, free = defaultdict(float), defaultdict(float)
        for r in C.sales:
            q = fiscal_quarter(r["date"])
            prim[q] += r["value"]
            free[q] += r["free"] * r["pts"]
        expect = {"FY26Q1": 4.68, "FY26Q2": 3.75, "FY26Q3": 3.47, "FY26Q4": 3.19, "FY27Q1": 3.69}
        for q, pct in expect.items():
            assert round(100 * free[q] / prim[q], 2) == pct

    def test_cfa_inventory_at_pts(self):
        expect = {date(2025, 6, 30): 17.49, date(2025, 9, 30): 15.35, date(2025, 12, 31): 13.89,
                  date(2026, 3, 31): 13.14, date(2026, 6, 30): 14.05}
        for d, cr in expect.items():
            v = sum(r["qty"] * C.pts(r["sku"]) for r in C.snapshots if r["date"] == d)
            assert round(v / 1e7, 2) == cr

    def test_expiry_claims_logged_by_quarter(self):
        by = defaultdict(float)
        for c in C.claims:
            if c["type"] in ("Near expiry", "Expired"):
                by[fiscal_quarter(c["cdate"])] += c["value_eff"]
        expect = {"FY26Q1": 0.62, "FY26Q2": 0.85, "FY26Q3": 1.21, "FY26Q4": 1.15, "FY27Q1": 1.41}
        for q, cr in expect.items():
            assert round(by[q] / 1e7, 2) == cr

    def test_fill_rate_matches_qbr_only_with_free_packs(self):
        by_o, by_i, by_f = defaultdict(float), defaultdict(float), defaultdict(float)
        for ln in C.lines.values():
            q = fiscal_quarter(ln["date"])
            by_o[q] += ln["ordered"]
            by_i[q] += ln["invoiced"]
            by_f[q] += ln["free"]
        assert round(100 * (by_i["FY27Q1"] + by_f["FY27Q1"]) / by_o["FY27Q1"], 1) == pytest.approx(90.8, abs=0.1)
        assert round(100 * by_i["FY27Q1"] / by_o["FY27Q1"], 1) == pytest.approx(88.0, abs=0.1)


class TestRawCodeDirt:
    """Raw claims carry trailing spaces on stockist codes and lower-case batch codes. If cleaning misses them, over-supply and repeat
    counts are wrong (found in the 22 Nov independent recheck: 141 false over-supply claims)."""

    def test_no_claim_code_is_untrimmed_or_lowercase(self):
        assert all(c["stk"] == c["stk"].strip().upper() for c in C.claims)
        assert all(c["batch"] == c["batch"].strip().upper() for c in C.claims)

    def test_known_padded_stockist_claim_is_matched_to_its_supply(self):
        # raw row: 'STK0106 ' (trailing space), batch A2460246, 16 packs; 2,436 packs of the batch were invoiced to STK0106
        c = next(c for c in C.claims if c["claim_no"] == "CLM-2407-04080")
        assert c["stk"] == "STK0106" and c["batch"] == "A2460246"
        assert C.supply[("STK0106", "A2460246")] == 2436.0

    def test_lowercase_batch_claims_resolve_to_the_batch_master(self):
        lower = [c for c in C.claims if c["claim_no"] in {"CLM-2407-04057", "CLM-2409-04252", "CLM-2410-04009"}]
        assert len(lower) == 3 and all(c["batch"] in C.batches for c in lower)

    def test_unverifiable_count_needs_batch_normalisation(self):
        credited = [c for c in C.claims if c["status"] == "Credited"]
        assert sum(1 for c in credited if c["batch"] not in C.batches) == 971
