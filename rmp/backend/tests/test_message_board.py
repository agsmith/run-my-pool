"""
Tests for the /messages endpoints (message board).

Routes under test:
  GET    /messages/pool/{pool_id}   — list messages (auth + pool membership required)
  POST   /messages/pool/{pool_id}   — post a message (auth + pool membership required)
  DELETE /messages/{message_id}     — delete a message (auth + ownership + pool access required)
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _reg(client, email, password="Pass1234!"):
    client.post("/auth/register", json={"email": email, "password": password})
    resp = client.post("/auth/login", json={"email": email, "password": password})
    return resp.json()["access_token"]


def _h(token):
    return {"Authorization": f"Bearer {token}"}


def _create_pool(client, token, name="MsgPool"):
    resp = client.post(
        "/pools/create",
        json={"name": name, "description": "test", "is_private": False},
        headers=_h(token),
    )
    return resp.json()["id"]


def _create_entry(client, token, pool_id, name="Entry"):
    resp = client.post(
        "/entries/create",
        json={"pool_id": pool_id, "name": name},
        headers=_h(token),
    )
    return resp.json()["id"]


def _post_msg(client, token, pool_id, message="Hello world"):
    return client.post(
        f"/messages/pool/{pool_id}",
        json={"pool_id": pool_id, "message": message},
        headers=_h(token),
    )


# ---------------------------------------------------------------------------
# TestMessageBoardAccess
# ---------------------------------------------------------------------------


class TestMessageBoardAccess:
    def test_alive_entry_user_can_post(self, client):
        """User with alive entry can post a message → 200."""
        token = _reg(client, "alive@example.com")
        pool_id = _create_pool(client, token)
        _create_entry(client, token, pool_id)

        resp = _post_msg(client, token, pool_id)
        assert resp.status_code == 200
        assert resp.json()["user_display_name"] == "alive"
        assert "user_email" not in resp.json()

        listed = client.get(f"/messages/pool/{pool_id}", headers=_h(token))
        assert listed.status_code == 200
        assert listed.json()[0]["user_display_name"] == "alive"
        assert "user_email" not in listed.json()[0]

    def test_eliminated_entry_user_can_post(self, client, db_session):
        """User whose entry is alive=False (eliminated) can still post — membership
        check is Entry existence, not alive status → 200."""
        import models as m

        token = _reg(client, "eliminated@example.com")
        pool_id = _create_pool(client, token)
        entry_id = _create_entry(client, token, pool_id)

        # Set entry alive=False directly in the DB
        db_session.query(m.Entry).filter(m.Entry.id == entry_id).update(
            {"alive": False}
        )
        db_session.commit()

        resp = _post_msg(client, token, pool_id)
        assert resp.status_code == 200

    def test_no_entry_user_cannot_post(self, client):
        """User with no entry in pool gets 403 with appropriate message."""
        owner_token = _reg(client, "owner_post@example.com")
        pool_id = _create_pool(client, owner_token)
        _create_entry(client, owner_token, pool_id)  # owner has entry

        outsider_token = _reg(client, "outsider_post@example.com")
        resp = _post_msg(client, outsider_token, pool_id)

        assert resp.status_code == 403
        assert "must be a member of this pool to post messages" in resp.json()["detail"]

    def test_deleted_entry_user_cannot_post(self, client):
        """User who deleted their own entry can no longer post → 403."""
        token = _reg(client, "deleted_entry@example.com")
        pool_id = _create_pool(client, token)
        entry_id = _create_entry(client, token, pool_id)

        # User deletes their own entry (no lock_time set, so deletion is allowed)
        del_resp = client.delete(f"/entries/{entry_id}", headers=_h(token))
        assert del_resp.status_code == 200

        resp = _post_msg(client, token, pool_id)
        assert resp.status_code == 403

    def test_no_entry_user_cannot_read(self, client):
        """User without entry in pool cannot read messages → 403."""
        owner_token = _reg(client, "owner_read@example.com")
        pool_id = _create_pool(client, owner_token)
        _create_entry(client, owner_token, pool_id)

        outsider_token = _reg(client, "outsider_read@example.com")
        resp = client.get(f"/messages/pool/{pool_id}", headers=_h(outsider_token))

        assert resp.status_code == 403
        assert "must be a member of this pool to view messages" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# TestRateLimit
# ---------------------------------------------------------------------------


class TestRateLimit:
    def test_fifth_message_succeeds(self, client):
        """Posting 5 messages all succeed (200)."""
        token = _reg(client, "rl5@example.com")
        pool_id = _create_pool(client, token)
        _create_entry(client, token, pool_id)

        for i in range(5):
            resp = _post_msg(client, token, pool_id, message=f"Msg {i + 1}")
            assert resp.status_code == 200, f"Message {i + 1} failed: {resp.json()}"

    def test_sixth_message_rejected_429(self, client):
        """The 6th message in the window is rejected with 429 and the exact detail string."""
        token = _reg(client, "rl6@example.com")
        pool_id = _create_pool(client, token)
        _create_entry(client, token, pool_id)

        for i in range(5):
            resp = _post_msg(client, token, pool_id, message=f"Msg {i + 1}")
            assert resp.status_code == 200

        sixth = _post_msg(client, token, pool_id, message="Sixth message")
        assert sixth.status_code == 429
        assert sixth.json()["detail"] == (
            "Rate limit exceeded: maximum 5 messages per 10 minutes per pool."
        )

    def test_rate_limit_resets_after_window(self, client, db_session):
        """After 5 messages, back-dating them past the window allows a 6th → 200."""
        import models as m

        token = _reg(client, "rl_reset@example.com")
        pool_id = _create_pool(client, token)
        _create_entry(client, token, pool_id)

        for i in range(5):
            resp = _post_msg(client, token, pool_id, message=f"Msg {i + 1}")
            assert resp.status_code == 200

        # Back-date all messages in this pool by 11 minutes so the window has expired
        old_time = datetime.now(timezone.utc) - timedelta(minutes=11)
        db_session.query(m.MessageBoard).filter(
            m.MessageBoard.pool_id == pool_id
        ).update({"created_at": old_time})
        db_session.commit()

        resp = _post_msg(client, token, pool_id, message="After window reset")
        assert resp.status_code == 200, f"Expected 200 after reset, got: {resp.json()}"


# ---------------------------------------------------------------------------
# TestContentConstraints
# ---------------------------------------------------------------------------


class TestContentConstraints:
    def test_empty_message_rejected(self, client):
        """Empty string message → 400."""
        token = _reg(client, "empty_msg@example.com")
        pool_id = _create_pool(client, token)
        _create_entry(client, token, pool_id)

        resp = _post_msg(client, token, pool_id, message="")
        assert resp.status_code == 400

    def test_whitespace_message_rejected(self, client):
        """Whitespace-only message → 400."""
        token = _reg(client, "ws_msg@example.com")
        pool_id = _create_pool(client, token)
        _create_entry(client, token, pool_id)

        resp = _post_msg(client, token, pool_id, message="   ")
        assert resp.status_code == 400

    def test_250_char_message_accepted(self, client):
        """Exactly 250 characters → 200."""
        token = _reg(client, "max_msg@example.com")
        pool_id = _create_pool(client, token)
        _create_entry(client, token, pool_id)

        resp = _post_msg(client, token, pool_id, message="A" * 250)
        assert resp.status_code == 200

    def test_251_char_message_rejected(self, client):
        """251 characters → 400."""
        token = _reg(client, "toolong_msg@example.com")
        pool_id = _create_pool(client, token)
        _create_entry(client, token, pool_id)

        resp = _post_msg(client, token, pool_id, message="A" * 251)
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# TestDeletion
# ---------------------------------------------------------------------------


class TestDeletion:
    def test_user_deletes_own_message(self, client):
        """Message owner can delete their message → 200, and message is gone."""
        token = _reg(client, "del_own@example.com")
        pool_id = _create_pool(client, token)
        _create_entry(client, token, pool_id)

        post_resp = _post_msg(client, token, pool_id, message="Delete me")
        assert post_resp.status_code == 200
        message_id = post_resp.json()["id"]

        del_resp = client.delete(f"/messages/{message_id}", headers=_h(token))
        assert del_resp.status_code == 200

        # Confirm message is gone
        list_resp = client.get(f"/messages/pool/{pool_id}", headers=_h(token))
        assert list_resp.status_code == 200
        ids = [msg["id"] for msg in list_resp.json()]
        assert message_id not in ids

    def test_user_cannot_delete_others_message(self, client):
        """User B (with pool entry) cannot delete User A's message → 403."""
        token_a = _reg(client, "del_a@example.com")
        pool_id = _create_pool(client, token_a)
        _create_entry(client, token_a, pool_id, name="Entry A")

        post_resp = _post_msg(client, token_a, pool_id, message="User A's message")
        assert post_resp.status_code == 200
        message_id = post_resp.json()["id"]

        # User B joins the same pool so they pass the pool-access check
        token_b = _reg(client, "del_b@example.com")
        _create_entry(client, token_b, pool_id, name="Entry B")

        del_resp = client.delete(f"/messages/{message_id}", headers=_h(token_b))
        assert del_resp.status_code == 403
        assert "You can only delete your own messages" in del_resp.json()["detail"]
