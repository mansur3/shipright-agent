"""Measured cost per request, and the check set as a regression test."""
import csv
from pathlib import Path

import pytest
from langchain_core.messages import AIMessage

import config as P
from agent.graph import add_usage, estimate_cost_inr

ROOT = Path(__file__).resolve().parent.parent


class TestMeasuredCost:
    def test_tokens_are_summed_from_the_provider_figures(self):
        a = add_usage({}, AIMessage(content="x", usage_metadata={"input_tokens": 800, "output_tokens": 300, "total_tokens": 1100}))
        b = add_usage(a, AIMessage(content="y", usage_metadata={"input_tokens": 1200, "output_tokens": 150, "total_tokens": 1350}))
        assert b == {"input_tokens": 2000, "output_tokens": 450}

    def test_missing_usage_counts_as_zero_not_a_guess(self):
        assert add_usage({"input_tokens": 5, "output_tokens": 2}, AIMessage(content="no usage")) == {"input_tokens": 5, "output_tokens": 2}

    def test_cost_is_tokens_times_configured_price(self):
        usd = 2000 / 1e6 * P.PRICE_USD_PER_M_INPUT + 450 / 1e6 * P.PRICE_USD_PER_M_OUTPUT
        assert estimate_cost_inr(2000, 450) == pytest.approx(usd * P.USD_INR, abs=1e-4)

    def test_one_model_name_everywhere(self):
        assert P.MODEL and "claude" not in P.MODEL_DEFAULT
        src = (ROOT / "agent" / "llm.py").read_text(encoding="utf-8")
        assert "gpt-4o-mini" not in src and "config.MODEL" in src


class TestCheckSet:
    def test_size_is_between_10_and_20_real_records(self):
        rows = list(csv.DictReader(open(ROOT / "checks" / "check_set.csv", encoding="utf-8")))
        assert 10 <= len(rows) <= 20 and len({r["check_id"] for r in rows}) == len(rows)
        assert {r["kind"] for r in rows} == {"register", "synthetic", "email"}

    def test_awkward_cases_are_present(self):
        text = (ROOT / "checks" / "check_set.csv").read_text(encoding="utf-8").lower()
        for needle in ("pre-approved", "letter o", "no batch number", "not a date", "stockist master", "before the batch master", "inbox case"):
            assert needle in text, needle

    def test_every_record_is_right(self):
        from checks.run_checks import main
        assert main(as_json=False) == 0
