"""
The one claim checker. Reproduction test first: replaying the register must give the tier counts
in verification/05_findings_ledger.md. Then one test per rule on real records.
"""
from collections import Counter
from datetime import date, timedelta

import pytest

from agent.claim_checks import APPROVE, PERSON, REJECT, ClaimInput, evaluate, evaluate_register_row
from agent.clean import get_clean

C = get_clean()


@pytest.fixture(scope="module")
def replay():
    return {c["claim_no"]: (c, evaluate_register_row(c)) for c in C.claims}


class TestLedgerReproduction:
    def test_credited_claim_tiers_match_ledger(self, replay):
        n = Counter(v.tier for c, v in replay.values() if c["status"] == "Credited")
        assert n["T1"] == 104       # 64 filed over 90 days after expiry + 40 over supply
        assert n["T2"] == 374       # 320 outside window + 54 exact repeats
        assert n["T3"] == 800       # 347 partial repeats + 453 no invoice reference
        assert n["T4"] == 971       # batches older than the batch master
        assert n["CLEAN"] == 1863
        assert sum(n.values()) == 4112

    def test_credit_value_by_tier_matches_ledger(self, replay):
        val = Counter()
        for c, v in replay.values():
            if c["status"] == "Credited":
                val[v.tier] += c["credit_eff"]
        assert round(val["T1"] / 1e5, 1) == 68.4    # whole-claim value of T1 claims (over-supply excess alone is INR 1.8 lakh)
        assert round(val["T2"] / 1e5, 1) == 39.0
        assert round(val["T4"] / 1e5, 1) == 85.4

    def test_decisions_follow_tiers(self, replay):
        for c, v in replay.values():
            assert v.decision == {"T1": REJECT, "T2": REJECT, "T3": PERSON, "T4": PERSON, "INVALID": PERSON, "CLEAN": APPROVE}[v.tier]

    def test_pending_claims_that_fail_today(self, replay):
        fails = [c for c, v in replay.values() if c["status"] == "Pending" and v.tier in ("T1", "T2")]
        assert 50 <= len(fails) <= 80      # ledger: 62 pending fail the window rules; repeat and quantity rules add a few


class TestRules:
    def _ci(self, **kw):
        base = dict(stockist="STK0025", batch="F2440122", qty=272, claim_date=date(2026, 5, 12), claim_type="Near expiry",
                    invoice_ref="", sku="PFL1401")
        base.update(kw)
        return ClaimInput(**base)

    def test_inbox_repeat_is_caught(self):
        # Controller's inbox case: STK0025, PFL1401, F2440122, 272 packs credited in April, again in May.
        v = evaluate(self._ci(qty=272, order=None))
        assert v.tier == "T2" and v.decision == REJECT and v.rule_ids == ["R_EXACT_REPEAT"]
        assert any("CLM-2603-01616" in r for r in v.reasons)

    def test_pre_window_batch_needs_a_person_not_reject(self):
        v = evaluate(ClaimInput(stockist="STK0007", batch="L2200185", qty=10, claim_date=date(2024, 7, 1), claim_type="Near expiry",
                                invoice_ref="INV/W01/2302/002323"))
        assert v.decision == PERSON and v.tier == "T4" and "pre_window" in v.flags

    def test_unknown_stockist_needs_a_person(self):
        v = evaluate(self._ci(stockist="STK9999"))
        assert v.decision == PERSON and v.rule_ids == ["R_ENTITY"]

    @pytest.mark.parametrize("qty", [0, -5])
    def test_bad_quantity_needs_a_person(self, qty):
        assert evaluate(self._ci(qty=qty)).decision == PERSON

    def test_unreadable_date_never_approves(self):
        assert evaluate(self._ci(claim_date=None)).decision == PERSON

    def test_unknown_type_needs_a_person(self):
        assert evaluate(self._ci(claim_type="Saleable return")).decision == PERSON

    def _free_batch(self):
        """A stockist + batch with supply and no credited claim yet."""
        for (stk, bat), sup in C.supply.items():
            if sup >= 200 and not C.credited_before(stk, bat) and bat in C.batches:
                inv = next(r for r in C.sales if r["stk"] == stk and r["batch"] == bat)
                return stk, bat, sup, inv
        raise AssertionError("no free batch found")

    def test_clean_claim_is_approved_with_evidence(self):
        stk, bat, sup, inv = self._free_batch()
        exp = C.batches[bat]["exp"]
        v = evaluate(ClaimInput(stockist=stk, batch=bat, qty=10, claim_date=exp - timedelta(days=30), claim_type="Near expiry", invoice_ref=inv["invoice_no"]))
        assert v.decision == APPROVE and v.tier == "CLEAN"
        assert any("primary_sales.csv" in e for e in v.evidence) and any("batch_master.csv" in e for e in v.evidence)

    def test_over_supply_is_t1(self):
        stk, bat, sup, inv = self._free_batch()
        exp = C.batches[bat]["exp"]
        v = evaluate(ClaimInput(stockist=stk, batch=bat, qty=sup + 1, claim_date=exp - timedelta(days=10), claim_type="Near expiry", invoice_ref=inv["invoice_no"]))
        assert v.tier == "T1" and v.rule_ids == ["R_OVER_SUPPLY"] and v.excess_packs == 1

    def test_cumulative_quantity_counts_earlier_claims(self):
        # a second claim that is within supply on its own but over supply with the first
        for (stk, bat), claims in C._credited_by_batch.items():
            if bat in C.batches and claims:
                sup = C.supply.get((stk, bat), 0.0)
                first = claims[-1]
                room = sup - sum(c["qty"] for c in claims)
                if room > 0:
                    v = evaluate(ClaimInput(stockist=stk, batch=bat, qty=room + 1, claim_date=date(2026, 9, 30), claim_type="Expired",
                                            invoice_ref=first["inv"], order=None))
                    assert v.tier == "T1"
                    return
        pytest.skip("no batch with room")

    def test_filed_over_90_days_after_expiry_is_never_accepted(self):
        stk, bat, sup, inv = self._free_batch()
        exp = C.batches[bat]["exp"]
        v = evaluate(ClaimInput(stockist=stk, batch=bat, qty=5, claim_date=exp + timedelta(days=91), claim_type="Expired", invoice_ref=inv["invoice_no"]))
        assert v.tier == "T1" and v.rule_ids == ["R_LATE_AFTER_EXPIRY"]

    @pytest.mark.parametrize("days,ok", [(-91, False), (-90, True), (0, True), (1, False)])
    def test_near_expiry_window_boundaries(self, days, ok):
        stk, bat, sup, inv = self._free_batch()
        exp = C.batches[bat]["exp"]
        v = evaluate(ClaimInput(stockist=stk, batch=bat, qty=5, claim_date=exp + timedelta(days=days), claim_type="Near expiry", invoice_ref=inv["invoice_no"]))
        assert (v.decision == APPROVE) is ok

    @pytest.mark.parametrize("days,ok", [(0, True), (90, True), (91, False)])
    def test_expired_window_boundaries(self, days, ok):
        stk, bat, sup, inv = self._free_batch()
        exp = C.batches[bat]["exp"]
        v = evaluate(ClaimInput(stockist=stk, batch=bat, qty=5, claim_date=exp + timedelta(days=days), claim_type="Expired", invoice_ref=inv["invoice_no"]))
        assert (v.decision == APPROVE) is ok

    @pytest.mark.parametrize("gap,ok", [(0, True), (7, True), (8, False)])
    def test_breakage_window_is_measured_from_the_invoice_not_the_expiry(self, gap, ok):
        stk, bat, sup, inv = self._free_batch()
        v = evaluate(ClaimInput(stockist=stk, batch=bat, qty=5, claim_date=inv["date"] + timedelta(days=gap), claim_type="Breakage in transit",
                                invoice_ref=inv["invoice_no"]))
        assert (v.decision == APPROVE) is ok
        if not ok:
            assert v.rule_ids == ["R_WINDOW"]

    def test_breakage_without_invoice_cannot_be_window_tested(self):
        stk, bat, sup, inv = self._free_batch()
        v = evaluate(ClaimInput(stockist=stk, batch=bat, qty=5, claim_date=inv["date"] + timedelta(days=3), claim_type="Short supply", invoice_ref=""))
        assert "window_not_testable" in v.flags and v.decision == PERSON

    def test_no_invoice_reference_goes_to_a_person_with_the_clause(self):
        stk, bat, sup, inv = self._free_batch()
        exp = C.batches[bat]["exp"]
        v = evaluate(ClaimInput(stockist=stk, batch=bat, qty=5, claim_date=exp - timedelta(days=20), claim_type="Near expiry", invoice_ref=""))
        assert v.decision == PERSON and v.rule_ids == ["R_NO_INVOICE_REF"] and "5.4" in v.clause

    def test_invoice_for_another_stockist_goes_to_a_person(self):
        stk, bat, sup, inv = self._free_batch()
        other = next(r for r in C.sales if r["stk"] != stk and r["batch"])
        exp = C.batches[bat]["exp"]
        v = evaluate(ClaimInput(stockist=stk, batch=bat, qty=5, claim_date=exp - timedelta(days=20), claim_type="Near expiry", invoice_ref=other["invoice_no"]))
        assert v.decision == PERSON and v.rule_ids == ["R_INVOICE_CHECK"]

    def test_hyphenated_codes_are_accepted(self):
        stk, bat, sup, inv = self._free_batch()
        exp = C.batches[bat]["exp"]
        sku = C.batches[bat]["sku"]
        v = evaluate(ClaimInput(stockist=stk.lower(), batch=bat.lower(), qty=5, claim_date=exp - timedelta(days=20), claim_type="Near expiry",
                                invoice_ref=inv["invoice_no"].replace("INV/", "INV-", 1), sku=sku[:3] + "-" + sku[3:]))
        assert v.decision == APPROVE

    def test_sku_that_disagrees_with_batch_goes_to_a_person(self):
        stk, bat, sup, inv = self._free_batch()
        exp = C.batches[bat]["exp"]
        other_sku = next(s for s in C.skus if s != C.batches[bat]["sku"])
        v = evaluate(ClaimInput(stockist=stk, batch=bat, qty=5, claim_date=exp - timedelta(days=20), claim_type="Near expiry", invoice_ref=inv["invoice_no"], sku=other_sku))
        assert v.rule_ids == ["R_SKU_MISMATCH"]

    def test_verdict_is_a_recommendation_and_names_the_owner(self):
        d = evaluate(self._ci(qty=272)).as_dict()
        assert "Recommendation only" in d["note"] and "Neha Bansal" in d["owner"]
        assert d["policy_clause"].startswith("CO-POL-014")


class TestPendingClaim:
    def test_new_claim_on_a_batch_with_a_pending_claim_goes_to_a_person(self):
        for (stk, bat), pend in C._pending_by_batch.items():
            if bat in C.batches and not C.credited_before(stk, bat) and C.supply.get((stk, bat), 0) > pend[0]["qty"] + 5:
                exp = C.batches[bat]["exp"]
                v = evaluate(ClaimInput(stockist=stk, batch=bat, qty=1, claim_date=exp - timedelta(days=10), claim_type="Near expiry", invoice_ref=pend[0]["inv"]))
                assert v.rule_ids == ["R_PENDING_CLAIM"] and v.decision == PERSON and pend[0]["claim_no"] in v.reason
                return
        pytest.skip("no suitable pending claim")

    def test_register_replay_is_unaffected(self, replay):
        n = Counter(v.tier for c, v in replay.values() if c["status"] == "Credited")
        assert n["T3"] == 800
