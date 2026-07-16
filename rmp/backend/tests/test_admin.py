"""
Tests for the /admin endpoints.

Routes under test:
  POST   /admin/pools/{pool_id}/transfer-entry          — transfer entry ownership (admin only)
  DELETE /admin/pools/{pool_id}/entries/{entry_id}      — delete any entry (admin only)
  POST   /admin/pools/{pool_id}/lock-week/{week}        — lock week and auto-pick (admin only)
  PATCH  /admin/pools/{pool_id}/picks/{pick_id}         — admin override a pick (admin only)
"""

import uuid
from datetime import datetime

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


def _create_pick(db_session, entry_id, week, team, locked=False):
    """Directly insert a Pick row and return the model instance."""
    import models as m

    pick = m.Pick(
        id=str(uuid.uuid4()),
        entry_id=entry_id,
        week=week,
        team=team,
        locked=locked,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db_session.add(pick)
    db_session.commit()
    db_session.refresh(pick)
    return pick


# ---------------------------------------------------------------------------
# Test class — existing endpoints
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
            json={"entry_id": "some-entry-id", "to_email": "someone@example.com"},
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
            json={"entry_id": entry_id, "to_email": "someone@example.com"},
            headers=_authed(token_b),
        )
        assert response.status_code == 403

    def test_transfer_entry_success(self, client):
        """Pool owner transfers an entry to a registered recipient — returns 200 with expected fields."""
        # Register owner and recipient
        token_owner = _register_and_login(client, email="transfer_owner@example.com")
        _register_and_login(client, email="transfer_recipient@example.com")

        headers_owner = _authed(token_owner)
        pool_id = _create_pool(client, headers_owner)
        entry_id = _create_entry(client, headers_owner, pool_id)

        response = client.post(
            f"/admin/pools/{pool_id}/transfer-entry",
            json={"entry_id": entry_id, "to_email": "transfer_recipient@example.com"},
            headers=headers_owner,
        )

        assert response.status_code == 200, f"Transfer failed: {response.json()}"
        data = response.json()
        assert "entry_id" in data
        assert "from_user" in data
        assert "to_user" in data
        assert data["to_user"] == "transfer_recipient@example.com"

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

    def test_delete_entry_admin_success(self, client):
        """Pool owner can delete their own entry via the admin endpoint — returns 200."""
        token = _register_and_login(client, email="del_success@example.com")
        headers = _authed(token)
        pool_id = _create_pool(client, headers)
        entry_id = _create_entry(client, headers, pool_id)

        response = client.delete(
            f"/admin/pools/{pool_id}/entries/{entry_id}",
            headers=headers,
        )
        assert response.status_code == 200

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
        _register_and_login(client, email="va_other@example.com")
        other_user = (
            db_session.query(m.User)
            .filter(m.User.email == "va_other@example.com")
            .first()
        )

        result = verify_admin_access(pool_id, other_user, db_session)
        assert result is False


# ---------------------------------------------------------------------------
# Test class — lock-week endpoint
# ---------------------------------------------------------------------------


class TestLockWeek:
    """Integration tests for POST /admin/pools/{pool_id}/lock-week/{week}."""

    def test_lock_week_creates_auto_pick(self, client, db_session):
        """
        Pool with 2 entries: entry A submits pick "NE", entry B submits no pick.
        Admin locks week 1. auto_picks_created == 1. Entry B now has a pick for
        week 1 equal to "NE" (most popular).
        """
        import models as m

        token = _register_and_login(client, email="lock_owner@example.com")
        headers = _authed(token)
        pool_id = _create_pool(client, headers)

        # Entry A — picks NE for week 1
        entry_a_id = _create_entry(client, headers, pool_id, name="Entry A")
        client.post(
            "/picks/create",
            json={"entry_id": entry_a_id, "week": 1, "team": "NE"},
            headers=headers,
        )

        # Entry B — no pick
        token_b = _register_and_login(client, email="lock_member@example.com")
        entry_b_id = _create_entry(client, _authed(token_b), pool_id, name="Entry B")

        # Admin locks week 1
        resp = client.post(f"/admin/pools/{pool_id}/lock-week/1", headers=headers)
        assert resp.status_code == 200, f"Lock-week failed: {resp.json()}"
        data = resp.json()
        assert data["auto_picks_created"] == 1

        # Entry B should now have a pick for week 1 equal to "NE"
        pick_b = (
            db_session.query(m.Pick)
            .filter(m.Pick.entry_id == entry_b_id, m.Pick.week == 1)
            .first()
        )
        assert pick_b is not None, "Auto-pick was not created for entry B"
        assert pick_b.team == "NE"

    def test_lock_week_idempotent(self, client):
        """Locking the same week twice — second call returns auto_picks_created: 0."""
        token = _register_and_login(client, email="lock_idem@example.com")
        headers = _authed(token)
        pool_id = _create_pool(client, headers)
        entry_id = _create_entry(client, headers, pool_id)

        # Give entry a pick so no auto-pick is needed
        client.post(
            "/picks/create",
            json={"entry_id": entry_id, "week": 1, "team": "GB"},
            headers=headers,
        )

        resp1 = client.post(f"/admin/pools/{pool_id}/lock-week/1", headers=headers)
        assert resp1.status_code == 200
        assert resp1.json()["auto_picks_created"] == 0

        resp2 = client.post(f"/admin/pools/{pool_id}/lock-week/1", headers=headers)
        assert resp2.status_code == 200
        assert resp2.json()["auto_picks_created"] == 0

    def test_lock_week_non_admin_forbidden(self, client):
        """A user who does not own the pool gets 403 when calling lock-week."""
        token_a = _register_and_login(client, email="lock_owner2@example.com")
        pool_id = _create_pool(client, _authed(token_a))

        token_b = _register_and_login(client, email="lock_intruder@example.com")
        resp = client.post(
            f"/admin/pools/{pool_id}/lock-week/1", headers=_authed(token_b)
        )
        assert resp.status_code == 403

    def test_lock_week_skips_entry_that_already_picked(self, client, db_session):
        """An entry that already has a pick for the week is not overwritten."""
        import models as m

        token = _register_and_login(client, email="lock_skip@example.com")
        headers = _authed(token)
        pool_id = _create_pool(client, headers)
        entry_id = _create_entry(client, headers, pool_id)

        # Pre-existing pick for week 1
        client.post(
            "/picks/create",
            json={"entry_id": entry_id, "week": 1, "team": "DAL"},
            headers=headers,
        )

        resp = client.post(f"/admin/pools/{pool_id}/lock-week/1", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["auto_picks_created"] == 0

        # Original pick must be untouched
        pick = (
            db_session.query(m.Pick)
            .filter(m.Pick.entry_id == entry_id, m.Pick.week == 1)
            .first()
        )
        assert pick is not None
        assert pick.team == "DAL"


# ---------------------------------------------------------------------------
# Test class — admin pick edit endpoint
# ---------------------------------------------------------------------------


class TestAdminPickEdit:
    """Integration tests for PATCH /admin/pools/{pool_id}/picks/{pick_id}."""

    def test_admin_update_pick_success(self, client, db_session):
        """Admin can change the team on a locked pick."""
        token = _register_and_login(client, email="pickadmin@example.com")
        headers = _authed(token)
        pool_id = _create_pool(client, headers)
        entry_id = _create_entry(client, headers, pool_id)

        pick = _create_pick(db_session, entry_id, week=1, team="NE", locked=True)

        resp = client.patch(
            f"/admin/pools/{pool_id}/picks/{pick.id}",
            json={"team": "KC"},
            headers=headers,
        )
        assert resp.status_code == 200, f"Patch failed: {resp.json()}"
        assert resp.json()["team"] == "KC"

    def test_admin_update_pick_team_conflict(self, client, db_session):
        """Admin cannot change a pick's team to one already used by the entry in another week."""
        token = _register_and_login(client, email="pickconflict@example.com")
        headers = _authed(token)
        pool_id = _create_pool(client, headers)
        entry_id = _create_entry(client, headers, pool_id)

        pick_w1 = _create_pick(db_session, entry_id, week=1, team="NE", locked=True)
        _create_pick(db_session, entry_id, week=2, team="KC", locked=True)

        # Try to change week-1 pick to "KC" — already used in week 2
        resp = client.patch(
            f"/admin/pools/{pool_id}/picks/{pick_w1.id}",
            json={"team": "KC"},
            headers=headers,
        )
        assert resp.status_code == 400

    def test_admin_update_pick_non_admin_forbidden(self, client, db_session):
        """A regular user (non-admin) cannot PATCH a pick via the admin endpoint."""
        token_a = _register_and_login(client, email="pickowner_a@example.com")
        pool_id = _create_pool(client, _authed(token_a))
        entry_id = _create_entry(client, _authed(token_a), pool_id)
        pick = _create_pick(db_session, entry_id, week=1, team="SF")

        token_b = _register_and_login(client, email="pickintruder_b@example.com")
        resp = client.patch(
            f"/admin/pools/{pool_id}/picks/{pick.id}",
            json={"team": "SEA"},
            headers=_authed(token_b),
        )
        assert resp.status_code == 403

    def test_admin_update_pick_not_in_pool(self, client, db_session):
        """Admin of pool A cannot edit a pick that belongs to pool B — returns 404."""
        # Pool A owner
        token_a = _register_and_login(client, email="pool_a_admin@example.com")
        pool_a_id = _create_pool(client, _authed(token_a))

        # Pool B with a pick
        token_b = _register_and_login(client, email="pool_b_owner@example.com")
        pool_b_id = _create_pool(client, _authed(token_b))
        entry_b_id = _create_entry(client, _authed(token_b), pool_b_id)
        pick_b = _create_pick(db_session, entry_b_id, week=1, team="MIA")

        # Pool A admin tries to edit pool B's pick
        resp = client.patch(
            f"/admin/pools/{pool_a_id}/picks/{pick_b.id}",
            json={"team": "BUF"},
            headers=_authed(token_a),
        )
        assert resp.status_code == 404
