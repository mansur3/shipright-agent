"""
Tools the agent calls. Each result is pinned to the value in verification/05_findings_ledger.md.
No model and no network: tools are plain functions over the clean data.
"""
import pytest

from agent import tools as T


class TestLookupBatch:
    def test_found(self):
        r = T.lookup_batch.invoke({"batch_no": "K2310408"})
        assert r["found"] and r["sku_code"] == "PFL1104" and "batch_master.csv line" in r["source"]

    def test_pre_window_batch_says_not_in_master_not_invalid(self):
        r = T.lookup_batch.invoke({"batch_no": "L2200185"})
        assert r["found"] is False and "Oct 2023" in r["note"]

    def test_case_and_space_insensitive(self):
        assert T.lookup_batch.invoke({"batch_no": " k2310408 "})["found"]


class TestValidateClaim:
    def test_returns_recommendation_with_rule_and_clause(self):
        r = T.validate_claim.invoke({"stockist_code": "STK0025", "batch_no": "F2440122", "sku_code": "PFL1401", "qty_claimed": 272,
                                     "claim_date": "2026-05-12", "claim_type": "Near expiry"})
        assert r["decision"] == "REJECT" and r["rule_id"] == "R_EXACT_REPEAT" and r["policy_clause"].startswith("CO-POL-014")
        assert "recommendation" in r["recommended_action"].lower() and r["valid"] is False

    def test_pre_window_is_a_person_not_a_reject(self):
        r = T.validate_claim.invoke({"stockist_code": "STK0007", "batch_no": "L2200185", "sku_code": "PFL1001", "qty_claimed": 10,
                                     "claim_date": "2024-07-01", "claim_type": "Near expiry", "invoice_ref": "INV/W01/2302/002323"})
        assert r["decision"] == "NEEDS A PERSON" and r["tier"] == "T4"

    def test_unreadable_date_is_a_person(self):
        r = T.validate_claim.invoke({"stockist_code": "STK0025", "batch_no": "F2440122", "sku_code": "PFL1401", "qty_claimed": 5,
                                     "claim_date": "not a date", "claim_type": "Near expiry"})
        assert r["decision"] == "NEEDS A PERSON"


class TestAtRiskStock:
    def test_empty_is_an_answer(self):
        r = T.get_at_risk_stock.invoke({"cnf_code": "", "days_threshold": 180})
        assert r["total_batches"] == 0 and "No stock on hand" in r["message"] and r["as_of"] == "2026-09-30"

    def test_one_year_horizon_has_stock(self):
        r = T.get_at_risk_stock.invoke({"cnf_code": "", "days_threshold": 365})
        assert r["total_batches"] > 0 and all(b["days_to_expiry"] <= 365 for b in r["batches"])


class TestFillRate:
    def test_latest_quarter_paid_and_qbr_basis(self):
        r = T.get_fill_rate.invoke({"cnf_code": ""})
        assert r["quarter"] == "FY27Q2" and r["overall_fill_rate_pct"] == 82.6 and r["overall_qbr_basis_pct"] == 84.8
        assert {x["cnf_code"] for x in r["by_cnf"]} == {"CF-N01", "CF-N02", "CF-E01", "CF-W01", "CF-S01", "CF-S02"}

    def test_single_cnf(self):
        r = T.get_fill_rate.invoke({"cnf_code": "cf-n02"})
        assert len(r["by_cnf"]) == 1 and r["by_cnf"][0]["fill_rate_pct"] == 74.6


class TestQuarterSpike:
    def test_fiscal_quarters_in_order_and_no_invented_rate(self):
        r = T.detect_quarter_spike.invoke({})
        qs = [p["quarter"] for p in r["phasing_by_quarter"]]
        assert qs == sorted(qs) and qs[-1] == "FY27Q2" and r["latest_quarter"] == "FY27Q2"
        rng = r["expected_return_range_inr"]
        assert rng["kind"] == "estimate" and rng["low"] < r["projected_expiry_return_inr"] < rng["high"]
        assert "0.15" not in str(r) and "15%" not in str(r)

    def test_sku_filter_has_no_estimate(self):
        r = T.detect_quarter_spike.invoke({"sku_code": "PFL1001"})
        assert r["expected_return_range_inr"] is None


class TestSchemeGate:
    def test_never_says_eligible_without_secondary_data(self):
        r = T.check_scheme_eligibility.invoke({"stockist_code": "STK0058", "sku_code": "PFL1002"})
        assert r["found"] and r["eligible"] is None and r["decision"] in ("NEEDS RSM CONFIRMATION", "NO FLAG FROM THE EXTRACTS")
        assert "secondary" in r["note"].lower() and r["clause"].startswith("CO-POL-014 4.5")

    def test_unknown_stockist(self):
        assert T.check_scheme_eligibility.invoke({"stockist_code": "STK9999", "sku_code": "PFL1002"})["found"] is False

    def test_not_every_stockist_is_flagged_ineligible(self):
        # the old proxy marked 12 of 12 sampled pairs "not eligible"
        outs = [T.check_scheme_eligibility.invoke({"stockist_code": f"STK{n:04d}", "sku_code": "PFL1002"})["decision"] for n in range(50, 62)]
        assert "NO FLAG FROM THE EXTRACTS" in outs


class TestStockistSummary:
    def test_tiers_reported(self):
        r = T.get_stockist_summary.invoke({"stockist_code": "STK0025"})
        assert r["found"] and sum(r["claims_by_evidence_tier"].values()) == r["total_claims"]

    def test_unknown(self):
        assert T.get_stockist_summary.invoke({"stockist_code": "NOPE"})["found"] is False


class TestNewTools:
    def test_stock_cover(self):
        r = T.get_stock_cover.invoke({})
        by = {x["cnf_code"]: x for x in r["by_cnf"]}
        assert by["CF-N02"]["share_of_stock_pct"] < 3 and by["CF-E01"]["share_of_stock_pct"] > 27
        assert r["shortage_split_last_6_month_ends"]["allocation_fixable_pct"] == pytest.approx(73, abs=1)

    def test_dispatch_quality_only_kolkata(self):
        r = T.get_dispatch_quality.invoke({})
        assert any(x["cnf_code"] == "CF-E01" and x["breach_pct"] > 50 for x in r["fefo_breaches_by_quarter"])
        assert all(x["breach_pct"] == 0 for x in r["fefo_breaches_by_quarter"] if x["cnf_code"] != "CF-E01")
        assert r["short_dated_dispatch"]["clause"].startswith("CO-POL-014 7.1")

    def test_scheme_cap(self):
        r = T.get_scheme_cap.invoke({})
        by = {x["quarter"]: x for x in r["free_goods_by_quarter"]}
        assert by["FY27Q1"]["over_cap"] and not by["FY27Q2"]["over_cap"]
        assert r["scheme_pack_claim_rates"]["multiple"] > 4


def test_claim_type_wording_is_normalised():
    from agent.tools import normalise_claim_type as n
    assert n("near-expiry") == "Near expiry" and n("near expiry") == "Near expiry"
    assert n("expiry") == "Expired" and n("Expired") == "Expired"
    assert n("damaged in transit") == "Breakage in transit" and n("short supply") == "Short supply"
    assert n("something else") == "something else"


def test_validate_claim_ignores_a_sku_that_is_not_one():
    base = {"stockist_code": "STK0054", "batch_no": "K2310267", "qty_claimed": 50, "claim_date": "15-09-2025", "claim_type": "Near expiry", "invoice_ref": "INV/E01/2404/000881"}
    wrong = T.validate_claim.invoke({**base, "sku_code": "50 STRIPS"})
    none = T.validate_claim.invoke(base)
    assert wrong["rule_id"] == none["rule_id"] and "mismatch" not in wrong["reason"].lower()
