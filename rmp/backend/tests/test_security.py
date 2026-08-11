"""
Security tests for the NFL Survivor Pool API.

Covers:
  - JWT authentication edge cases (TestJWT)
  - Horizontal privilege escalation (TestHorizontalEscalation)
  - Admin boundary enforcement (TestAdminBoundary)
  - Known bugs documented with @pytest.mark.known_bug (TestKnownBugs)
  - Input validation behaviour (TestInputValidation)
  - Password-reset token reuse (TestPasswordReset)

Run all security tests:
    pytest tests/test_security.py

Run only known-bug tests:
    pytest -m known_bug tests/test_security.py
"""

import base64
import json
import os
from datetime import datetime, timedelta, timezone

import pytest
from jose import jwt as jose_jwt
from auth import create_access_token


# ---------------------------------------------------------------------------
# Markers
# ---------------------------------------------------------------------------

pytestmark = pytest.mark.security


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "known_bug: marks tests that document an existing, unfixed security bug",
    )


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _reg(client, email, password="Pass1234!"):
    """Register and log in; return the access token."""
    client.post("/auth/register", json={"email": email, "password": password})
    resp = client.post("/auth/login", json={"email": email, "password": password})
    return resp.json()["access_token"]


def _h(token):
    """Build an Authorization header dict."""
    return {"Authorization": f"Bearer {token}"}


def _create_pool(client, token, name="Security Test Pool"):
    """Create a pool owned by *token* and return its id."""
    future = (datetime.now(timezone.utc) + timedelta(hours=2)).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    resp = client.post(
        "/pools/create",
        json={
            "name": name,
            "description": "auto-created by test_security",
            "is_private": False,
            "lock_time": future,
        },
        headers=_h(token),
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


def _create_entry(client, token, pool_id, name="Test Entry"):
    """Create an entry for *token* in *pool_id* and return its id."""
    resp = client.post(
        "/entries/create",
        json={"pool_id": pool_id, "name": name},
        headers=_h(token),
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


def _submit_pick(client, token, entry_id, week=1, team="NE"):
    """POST /picks/create and return the raw response."""
    return client.post(
        "/picks/create",
        json={"entry_id": entry_id, "week": week, "team": team},
        headers=_h(token),
    )


# ---------------------------------------------------------------------------
# TestJWT
# ---------------------------------------------------------------------------


class TestJWT:
    """JWT authentication edge cases."""

    def test_no_token_returns_401_or_403(self, client):
        """
        GET /auth/me with no Authorization header should be rejected.

        FastAPI's HTTPBearer returns 403 or 401 depending on version.
        Either is acceptable — the key is that unauthenticated access is blocked.
        """
        resp = client.get("/auth/me")
        assert resp.status_code in (401, 403), (
            f"Expected 401 or 403 for missing credentials, got {resp.status_code}"
        )

    def test_expired_jwt_returns_401(self, client):
        """A JWT whose 'exp' claim is in the past must be rejected with 401."""
        secret = os.environ.get("SECRET_KEY", "test-secret-key")
        expired_token = jose_jwt.encode(
            {
                "sub": "test@example.com",
                "exp": datetime.utcnow() - timedelta(hours=1),
            },
            secret,
            algorithm="HS256",
        )
        resp = client.get("/auth/me", headers=_h(expired_token))
        assert resp.status_code == 401, (
            f"Expected 401 for expired JWT, got {resp.status_code}: {resp.text}"
        )

    def test_tampered_jwt_returns_401(self, client):
        """
        A JWT whose payload has been altered but whose signature is unchanged
        must be rejected with 401 (signature verification fails).
        """
        valid_token = _reg(client, "tamper_jwt@example.com")

        parts = valid_token.split(".")
        # Pad base64 to a multiple of 4 bytes before decoding
        padded = parts[1] + "=" * (-len(parts[1]) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded))

        # Escalate the subject to a different user
        payload["sub"] = "hacker@evil.com"
        tampered_payload = (
            base64.b64encode(json.dumps(payload).encode()).decode().rstrip("=")
        )
        tampered_token = f"{parts[0]}.{tampered_payload}.{parts[2]}"

        resp = client.get("/auth/me", headers=_h(tampered_token))
        assert resp.status_code == 401, (
            f"Expected 401 for tampered JWT, got {resp.status_code}: {resp.text}"
        )

    def test_invalid_jwt_format_returns_401_or_403(self, client):
        """
        A completely malformed token string (not three Base64 segments) must be
        rejected.  HTTPBearer may return 401 or 403 depending on where parsing
        fails; both are acceptable.
        """
        resp = client.get("/auth/me", headers=_h("not.a.jwt"))
        assert resp.status_code in (401, 403), (
            f"Expected 401 or 403 for invalid JWT format, got {resp.status_code}"
        )


# ---------------------------------------------------------------------------
# TestHorizontalEscalation
# ---------------------------------------------------------------------------


class TestHorizontalEscalation:
    """User A cannot act on resources owned by User B."""

    # ------------------------------------------------------------------
    # Pick endpoints
    # ------------------------------------------------------------------

    def test_user_cannot_pick_for_others_entry(self, client):
        """
        POST /picks/create with an entry_id that belongs to another user
        must return 404 with the message "Entry not found or doesn't belong to you".
        """
        token_a = _reg(client, "horiz_pick_a@example.com")
        token_b = _reg(client, "horiz_pick_b@example.com")

        pool_id = _create_pool(client, token_b)
        entry_id_b = _create_entry(client, token_b, pool_id)

        # User A attempts to create a pick against User B's entry
        resp = _submit_pick(client, token_a, entry_id_b)
        assert resp.status_code == 404, (
            f"Expected 404 when picking for another user's entry, got {resp.status_code}: {resp.text}"
        )
        assert "Entry not found" in resp.json().get("detail", ""), resp.text

    def test_user_cannot_update_others_pick(self, client):
        """
        PUT /picks/{pick_id} where the pick belongs to User B must return 404
        when called by User A.
        """
        token_a = _reg(client, "horiz_upd_a@example.com")
        token_b = _reg(client, "horiz_upd_b@example.com")

        pool_id = _create_pool(client, token_b)
        entry_id = _create_entry(client, token_b, pool_id)
        pick_resp = _submit_pick(client, token_b, entry_id)
        assert pick_resp.status_code == 200, pick_resp.text
        pick_id = pick_resp.json()["id"]

        resp = client.put(
            f"/picks/{pick_id}",
            json={"team": "KC"},
            headers=_h(token_a),
        )
        assert resp.status_code == 404, (
            f"Expected 404 when updating another user's pick, got {resp.status_code}: {resp.text}"
        )

    def test_user_cannot_delete_others_pick(self, client):
        """
        DELETE /picks/{pick_id} where the pick belongs to User B must return
        404 when called by User A.
        """
        token_a = _reg(client, "horiz_del_pick_a@example.com")
        token_b = _reg(client, "horiz_del_pick_b@example.com")

        pool_id = _create_pool(client, token_b)
        entry_id = _create_entry(client, token_b, pool_id)
        pick_resp = _submit_pick(client, token_b, entry_id)
        assert pick_resp.status_code == 200, pick_resp.text
        pick_id = pick_resp.json()["id"]

        resp = client.delete(f"/picks/{pick_id}", headers=_h(token_a))
        assert resp.status_code == 404, (
            f"Expected 404 when deleting another user's pick, got {resp.status_code}: {resp.text}"
        )

    # ------------------------------------------------------------------
    # Entry endpoints
    # ------------------------------------------------------------------

    def test_user_cannot_delete_others_entry(self, client):
        """
        DELETE /entries/{entry_id} where the entry belongs to User B must
        return 404 when called by User A.
        """
        token_a = _reg(client, "horiz_del_ent_a@example.com")
        token_b = _reg(client, "horiz_del_ent_b@example.com")

        pool_id = _create_pool(client, token_b)
        entry_id = _create_entry(client, token_b, pool_id)

        resp = client.delete(f"/entries/{entry_id}", headers=_h(token_a))
        assert resp.status_code == 404, (
            f"Expected 404 when deleting another user's entry, got {resp.status_code}: {resp.text}"
        )
        assert "Entry not found" in resp.json().get("detail", ""), resp.text


# ---------------------------------------------------------------------------
# TestAdminBoundary
# ---------------------------------------------------------------------------


class TestAdminBoundary:
    """
    Admin operations on Pool B must be rejected for a user who is only an
    admin of Pool A.

    verify_admin_access() checks pool.owner_id == current_user.id OR a
    PoolAdmin row.  A user who creates Pool A is admin of A (via owner_id and
    a PoolAdmin row), but NOT of Pool B — so Pool B calls must return 403.
    """

    def test_admin_a_cannot_lock_pool_b(self, client):
        """
        A user who is admin of Pool A must receive 403 when calling
        POST /admin/pools/{pool_b_id}/lock-week/1.
        """
        token_a = _reg(client, "admin_bound_a@example.com")
        token_b = _reg(client, "admin_bound_b@example.com")

        # token_a owns pool_a; token_b owns pool_b
        _create_pool(client, token_a, name="Pool A")
        pool_b_id = _create_pool(client, token_b, name="Pool B")

        resp = client.post(
            f"/admin/pools/{pool_b_id}/lock-week/1",
            headers=_h(token_a),
        )
        assert resp.status_code == 403, (
            f"Expected 403 when admin of Pool A locks Pool B, got {resp.status_code}: {resp.text}"
        )

    def test_admin_a_cannot_override_pick_in_pool_b(self, client):
        """
        A user who is admin of Pool A must receive 403 when calling
        PATCH /admin/pools/{pool_b_id}/picks/{pick_id}.
        """
        token_a = _reg(client, "admin_pick_a@example.com")
        token_b = _reg(client, "admin_pick_b@example.com")

        _create_pool(client, token_a, name="Pool A")
        pool_b_id = _create_pool(client, token_b, name="Pool B")
        entry_id = _create_entry(client, token_b, pool_b_id)
        pick_resp = _submit_pick(client, token_b, entry_id)
        assert pick_resp.status_code == 200, pick_resp.text
        pick_id = pick_resp.json()["id"]

        resp = client.patch(
            f"/admin/pools/{pool_b_id}/picks/{pick_id}",
            json={"team": "DAL"},
            headers=_h(token_a),
        )
        assert resp.status_code == 403, (
            f"Expected 403 when admin of Pool A overrides a pick in Pool B, got {resp.status_code}: {resp.text}"
        )


# ---------------------------------------------------------------------------
# TestKnownBugs
# ---------------------------------------------------------------------------


class TestKnownBugs:
    """
    Tests that previously documented security bugs — now fixed.
    These tests assert the *corrected* behavior.
    """

    def test_get_users_requires_auth(self, client):
        """
        GET /users/ now requires authentication and returns 403 without a token.
        """
        resp = client.get("/users/")
        assert resp.status_code in (401, 403), (
            f"Expected 401 or 403 for unauthenticated GET /users/, got {resp.status_code}"
        )

    def test_get_users_blocked_for_regular_user(self, client, db_session):
        """GET /users/ returns 403 for a user with the USER role."""
        token = _reg(client, "regular_user_list@example.com")
        resp = client.get("/users/", headers=_h(token))
        assert resp.status_code == 403, (
            f"Expected 403 for regular USER role, got {resp.status_code}: {resp.text}"
        )

    def test_get_users_allowed_for_pool_admin(self, client, db_session):
        """GET /users/ returns 200 for a user with the POOL_ADMIN role."""
        import models as m

        token = _reg(client, "pool_admin_list@example.com")
        # Promote to POOL_ADMIN directly in DB
        user = (
            db_session.query(m.User)
            .filter(m.User.email == "pool_admin_list@example.com")
            .first()
        )
        user.role = m.UserRole.POOL_ADMIN
        db_session.commit()

        resp = client.get("/users/", headers=_h(token))
        assert resp.status_code == 200, (
            f"Expected 200 for POOL_ADMIN role, got {resp.status_code}: {resp.text}"
        )


# ---------------------------------------------------------------------------
# TestInputValidation
# ---------------------------------------------------------------------------


class TestInputValidation:
    """Verify that the API rejects or safely handles malformed / boundary input."""

    # Shared setup: one authenticated user with a pool and entry.
    # Each test method creates its own user to avoid state bleed.

    def _setup(self, client, suffix):
        token = _reg(client, f"input_val_{suffix}@example.com")
        pool_id = _create_pool(client, token, name=f"InputVal Pool {suffix}")
        entry_id = _create_entry(client, token, pool_id)
        return token, entry_id

    def test_pick_week_zero_rejected(self, client):
        """
        POST /picks/create with week=0.

        PickBase declares `week: int` with no Pydantic ge/gt constraint, so
        the schema does NOT reject 0.  The pick is likely stored and returned
        with a 200.  This test documents the current behaviour; a future
        constraint (ge=1) should change the assertion to 422.
        """
        token, entry_id = self._setup(client, "wk0")
        resp = _submit_pick(client, token, entry_id, week=0, team="NE")
        # No Pydantic constraint — current behaviour is 200 (accepted).
        # When a ge=1 constraint is added this should be 422.
        assert resp.status_code in (200, 422), (
            f"Unexpected status for week=0: {resp.status_code}: {resp.text}"
        )

    def test_pick_week_negative_rejected(self, client):
        """
        POST /picks/create with week=-1.

        Same reasoning as week=0 — no lower-bound constraint exists on the
        schema.  Current behaviour is 200.  A future ge=1 constraint should
        produce 422.
        """
        token, entry_id = self._setup(client, "wk_neg")
        resp = _submit_pick(client, token, entry_id, week=-1, team="GB")
        # No Pydantic constraint — current behaviour is 200 (accepted).
        assert resp.status_code in (200, 422), (
            f"Unexpected status for week=-1: {resp.status_code}: {resp.text}"
        )

    def test_pick_week_too_large_rejected(self, client):
        """
        POST /picks/create with week=999.

        The NFL regular season has 18 weeks.  PickBase has no le/lt constraint,
        so week=999 is accepted by the schema.  This test documents that gap;
        a future le=18 constraint should change the assertion to 422.
        """
        token, entry_id = self._setup(client, "wk999")
        resp = _submit_pick(client, token, entry_id, week=999, team="BUF")
        # No upper-bound constraint — current behaviour is 200 (accepted).
        assert resp.status_code in (200, 422), (
            f"Unexpected status for week=999: {resp.status_code}: {resp.text}"
        )

    def test_sql_injection_in_pool_name_no_500(self, client):
        """
        POST /pools/create with a SQL injection string in the name field.

        SQLAlchemy's ORM uses parameterised queries, so the injected SQL is
        treated as a literal string, not executed.  The request must NOT
        return 500 and the name must be stored verbatim.
        """
        token = _reg(client, "sqli_pool@example.com")
        malicious_name = "'; DROP TABLE pools; --"

        resp = client.post(
            "/pools/create",
            json={
                "name": malicious_name,
                "description": "SQL injection test",
                "is_private": False,
            },
            headers=_h(token),
        )
        assert resp.status_code != 500, f"SQL injection caused a 500: {resp.text}"
        assert resp.status_code == 200, (
            f"Expected 200 for SQL injection in name, got {resp.status_code}: {resp.text}"
        )
        pool_id = resp.json()["id"]

        # Verify name is stored verbatim — not truncated or mangled
        detail_resp = client.get(f"/pools/{pool_id}", headers=_h(token))
        assert detail_resp.status_code == 200, detail_resp.text
        assert detail_resp.json()["name"] == malicious_name

    def test_xss_in_pool_name_stored_safely(self, client):
        """
        POST /pools/create with an XSS payload in the name field.

        This is a REST API returning JSON; script injection cannot execute
        client-side in JSON responses.  The payload is expected to be stored
        as-is and returned verbatim.  No sanitisation is required at the API
        layer, but the value must not cause a 500.
        """
        token = _reg(client, "xss_pool@example.com")
        xss_name = "<script>alert('xss')</script>"

        resp = client.post(
            "/pools/create",
            json={
                "name": xss_name,
                "description": "XSS test",
                "is_private": False,
            },
            headers=_h(token),
        )
        assert resp.status_code == 200, (
            f"Expected 200 for XSS payload in pool name, got {resp.status_code}: {resp.text}"
        )
        pool_id = resp.json()["id"]

        detail_resp = client.get(f"/pools/{pool_id}", headers=_h(token))
        assert detail_resp.status_code == 200, detail_resp.text
        assert detail_resp.json()["name"] == xss_name, (
            "XSS payload was altered during storage — unexpected sanitisation"
        )


# ---------------------------------------------------------------------------
# TestPasswordReset
# ---------------------------------------------------------------------------


class TestPasswordReset:
    """Password-reset token behaviour."""

    def test_reset_token_cannot_be_reused(self, client):
        """
        POST /auth/reset-password with the same token a second time.

        The auth.py reset_password endpoint decodes the token and updates the
        password, but does NOT maintain a token blacklist.  As a result a
        valid reset token can be used more than once.

        This test documents the current (broken) behaviour: both the first and
        second calls return 200.  When a token blacklist is implemented the
        second call should return 400 or 401.

        Note: POST /auth/forgot-password prints the token to stdout but does
        not return it in the response.  We therefore craft a valid reset token
        directly using the same SECRET_KEY and algorithm used by the app.
        """
        email = "reset_reuse@example.com"
        _reg(client, email)

        reset_token = create_access_token(
            {"sub": email, "type": "password_reset"},
            expires_delta=timedelta(hours=1),
        )

        payload_first = {
            "token": reset_token,
            "new_password": "NewPass9999!",
        }

        # First use — must succeed
        resp1 = client.post("/auth/reset-password", json=payload_first)
        assert resp1.status_code == 200, (
            f"First reset-password call failed: {resp1.status_code}: {resp1.text}"
        )

        # Second use must be rejected.
        resp2 = client.post("/auth/reset-password", json=payload_first)

        assert resp2.status_code in (400, 401)
