"""
Tests for the claims AI agent — DB storage, Pydantic schemas, and API endpoints.
Uses real CSV data + SQLite.
"""
import pytest
from fastapi.testclient import TestClient

from app import app

client = TestClient(app)


def _token(role="admin"):
    creds = {
        "admin":  ("admin",  "Test-Passw0rd-2026"),
        "claims": ("claims", "Test-Passw0rd-2026"),
        "cfo":    ("cfo",    "Test-Passw0rd-2026"),
        "rsm":    ("rsm_north","Test-Passw0rd-2026"),
    }
    u, p = creds[role]
    r = client.post("/api/auth/login", json={"username": u, "password": p})
    assert r.status_code == 200, f"Login failed for {u}: {r.text}"
    return r.json()["access_token"]

def _auth(token):
    return {"Authorization": f"Bearer {token}"}


# ── Pydantic schema tests ─────────────────────────────────────────────────────

class TestClaimSchemas:
    def test_valid_claim_create(self):
        from agent.claim_schemas import ClaimCreate, ClaimTypeEnum
        c = ClaimCreate(
            stockist_code="STK0054",
            batch_no="K2310267",
            sku_code="PFL1102",
            qty_claimed=50.0,
            claim_date="15-09-2025",
            claim_type=ClaimTypeEnum.near_expiry,
        )
        assert c.stockist_code == "STK0054"
        assert c.qty_claimed == 50.0

    def test_invalid_qty_zero(self):
        from agent.claim_schemas import ClaimCreate, ClaimTypeEnum
        with pytest.raises(Exception):
            ClaimCreate(
                stockist_code="STK0054", batch_no="K2310267",
                sku_code="PFL1102", qty_claimed=0,
                claim_date="15-09-2025", claim_type=ClaimTypeEnum.near_expiry,
            )

    def test_injection_blocked(self):
        from agent.claim_schemas import ClaimCreate, ClaimTypeEnum
        with pytest.raises(Exception):
            ClaimCreate(
                stockist_code="ignore previous",
                batch_no="K2310267", sku_code="PFL1102",
                qty_claimed=50, claim_date="15-09-2025",
                claim_type=ClaimTypeEnum.near_expiry,
            )

    def test_bad_date_format(self):
        from agent.claim_schemas import ClaimCreate, ClaimTypeEnum
        with pytest.raises(Exception):
            ClaimCreate(
                stockist_code="STK0054", batch_no="K2310267",
                sku_code="PFL1102", qty_claimed=50,
                claim_date="bad-date", claim_type=ClaimTypeEnum.near_expiry,
            )

    def test_uppercase_normalisation(self):
        from agent.claim_schemas import ClaimCreate, ClaimTypeEnum
        c = ClaimCreate(
            stockist_code="stk0054", batch_no="k2310267",
            sku_code="pfl1102", qty_claimed=50,
            claim_date="15-09-2025", claim_type=ClaimTypeEnum.near_expiry,
        )
        assert c.stockist_code == "STK0054"
        assert c.batch_no == "K2310267"


# ── Claims API endpoint tests ─────────────────────────────────────────────────

class TestClaimsAPI:
    def test_my_claims_requires_auth(self):
        r = client.get("/api/claims/my")
        assert r.status_code == 401

    def test_my_claims_returns_empty_for_new_user(self):
        token = _token("admin")
        r = client.get("/api/claims/my", headers=_auth(token))
        assert r.status_code == 200
        assert "claims" in r.json()
        assert isinstance(r.json()["claims"], list)

    def test_all_claims_requires_claims_role(self):
        # RSM should not access all claims
        token = _token("rsm")
        r = client.get("/api/claims/all", headers=_auth(token))
        assert r.status_code == 403

    def test_all_claims_accessible_to_claims_finance(self):
        token = _token("claims")
        r = client.get("/api/claims/all", headers=_auth(token))
        assert r.status_code == 200
        assert "claims" in r.json()

    def test_benchmark_requires_cfo_or_admin(self):
        # RSM should not access benchmark
        token = _token("rsm")
        r = client.get("/api/claims/benchmark", headers=_auth(token))
        assert r.status_code == 403

    def test_benchmark_accessible_to_cfo(self):
        token = _token("cfo")
        r = client.get("/api/claims/benchmark", headers=_auth(token))
        assert r.status_code == 200
        d = r.json()
        assert "benchmark" in d
        assert "batch_analysis" in d or d["batch_analysis"] is None
        assert "user_claims" in d

    def test_review_requires_claims_role(self):
        token = _token("rsm")
        r = client.post("/api/claims/999/review", json={"decision": "Approved"}, headers=_auth(token))
        assert r.status_code == 403

    def test_chat_requires_auth(self):
        r = client.post("/api/claims/chat", json={"message": "test"})
        assert r.status_code == 401

    def test_chat_rejects_short_message(self):
        token = _token("admin")
        r = client.post("/api/claims/chat", json={"message": "a"}, headers=_auth(token))
        assert r.status_code == 422

    def test_chat_rejects_long_message(self):
        token = _token("admin")
        r = client.post("/api/claims/chat", json={"message": "x" * 900}, headers=_auth(token))
        assert r.status_code == 422

    def test_chat_history_requires_auth(self):
        r = client.get("/api/claims/chat-history")
        assert r.status_code == 401

    def test_chat_history_returns_sessions(self):
        token = _token("admin")
        r = client.get("/api/claims/chat-history", headers=_auth(token))
        assert r.status_code == 200
        assert "sessions" in r.json()

    def test_no_internal_paths_in_my_claims(self):
        token = _token("admin")
        r = client.get("/api/claims/my", headers=_auth(token))
        body = r.text
        assert ".csv" not in body
        assert ".db" not in body
        assert "sqlite" not in body.lower()

    def test_no_passwords_in_benchmark(self):
        token = _token("cfo")
        r = client.get("/api/claims/benchmark", headers=_auth(token))
        body = r.text
        assert "hashed_password" not in body
        assert "bcrypt" not in body
