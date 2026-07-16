"""
Tests for the /messages endpoints (message board).

Routes under test:
  GET    /messages/pool/{pool_id}   — list messages (auth + pool membership required)
  POST   /messages/pool/{pool_id}   — post a message (auth + pool membership required)
  DELETE /messages/{message_id}     — delete a message (auth + ownership required)
"""

from datetime import datetime, timezone

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


# ---------------------------------------------------------------------------
# Test class — rate limiting
# ---------------------------------------------------------------------------


class TestMessageBoardRateLimit:
    """Integration tests for the per-user-per-pool message rate limit."""

    def test_rate_limit_allows_five_messages(self, client):
        """A user can post 5 messages in a row without hitting the rate limit."""
        token, pool_id, _ = _setup_user_with_pool_entry(
            client, email="rl_five@example.com"
        )
        headers = _authed(token)

        for i in range(5):
            resp = client.post(
                f"/messages/pool/{pool_id}",
                json={"pool_id": pool_id, "message": f"Message {i + 1}"},
                headers=headers,
            )
            assert resp.status_code == 200, (
                f"Message {i + 1} was unexpectedly blocked: {resp.json()}"
            )

    def test_rate_limit_blocks_sixth_message(self, client):
        """After 5 messages the 6th is rejected with 429 containing 'Rate limit exceeded'."""
        token, pool_id, _ = _setup_user_with_pool_entry(
            client, email="rl_sixth@example.com"
        )
        headers = _authed(token)

        for i in range(5):
            resp = client.post(
                f"/messages/pool/{pool_id}",
                json={"pool_id": pool_id, "message": f"Message {i + 1}"},
                headers=headers,
            )
            assert resp.status_code == 200

        sixth = client.post(
            f"/messages/pool/{pool_id}",
            json={"pool_id": pool_id, "message": "This should be blocked"},
            headers=headers,
        )
        assert sixth.status_code == 429
        assert "Rate limit exceeded" in sixth.json().get("detail", "")

    def test_rate_limit_resets_after_window(self, client, db_session):
        """
        After hitting 5 messages, back-dating them past the rate-limit window
        allows a 6th message to succeed.
        """
        from datetime import timedelta
        import models as m

        token, pool_id, _ = _setup_user_with_pool_entry(
            client, email="rl_reset@example.com"
        )
        headers = _authed(token)

        for i in range(5):
            resp = client.post(
                f"/messages/pool/{pool_id}",
                json={"pool_id": pool_id, "message": f"Message {i + 1}"},
                headers=headers,
            )
            assert resp.status_code == 200

        # Move all messages for this pool 15 minutes into the past
        old_time = datetime.now(timezone.utc) - timedelta(minutes=15)
        (
            db_session.query(m.MessageBoard)
            .filter(m.MessageBoard.pool_id == pool_id)
            .update({"created_at": old_time})
        )
        db_session.commit()

        resp = client.post(
            f"/messages/pool/{pool_id}",
            json={
                "pool_id": pool_id,
                "message": "Should be allowed after window reset",
            },
            headers=headers,
        )
        assert resp.status_code == 200, (
            f"Expected 200 after window reset, got: {resp.json()}"
        )

    def test_rate_limit_is_per_user_per_pool(self, client):
        """
        User A hitting the limit in pool 1 does not block:
          - User B posting to pool 1
          - User A posting to pool 2
        """
        # User A: pool 1 owner
        token_a, pool1_id, _ = _setup_user_with_pool_entry(
            client, email="rl_user_a@example.com"
        )
        headers_a = _authed(token_a)

        # User B: joins pool 1 with their own entry, and creates pool 2
        token_b, pool2_id, _ = _setup_user_with_pool_entry(
            client, email="rl_user_b@example.com"
        )
        headers_b = _authed(token_b)

        # User B joins pool 1
        entry_resp = client.post(
            "/entries/create",
            json={"pool_id": pool1_id, "name": "B's Entry in Pool 1"},
            headers=headers_b,
        )
        assert entry_resp.status_code == 200

        # User A also joins pool 2
        entry_resp = client.post(
            "/entries/create",
            json={"pool_id": pool2_id, "name": "A's Entry in Pool 2"},
            headers=headers_a,
        )
        assert entry_resp.status_code == 200

        # User A hits limit in pool 1
        for i in range(5):
            resp = client.post(
                f"/messages/pool/{pool1_id}",
                json={"pool_id": pool1_id, "message": f"A pool1 msg {i + 1}"},
                headers=headers_a,
            )
            assert resp.status_code == 200

        blocked = client.post(
            f"/messages/pool/{pool1_id}",
            json={"pool_id": pool1_id, "message": "A blocked in pool1"},
            headers=headers_a,
        )
        assert blocked.status_code == 429

        # User B can still post to pool 1
        resp_b = client.post(
            f"/messages/pool/{pool1_id}",
            json={"pool_id": pool1_id, "message": "B posts to pool 1"},
            headers=headers_b,
        )
        assert resp_b.status_code == 200, (
            f"User B unexpectedly blocked in pool 1: {resp_b.json()}"
        )

        # User A can still post to pool 2
        resp_a2 = client.post(
            f"/messages/pool/{pool2_id}",
            json={"pool_id": pool2_id, "message": "A posts to pool 2"},
            headers=headers_a,
        )
        assert resp_a2.status_code == 200, (
            f"User A unexpectedly blocked in pool 2: {resp_a2.json()}"
        )
