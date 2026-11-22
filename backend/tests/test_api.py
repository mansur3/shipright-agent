"""
Integration tests for FastAPI endpoints.
Tests that require auth use the admin user seeded by init_db().
Tests for public tool endpoints (no auth) remain unchanged.
"""
import pytest
from fastapi.testclient import TestClient

from app import app

client = TestClient(app)

# ── Auth helper ────────────────────────────────────────────────────────────────
def _admin_token() -> str:
    r = client.post("/api/auth/login", json={"username": "admin", "password": "Test-Passw0rd-2026"})
    assert r.status_code == 200, f"Login failed: {r.text}"
    return r.json()["access_token"]

def _claims_token() -> str:
    r = client.post("/api/auth/login", json={"username": "claims", "password": "Test-Passw0rd-2026"})
    assert r.status_code == 200, f"Login failed: {r.text}"
    return r.json()["access_token"]

def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── Health (public) ────────────────────────────────────────────────────────────
class TestHealth:
    def test_health_ok(self):
        r = client.get("/api/health")
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True

    def test_no_internal_paths(self):
        r = client.get("/api/health")
        body = r.text
        assert ".csv" not in body
        assert ".db"  not in body
        assert "\\FDE\\" not in body


# ── Auth ───────────────────────────────────────────────────────────────────────
class TestAuth:
    def test_login_valid(self):
        r = client.post("/api/auth/login", json={"username": "admin", "password": "Test-Passw0rd-2026"})
        assert r.status_code == 200
        d = r.json()
        assert "access_token" in d
        assert d["role"] == "admin"

    def test_login_invalid(self):
        r = client.post("/api/auth/login", json={"username": "admin", "password": "wrong"})
        assert r.status_code == 401

    def test_me_requires_auth(self):
        r = client.get("/api/auth/me")
        assert r.status_code == 401

    def test_me_returns_role(self):
        token = _admin_token()
        r = client.get("/api/auth/me", headers=_auth(token))
        assert r.status_code == 200
        assert r.json()["role"] == "admin"

    def test_role_in_response(self):
        r = client.post("/api/auth/login", json={"username": "claims", "password": "Test-Passw0rd-2026"})
        assert r.json()["role"] == "claims_finance"


# ── Analytics (RBAC-gated) ────────────────────────────────────────────────────
class TestAnalytics:
    def test_summary_requires_auth(self):
        r = client.get("/api/analytics/summary")
        assert r.status_code == 401

    def test_summary_accessible_to_admin(self):
        token = _admin_token()
        r = client.get("/api/analytics/summary", headers=_auth(token))
        assert r.status_code == 200
        d = r.json()
        # Either has batch data or the "no batch run" message
        assert "run_at" in d or "message" in d

    def test_claim_findings_requires_auth(self):
        r = client.get("/api/analytics/claim-findings")
        assert r.status_code == 401

    def test_claim_findings_accessible_to_claims(self):
        token = _claims_token()
        r = client.get("/api/analytics/claim-findings", headers=_auth(token))
        assert r.status_code == 200
        d = r.json()
        assert "findings" in d

    def test_at_risk_requires_auth(self):
        r = client.get("/api/analytics/at-risk-stock")
        assert r.status_code == 401

    def test_at_risk_accessible_to_admin(self):
        token = _admin_token()
        r = client.get("/api/analytics/at-risk-stock?days=90", headers=_auth(token))
        assert r.status_code == 200
        assert "batches" in r.json()

    def test_no_internal_paths_in_findings(self):
        token = _admin_token()
        r = client.get("/api/analytics/claim-findings", headers=_auth(token))
        body = r.text
        assert ".csv" not in body
        assert "\\FDE\\" not in body
        assert "sqlite" not in body.lower()

    def test_rsm_blocked_from_all_stock(self):
        """Sales RSM cannot call read:at_risk_all — only their cnf."""
        r = client.post("/api/auth/login", json={"username": "rsm_north", "password": "Test-Passw0rd-2026"})
        token = r.json()["access_token"]
        r2 = client.get("/api/analytics/at-risk-stock?days=90", headers=_auth(token))
        assert r2.status_code == 403


# ── Structured tool endpoints: authenticated and role-checked (they were public) ──────────────────
class TestToolEndpointsNeedAuth:
    PATHS = ["/api/at-risk-stock?days=90", "/api/fill-rate", "/api/quarter-spike", "/api/stockist/STK0054",
             "/api/stock-cover", "/api/dispatch-quality", "/api/scheme-cap"]

    @pytest.mark.parametrize("path", PATHS)
    def test_anonymous_is_refused(self, path):
        assert client.get(path).status_code == 401

    def test_ask_and_audit_refuse_anonymous(self):
        assert client.post("/api/ask", json={"question": "fill rate by territory"}).status_code == 401
        assert client.post("/api/audit-claim", json={"stockist_code": "STK0025", "batch_no": "F2440122", "qty_claimed": 5}).status_code == 401

    @pytest.mark.parametrize("path", PATHS)
    def test_admin_can_read(self, path):
        r = client.get(path, headers=_auth(_admin_token()))
        assert r.status_code == 200

    def test_fill_rate_shape(self):
        r = client.get("/api/fill-rate", headers=_auth(_admin_token())).json()
        assert "overall_fill_rate_pct" in r and r["quarter"] == "FY27Q2"

    def test_spike_shape(self):
        assert "phasing_by_quarter" in client.get("/api/quarter-spike", headers=_auth(_admin_token())).json()

    def test_days_filter_respected(self):
        h = _auth(_admin_token())
        r30, r180 = client.get("/api/at-risk-stock?days=30", headers=h), client.get("/api/at-risk-stock?days=180", headers=h)
        assert r30.json()["total_batches"] <= r180.json()["total_batches"]

    def test_stockist_known_and_unknown(self):
        h = _auth(_admin_token())
        assert client.get("/api/stockist/STK0054", headers=h).json()["found"] is True
        assert client.get("/api/stockist/STKZZZZ", headers=h).json().get("found") is False

    def test_rsm_cannot_read_network_stock(self):
        t = client.post("/api/auth/login", json={"username": "rsm_north", "password": "Test-Passw0rd-2026"}).json()["access_token"]
        assert client.get("/api/stock-cover", headers=_auth(t)).status_code == 403
        assert client.get("/api/dispatch-quality", headers=_auth(t)).status_code == 403


class TestAuditClaimEndpoint:
    def _post(self, body, who="claims"):
        t = client.post("/api/auth/login", json={"username": who, "password": "Test-Passw0rd-2026"}).json()["access_token"]
        return client.post("/api/audit-claim", json=body, headers=_auth(t))

    def test_inbox_repeat_is_recommended_for_rejection(self):
        r = self._post({"stockist_code": "STK0025", "batch_no": "F2440122", "qty_claimed": 272, "claim_date": "2026-05-12", "claim_type": "Near expiry"}).json()
        assert r["verdict"]["decision"] == "REJECT" and r["verdict"]["rule_id"] == "R_EXACT_REPEAT" and r["verdict"]["checks_failed"]

    def test_pre_window_batch_is_a_person(self):
        r = self._post({"stockist_code": "STK0007", "batch_no": "L2200185", "qty_claimed": 10, "claim_date": "2024-07-01", "claim_type": "Near expiry",
                        "original_invoice_ref": "INV/W01/2302/002323"}).json()
        assert r["verdict"]["decision"] == "NEEDS A PERSON"

    @pytest.mark.parametrize("bad", [{"qty_claimed": 0}, {"qty_claimed": -3}, {"qty_claimed": 1e12}, {"stockist_code": ""}])
    def test_bad_input_is_refused(self, bad):
        body = {"stockist_code": "STK0025", "batch_no": "F2440122", "qty_claimed": 5}
        body.update(bad)
        assert self._post(body).status_code == 422

    def test_rsm_may_not_audit_claims(self):
        r = self._post({"stockist_code": "STK0025", "batch_no": "F2440122", "qty_claimed": 5}, who="rsm_north")
        assert r.status_code == 403


class TestEvaluateSchemeEndpoint:
    """POST /api/evaluate-scheme: R6, policy 4.5. Code decides; the response carries latency, the tool that ran and its evidence."""

    def _post(self, body, who="rsm_north"):
        t = client.post("/api/auth/login", json={"username": who, "password": "Test-Passw0rd-2026"}).json()["access_token"]
        return client.post("/api/evaluate-scheme", json=body, headers=_auth(t))

    def _stockist_with_a_baseline(self):
        from agent import analysis
        for n in range(1, 157):
            g = analysis.scheme_gate(f"STK{n:04d}", "PFL1002", 1)
            if g.get("found") and g.get("baseline_packs_per_month_ex_month3"):
                return g
        raise AssertionError("no baseline found")

    def test_an_oversized_order_is_blocked_with_evidence_latency_and_the_tool_named(self):
        g = self._stockist_with_a_baseline()
        r = self._post({"stockist_code": g["stockist_code"], "sku_code": "PFL1002", "proposed_order_qty": g["baseline_packs_per_month_ex_month3"] * 5, "scheme_foc_qty": 20}).json()
        assert r["verdict"]["decision"] == "BLOCK SCHEME" and r["verdict"]["clause"].startswith("CO-POL-014 4.5")
        assert r["tools_called"] == ["analysis.scheme_gate"] and r["latency_ms"] >= 0 and r["model_calls"] == 0
        assert r["evidence"]["projected_months_of_stock_added"] > 2.5

    def test_unknown_stockist_is_not_invented(self):
        r = self._post({"stockist_code": "STK9999", "sku_code": "PFL1002", "proposed_order_qty": 100}).json()
        assert r["verdict"]["found"] is False

    @pytest.mark.parametrize("bad", [{"proposed_order_qty": -1}, {"proposed_order_qty": 1e12}, {"scheme_foc_qty": -5}, {"sku_code": ""}])
    def test_bad_input_is_refused(self, bad):
        body = {"stockist_code": "STK0054", "sku_code": "PFL1102", "proposed_order_qty": 100}
        body.update(bad)
        assert self._post(body).status_code == 422

    def test_claims_finance_may_not_evaluate_schemes(self):
        assert self._post({"stockist_code": "STK0054", "sku_code": "PFL1102", "proposed_order_qty": 100}, who="claims").status_code == 403

    def test_unauthenticated_is_refused(self):
        assert client.post("/api/evaluate-scheme", json={"stockist_code": "STK0054", "sku_code": "PFL1102", "proposed_order_qty": 1}).status_code == 401


class TestAuditClaimResponseShape:
    def test_reports_latency_and_the_deterministic_tool_with_no_model_call(self):
        t = client.post("/api/auth/login", json={"username": "claims", "password": "Test-Passw0rd-2026"}).json()["access_token"]
        r = client.post("/api/audit-claim", json={"stockist_code": "STK0025", "batch_no": "F2440122", "qty_claimed": 272, "claim_date": "2026-05-12"}, headers=_auth(t)).json()
        assert r["latency_ms"] >= 0 and r["tools_called"] == ["claim_checks.evaluate"] and r["model_calls"] == 0


class TestSecurityBasics:
    def test_health_is_minimal(self):
        assert client.get("/api/health").json() == {"ok": True}

    def test_login_is_rate_limited(self):
        from auth import ratelimit
        ratelimit.reset()
        ratelimit.ENABLED = True
        codes = [client.post("/api/auth/login", json={"username": "admin", "password": "wrong-password-x"}).status_code for _ in range(12)]
        assert 429 in codes
        ratelimit.ENABLED = False
        ratelimit.reset()

    def test_no_password_in_source(self):
        from pathlib import Path
        src = (Path(__file__).resolve().parent.parent / "db" / "database.py").read_text(encoding="utf-8")
        assert "@2026" not in src

    def test_cors_is_not_wildcard(self):
        r = client.options("/api/health", headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "GET"})
        assert r.headers.get("access-control-allow-origin") != "*"
        assert r.headers.get("access-control-allow-origin") != "https://evil.example"


# ── Admin (admin-only) ─────────────────────────────────────────────────────────
class TestAdmin:
    def test_users_requires_admin(self):
        token = _claims_token()
        r = client.get("/api/admin/users", headers=_auth(token))
        assert r.status_code == 403

    def test_users_accessible_to_admin(self):
        token = _admin_token()
        r = client.get("/api/admin/users", headers=_auth(token))
        assert r.status_code == 200
        users = r.json()
        assert len(users) >= 6
        usernames = [u["username"] for u in users]
        assert "admin" in usernames
        assert "claims" in usernames

    def test_no_passwords_in_user_list(self):
        token = _admin_token()
        r = client.get("/api/admin/users", headers=_auth(token))
        body = r.text
        assert "hashed_password" not in body
        assert "bcrypt" not in body

    def test_batch_history_accessible(self):
        token = _admin_token()
        r = client.get("/api/admin/batch-history", headers=_auth(token))
        assert r.status_code == 200
        assert isinstance(r.json(), list)


class TestPublicDemo:
    """Password-free panel entry: off by default, never admin, read roles only."""

    def test_off_by_default(self, monkeypatch):
        monkeypatch.delenv("SANKALP_PUBLIC_DEMO", raising=False)
        assert client.get("/api/auth/demo-status").json() == {"enabled": False, "roles": []}
        assert client.post("/api/auth/demo-login", json={"role": "cfo"}).status_code == 404

    def test_on_gives_read_roles_and_never_admin(self, monkeypatch):
        import db.database as dbd
        monkeypatch.setenv("SANKALP_PUBLIC_DEMO", "1")
        dbd.ensure_public_demo_users()
        s = client.get("/api/auth/demo-status").json()
        assert s["enabled"] and "admin" not in s["roles"] and set(s["roles"]) == {"claims_finance", "supply_chain", "cfo"}
        r = client.post("/api/auth/demo-login", json={"role": "supply_chain"})
        assert r.status_code == 200 and r.json()["role"] == "supply_chain"
        tok = r.json()["access_token"]
        assert client.get("/api/stock-cover", headers=_auth(tok)).status_code == 200
        assert client.get("/api/admin/users", headers=_auth(tok)).status_code == 403
        assert client.post("/api/auth/demo-login", json={"role": "admin"}).status_code == 400

    def test_demo_accounts_cannot_log_in_with_a_password(self, monkeypatch):
        import db.database as dbd
        monkeypatch.setenv("SANKALP_PUBLIC_DEMO", "1")
        dbd.ensure_public_demo_users()
        assert client.post("/api/auth/login", json={"username": "demo_cfo", "password": "anything-at-all-123"}).status_code == 401
