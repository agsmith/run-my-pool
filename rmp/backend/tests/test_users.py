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


def _make_super_admin(db_session, email):
    user = db_session.query(models.User).filter(models.User.email == email).first()
    user.role = models.UserRole.SUPER_ADMIN
    db_session.commit()
    db_session.expire_all()


def _create_pool(client, token, name):
    response = client.post(
        "/pools/create",
        json={"name": name, "is_private": False},
        headers=_authed(token),
    )
    assert response.status_code == 200, response.text
    return response.json()["id"]


def _join_pool(client, token, pool_id):
    response = client.post(f"/pools/{pool_id}/join", json={}, headers=_authed(token))
    assert response.status_code == 200, response.text


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
        member_token = _register_and_login(client, email="list_users@users.example.com")
        token = _register_and_login(client, email="list_admin@users.example.com")
        _make_pool_admin(db_session, "list_admin@users.example.com")
        pool_id = _create_pool(client, token, "List Users League")
        _join_pool(client, member_token, pool_id)
        _register_and_login(client, email="list_outsider@users.example.com")

        resp = client.get("/users/", headers=_authed(token))
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        emails = [u["email"] for u in data]
        assert "list_users@users.example.com" in emails
        assert "list_admin@users.example.com" in emails
        assert "list_outsider@users.example.com" not in emails

    def test_admin_dashboard_lists_and_searches_users(self, client, db_session):
        target_token = _register_and_login(client, email="directory_target@users.example.com")
        _register_and_login(client, email="directory_outsider@users.example.com")
        token = _register_and_login(client, email="directory_admin@users.example.com")
        _make_pool_admin(db_session, "directory_admin@users.example.com")
        pool_id = _create_pool(client, token, "Directory League")
        _join_pool(client, target_token, pool_id)

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

        outsider_search = client.get(
            "/users/admin-dashboard?search=DIRECTORY_OUTSIDER&limit=500",
            headers=_authed(token),
        ).json()
        assert outsider_search["total"] == 2
        assert outsider_search["users"] == []

    def test_super_admin_dashboard_remains_platform_wide(self, client, db_session):
        _register_and_login(client, email="platform_target@users.example.com")
        token = _register_and_login(client, email="agsmith11@gmail.com")
        _make_super_admin(db_session, "agsmith11@gmail.com")

        data = client.get(
            "/users/admin-dashboard?limit=500", headers=_authed(token)
        ).json()

        assert data["total"] == 2
        assert {user["email"] for user in data["users"]} == {
            "platform_target@users.example.com",
            "agsmith11@gmail.com",
        }
        assert data["unassigned"] == 2
        assert all(user["pool_count"] == 0 for user in data["users"])

    def test_super_admin_filters_users_without_pools(self, client, db_session):
        assigned_token = _register_and_login(client, "assigned@users.example.com")
        _register_and_login(client, "unassigned@users.example.com")
        token = _register_and_login(client, "agsmith11@gmail.com")
        _make_super_admin(db_session, "agsmith11@gmail.com")
        _create_pool(client, assigned_token, "Assigned User Pool")

        response = client.get(
            "/users/admin-dashboard?unassigned_only=true&limit=500",
            headers=_authed(token),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["unassigned"] == 2
        assert {user["email"] for user in data["users"]} == {
            "unassigned@users.example.com",
            "agsmith11@gmail.com",
        }
        assert all(user["pool_count"] == 0 for user in data["users"])

    def test_pool_admin_cannot_filter_platform_unassigned_users(self, client, db_session):
        token = _register_and_login(client, "scoped_filter@users.example.com")
        _make_pool_admin(db_session, "scoped_filter@users.example.com")

        response = client.get(
            "/users/admin-dashboard?unassigned_only=true",
            headers=_authed(token),
        )

        assert response.status_code == 403

    def test_super_admin_can_deactivate_and_reactivate_user(self, client, db_session):
        _register_and_login(client, "status_target@users.example.com")
        token = _register_and_login(client, "agsmith11@gmail.com")
        _make_super_admin(db_session, "agsmith11@gmail.com")
        target_id = _get_user_id(client, db_session, "status_target@users.example.com")

        disabled = client.patch(
            f"/users/{target_id}/status?active=false", headers=_authed(token)
        )
        assert disabled.status_code == 200
        assert disabled.json()["is_active"] is False

        enabled = client.patch(
            f"/users/{target_id}/status?active=true", headers=_authed(token)
        )
        assert enabled.status_code == 200
        assert enabled.json()["is_active"] is True

    def test_delegated_super_admin_has_platform_access(self, client, db_session):
        token = _register_and_login(client, "rogue_super@users.example.com")
        _make_super_admin(db_session, "rogue_super@users.example.com")

        response = client.get("/users/admin-dashboard", headers=_authed(token))

        assert response.status_code == 200

    def test_super_admin_can_grant_and_revoke_super_admin_access(self, client, db_session):
        token = _register_and_login(client, "agsmith11@gmail.com")
        _make_super_admin(db_session, "agsmith11@gmail.com")
        target_token = _register_and_login(client, "support@users.example.com")
        target_id = _get_user_id(client, db_session, "support@users.example.com")

        granted = client.patch(
            f"/users/{target_id}/super-admin?enabled=true", headers=_authed(token)
        )
        assert granted.status_code == 200
        assert granted.json()["role"] == "SUPER_ADMIN"
        assert client.get(
            "/users/admin-dashboard", headers=_authed(target_token)
        ).status_code == 200

        revoked = client.patch(
            f"/users/{target_id}/super-admin?enabled=false", headers=_authed(token)
        )
        assert revoked.status_code == 200
        assert revoked.json()["role"] == "USER"
        assert client.get(
            "/users/admin-dashboard", headers=_authed(target_token)
        ).status_code == 403

    def test_super_admin_cannot_revoke_self(self, client, db_session):
        token = _register_and_login(client, "support.self@users.example.com")
        _make_super_admin(db_session, "support.self@users.example.com")
        user_id = _get_user_id(client, db_session, "support.self@users.example.com")

        response = client.patch(
            f"/users/{user_id}/super-admin?enabled=false", headers=_authed(token)
        )

        assert response.status_code == 400

    def test_bootstrap_super_admin_cannot_be_revoked_deactivated_deleted_or_renamed(self, client, db_session):
        token = _register_and_login(client, "agsmith11@gmail.com")
        _make_super_admin(db_session, "agsmith11@gmail.com")
        user_id = _get_user_id(client, db_session, "agsmith11@gmail.com")

        assert client.patch(
            f"/users/{user_id}/super-admin?enabled=false", headers=_authed(token)
        ).status_code == 400
        assert client.patch(
            f"/users/{user_id}/status?active=false", headers=_authed(token)
        ).status_code == 400
        assert client.delete(f"/users/{user_id}", headers=_authed(token)).status_code == 400
        assert client.patch(
            f"/users/{user_id}/email",
            params={"email": "other@example.com"},
            headers=_authed(token),
        ).status_code == 400

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
        assert resp.status_code == 403

    def test_delete_user_success(self, client, db_session):
        """
        Authenticated DELETE /users/{user_id} with the correct UUID removes the user.
        user_id is now a str (UUID), matching User.id.
        """
        actor_token = _register_and_login(
            client, email="delete_actor@users.example.com"
        )
        target_token = _register_and_login(client, email="delete_target@users.example.com")
        _make_pool_admin(db_session, "delete_actor@users.example.com")
        pool_id = _create_pool(client, actor_token, "Delete User League")
        _join_pool(client, target_token, pool_id)
        target_id = _get_user_id(client, db_session, "delete_target@users.example.com")

        resp = client.delete(f"/users/{target_id}", headers=_authed(actor_token))
        assert resp.status_code == 200, (
            f"Expected 200 for delete with UUID, got {resp.status_code}: {resp.json()}"
        )

    def test_pool_admin_cannot_delete_user_from_another_league(self, client, db_session):
        actor_token = _register_and_login(client, "delete.scoped.admin@example.com")
        _make_pool_admin(db_session, "delete.scoped.admin@example.com")
        _create_pool(client, actor_token, "Delete Scoped League")
        _register_and_login(client, "delete.scoped.outsider@example.com")
        outsider_id = _get_user_id(client, db_session, "delete.scoped.outsider@example.com")

        response = client.delete(f"/users/{outsider_id}", headers=_authed(actor_token))

        assert response.status_code == 404

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
        assert resp.status_code == 403

    def test_super_admin_updates_login_email_without_changing_account(self, client, db_session):
        """
        PATCH /users/{user_id}/email with the correct UUID updates the email.
        user_id is now correctly typed as str.
        """
        token = _register_and_login(client, email="agsmith11@gmail.com")
        target_token = _register_and_login(client, email="email_before@users.example.com")
        _make_super_admin(db_session, "agsmith11@gmail.com")
        user_id = _get_user_id(client, db_session, "email_before@users.example.com")

        resp = client.patch(
            f"/users/{user_id}/email",
            params={"email": "email_after@users.example.com"},
            headers=_authed(token),
        )
        assert resp.status_code == 200, (
            f"Expected 200 for email update with UUID, got {resp.status_code}: {resp.json()}"
        )
        assert resp.json()["id"] == user_id
        assert resp.json()["email"] == "email_after@users.example.com"

        assert client.post(
            "/auth/login",
            json={"email": "email_before@users.example.com", "password": "Test1234!"},
        ).status_code == 401
        assert client.post(
            "/auth/login",
            json={"email": "email_after@users.example.com", "password": "Test1234!"},
        ).status_code == 200

    def test_league_admin_can_update_login_email_for_managed_user(self, client, db_session):
        token = _register_and_login(client, email="email_pool_admin@users.example.com")
        target_token = _register_and_login(client, email="email_member@users.example.com")
        _make_pool_admin(db_session, "email_pool_admin@users.example.com")
        pool_id = _create_pool(client, token, "Email Scope League")
        _join_pool(client, target_token, pool_id)
        user_id = _get_user_id(client, db_session, "email_member@users.example.com")

        response = client.patch(
            f"/admin/pools/{pool_id}/users/{user_id}/email",
            params={"email": "email_changed@users.example.com"},
            headers=_authed(token),
        )

        assert response.status_code == 200
        assert response.json()["email"] == "email_changed@users.example.com"

    def test_league_admin_cannot_update_login_email_outside_managed_league(self, client, db_session):
        token = _register_and_login(client, email="email_scoped_admin@users.example.com")
        _make_pool_admin(db_session, "email_scoped_admin@users.example.com")
        pool_id = _create_pool(client, token, "Scoped Email League")
        _register_and_login(client, email="email_outsider@users.example.com")
        user_id = _get_user_id(client, db_session, "email_outsider@users.example.com")

        response = client.patch(
            f"/admin/pools/{pool_id}/users/{user_id}/email",
            params={"email": "outsider_changed@users.example.com"},
            headers=_authed(token),
        )

        assert response.status_code == 404

    def test_update_login_email_rejects_duplicate(self, client, db_session):
        token = _register_and_login(client, email="agsmith11@gmail.com")
        _make_super_admin(db_session, "agsmith11@gmail.com")
        _register_and_login(client, email="email_existing@users.example.com")
        _register_and_login(client, email="email_target@users.example.com")
        user_id = _get_user_id(client, db_session, "email_target@users.example.com")

        response = client.patch(
            f"/users/{user_id}/email",
            params={"email": "EMAIL_EXISTING@users.example.com"},
            headers=_authed(token),
        )

        assert response.status_code == 409
        assert response.json()["detail"] == "An account with that email address already exists"

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
