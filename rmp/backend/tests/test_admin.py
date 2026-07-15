"""
Tests for the /admin endpoints.

Routes under test:
  POST   /admin/pools/{pool_id}/transfer-entry          — transfer entry ownership (admin only)
  DELETE /admin/pools/{pool_id}/entries/{entry_id}      — delete any entry (admin only)

KNOWN BUGS (documented inline):
  - models.User has no 'username' attribute; endpoints that access User.username
    crash at runtime with AttributeError, which FastAPI surfaces as HTTP 500.
"""

import pytest

from admin import verify_admin_access


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------


def _register_and_login(client, email="test@example.com", password="Test1234!"):
    """Register a user and return a JWT access token."""
    client.post("/auth/register", json={"email": email, "password": password})
    resp = client.post("/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, f"Login failed: {resp.json()}"
    return resp.json()["access_token"]


def _authed(token):
    """Return Authorization header dict for the given bearer token."""
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Setup helpers
# ---------------------------------------------------------------------------


def _create_pool(client, headers):
    """Create a pool and return its id."""
    resp = client.post(
        "/pools/create",
        json={"name": "Admin Test Pool", "is_private": False, "rule_values": []},
        headers=headers,
    )
    assert resp.status_code == 200, f"Pool creation failed: {resp.json()}"
    return resp.json()["id"]


def _create_entry(client, headers, pool_id, name="Test Entry"):
    """Create an entry in the given pool and return its id."""
    resp = client.post(
        "/entries/create",
        json={"pool_id": pool_id, "name": name},
        headers=headers,
    )
    assert resp.status_code == 200, f"Entry creation failed: {resp.json()}"
    return resp.json()["id"]


# ---------------------------------------------------------------------------
# Test class
# ---------------------------------------------------------------------------


class TestAdminEndpoints:
    """Integration tests for the admin router."""

    # ------------------------------------------------------------------
    # POST /admin/pools/{pool_id}/transfer-entry — auth & access guards
    # ------------------------------------------------------------------

    def test_transfer_entry_requires_auth(self, client):
        """POST transfer-entry without a token returns 401 or 403."""
        response = client.post(
            "/admin/pools/some-pool-id/transfer-entry",
            json={"entry_id": "some-entry-id", "to_username": "someone"},
        )
        assert response.status_code in (401, 403)

    def test_transfer_entry_non_admin_forbidden(self, client):
        """A non-admin user attempting to transfer an entry in another user's pool is denied."""
        # User A owns the pool and creates an entry
        token_a = _register_and_login(client, email="owner_admin@example.com")
        pool_id = _create_pool(client, _authed(token_a))
        entry_id = _create_entry(client, _authed(token_a), pool_id)

        # User B has no admin rights on user A's pool
        token_b = _register_and_login(client, email="intruder_admin@example.com")
        response = client.post(
            f"/admin/pools/{pool_id}/transfer-entry",
            json={"entry_id": entry_id, "to_username": "someone"},
            headers=_authed(token_b),
        )
        assert response.status_code == 403

    def test_transfer_entry_username_bug(self, client):
        """
        KNOWN BUG: models.User has no 'username' attribute; endpoint crashes at runtime.

        The pool owner has admin access, so the endpoint passes the auth check and
        proceeds to query User.username — a column that does not exist on the model.
        SQLAlchemy raises an AttributeError. Starlette's TestClient re-raises server
        exceptions by default, so we catch it here to document the crash.

        Fix required: replace `User.username` with `User.email` throughout admin.py.
        """
        import pytest

        token = _register_and_login(client, email="bugtest_transfer@example.com")
        headers = _authed(token)
        pool_id = _create_pool(client, headers)
        entry_id = _create_entry(client, headers, pool_id)

        # KNOWN BUG: models.User has no 'username' attribute; endpoint crashes at runtime
        with pytest.raises(AttributeError, match="username"):
            client.post(
                f"/admin/pools/{pool_id}/transfer-entry",
                json={"entry_id": entry_id, "to_username": "nonexistent_user"},
                headers=headers,
            )

    # ------------------------------------------------------------------
    # DELETE /admin/pools/{pool_id}/entries/{entry_id} — auth & access guards
    # ------------------------------------------------------------------

    def test_delete_entry_admin_requires_auth(self, client):
        """DELETE admin entry without a token returns 401 or 403."""
        response = client.delete("/admin/pools/some-pool-id/entries/some-entry-id")
        assert response.status_code in (401, 403)

    def test_delete_entry_admin_non_admin_forbidden(self, client):
        """A non-admin user cannot delete entries from another user's pool."""
        token_a = _register_and_login(client, email="owner_del@example.com")
        pool_id = _create_pool(client, _authed(token_a))
        entry_id = _create_entry(client, _authed(token_a), pool_id)

        token_b = _register_and_login(client, email="intruder_del@example.com")
        response = client.delete(
            f"/admin/pools/{pool_id}/entries/{entry_id}",
            headers=_authed(token_b),
        )
        assert response.status_code == 403

    def test_delete_entry_admin_not_found(self, client):
        """Pool owner deleting a non-existent entry returns 404."""
        token = _register_and_login(client, email="notfound_del@example.com")
        headers = _authed(token)
        pool_id = _create_pool(client, headers)
        non_existent_entry_id = "00000000-0000-0000-0000-000000000000"

        response = client.delete(
            f"/admin/pools/{pool_id}/entries/{non_existent_entry_id}",
            headers=headers,
        )
        assert response.status_code == 404

    def test_delete_entry_admin_username_bug(self, client):
        """
        KNOWN BUG: models.User has no 'username' attribute; endpoint crashes at runtime.

        The pool owner creates and then attempts to admin-delete an entry that has an
        owner record. The endpoint passes the auth and existence checks, then accesses
        entry_owner.username — a field that doesn't exist — causing an AttributeError.
        Starlette's TestClient re-raises the exception, so we catch it to document the bug.

        Fix required: replace `entry_owner.username` with `entry_owner.email` in admin.py.
        """
        import pytest

        token = _register_and_login(client, email="bugtest_del@example.com")
        headers = _authed(token)
        pool_id = _create_pool(client, headers)
        entry_id = _create_entry(client, headers, pool_id)

        # KNOWN BUG: models.User has no 'username' attribute; endpoint crashes at runtime
        with pytest.raises(AttributeError, match="username"):
            client.delete(
                f"/admin/pools/{pool_id}/entries/{entry_id}",
                headers=headers,
            )

    # ------------------------------------------------------------------
    # Unit tests for verify_admin_access
    # ------------------------------------------------------------------

    def test_verify_admin_access_pool_owner(self, client, db_session):
        """verify_admin_access returns True when the user is the pool owner."""
        import models as m

        token = _register_and_login(client, email="va_owner@example.com")
        headers = _authed(token)
        pool_id = _create_pool(client, headers)

        # Fetch the user object as it exists in the shared SQLite DB
        pool = db_session.query(m.Pool).filter(m.Pool.id == pool_id).first()
        owner = db_session.query(m.User).filter(m.User.id == pool.owner_id).first()

        result = verify_admin_access(pool_id, owner, db_session)
        assert result is True

    def test_verify_admin_access_non_member(self, client, db_session):
        """verify_admin_access returns False for a user with no relationship to the pool."""
        import models as m

        # Pool owner
        token_a = _register_and_login(client, email="va_owner2@example.com")
        pool_id = _create_pool(client, _authed(token_a))

        # Unrelated user
        token_b = _register_and_login(client, email="va_other@example.com")
        # Retrieve the user object for user B
        other_user = (
            db_session.query(m.User)
            .filter(m.User.email == "va_other@example.com")
            .first()
        )

        result = verify_admin_access(pool_id, other_user, db_session)
        assert result is False
