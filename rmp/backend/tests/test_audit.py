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
import json
import uuid
from datetime import datetime, timedelta, timezone
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
        email = "pick.create@audit.example.com"
        token = _reg(client, email)
        pool = _create_pool(client, token)
        entry = _create_entry(client, token, pool["id"], "Sunday Ticket")
        _create_pick(client, token, entry["id"])
        event = _qlogs(db_session, "CREATE_PICK")[-1]
        payload = json.loads(event.details)["additional_data"]
        assert payload["team"] == "NE"
        assert payload["team_name"] == "NE"
        assert payload["username"] == email
        assert payload["entry_name"] == "Sunday Ticket"

    def test_update_pick_creates_audit(self, client, db_session):
        """Updating a pick should produce an UPDATE_PICK audit log."""
        email = "pick.update@audit.example.com"
        token = _reg(client, email)
        pool = _create_pool(client, token)
        entry = _create_entry(client, token, pool["id"], "Comeback Entry")
        pick = _create_pick(client, token, entry["id"], team="NE")
        resp = client.put(
            f"/picks/{pick['id']}", json={"team": "KC"}, headers=_h(token)
        )
        assert resp.status_code == 200, resp.text
        event = _qlogs(db_session, "UPDATE_PICK")[-1]
        changes = json.loads(event.details)["additional_data"]["changes"]
        assert changes["team"] == {"old": "NE", "new": "KC"}
        assert changes["context"]["old_team_name"] == "NE"
        assert changes["context"]["new_team_name"] == "KC"
        assert changes["context"]["username"] == email
        assert changes["context"]["entry_name"] == "Comeback Entry"

    def test_delete_pick_creates_audit(self, client, db_session):
        """Deleting a pick should produce a DELETE_PICK audit log."""
        email = "pick.delete@audit.example.com"
        token = _reg(client, email)
        pool = _create_pool(client, token)
        entry = _create_entry(client, token, pool["id"], "Delete Me")
        pick = _create_pick(client, token, entry["id"])
        resp = client.delete(f"/picks/{pick['id']}", headers=_h(token))
        assert resp.status_code == 200, resp.text
        event = _qlogs(db_session, "DELETE_PICK")[-1]
        payload = json.loads(event.details)["additional_data"]
        assert payload["team"] == "NE"
        assert payload["team_name"] == "NE"
        assert payload["username"] == email
        assert payload["entry_name"] == "Delete Me"

    def test_pick_audit_api_returns_pool_scoped_lifecycle(self, client):
        """The admin audit feed exposes create, update, and delete for one pool."""
        token = _reg(client, "pick.feed@audit.example.com")
        pool = _create_pool(client, token)
        entry = _create_entry(client, token, pool["id"])
        pick = _create_pick(client, token, entry["id"], team="NE")

        update = client.put(
            f"/picks/{pick['id']}", json={"team": "KC"}, headers=_h(token)
        )
        assert update.status_code == 200, update.text
        delete = client.delete(f"/picks/{pick['id']}", headers=_h(token))
        assert delete.status_code == 200, delete.text

        response = client.get(
            f"/audit/?pool_id={pool['id']}&action=PICK", headers=_h(token)
        )
        assert response.status_code == 200, response.text
        events = response.json()
        assert [event["action"] for event in events] == [
            "DELETE_PICK",
            "UPDATE_PICK",
            "CREATE_PICK",
        ]
        assert all(event["created_at"] for event in events)
        assert all(pool["id"] in event["details"] for event in events)
        assert all(event["username"] == "pick.feed@audit.example.com" for event in events)

    def test_audit_feed_resolves_username_for_legacy_event(self, client, db_session):
        """Rows without email context still resolve their user ID to an email."""
        email = "legacy.audit@example.com"
        token = _reg(client, email)
        user = client.get("/auth/me", headers=_h(token)).json()
        pool_id = _create_pool(client, token, "Legacy Audit Pool")["id"]
        db_session.add(AuditLog(
            id=str(uuid.uuid4()),
            user_id=user["id"],
            action="UPDATE_PICK",
            details=json.dumps({
                "description": "Legacy event",
                "additional_data": {"pool_id": pool_id},
            }),
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        ))
        db_session.commit()

        event = client.get(
            f"/audit/?pool_id={pool_id}", headers=_h(token)
        ).json()[0]
        assert event["user_id"] == user["id"]
        assert event["username"] == email

    def test_audit_feed_handles_unknown_and_system_users(self, client, db_session):
        """Deleted/unknown users and system events return a null username."""
        token = _reg(client, "audit.unknown@example.com")
        pool_id = _create_pool(client, token, "Unknown Audit Pool")["id"]
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        db_session.add_all([
            AuditLog(
                id=str(uuid.uuid4()), user_id=str(uuid.uuid4()),
                action="UNKNOWN_USER_EVENT",
                details=json.dumps({"pool_id": pool_id}), created_at=now,
            ),
            AuditLog(
                id=str(uuid.uuid4()), user_id=None, action="SYSTEM_EVENT",
                details=json.dumps({"pool_id": pool_id}),
                created_at=now - timedelta(seconds=1),
            ),
        ])
        db_session.commit()

        events = client.get(f"/audit/?pool_id={pool_id}", headers=_h(token)).json()
        assert [event["username"] for event in events] == [None, None]

    def test_pick_upsert_audit_includes_before_after_and_pool(self, client):
        """POSTing the same week is an audited update with complete context."""
        token = _reg(client, "pick.upsert@audit.example.com")
        pool = _create_pool(client, token)
        entry = _create_entry(client, token, pool["id"])
        pick = _create_pick(client, token, entry["id"], team="NE")

        response = client.post(
            "/picks/create",
            json={"entry_id": entry["id"], "week": 1, "team": "KC"},
            headers=_h(token),
        )
        assert response.status_code == 200, response.text
        assert response.json()["id"] == pick["id"]

        feed = client.get(
            f"/audit/?pool_id={pool['id']}&action=UPDATE_PICK", headers=_h(token)
        ).json()
        assert len(feed) == 1
        details = json.loads(feed[0]["details"])["additional_data"]["changes"]
        assert details == {
            "old_team": "NE",
            "old_team_name": "NE",
            "new_team": "KC",
            "new_team_name": "KC",
            "week": 1,
            "entry_id": entry["id"],
            "entry_name": "My Entry",
            "pool_id": pool["id"],
            "username": "pick.upsert@audit.example.com",
        }

    def test_direct_pick_update_audit_includes_diff_and_context(self, client):
        token = _reg(client, "pick.diff@audit.example.com")
        pool = _create_pool(client, token)
        entry = _create_entry(client, token, pool["id"])
        pick = _create_pick(client, token, entry["id"], team="NE")
        client.put(f"/picks/{pick['id']}", json={"team": "KC"}, headers=_h(token))

        event = client.get(
            f"/audit/?pool_id={pool['id']}&action=UPDATE_PICK", headers=_h(token)
        ).json()[0]
        changes = json.loads(event["details"])["additional_data"]["changes"]
        assert changes["team"] == {"old": "NE", "new": "KC"}
        assert changes["context"] == {
            "entry_id": entry["id"],
            "entry_name": "My Entry",
            "pool_id": pool["id"],
            "week": 1,
            "username": "pick.diff@audit.example.com",
            "old_team_name": "NE",
            "new_team_name": "KC",
        }

    def test_deleted_pick_audit_preserves_deleted_values(self, client):
        token = _reg(client, "pick.deleted.payload@audit.example.com")
        pool = _create_pool(client, token)
        entry = _create_entry(client, token, pool["id"])
        pick = _create_pick(client, token, entry["id"], week=2, team="KC")
        client.delete(f"/picks/{pick['id']}", headers=_h(token))

        event = client.get(
            f"/audit/?pool_id={pool['id']}&action=DELETE_PICK", headers=_h(token)
        ).json()[0]
        payload = json.loads(event["details"])["additional_data"]
        assert payload == {
            "team": "KC",
            "team_name": "KC",
            "week": 2,
            "entry_id": entry["id"],
            "entry_name": "My Entry",
            "pool_id": pool["id"],
            "username": "pick.deleted.payload@audit.example.com",
        }

    def test_audit_feed_isolates_pools(self, client):
        token = _reg(client, "pick.isolation@audit.example.com")
        pool_a = _create_pool(client, token, "Pool A")
        pool_b = _create_pool(client, token, "Pool B")
        entry_a = _create_entry(client, token, pool_a["id"], "Entry A")
        entry_b = _create_entry(client, token, pool_b["id"], "Entry B")
        pick_a = _create_pick(client, token, entry_a["id"], team="NE")
        _create_pick(client, token, entry_b["id"], team="KC")

        events = client.get(
            f"/audit/?pool_id={pool_a['id']}&action=PICK", headers=_h(token)
        ).json()
        assert [event["id"] for event in events]
        assert len(events) == 1
        assert pick_a["id"] in events[0]["details"]
        assert pool_b["id"] not in events[0]["details"]

    def test_audit_feed_requires_authentication(self, client):
        response = client.get("/audit/")
        assert response.status_code in (401, 403)

    def test_audit_feed_filters_user_action_and_dates(self, client, db_session):
        token = _reg(client, "pick.filters@audit.example.com")
        current_user = client.get("/auth/me", headers=_h(token)).json()
        pool = _create_pool(client, token)
        entry = _create_entry(client, token, pool["id"])
        _create_pick(client, token, entry["id"], team="NE")

        response = client.get(
            "/audit/",
            params={
                "pool_id": pool["id"],
                "user_id": current_user["id"],
                "action": "create_pick",
                "date_from": (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat(),
                "date_to": (datetime.now(timezone.utc) + timedelta(minutes=1)).isoformat(),
            },
            headers=_h(token),
        )
        assert response.status_code == 200, response.text
        assert [event["action"] for event in response.json()] == ["CREATE_PICK"]

        assert client.get(
            "/audit/",
            params={"pool_id": pool["id"], "user_id": str(uuid.uuid4())},
            headers=_h(token),
        ).json() == []

    def test_audit_filter_options_and_exact_event_type_are_pool_scoped(
        self, client
    ):
        token = _reg(client, "filter.options@audit.example.com")
        pool = _create_pool(client, token)
        entry = _create_entry(client, token, pool["id"])
        _create_pick(client, token, entry["id"], team="NE")

        options = client.get(
            "/audit/filter-options",
            params={"pool_id": pool["id"]},
            headers=_h(token),
        )
        assert options.status_code == 200, options.text
        payload = options.json()
        assert "CREATE_PICK" in payload["event_types"]
        assert {
            "id": client.get("/auth/me", headers=_h(token)).json()["id"],
            "email": "filter.options@audit.example.com",
        } in payload["users"]

        exact = client.get(
            "/audit/",
            params={"pool_id": pool["id"], "event_type": "CREATE_PICK"},
            headers=_h(token),
        )
        assert exact.status_code == 200
        assert [event["action"] for event in exact.json()] == ["CREATE_PICK"]
        assert client.get(
            "/audit/",
            params={"pool_id": pool["id"], "event_type": "PICK"},
            headers=_h(token),
        ).json() == []

    def test_audit_filter_options_reject_admin_for_another_pool(self, client):
        owner_a = _reg(client, "filter.scope.a@audit.example.com")
        owner_b = _reg(client, "filter.scope.b@audit.example.com")
        pool_b = _create_pool(client, owner_b)

        response = client.get(
            "/audit/filter-options",
            params={"pool_id": pool_b["id"]},
            headers=_h(owner_a),
        )
        assert response.status_code == 403
        assert client.get(
            "/audit/",
            params={"pool_id": pool["id"], "date_from": "2999-01-01T00:00:00"},
            headers=_h(token),
        ).json() == []

    def test_audit_feed_filters_by_username_without_exposing_user_id(self, client):
        token = _reg(client, "searchable.user@audit.example.com")
        pool = _create_pool(client, token)
        entry = _create_entry(client, token, pool["id"])
        _create_pick(client, token, entry["id"], team="NE")

        response = client.get(
            "/audit/",
            params={"pool_id": pool["id"], "username": "SEARCHABLE.USER"},
            headers=_h(token),
        )
        assert response.status_code == 200, response.text
        events = response.json()
        assert events
        assert all(event["username"] == "searchable.user@audit.example.com" for event in events)

        unknown = client.get(
            "/audit/",
            params={"pool_id": pool["id"], "username": "does-not-exist"},
            headers=_h(token),
        )
        assert unknown.status_code == 200
        assert unknown.json() == []

    def test_audit_feed_newest_first_and_honors_limit(self, client, db_session):
        token = _reg(client, "pick.order@audit.example.com")
        pool_id = _create_pool(client, token, "Ordered Audit Pool")["id"]
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        for index in range(3):
            db_session.add(AuditLog(
                id=str(uuid.uuid4()),
                user_id=None,
                action=f"SYSTEM_PICK_{index}",
                details=json.dumps({"pool_id": pool_id}),
                created_at=now + timedelta(seconds=index),
            ))
        db_session.commit()

        response = client.get(
            f"/audit/?pool_id={pool_id}&action=PICK&limit=2", headers=_h(token)
        )
        assert response.status_code == 200, response.text
        events = response.json()
        assert [event["action"] for event in events] == ["SYSTEM_PICK_2", "SYSTEM_PICK_1"]
        assert all(event["user_id"] is None for event in events)

    def test_audit_feed_rejects_admin_for_another_league(self, client):
        owner_a = _reg(client, "audit.scope.a@example.com")
        owner_b = _reg(client, "audit.scope.b@example.com")
        _create_pool(client, owner_a, "Audit Scope A")
        pool_b = _create_pool(client, owner_b, "Audit Scope B")

        response = client.get(
            f"/audit/?pool_id={pool_b['id']}", headers=_h(owner_a)
        )

        assert response.status_code == 403

    def test_non_super_admin_must_select_a_league_for_audit_feed(self, client):
        token = _reg(client, "audit.scope.required@example.com")
        response = client.get("/audit/", headers=_h(token))
        assert response.status_code == 403

    @pytest.mark.parametrize("limit", [0, 501])
    def test_audit_feed_rejects_invalid_limits(self, client, limit):
        token = _reg(client, f"audit.limit.{limit}@example.com")
        response = client.get(f"/audit/?limit={limit}", headers=_h(token))
        assert response.status_code == 422

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
        joined = client.post(
            f"/pools/{pool['id']}/join", json={}, headers=_h(token_b)
        )
        assert joined.status_code == 200, joined.text
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
