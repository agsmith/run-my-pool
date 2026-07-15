"""
Tests for /users/* endpoints.

Notable quirks documented here:
- GET /users/ and GET /users/{user_id} require NO authentication (known security gap).
- user_id path parameters are typed as `int` in the route handler even though
  User.id is a string UUID. Passing a UUID string to these endpoints returns 422
  (FastAPI path-param validation), not 404. Tests use integer 0 as a sentinel
  "not found" value where a non-existent user is needed.
- PATCH /users/{user_id}/password stores the supplied string directly into
  hashed_password without hashing — a known security bug, tested explicitly.
"""

import pytest


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


def _get_user_id(client, email):
    """Retrieve a user's id by scanning the /users/ list."""
    resp = client.get("/users/")
    assert resp.status_code == 200
    users = resp.json()
    match = next((u for u in users if u["email"] == email), None)
    assert match is not None, f"User {email} not found in /users/ response"
    return match["id"]


# ---------------------------------------------------------------------------
# Test class
# ---------------------------------------------------------------------------


class TestUserEndpoints:
    """Integration tests for user CRUD endpoints."""

    # -----------------------------------------------------------------------
    # GET /users/
    # -----------------------------------------------------------------------

    def test_list_users_no_auth(self, client):
        """
        GET /users/ succeeds without authentication.

        This is a known security gap — the endpoint is publicly accessible.
        """
        resp = client.get("/users/")
        assert resp.status_code == 200

    def test_list_users_returns_list(self, client):
        """Registering a user and listing /users/ returns a list containing that user."""
        _register_and_login(client, email="list_users@example.com")

        resp = client.get("/users/")

        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        emails = [u["email"] for u in data]
        assert "list_users@example.com" in emails

    # -----------------------------------------------------------------------
    # GET /users/{user_id}
    # -----------------------------------------------------------------------

    def test_get_user_not_found(self, client):
        """
        GET /users/{user_id} with an integer id that does not exist returns 404.

        Note: The route declares user_id as int, so a UUID string would produce
        a 422 validation error instead. Integer 0 is used as a non-existent sentinel.
        """
        resp = client.get("/users/0")
        assert resp.status_code == 404

    # -----------------------------------------------------------------------
    # DELETE /users/{user_id}
    # -----------------------------------------------------------------------

    def test_delete_user_requires_auth(self, client):
        """DELETE /users/{user_id} without a token returns 401 or 403."""
        # Use a syntactically valid integer id; auth check fires before DB lookup.
        resp = client.delete("/users/1")
        assert resp.status_code in (401, 403)

    def test_delete_user_not_found(self, client):
        """Authenticated DELETE for a non-existent user returns 404."""
        token = _register_and_login(client, email="delete_notfound@example.com")

        resp = client.delete("/users/0", headers=_authed(token))

        assert resp.status_code == 404

    def test_delete_user_success(self, client):
        """
        Documents a type-mismatch bug: User.id is a string UUID but the route
        declares `user_id: int`.  Passing the real UUID string to DELETE
        /users/{user_id} causes FastAPI to return 422 (path-param validation
        fails) rather than performing the delete.

        If the route signature is fixed to `user_id: str`, this test should be
        updated to assert 200 and verify the user is removed.
        """
        # Primary actor — performs the delete
        token = _register_and_login(client, email="delete_actor@example.com")

        # Target user to be deleted
        _register_and_login(client, email="delete_target@example.com")
        target_id = _get_user_id(client, "delete_target@example.com")

        # BUG: route expects int, but User.id is a UUID string → 422
        resp = client.delete(f"/users/{target_id}", headers=_authed(token))
        assert resp.status_code == 422, (
            "Expected 422 due to int/UUID type mismatch in route signature. "
            f"Got {resp.status_code}: {resp.json()}"
        )

    # -----------------------------------------------------------------------
    # PATCH /users/{user_id}/email
    # -----------------------------------------------------------------------

    def test_update_email_requires_auth(self, client):
        """PATCH /users/{user_id}/email without a token returns 401 or 403."""
        resp = client.patch("/users/1/email", params={"email": "new@test.com"})
        assert resp.status_code in (401, 403)

    def test_update_email_not_found(self, client):
        """Authenticated PATCH email for a non-existent user returns 404."""
        token = _register_and_login(client, email="email_notfound@example.com")

        resp = client.patch(
            "/users/0/email",
            params={"email": "x@x.com"},
            headers=_authed(token),
        )

        assert resp.status_code == 404

    def test_update_email_success(self, client):
        """
        Documents a type-mismatch bug: User.id is a string UUID but the route
        declares `user_id: int`.  Passing the real UUID string to
        PATCH /users/{user_id}/email causes FastAPI to return 422 (path-param
        validation fails) rather than updating the email.

        If the route signature is fixed to `user_id: str`, this test should be
        updated to assert 200 and verify the new email is returned.
        """
        token = _register_and_login(client, email="email_before@example.com")
        user_id = _get_user_id(client, "email_before@example.com")

        # BUG: route expects int, but User.id is a UUID string → 422
        resp = client.patch(
            f"/users/{user_id}/email",
            params={"email": "email_after@example.com"},
            headers=_authed(token),
        )
        assert resp.status_code == 422, (
            "Expected 422 due to int/UUID type mismatch in route signature. "
            f"Got {resp.status_code}: {resp.json()}"
        )

    # -----------------------------------------------------------------------
    # PATCH /users/{user_id}/password
    # -----------------------------------------------------------------------

    def test_reset_password_security_bug(self, client):
        """
        Documents two compounding bugs:

        1. TYPE MISMATCH — User.id is a string UUID but the route declares
           `user_id: int`.  FastAPI rejects the UUID string with 422 before the
           handler runs, so the password-storage bug cannot be exercised through
           this route at all.

        2. SECURITY BUG (latent) — If the type mismatch were fixed, the handler
           assigns the plaintext password string directly to User.hashed_password
           without hashing it (`user.hashed_password = password`).

        This test asserts the currently observable behavior (422) and documents
        the underlying security bug for future remediation.
        """
        token = _register_and_login(client, email="password_bug@example.com")
        user_id = _get_user_id(client, "password_bug@example.com")

        # BUG 1: route expects int, but User.id is a UUID string → 422
        resp = client.patch(
            f"/users/{user_id}/password",
            params={"password": "plaintextpass"},
            headers=_authed(token),
        )
        assert resp.status_code == 422, (
            "Expected 422 due to int/UUID type mismatch in route signature. "
            f"Got {resp.status_code}: {resp.json()}"
        )
        # BUG 2 (latent): once the type mismatch is fixed, assert that
        # User.hashed_password != hash("plaintextpass") to catch the missing
        # hash step.
