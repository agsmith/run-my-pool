"""
Tests for /picks/* endpoints.

Covers: create (upsert + team uniqueness), list by entry, update, delete.
All locking enforcement is tested by setting Pick.locked=True directly via
the db_session fixture — no HTTP-level lock endpoint exists.
"""

import pytest
import models


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _register_and_login(client, email="picks_test@example.com", password="Test1234!"):
    """Register a user and return an auth token."""
    client.post("/auth/register", json={"email": email, "password": password})
    resp = client.post("/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, f"Login failed: {resp.json()}"
    return resp.json()["access_token"]


def _authed(token):
    """Return Authorization header dict for the given bearer token."""
    return {"Authorization": f"Bearer {token}"}


def _create_pool(client, headers):
    """Create a minimal pool and return its id."""
    resp = client.post(
        "/pools/create",
        json={"name": "Test Pool", "is_private": False, "rule_values": []},
        headers=headers,
    )
    assert resp.status_code == 200, f"Pool creation failed: {resp.json()}"
    return resp.json()["id"]


def _create_entry(client, headers, pool_id, name="My Entry"):
    """Create an entry in the given pool and return its id."""
    resp = client.post(
        "/entries/create",
        json={"pool_id": pool_id, "name": name},
        headers=headers,
    )
    assert resp.status_code == 200, f"Entry creation failed: {resp.json()}"
    return resp.json()["id"]


def _create_pick(client, headers, entry_id, week=1, team="NE"):
    """Create a pick and return the full response JSON."""
    resp = client.post(
        "/picks/create",
        json={"entry_id": entry_id, "week": week, "team": team},
        headers=headers,
    )
    return resp


# ---------------------------------------------------------------------------
# Test class
# ---------------------------------------------------------------------------


class TestPickEndpoints:
    """Integration tests for pick CRUD endpoints."""

    # -----------------------------------------------------------------------
    # POST /picks/create
    # -----------------------------------------------------------------------

    def test_create_pick_success(self, client):
        """Creating a pick for a valid entry returns 200 with correct fields."""
        token = _register_and_login(client, email="picks_create@example.com")
        headers = _authed(token)
        pool_id = _create_pool(client, headers)
        entry_id = _create_entry(client, headers, pool_id)

        resp = _create_pick(client, headers, entry_id, week=1, team="NE")

        assert resp.status_code == 200, resp.json()
        data = resp.json()
        assert data["entry_id"] == entry_id
        assert data["week"] == 1
        assert data["team"] == "NE"
        assert data["locked"] is False
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    def test_create_pick_upserts_existing_week(self, client):
        """POSTing a pick for the same entry+week replaces the existing pick's team."""
        token = _register_and_login(client, email="picks_upsert@example.com")
        headers = _authed(token)
        pool_id = _create_pool(client, headers)
        entry_id = _create_entry(client, headers, pool_id)

        # Initial pick for week 1
        first = _create_pick(client, headers, entry_id, week=1, team="NE")
        assert first.status_code == 200
        pick_id = first.json()["id"]

        # Upsert — same entry+week, different team
        second = _create_pick(client, headers, entry_id, week=1, team="GB")

        assert second.status_code == 200, second.json()
        data = second.json()
        assert data["team"] == "GB"
        assert data["week"] == 1
        assert data["entry_id"] == entry_id
        # Should be the same row, not a new one
        assert data["id"] == pick_id

    def test_create_pick_duplicate_team_rejected(self, client):
        """Using a team already picked in another week for the same entry returns 400."""
        token = _register_and_login(client, email="picks_dupteam@example.com")
        headers = _authed(token)
        pool_id = _create_pool(client, headers)
        entry_id = _create_entry(client, headers, pool_id)

        # Pick "NE" for week 1
        first = _create_pick(client, headers, entry_id, week=1, team="NE")
        assert first.status_code == 200

        # Attempt to pick "NE" again for week 2 — should be rejected
        second = _create_pick(client, headers, entry_id, week=2, team="NE")

        assert second.status_code == 400, second.json()
        assert "NE" in second.json()["detail"]

    def test_create_pick_wrong_entry_rejected(self, client):
        """Creating a pick for another user's entry returns 404."""
        # User A creates an entry
        token_a = _register_and_login(client, email="picks_usera@example.com")
        headers_a = _authed(token_a)
        pool_id = _create_pool(client, headers_a)
        entry_id = _create_entry(client, headers_a, pool_id)

        # User B attempts to create a pick for user A's entry
        token_b = _register_and_login(client, email="picks_userb@example.com")
        headers_b = _authed(token_b)

        resp = _create_pick(client, headers_b, entry_id, week=1, team="NE")

        assert resp.status_code == 404, resp.json()

    def test_create_pick_no_auth_rejected(self, client):
        """POST /picks/create without a token returns 403."""
        resp = client.post(
            "/picks/create",
            json={
                "entry_id": "00000000-0000-0000-0000-000000000000",
                "week": 1,
                "team": "NE",
            },
        )
        assert resp.status_code in (401, 403)

    # -----------------------------------------------------------------------
    # GET /picks/entry/{entry_id}
    # -----------------------------------------------------------------------

    def test_get_picks_for_entry_success(self, client):
        """Fetching picks for an owned entry returns all picks ordered by week."""
        token = _register_and_login(client, email="picks_list@example.com")
        headers = _authed(token)
        pool_id = _create_pool(client, headers)
        entry_id = _create_entry(client, headers, pool_id)

        _create_pick(client, headers, entry_id, week=1, team="NE")
        _create_pick(client, headers, entry_id, week=2, team="GB")

        resp = client.get(f"/picks/entry/{entry_id}", headers=headers)

        assert resp.status_code == 200, resp.json()
        picks = resp.json()
        assert isinstance(picks, list)
        assert len(picks) == 2
        weeks = [p["week"] for p in picks]
        assert weeks == sorted(weeks)  # ordered by week

    def test_get_picks_for_entry_wrong_user(self, client):
        """Fetching picks for another user's entry returns 404."""
        # User A creates an entry with a pick
        token_a = _register_and_login(client, email="picks_list_a@example.com")
        headers_a = _authed(token_a)
        pool_id = _create_pool(client, headers_a)
        entry_id = _create_entry(client, headers_a, pool_id)
        _create_pick(client, headers_a, entry_id, week=1, team="NE")

        # User B tries to read user A's picks
        token_b = _register_and_login(client, email="picks_list_b@example.com")
        headers_b = _authed(token_b)

        resp = client.get(f"/picks/entry/{entry_id}", headers=headers_b)

        assert resp.status_code == 404, resp.json()

    # -----------------------------------------------------------------------
    # PUT /picks/{pick_id}
    # -----------------------------------------------------------------------

    def test_update_pick_success(self, client):
        """Updating an unlocked pick's team returns 200 with the new team."""
        token = _register_and_login(client, email="picks_update@example.com")
        headers = _authed(token)
        pool_id = _create_pool(client, headers)
        entry_id = _create_entry(client, headers, pool_id)

        create_resp = _create_pick(client, headers, entry_id, week=1, team="NE")
        pick_id = create_resp.json()["id"]

        resp = client.put(
            f"/picks/{pick_id}",
            json={"team": "KC"},
            headers=headers,
        )

        assert resp.status_code == 200, resp.json()
        data = resp.json()
        assert data["team"] == "KC"
        assert data["id"] == pick_id

    def test_update_locked_pick_rejected(self, client, db_session):
        """Updating a locked pick returns 400."""
        token = _register_and_login(client, email="picks_update_locked@example.com")
        headers = _authed(token)
        pool_id = _create_pool(client, headers)
        entry_id = _create_entry(client, headers, pool_id)

        create_resp = _create_pick(client, headers, entry_id, week=1, team="NE")
        pick_id = create_resp.json()["id"]

        # Lock the pick directly in the database
        pick = db_session.query(models.Pick).filter(models.Pick.id == pick_id).first()
        pick.locked = True
        db_session.commit()

        resp = client.put(
            f"/picks/{pick_id}",
            json={"team": "KC"},
            headers=headers,
        )

        assert resp.status_code == 400, resp.json()
        assert "locked" in resp.json()["detail"].lower()

    # -----------------------------------------------------------------------
    # DELETE /picks/{pick_id}
    # -----------------------------------------------------------------------

    def test_delete_pick_success(self, client):
        """Deleting an unlocked pick returns 200."""
        token = _register_and_login(client, email="picks_delete@example.com")
        headers = _authed(token)
        pool_id = _create_pool(client, headers)
        entry_id = _create_entry(client, headers, pool_id)

        create_resp = _create_pick(client, headers, entry_id, week=1, team="NE")
        pick_id = create_resp.json()["id"]

        resp = client.delete(f"/picks/{pick_id}", headers=headers)

        assert resp.status_code == 200, resp.json()

        # Confirm the pick is gone
        list_resp = client.get(f"/picks/entry/{entry_id}", headers=headers)
        assert list_resp.status_code == 200
        assert list_resp.json() == []

    def test_delete_locked_pick_rejected(self, client, db_session):
        """Deleting a locked pick returns 400."""
        token = _register_and_login(client, email="picks_delete_locked@example.com")
        headers = _authed(token)
        pool_id = _create_pool(client, headers)
        entry_id = _create_entry(client, headers, pool_id)

        create_resp = _create_pick(client, headers, entry_id, week=1, team="NE")
        pick_id = create_resp.json()["id"]

        # Lock the pick directly in the database
        pick = db_session.query(models.Pick).filter(models.Pick.id == pick_id).first()
        pick.locked = True
        db_session.commit()

        resp = client.delete(f"/picks/{pick_id}", headers=headers)

        assert resp.status_code == 400, resp.json()
        assert "locked" in resp.json()["detail"].lower()
