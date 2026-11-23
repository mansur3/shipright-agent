"""The opportunity register must tie to the claim checker, the analysis layer and the findings ledger, and must keep kinds of money apart."""
import pytest

from agent import analysis, opportunities, recovery


@pytest.fixture(scope="module")
def reg():
    return opportunities.build()


def by_id(reg, i):
    return next(o for o in reg["opportunities"] if o["id"] == i)


def test_claim_opportunities_equal_recovery_buckets(reg):
    b = recovery.build()["buckets"]
    assert by_id(reg, "OPP-01")["amount_inr"] == b["recover_t1"]["inr"]
    assert by_id(reg, "OPP-02")["amount_inr"] == b["recover_t2"]["inr"]
    assert by_id(reg, "OPP-03")["amount_inr"] == b["hold"]["inr"]
    assert round(reg["headline"]["credited_cash_to_review_inr"] / 1e5, 1) == 51.5


def test_ledger_figures(reg):
    assert round(by_id(reg, "OPP-04")["amount_inr"] / 1e7, 2) == 0.68            # free goods above cap, last 4 quarters
    assert round(by_id(reg, "OPP-05")["amount_inr"] / 1e7, 1) == pytest.approx(3.4, abs=0.1)  # ledger 2.7 to 3.4 cr
    assert round(by_id(reg, "OPP-09")["reference_inr"] / 1e5, 1) == 85.4
    assert by_id(reg, "OPP-08")["claims"] == 800


def test_revenue_opportunity_uses_latest_month_not_six_month_sum(reg):
    one, six = analysis.unfilled_shortfall(1), analysis.unfilled_shortfall(6)
    assert by_id(reg, "OPP-06")["amount_inr"] == one["allocation_fixable_inr"] < six["allocation_fixable_inr"]


def test_every_opportunity_is_complete_and_classified(reg):
    for o in reg["opportunities"]:
        assert o["class"] in opportunities.CLASSES
        assert o["validated"], o["id"]
        assert o["formula"] and o["evidence"] and o["owner"] and o["agent"]
        # an unsized item must not carry an amount; sized ones must
        assert (o["amount_inr"] is not None) == o["sized"]


def test_unsized_risks_and_exposure_are_never_totalled_as_money(reg):
    for cls in ("operational_risk", "exposure"):
        assert reg["totals_by_class"][cls]["amount_inr"] == 0
    for i in ("OPP-07", "OPP-08", "OPP-09", "OPP-10"):
        assert by_id(reg, i)["amount_inr"] is None


def test_no_cross_class_grand_total(reg):
    assert "total" not in reg["headline"] and "grand_total_inr" not in reg
    assert reg["headline"]["credited_cash_to_review_inr"] == pytest.approx(
        reg["headline"]["confirmed_leakage_inr"] + reg["headline"]["potentially_recoverable_inr"], abs=0.01)


def test_overlapping_scheme_items_are_flagged(reg):
    assert "OPP-04" in by_id(reg, "OPP-05")["overlap"] and "OPP-05" in by_id(reg, "OPP-10")["overlap"]
