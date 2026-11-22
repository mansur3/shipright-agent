"""
Policy constants and small helpers. The claim rules have one implementation (agent/claim_checks.py,
tested in test_claim_checks.py); this file checks that the constants match the policy and that nothing re-implements them.
"""
import ast
from datetime import datetime
from pathlib import Path

import pytest

import config as P
from agent import rules as R

BACKEND = Path(__file__).resolve().parent.parent


class TestPolicyConstants:
    def test_claim_windows(self):
        assert (P.CLAIM_WINDOW_NE_DAYS, P.CLAIM_WINDOW_POST_EXPIRY_DAYS, P.CLAIM_WINDOW_BED_DAYS) == (90, 90, 7)

    def test_scheme_policy(self):
        assert P.SCHEME_FREE_CAP_PCT == 3.0 and P.SCHEME_STOCK_NORM_MONTHS == 2.5 and P.QS_MIN_ORDER_MULT == 1.5

    def test_dispatch_and_credit_terms(self):
        assert P.MIN_RSL_PCT == 0.60 and P.MIN_DAYS_AT_DISPATCH == 60 and P.CREDIT_TAT_DAYS == 30

    def test_scheme_tiers_match_annex_b(self):
        assert len(P.SCHEME_TIER_A_SKUS) == 10 and len(P.SCHEME_TIER_B_SKUS) == 5
        assert not (P.SCHEME_TIER_A_SKUS & P.SCHEME_TIER_B_SKUS)

    def test_no_unsourced_return_rate_constant(self):
        assert not hasattr(P, "RETURN_RATE") and not hasattr(P, "ASSUMED_RETURN_RATE")


class TestRulesModuleIsThin:
    def test_constants_come_from_config(self):
        assert R.CLAIM_WINDOW_NE_BEFORE_DAYS == P.CLAIM_WINDOW_NE_DAYS and R.SCHEME_CAP_PCT == P.SCHEME_FREE_CAP_PCT

    def test_days_to_expiry(self):
        assert R.days_to_expiry(datetime(2026, 12, 31), datetime(2026, 10, 1)) == 91
        assert R.days_to_expiry(datetime(2026, 9, 1), datetime(2026, 10, 1)) == -30

    def test_at_risk_value(self):
        assert R.at_risk_value(100, 71.4) == pytest.approx(7140.0)

    @pytest.mark.parametrize("free,prim,over", [(3.0, 100.0, False), (3.01, 100.0, True), (0, 100.0, False)])
    def test_free_goods_cap_boundary(self, free, prim, over):
        assert R.over_free_goods_cap(free, prim) is over


class TestOneImplementation:
    """The claim window, quantity and repeat rules must not be written a second time anywhere."""

    def _source(self, rel):
        return (BACKEND / rel).read_text(encoding="utf-8")

    @pytest.mark.parametrize("rel", ["app.py", "agent/tools.py", "agent/claims_graph.py", "batch/processor.py", "checks/run_checks.py"])
    def test_no_second_copy_of_the_window_rule(self, rel):
        src = self._source(rel)
        for needle in ("timedelta(days=90)", "CLAIM_WINDOW_NE", "def is_in_claim_window", "def qty_exceeds_invoiced", "def is_duplicate", "def claim_risk_score"):
            assert needle not in src, f"{rel} re-implements a claim rule ({needle})"

    @pytest.mark.parametrize("rel", ["app.py", "agent/tools.py", "agent/claims_graph.py", "batch/processor.py", "checks/run_checks.py"])
    def test_callers_use_the_claim_checker(self, rel):
        assert "claim_checks" in self._source(rel) or rel == "agent/tools.py"

    def test_tools_module_parses_and_exports_ten_tools(self):
        from agent.tools import TOOLS
        assert len(TOOLS) == 11 and len({t.name for t in TOOLS}) == 11

    def test_every_tool_is_allowed_by_the_tool_guard(self):
        from agent.guardrails import ALLOWED_TOOLS
        from agent.tools import TOOLS
        assert {t.name for t in TOOLS} == ALLOWED_TOOLS
