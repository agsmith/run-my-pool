"""
Tests for /users/* endpoints.

After the fix-security-gaps-and-lock-enforcement change:
- GET /users/ and GET /users/{user_id} require POOL_ADMIN or SUPER_ADMIN role
- user_id path parameters are now correctly typed as str (UUID)
- PATCH /users/{user_id}/password has been removed
"""

import pytest
import models


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _register_and_login(client, email="users_test@example.com", password="Test1234!"):
    """Register a user and return an auth token."""
    client.post("/auth/register", json={"email": email, "password": password})
    resp = client.post("/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, f"Login failed: {resp.json()}"
    return resp.json()["access_token"]


def _authed(token):
    """Return Authorization header dict for the given bearer token."""
    return {"Authorization": f"Bearer {token}"}


def _get_user_id(client, db_session, email):
    """Retrieve a user's id directly from the DB (avoids HTTP auth requirement)."""
    user = db_session.query(models.User).filter(models.User.email == email).first()
    assert user is not None, f"User {email} not found in DB"
    return user.id


def _make_pool_admin(db_session, email):
    """Promote a user to POOL_ADMIN role directly in the DB."""
    user = db_session.query(models.User).filter(models.User.email == email).first()
    assert user is not None, f"User {email} not found"
    user.role = models.UserRole.POOL_ADMIN
    db_session.commit()
    db_session.expire_all()


# ---------------------------------------------------------------------------
# Test class
# ---------------------------------------------------------------------------


class TestUserEndpoints:
    """Integration tests for user CRUD endpoints."""

    # -----------------------------------------------------------------------
    # GET /users/
    # -----------------------------------------------------------------------

    def test_list_users_no_auth(self, client):
        """GET /users/ without a token returns 401 or 403."""
        resp = client.get("/users/")
        assert resp.status_code in (401, 403), (
            f"Expected 401 or 403, got {resp.status_code}"
        )

    def test_list_users_regular_user_forbidden(self, client):
        """GET /users/ with a regular USER role token returns 403."""
        token = _register_and_login(client, email="regular_user@users.example.com")
        resp = client.get("/users/", headers=_authed(token))
        assert resp.status_code == 403, (
            f"Expected 403 for regular USER, got {resp.status_code}"
        )

    def test_list_users_returns_list_for_admin(self, client, db_session):
        """POOL_ADMIN can list users and the list contains the registered user."""
        _register_and_login(client, email="list_users@users.example.com")
        token = _register_and_login(client, email="list_admin@users.example.com")
        _make_pool_admin(db_session, "list_admin@users.example.com")

        resp = client.get("/users/", headers=_authed(token))
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        emails = [u["email"] for u in data]
        assert "list_users@users.example.com" in emails

    def test_admin_dashboard_lists_and_searches_users(self, client, db_session):
        _register_and_login(client, email="directory_target@users.example.com")
        token = _register_and_login(client, email="directory_admin@users.example.com")
        _make_pool_admin(db_session, "directory_admin@users.example.com")

        response = client.get(
            "/users/admin-dashboard?search=DIRECTORY_TARGET&limit=500",
            headers=_authed(token),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert data["active"] == 2
        assert data["pool_admins"] == 1
        assert [user["email"] for user in data["users"]] == ["directory_target@users.example.com"]

    # -----------------------------------------------------------------------
    # GET /users/{user_id}
    # -----------------------------------------------------------------------

    def test_get_user_no_auth(self, client):
        """GET /users/{user_id} without a token returns 401 or 403."""
        resp = client.get("/users/00000000-0000-0000-0000-000000000000")
        assert resp.status_code in (401, 403)

    def test_get_user_not_found(self, client, db_session):
        """
        GET /users/{user_id} with a valid admin token and a non-existent UUID returns 404.
        user_id is now correctly typed as str.
        """
        token = _register_and_login(
            client, email="get_notfound_admin@users.example.com"
        )
        _make_pool_admin(db_session, "get_notfound_admin@users.example.com")

        resp = client.get(
            "/users/00000000-0000-0000-0000-000000000000",
            headers=_authed(token),
        )
        assert resp.status_code == 404

    # -----------------------------------------------------------------------
    # DELETE /users/{user_id}
    # -----------------------------------------------------------------------

    def test_delete_user_requires_auth(self, client):
        """DELETE /users/{user_id} without a token returns 401 or 403."""
        resp = client.delete("/users/00000000-0000-0000-0000-000000000000")
        assert resp.status_code in (401, 403)

    def test_delete_user_not_found(self, client):
        """Authenticated DELETE for a non-existent UUID returns 404."""
        token = _register_and_login(client, email="delete_notfound@users.example.com")
        resp = client.delete(
            "/users/00000000-0000-0000-0000-000000000000",
            headers=_authed(token),
        )
        assert resp.status_code == 404

    def test_delete_user_success(self, client, db_session):
        """
        Authenticated DELETE /users/{user_id} with the correct UUID removes the user.
        user_id is now a str (UUID), matching User.id.
        """
        actor_token = _register_and_login(
            client, email="delete_actor@users.example.com"
        )
        _register_and_login(client, email="delete_target@users.example.com")
        target_id = _get_user_id(client, db_session, "delete_target@users.example.com")

        resp = client.delete(f"/users/{target_id}", headers=_authed(actor_token))
        assert resp.status_code == 200, (
            f"Expected 200 for delete with UUID, got {resp.status_code}: {resp.json()}"
        )

    # -----------------------------------------------------------------------
    # PATCH /users/{user_id}/email
    # -----------------------------------------------------------------------

    def test_update_email_requires_auth(self, client):
        """PATCH /users/{user_id}/email without a token returns 401 or 403."""
        resp = client.patch(
            "/users/00000000-0000-0000-0000-000000000000/email",
            params={"email": "new@test.com"},
        )
        assert resp.status_code in (401, 403)

    def test_update_email_not_found(self, client):
        """Authenticated PATCH email for a non-existent UUID returns 404."""
        token = _register_and_login(client, email="email_notfound@users.example.com")
        resp = client.patch(
            "/users/00000000-0000-0000-0000-000000000000/email",
            params={"email": "x@x.com"},
            headers=_authed(token),
        )
        assert resp.status_code == 404

    def test_update_email_success(self, client, db_session):
        """
        PATCH /users/{user_id}/email with the correct UUID updates the email.
        user_id is now correctly typed as str.
        """
        token = _register_and_login(client, email="email_before@users.example.com")
        user_id = _get_user_id(client, db_session, "email_before@users.example.com")

        resp = client.patch(
            f"/users/{user_id}/email",
            params={"email": "email_after@users.example.com"},
            headers=_authed(token),
        )
        assert resp.status_code == 200, (
            f"Expected 200 for email update with UUID, got {resp.status_code}: {resp.json()}"
        )

    # -----------------------------------------------------------------------
    # PATCH /users/{user_id}/password — removed
    # -----------------------------------------------------------------------

    def test_reset_password_endpoint_removed(self, client):
        """
        PATCH /users/{user_id}/password has been removed.
        Password reset is handled by POST /auth/forgot-password +
        POST /auth/reset-password instead.
        """
        resp = client.patch(
            "/users/00000000-0000-0000-0000-000000000000/password",
            params={"password": "newpass"},
        )
        # Route no longer exists — 404 or 405 expected
        assert resp.status_code in (404, 405), (
            f"Expected 404 or 405 for removed endpoint, got {resp.status_code}"
        )
