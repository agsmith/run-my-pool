"""
Security tests covering OWASP Top 10.
All tests marked @pytest.mark.security.
Run with: pytest -m security
"""

import base64
import json
import os

import pytest
from jose import jwt as jose_jwt
from datetime import datetime, timedelta, timezone


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _reg(client, email, password="SecurePass1!"):
    client.post("/auth/register", json={"email": email, "password": password})
    resp = client.post("/auth/login", json={"email": email, "password": password})
    return resp.json()["access_token"]


def _h(token):
    return {"Authorization": f"Bearer {token}"}


def _create_pool(client, token, name="Security Pool"):
    future = (datetime.now(timezone.utc) + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S")
    resp = client.post(
        "/pools/create",
        json={
            "name": name,
            "description": "Security test pool",
            "is_private": False,
            "lock_time": future,
        },
        headers=_h(token),
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


def _create_entry(client, token, pool_id, name="My Entry"):
    resp = client.post(
        "/entries/create",
        json={"pool_id": pool_id, "name": name},
        headers=_h(token),
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


def _submit_pick(client, token, entry_id, week, team):
    return client.post(
        "/picks/create",
        json={"entry_id": entry_id, "week": week, "team": team},
        headers=_h(token),
    )


# ---------------------------------------------------------------------------
# A01 - Broken Access Control
# ---------------------------------------------------------------------------


@pytest.mark.security
class TestA01BrokenAccessControl:
    def test_user_cannot_modify_another_users_pick(self, client):
        """User B cannot update User A's pick — returns 404 (ownership enforced)."""
        token_a = _reg(client, "a01_a@example.com")
        token_b = _reg(client, "a01_b@example.com")

        pool_id = _create_pool(client, token_a)
        entry_id = _create_entry(client, token_a, pool_id)

        resp = _submit_pick(client, token_a, entry_id, week=1, team="NE")
        assert resp.status_code == 200
        pick_id = resp.json()["id"]

        # User B attempts to update User A's pick
        resp = client.put(
            f"/picks/{pick_id}",
            json={"team": "KC"},
            headers=_h(token_b),
        )
        assert resp.status_code == 404

    def test_user_cannot_delete_another_users_entry(self, client):
        """User B cannot delete User A's entry — returns 404."""
        token_a = _reg(client, "a01_del_a@example.com")
        token_b = _reg(client, "a01_del_b@example.com")

        pool_id = _create_pool(client, token_a)
        entry_id = _create_entry(client, token_a, pool_id)

        resp = client.delete(f"/entries/{entry_id}", headers=_h(token_b))
        assert resp.status_code == 404

    def test_non_admin_cannot_call_lock_week(self, client):
        """A non-admin user cannot call the admin lock-week endpoint — returns 403."""
        token_admin = _reg(client, "a01_admin@example.com")
        token_other = _reg(client, "a01_other@example.com")

        pool_id = _create_pool(client, token_admin)

        resp = client.post(
            f"/admin/pools/{pool_id}/lock-week/1",
            headers=_h(token_other),
        )
        assert resp.status_code == 403

    def test_user_cannot_read_another_pools_messages(self, client):
        """A user with no entry in pool1 cannot read its messages — returns 403."""
        token_a = _reg(client, "a01_msg_a@example.com")
        token_b = _reg(client, "a01_msg_b@example.com")

        pool_id = _create_pool(client, token_a)
        # User A has an entry; User B does not
        _create_entry(client, token_a, pool_id)

        resp = client.get(f"/messages/pool/{pool_id}", headers=_h(token_b))
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# A03 - Injection
# ---------------------------------------------------------------------------


@pytest.mark.security
class TestA03Injection:
    def test_sql_metacharacters_in_pool_name(self, client):
        """SQL metacharacters in pool name are stored as a literal string."""
        token = _reg(client, "sql_inject@example.com")
        malicious_name = "'; DROP TABLE pools; --"

        resp = client.post(
            "/pools/create",
            json={
                "name": malicious_name,
                "description": "injection test",
                "is_private": False,
            },
            headers=_h(token),
        )
        assert resp.status_code == 200
        pool_id = resp.json()["id"]

        # Read back and confirm name is stored verbatim
        resp = client.get(f"/pools/{pool_id}", headers=_h(token))
        assert resp.status_code == 200
        assert resp.json()["name"] == malicious_name

    def test_xss_payload_in_message_stored_as_text(self, client):
        """XSS payload in a message is returned as plain JSON text, not executed."""
        token = _reg(client, "xss_msg@example.com")
        pool_id = _create_pool(client, token)
        _create_entry(client, token, pool_id)

        xss_payload = "<script>alert(1)</script>"
        resp = client.post(
            f"/messages/pool/{pool_id}",
            json={"pool_id": pool_id, "message": xss_payload},
            headers=_h(token),
        )
        assert resp.status_code == 200

        # Read back messages and verify the string is returned verbatim
        resp = client.get(f"/messages/pool/{pool_id}", headers=_h(token))
        assert resp.status_code == 200
        messages = resp.json()
        assert any(m["message"] == xss_payload for m in messages)

    def test_oversized_message_rejected(self, client):
        """A message exceeding 250 characters returns 400."""
        token = _reg(client, "big_msg@example.com")
        pool_id = _create_pool(client, token)
        _create_entry(client, token, pool_id)

        long_message = "A" * 251
        resp = client.post(
            f"/messages/pool/{pool_id}",
            json={"pool_id": pool_id, "message": long_message},
            headers=_h(token),
        )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# A07 - Authentication Failures
# ---------------------------------------------------------------------------


@pytest.mark.security
class TestA07AuthFailures:
    def test_expired_jwt_rejected(self, client):
        """A JWT with an expiry in the past is rejected with 401."""
        secret = os.environ.get("SECRET_KEY", "test-secret-key")
        token = jose_jwt.encode(
            {
                "sub": "expired@example.com",
                "exp": datetime.now(timezone.utc) - timedelta(seconds=1),
            },
            secret,
            algorithm="HS256",
        )
        resp = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401

    def test_tampered_jwt_rejected(self, client):
        """A JWT whose payload has been tampered with is rejected with 401."""
        token = _reg(client, "tamper@example.com")

        # Split the token into its three parts
        header, payload_b64, signature = token.split(".")

        # Decode payload, tamper with it, re-encode
        # Pad base64 to a multiple of 4 bytes
        padded = payload_b64 + "=" * (-len(payload_b64) % 4)
        payload_data = json.loads(base64.urlsafe_b64decode(padded))
        payload_data["sub"] = "attacker@example.com"
        tampered_payload = (
            base64.urlsafe_b64encode(json.dumps(payload_data).encode())
            .rstrip(b"=")
            .decode()
        )

        tampered_token = f"{header}.{tampered_payload}.{signature}"
        resp = client.get(
            "/auth/me", headers={"Authorization": f"Bearer {tampered_token}"}
        )
        assert resp.status_code == 401

    def test_missing_token_returns_401_or_403(self, client):
        """Calling a protected endpoint with no token returns 401 or 403."""
        resp = client.get("/pools/my-pools")
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# A05 - Security Misconfiguration
# ---------------------------------------------------------------------------


@pytest.mark.security
class TestA05SecurityMisconfiguration:
    def test_user_enumeration_endpoint_unauthenticated_known_gap(self, client):
        """
        GET /users/ without a token returns 200 — this is a known security gap.
        The endpoint does not require authentication, allowing unauthenticated
        user enumeration.  This test documents the current behavior so any
        future fix (returning 401/403) is immediately visible.
        """
        resp = client.get("/users/")
        # Known gap: endpoint is publicly accessible without authentication.
        # When this is fixed, this assertion will fail and the test should be
        # updated to assert resp.status_code in (401, 403).
        assert resp.status_code == 200

    def test_cors_allows_configured_origin(self, client):
        """OPTIONS preflight response includes the Access-Control-Allow-Origin header."""
        resp = client.options(
            "/auth/login",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
            },
        )
        # CORS headers should be present in the response
        assert "access-control-allow-origin" in resp.headers
