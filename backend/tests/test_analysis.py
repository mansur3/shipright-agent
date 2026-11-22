"""Measured analytics. Every pinned value is in verification/05_findings_ledger.md."""
from datetime import date

import pytest

from agent import analysis as A


def _row(rows, **kw):
    return next(r for r in rows if all(r[k] == v for k, v in kw.items()))


class TestFillRate:
    def test_paid_and_qbr_basis(self):
        r = _row(A.fill_rates(), quarter="FY27Q1", cnf_code="ALL")
        assert r["paid_pct"] == 88.0 and r["qbr_basis_pct"] == 90.8

    def test_latest_quarter_and_lucknow(self):
        assert _row(A.fill_rates(), quarter="FY27Q2", cnf_code="ALL")["paid_pct"] == 82.6
        assert _row(A.fill_rates(), quarter="FY27Q2", cnf_code="CF-N02")["paid_pct"] == 74.6

    def test_unfilled_value_last_four_quarters(self):
        tot = sum(r["unfilled_inr"] for r in A.fill_rates() if r["cnf_code"] == "ALL" and r["quarter"] in ("FY26Q3", "FY26Q4", "FY27Q1", "FY27Q2"))
        assert round(tot / 1e7, 2) == 39.94


class TestFreeGoodsCap:
    def test_quarters_over_the_cap(self):
        by = {r["quarter"]: r for r in A.foc_by_quarter()}
        assert by["FY27Q1"]["foc_pct"] == 3.69 and by["FY27Q1"]["over_cap"]
        assert by["FY25Q3"]["foc_pct"] == 4.95
        assert not by["FY27Q2"]["over_cap"] and by["FY27Q2"]["foc_pct"] == 2.82
        assert [q for q, r in by.items() if r["over_cap"]] == ["FY25Q3", "FY25Q4", "FY26Q1", "FY26Q2", "FY26Q3", "FY26Q4", "FY27Q1"]


class TestPhasing:
    def test_step_change_in_december_2024_quarter(self):
        by = {r["quarter"]: r for r in A.phasing()}
        assert by["FY25Q2"]["last9d_pct"] < 22 and by["FY25Q3"]["last9d_pct"] > 32
        assert by["FY27Q2"]["last9d_pct"] == pytest.approx(25, abs=1.5)

    def test_months_add_to_one_hundred(self):
        for r in A.phasing():
            assert r["month1_pct"] + r["month2_pct"] + r["month3_pct"] == pytest.approx(100, abs=0.3)


class TestSchemeClaims:
    def test_scheme_packs_claimed_more(self):
        r = A.scheme_claim_rates()
        assert r["rate_no_scheme_packs_pct"] == pytest.approx(1.2, abs=0.05)
        assert r["scheme_pack_rate_pct"] == pytest.approx(13.0, abs=0.3) and r["multiple"] == pytest.approx(5.5, abs=0.3)
        assert r["tier_a_multiple"] == pytest.approx(2.5, abs=0.2)     # inside tier-A SKUs only, so SKU mix cannot explain it

    def test_cohort_range_and_estimate(self):
        r = A.scheme_claim_rates()
        assert r["cohort_low_pct"] == pytest.approx(12.22, abs=0.05) and r["cohort_high_pct"] == pytest.approx(19.65, abs=0.05)
        e = A.scheme_return_estimate("FY27Q1")
        assert round(e["scheme_supply_inr"] / 1e7, 2) == 13.02
        assert round(e["expected_return_low_inr"] / 1e5) == 159 and round(e["expected_return_high_inr"] / 1e5) == 256
        assert e["kind"] == "estimate"


class TestStockCover:
    def test_lucknow_has_no_stock_on_most_skus_while_others_hold_spare(self):
        r = A.stock_cover(date(2026, 7, 31))
        n02 = next(x for x in r["by_cnf"] if x["cnf_code"] == "CF-N02")
        assert n02["skus_with_no_stock"] == 20
        assert r["cnfs_lacking_skus_that_other_cnfs_hold_spare"]["CF-N02"]["spare_stock_elsewhere_inr"] > 4e7 * 0.1

    def test_kolkata_overstocked_lucknow_starved_latest(self):
        r = A.stock_cover()
        by = {x["cnf_code"]: x for x in r["by_cnf"]}
        assert by["CF-N02"]["share_of_stock_pct"] < 3 and by["CF-N02"]["share_of_outward_pct"] > 18
        assert by["CF-E01"]["share_of_stock_pct"] > 27 and by["CF-E01"]["cover_months"] > 3.5

    def test_most_of_the_shortage_is_allocation(self):
        # Each spare pack can be given to one short C&F only. Counting it for every short C&F gave 73%, which overstated
        # what reallocation can fix (independent recheck, 22 Nov: verification_recheck/recheck12.py). Used once: 58%.
        r = A.unfilled_shortfall(6)
        assert round(r["shortfall_inr"] / 1e7, 2) == 10.18
        assert r["allocation_fixable_pct"] == pytest.approx(58, abs=1)
        assert round(r["allocation_fixable_inr"] / 1e7, 2) == pytest.approx(5.91, abs=0.02)
        assert round(r["not_coverable_inr"] / 1e7, 2) == pytest.approx(4.27, abs=0.02)
        assert r["allocation_fixable_inr"] + r["not_coverable_inr"] == pytest.approx(r["shortfall_inr"], abs=2)

    def test_reallocation_never_counts_a_spare_pack_twice(self):
        r = A.unfilled_shortfall(6)
        total_spare = 0.0
        C = A.get_clean()
        for d in C.snapshot_dates[-6:]:
            for s in C.skus:
                total_spare += sum(max(0.0, C.stock.get((d, c, s), 0.0) - A.P.COVER_FLOOR_MONTHS * C.outward.get((d, c, s), 0.0)) for c in A.CNF_CODES) * C.pts(s)
        assert r["allocation_fixable_inr"] <= total_spare + 1


class TestAtRisk:
    def test_nothing_within_180_days_today(self):
        r = A.at_risk_stock(180)
        assert r["as_of"] == "2026-09-30" and r["total_batches"] == 0 and r["total_value_inr"] == 0

    def test_a_year_out_is_small(self):
        r = A.at_risk_stock(365)
        assert 0.5e7 < r["total_value_inr"] < 1.0e7


class TestDispatchQuality:
    def test_only_kolkata_breaks_fefo_and_only_recently(self):
        rows = A.fefo_breaches()
        e01 = {r["quarter"]: r["breach_pct"] for r in rows if r["cnf_code"] == "CF-E01"}
        assert e01["FY26Q3"] == 0 and e01["FY27Q1"] == pytest.approx(54.2, abs=0.5) and e01["FY27Q2"] == pytest.approx(64.1, abs=0.5)
        assert all(r["breach_pct"] == 0 for r in rows if r["cnf_code"] != "CF-E01")

    def test_short_dated_dispatch(self):
        r = A.short_dated_dispatch()
        assert r["rows"] == 90435 or r["rows"] > 90000
        assert r["rows_under_60pct"] == pytest.approx(4866, abs=60) and r["share_pct"] == pytest.approx(5.4, abs=0.2)
