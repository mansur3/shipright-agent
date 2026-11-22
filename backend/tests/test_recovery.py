"""The recovery view must reproduce the ledger: INR 51.5 L against clear rules, 69 pending INR 21.0 L, 800 for a person, 971 unverifiable."""
from agent import recovery
from agent.tools import get_recovery_summary


def test_recovery_buckets_match_ledger():
    r = recovery.build()
    b = r["buckets"]
    assert round(r["recover_inr"] / 1e5, 1) == 51.5
    assert round(b["recover_t1"]["inr"] / 1e5, 1) == 12.5 and b["recover_t1"]["claims"] == 104
    assert round(b["recover_t2"]["inr"] / 1e5, 1) == 39.0 and b["recover_t2"]["claims"] == 374
    assert b["hold"]["claims"] == 69 and round(b["hold"]["inr"] / 1e5, 1) == 21.0
    assert b["review"]["claims"] == 800
    assert b["unverifiable"]["claims"] == 971 and round(b["unverifiable"]["inr"] / 1e5, 1) == 85.4


def test_recovery_kinds_not_mixed():
    r = recovery.build()
    assert r["recover_inr"] == round(r["buckets"]["recover_t1"]["inr"] + r["buckets"]["recover_t2"]["inr"], 2)
    assert all(c["bucket"] in ("recover_t1", "recover_t2", "hold") for c in r["claims"])


def test_stockist_rows_sum_to_total():
    r = recovery.build()
    assert abs(sum(s["recover_inr"] for s in r["by_stockist"]) - r["recover_inr"]) < 1.0


def test_tool_returns_interpretation_and_stockist_detail():
    top = get_recovery_summary.invoke({})
    assert "lakh" in top["interpretation"] and len(top["top_stockists"]) == 10
    one = get_recovery_summary.invoke({"stockist_code": top["top_stockists"][0]["stockist_code"]})
    assert one["stockist"]["recover_inr"] == top["top_stockists"][0]["recover_inr"]
    assert get_recovery_summary.invoke({"stockist_code": "STK9999"})["stockist"]["claims"] == 0
