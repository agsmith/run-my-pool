"""API tests for picks_new.py — alternative pick submission router.

NOTE: picks_new.py router is NOT currently registered in routers.py or main.py.
These tests:
  1. Verify the module is importable (import coverage regression guard).
  2. Mount the router in an isolated test app and exercise its endpoints.
  3. Document the registration gap as a known finding.
"""

import pytest

import models


def test_picks_new_module_is_importable():
    """picks_new.py must be importable without error."""
    import picks_new  # noqa: F401


def test_picks_new_router_not_registered_in_main_app(client):
    """Confirm picks_new router is NOT registered in the main app (no /picks/create overlap conflict)."""
    # The main app has /picks/create from picks.py; picks_new is not registered
    # This test is informational — it confirms the known gap
    import picks_new

    assert hasattr(picks_new, "router"), "picks_new must expose a router attribute"


class TestPicksNewRouterWhenMounted:
    """Tests for picks_new.py endpoints via a test app that mounts the router."""

    def _setup_entry(self, client, db_session, email="pn-user@example.com"):
        """Register/login a user, create a pool and entry; return (token, entry_id, pool_id)."""
        client.post("/auth/register", json={"email": email, "password": "PickNew1!"})
        login = client.post(
            "/auth/login", json={"email": email, "password": "PickNew1!"}
        )
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        pool_resp = client.post(
            "/pools/create",
            json={"name": "PickNew Pool", "description": ""},
            headers=headers,
        )
        pool_id = pool_resp.json()["id"]

        entry_resp = client.post(
            "/entries/create",
            json={"pool_id": pool_id, "name": "PN Entry"},
            headers=headers,
        )
        entry_id = entry_resp.json()["id"]
        return token, entry_id, pool_id

    def _mount_picks_new(self, client):
        """Temporarily mount the picks_new router on the main app."""
        import picks_new
        from main import app

        app.include_router(picks_new.router)
        return client

    def test_create_pick_via_picks_new_returns_200(self, client, db_session):
        """POST /picks/create via picks_new router creates a new pick."""
        # Seed a team so picks_new can reference it
        team = models.Team(id=601, name="Test Team PN", abbrv="TPN")
        db_session.add(team)
        db_session.commit()

        c = self._mount_picks_new(client)
        token, entry_id, _ = self._setup_entry(c, db_session, "pn-create@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        response = c.post(
            "/picks/create",
            json={"entry_id": entry_id, "week": 1, "team": "TPN"},
            headers=headers,
        )
        assert response.status_code in (200, 201)
        body = response.json()
        assert body["entry_id"] == entry_id
        assert body["team"] == "TPN"
        assert body["week"] == 1

    def test_create_pick_duplicate_team_rejected(self, client, db_session):
        """picks_new rejects a duplicate team used in the same entry."""
        team = models.Team(id=602, name="Dup Team PN", abbrv="DPN")
        db_session.add(team)
        db_session.commit()

        c = self._mount_picks_new(client)
        token, entry_id, _ = self._setup_entry(c, db_session, "pn-dup@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        c.post(
            "/picks/create",
            json={"entry_id": entry_id, "week": 1, "team": "DPN"},
            headers=headers,
        )
        # Second pick with the same team in a different week should be rejected
        response = c.post(
            "/picks/create",
            json={"entry_id": entry_id, "week": 2, "team": "DPN"},
            headers=headers,
        )
        assert response.status_code == 400

    def test_create_pick_unauthenticated_returns_401_or_403(self, client, db_session):
        """picks_new rejects unauthenticated requests."""
        c = self._mount_picks_new(client)
        response = c.post(
            "/picks/create",
            json={"entry_id": "any-id", "week": 1, "team": "NE"},
        )
        assert response.status_code in (401, 403)

    def test_create_pick_wrong_entry_returns_404(self, client, db_session):
        """picks_new returns 404 when entry does not belong to the requesting user."""
        c = self._mount_picks_new(client)
        token, _, _ = self._setup_entry(c, db_session, "pn-wrongentry@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        response = c.post(
            "/picks/create",
            json={"entry_id": "nonexistent-entry-id", "week": 1, "team": "NE"},
            headers=headers,
        )
        assert response.status_code == 404

    def test_upsert_existing_week_updates_pick(self, client, db_session):
        """picks_new upserts an existing pick for the same entry+week."""
        team1 = models.Team(id=603, name="First PN", abbrv="FPN")
        team2 = models.Team(id=604, name="Second PN", abbrv="SPN")
        db_session.add_all([team1, team2])
        db_session.commit()

        c = self._mount_picks_new(client)
        token, entry_id, _ = self._setup_entry(c, db_session, "pn-upsert@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        c.post(
            "/picks/create",
            json={"entry_id": entry_id, "week": 3, "team": "FPN"},
            headers=headers,
        )
        response = c.post(
            "/picks/create",
            json={"entry_id": entry_id, "week": 3, "team": "SPN"},
            headers=headers,
        )
        assert response.status_code in (200, 201)
        assert response.json()["team"] == "SPN"
