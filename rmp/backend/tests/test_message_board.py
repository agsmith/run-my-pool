"""
Tests for the /messages endpoints (message board).

Routes under test:
  GET    /messages/pool/{pool_id}   — list messages (auth + pool membership required)
  POST   /messages/pool/{pool_id}   — post a message (auth + pool membership required)
  DELETE /messages/{message_id}     — delete a message (auth + ownership required)
"""

import pytest


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
# Shared setup helper
# ---------------------------------------------------------------------------


def _setup_user_with_pool_entry(
    client, email="member@example.com", password="Test1234!"
):
    """
    Register a user, create a pool, and join the pool with an entry.

    Returns:
        tuple[str, str, str]: (access_token, pool_id, entry_id)
    """
    token = _register_and_login(client, email=email, password=password)
    headers = _authed(token)

    pool_resp = client.post(
        "/pools/create",
        json={"name": "Test Pool", "is_private": False, "rule_values": []},
        headers=headers,
    )
    assert pool_resp.status_code == 200, f"Pool creation failed: {pool_resp.json()}"
    pool_id = pool_resp.json()["id"]

    entry_resp = client.post(
        "/entries/create",
        json={"pool_id": pool_id, "name": "My Entry"},
        headers=headers,
    )
    assert entry_resp.status_code == 200, f"Entry creation failed: {entry_resp.json()}"
    entry_id = entry_resp.json()["id"]

    return token, pool_id, entry_id


# ---------------------------------------------------------------------------
# Test class
# ---------------------------------------------------------------------------


class TestMessageBoardEndpoints:
    """Integration tests for the message board router."""

    # ------------------------------------------------------------------
    # GET /messages/pool/{pool_id}
    # ------------------------------------------------------------------

    def test_list_messages_requires_auth(self, client):
        """Unauthenticated GET /messages/pool/... returns 401 or 403."""
        response = client.get("/messages/pool/some-id")
        assert response.status_code in (401, 403)

    def test_list_messages_requires_pool_membership(self, client):
        """Authenticated user without a pool entry is denied with 403."""
        # Create the pool under user A
        token_a, pool_id, _ = _setup_user_with_pool_entry(
            client, email="owner_mb@example.com"
        )

        # User B has no entry in the pool
        token_b = _register_and_login(client, email="outsider_mb@example.com")
        response = client.get(f"/messages/pool/{pool_id}", headers=_authed(token_b))

        assert response.status_code == 403

    def test_list_messages_empty_pool(self, client):
        """A pool member sees an empty list when no messages have been posted."""
        token, pool_id, _ = _setup_user_with_pool_entry(
            client, email="empty_pool_mb@example.com"
        )
        response = client.get(f"/messages/pool/{pool_id}", headers=_authed(token))

        assert response.status_code == 200
        assert response.json() == []

    # ------------------------------------------------------------------
    # POST /messages/pool/{pool_id}
    # ------------------------------------------------------------------

    def test_post_message_success(self, client):
        """A pool member can post a message; response includes message text and user_email."""
        token, pool_id, _ = _setup_user_with_pool_entry(
            client, email="poster_mb@example.com"
        )
        payload = {"pool_id": pool_id, "message": "Hello pool!"}
        response = client.post(
            f"/messages/pool/{pool_id}", json=payload, headers=_authed(token)
        )

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Hello pool!"
        assert data["user_email"] == "poster_mb@example.com"
        assert "id" in data
        assert data["pool_id"] == pool_id

    def test_post_message_too_long(self, client):
        """A message exceeding 250 characters is rejected with 400."""
        token, pool_id, _ = _setup_user_with_pool_entry(
            client, email="toolong_mb@example.com"
        )
        long_message = "x" * 251
        payload = {"pool_id": pool_id, "message": long_message}
        response = client.post(
            f"/messages/pool/{pool_id}", json=payload, headers=_authed(token)
        )

        assert response.status_code == 400

    def test_post_message_empty(self, client):
        """An empty message (blank string) is rejected with 400."""
        token, pool_id, _ = _setup_user_with_pool_entry(
            client, email="empty_msg_mb@example.com"
        )
        payload = {"pool_id": pool_id, "message": ""}
        response = client.post(
            f"/messages/pool/{pool_id}", json=payload, headers=_authed(token)
        )

        assert response.status_code == 400

    def test_post_message_requires_pool_membership(self, client):
        """A user without a pool entry cannot post messages; expects 403."""
        token_a, pool_id, _ = _setup_user_with_pool_entry(
            client, email="owner_post_mb@example.com"
        )
        token_b = _register_and_login(client, email="outsider_post_mb@example.com")

        payload = {"pool_id": pool_id, "message": "Should not be allowed"}
        response = client.post(
            f"/messages/pool/{pool_id}", json=payload, headers=_authed(token_b)
        )

        assert response.status_code == 403

    # ------------------------------------------------------------------
    # DELETE /messages/{message_id}
    # ------------------------------------------------------------------

    def test_delete_message_success(self, client):
        """The message owner can delete their own message."""
        token, pool_id, _ = _setup_user_with_pool_entry(
            client, email="deleter_mb@example.com"
        )
        headers = _authed(token)

        # Post a message first
        post_resp = client.post(
            f"/messages/pool/{pool_id}",
            json={"pool_id": pool_id, "message": "Delete me"},
            headers=headers,
        )
        assert post_resp.status_code == 200
        message_id = post_resp.json()["id"]

        # Now delete it
        delete_resp = client.delete(f"/messages/{message_id}", headers=headers)
        assert delete_resp.status_code == 200

    def test_delete_message_wrong_user(self, client):
        """User B cannot delete a message posted by user A; expects 403."""
        token_a, pool_id, _ = _setup_user_with_pool_entry(
            client, email="poster_a_mb@example.com"
        )

        # User A posts the message
        post_resp = client.post(
            f"/messages/pool/{pool_id}",
            json={"pool_id": pool_id, "message": "User A's message"},
            headers=_authed(token_a),
        )
        assert post_resp.status_code == 200
        message_id = post_resp.json()["id"]

        # User B joins the same pool then tries to delete user A's message
        token_b = _register_and_login(client, email="poster_b_mb@example.com")
        entry_resp = client.post(
            "/entries/create",
            json={"pool_id": pool_id, "name": "B Entry"},
            headers=_authed(token_b),
        )
        assert entry_resp.status_code == 200

        delete_resp = client.delete(f"/messages/{message_id}", headers=_authed(token_b))
        assert delete_resp.status_code == 403

    def test_delete_message_not_found(self, client):
        """Deleting a non-existent message returns 404."""
        token = _register_and_login(client, email="notfound_mb@example.com")
        non_existent_id = "00000000-0000-0000-0000-000000000000"

        response = client.delete(f"/messages/{non_existent_id}", headers=_authed(token))
        assert response.status_code == 404
