"""The claims intake agent keeps a half-filed claim across turns, never crashes on a missing field, and the model may only reword."""
import uuid

import pytest

from agent import claims_graph as cg


@pytest.fixture(autouse=True)
def no_model(monkeypatch):
    monkeypatch.setattr(cg, "_polish", lambda q, d: (d, False))


def test_missing_fields_are_asked_in_one_message_and_remembered():
    sid = f"t-{uuid.uuid4().hex[:8]}"
    r1 = cg.run_claims_agent("I want to file a near expiry claim", "flowuser", sid)
    assert r1["intent"] == "create_claim" and "still need" in r1["answer"]
    r2 = cg.run_claims_agent("stockist STK0054 batch K2310267", "flowuser", sid)
    assert r2["intent"] == "create_claim"
    assert "SKU" in r2["answer"] and "stockist code STK0054" in r2["answer"]   # remembered from this turn
    r3 = cg.run_claims_agent("sku PFL1102 50 strips on 15-09-2025 invoice INV/E01/2404/000881", "flowuser", sid)
    assert r3["claim_no"] and "Claim created" in r3["answer"]
    # the next message starts fresh, not another claim
    r4 = cg.run_claims_agent("hello", "flowuser", sid)
    assert r4["claim_no"] is None and r4["intent"] != "create_claim"


def test_draft_rebuilt_from_history_only_since_last_claim():
    sid = f"t-{uuid.uuid4().hex[:8]}"
    cg.run_claims_agent("file a near expiry claim stockist STK0054 batch K2310267 sku PFL1102 50 strips 15-09-2025", "flowuser2", sid)
    intent, draft = cg._load_draft(sid)
    assert intent == "" and draft == {}          # claim was created, draft cleared


def test_polish_falls_back_when_model_changes_a_number(monkeypatch):
    monkeypatch.undo()   # use the real _polish

    class Fake:
        def __init__(self, text): self.text = text
        def invoke(self, _): return type("R", (), {"content": self.text})()

    monkeypatch.setattr(cg, "get_llm", lambda: Fake("The claim is worth INR 9,999."))
    out, used = cg._polish("q", "Claim value INR 4,465.")
    assert out == "Claim value INR 4,465." and used is False
    monkeypatch.setattr(cg, "get_llm", lambda: Fake("Your claim is worth INR 4,465."))
    out, used = cg._polish("q", "Claim value INR 4,465.")
    assert used is True and "4,465" in out


def test_polish_falls_back_when_model_unavailable(monkeypatch):
    monkeypatch.undo()

    def boom():
        raise ValueError("OPENROUTER_API_KEY not set")

    monkeypatch.setattr(cg, "get_llm", boom)
    assert cg._polish("q", "Draft text 12.") == ("Draft text 12.", False)


def test_polish_falls_back_when_model_adds_a_new_figure(monkeypatch):
    monkeypatch.undo()

    class Fake:
        def invoke(self, _): return type("R", (), {"content": "Your claim is worth INR 4,465, about INR 9,999 with interest."})()

    monkeypatch.setattr(cg, "get_llm", lambda: Fake())
    assert cg._polish("q", "Claim value INR 4,465.") == ("Claim value INR 4,465.", False)
