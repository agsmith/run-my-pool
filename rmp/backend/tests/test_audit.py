"""
Tests for the audit trail system.

Verifies that audit log entries are created correctly for all major
application operations: auth, pools, entries, picks, messages, and admin actions.

Note: SQLite StaticPool means all sessions share one connection. We use
db_session (the fixture's session) with expire_all() to see committed data
from the API's session, rather than opening a fresh session (which would
contend on the shared connection).
"""

import pytest
from unittest.mock import patch

import models
from models import AuditLog


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _reg(client, email, password="Pass1234!"):
    client.post("/auth/register", json={"email": email, "password": password})
    resp = client.post("/auth/login", json={"email": email, "password": password})
    return resp.json()["access_token"]


def _h(token):
    return {"Authorization": f"Bearer {token}"}


def _create_pool(client, token, name="Audit Test Pool"):
    resp = client.post(
        "/pools/create",
        json={"name": name, "description": "Pool for audit tests", "is_private": False},
        headers=_h(token),
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def _create_entry(client, token, pool_id, name="My Entry"):
    resp = client.post(
        "/entries/create",
        json={"pool_id": pool_id, "name": name},
        headers=_h(token),
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def _create_pick(client, token, entry_id, week=1, team="NE"):
    resp = client.post(
        "/picks/create",
        json={"entry_id": entry_id, "week": week, "team": team},
        headers=_h(token),
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def _qlogs(db, action=None):
    """Query audit logs from the given session. expire_all() to see committed data."""
    db.expire_all()
    q = db.query(AuditLog)
    if action:
        q = q.filter(AuditLog.action == action)
    return q.all()


def _qlogs_like(db, pattern):
    db.expire_all()
    return db.query(AuditLog).filter(AuditLog.action.like(pattern)).all()


def _qlogs_contains(db, substr):
    db.expire_all()
    return db.query(AuditLog).filter(AuditLog.action.contains(substr)).all()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestAuditTrail:
    def test_register_creates_audit(self, client, db_session):
        """Registering a user should produce a CREATE_USER audit log."""
        client.post(
            "/auth/register",
            json={"email": "reg@audit.example.com", "password": "Pass1234!"},
        )
        assert len(_qlogs(db_session, "CREATE_USER")) >= 1

    def test_failed_login_creates_audit(self, client, db_session):
        """A login attempt with wrong credentials should produce LOGIN_FAILED."""
        client.post(
            "/auth/register",
            json={"email": "fail@audit.example.com", "password": "Pass1234!"},
        )
        client.post(
            "/auth/login",
            json={"email": "fail@audit.example.com", "password": "WrongPass!"},
        )
        assert len(_qlogs(db_session, "LOGIN_FAILED")) >= 1

    def test_successful_login_creates_audit(self, client, db_session):
        """A successful login should produce a LOGIN_SUCCESS audit log."""
        client.post(
            "/auth/register",
            json={"email": "ok@audit.example.com", "password": "Pass1234!"},
        )
        client.post(
            "/auth/login",
            json={"email": "ok@audit.example.com", "password": "Pass1234!"},
        )
        assert len(_qlogs(db_session, "LOGIN_SUCCESS")) >= 1

    def test_create_pool_creates_audit(self, client, db_session):
        """Creating a pool should produce a CREATE_POOL audit log containing the pool id."""
        token = _reg(client, "pool@audit.example.com")
        pool = _create_pool(client, token)
        pool_id = pool["id"]
        logs = _qlogs(db_session, "CREATE_POOL")
        assert len(logs) >= 1
        assert any(pool_id in (log.details or "") for log in logs), (
            f"Expected pool id {pool_id!r} in audit details"
        )

    def test_create_entry_creates_audit(self, client, db_session):
        """Creating an entry should produce a CREATE_ENTRY audit log."""
        token = _reg(client, "entry@audit.example.com")
        pool = _create_pool(client, token)
        _create_entry(client, token, pool["id"])
        assert len(_qlogs(db_session, "CREATE_ENTRY")) >= 1

    def test_create_pick_creates_audit(self, client, db_session):
        """Creating a pick should produce a CREATE_PICK audit log."""
        token = _reg(client, "pick.create@audit.example.com")
        pool = _create_pool(client, token)
        entry = _create_entry(client, token, pool["id"])
        _create_pick(client, token, entry["id"])
        assert len(_qlogs(db_session, "CREATE_PICK")) >= 1

    def test_update_pick_creates_audit(self, client, db_session):
        """Updating a pick should produce an UPDATE_PICK audit log."""
        token = _reg(client, "pick.update@audit.example.com")
        pool = _create_pool(client, token)
        entry = _create_entry(client, token, pool["id"])
        pick = _create_pick(client, token, entry["id"], team="NE")
        resp = client.put(
            f"/picks/{pick['id']}", json={"team": "KC"}, headers=_h(token)
        )
        assert resp.status_code == 200, resp.text
        assert len(_qlogs(db_session, "UPDATE_PICK")) >= 1

    def test_delete_pick_creates_audit(self, client, db_session):
        """Deleting a pick should produce a DELETE_PICK audit log."""
        token = _reg(client, "pick.delete@audit.example.com")
        pool = _create_pool(client, token)
        entry = _create_entry(client, token, pool["id"])
        pick = _create_pick(client, token, entry["id"])
        resp = client.delete(f"/picks/{pick['id']}", headers=_h(token))
        assert resp.status_code == 200, resp.text
        assert len(_qlogs(db_session, "DELETE_PICK")) >= 1

    def test_create_message_creates_audit(self, client, db_session):
        """Posting a pool message should produce a CREATE_MESSAGE audit log."""
        token = _reg(client, "msg@audit.example.com")
        pool = _create_pool(client, token)
        _create_entry(client, token, pool["id"])
        resp = client.post(
            f"/messages/pool/{pool['id']}",
            json={"pool_id": pool["id"], "message": "Hello audit"},
            headers=_h(token),
        )
        assert resp.status_code == 200, resp.text
        assert len(_qlogs(db_session, "CREATE_MESSAGE")) >= 1

    def test_lock_week_creates_admin_audit(self, client, db_session):
        """Locking a week should produce at least one ADMIN_ audit log entry.

        Note: lock-week only writes ADMIN_ audit entries when auto-pick fires
        (for entries with no pick). We create an entry WITHOUT a pick so
        auto-pick runs and writes ADMIN_AUTO_PICK to the audit log.
        """
        token = _reg(client, "lock@audit.example.com")
        pool = _create_pool(client, token)
        _create_entry(client, token, pool["id"])  # NO pick → auto-pick will fire
        resp = client.post(f"/admin/pools/{pool['id']}/lock-week/1", headers=_h(token))
        assert resp.status_code < 300, resp.text
        assert len(_qlogs_like(db_session, "ADMIN_%")) >= 1

    def test_admin_pick_override_creates_audit(self, client, db_session):
        """Admin pick override should produce an audit entry containing ADMIN_PICK_EDIT."""
        token = _reg(client, "override@audit.example.com")
        pool = _create_pool(client, token)
        entry = _create_entry(client, token, pool["id"])
        pick = _create_pick(client, token, entry["id"], week=1, team="NE")
        resp = client.patch(
            f"/admin/pools/{pool['id']}/picks/{pick['id']}",
            json={"team": "KC"},
            headers=_h(token),
        )
        assert resp.status_code < 300, resp.text
        # log_admin_action(action="ADMIN_PICK_EDIT") → stored as "ADMIN_ADMIN_PICK_EDIT"
        assert len(_qlogs_contains(db_session, "ADMIN_PICK_EDIT")) >= 1

    def test_admin_transfer_entry_creates_audit(self, client, db_session):
        """Admin transfer of an entry should produce an ADMIN_TRANSFER_ENTRY audit log."""
        token_a = _reg(client, "transferA@audit.example.com")
        token_b = _reg(client, "transferB@audit.example.com")
        user_b_email = client.get("/auth/me", headers=_h(token_b)).json()["email"]
        pool = _create_pool(client, token_a)
        entry = _create_entry(client, token_a, pool["id"])
        resp = client.post(
            f"/admin/pools/{pool['id']}/transfer-entry",
            json={"entry_id": entry["id"], "to_email": user_b_email},
            headers=_h(token_a),
        )
        assert resp.status_code < 300, resp.text
        assert len(_qlogs(db_session, "ADMIN_TRANSFER_ENTRY")) >= 1

    def test_audit_failure_does_not_break_operation(self, client, db_session):
        """If audit logging raises an exception the main operation must still succeed.

        The audit system (create_audit_log) internally catches all exceptions,
        so we test the internal failure by patching models.AuditLog to raise
        on instantiation — this causes the exception inside create_audit_log's
        try block, which is then swallowed by the except clause.
        """
        token = _reg(client, "resilient@audit.example.com")
        pool = _create_pool(client, token)
        entry = _create_entry(client, token, pool["id"])

        # Patch AuditLog constructor to raise — this is caught by
        # create_audit_log's internal try/except, so the pick should still succeed.
        original_init = models.AuditLog.__init__

        def failing_init(self_obj, **kwargs):
            raise Exception("Simulated audit DB failure")

        with patch.object(models.AuditLog, "__init__", failing_init):
            resp = client.post(
                "/picks/create",
                json={"entry_id": entry["id"], "week": 1, "team": "NE"},
                headers=_h(token),
            )

        assert resp.status_code == 200, (
            f"Pick creation should succeed even when audit logging fails; "
            f"got {resp.status_code}: {resp.text}"
        )

    def test_no_audit_delete_endpoint(self, client):
        """There should be no DELETE route for audit logs (404 or 405)."""
        assert client.delete("/audit/").status_code in (404, 405)
        assert client.delete("/audit/fake-id").status_code in (404, 405)
