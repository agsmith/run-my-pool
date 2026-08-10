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


# ---------------------------------------------------------------------------
# Breakdown endpoint
# ---------------------------------------------------------------------------


def _seed_team(db, team_id, name, abbrv):
    """Insert a team row directly (bypasses HTTP layer)."""
    team = models.Team(id=team_id, name=name, abbrv=abbrv, logo=None)
    db.merge(team)
    db.commit()
    return team


def _seed_schedule(db, game_id, week_num, home_team_id, away_team_id, start_time):
    """Insert a schedule row directly."""
    game = models.Schedule(
        game_id=game_id,
        week_num=week_num,
        home_team_id=home_team_id,
        away_team_id=away_team_id,
        start_time=start_time,
        winning_team_id=None,
    )
    db.merge(game)
    db.commit()
    return game


class TestPickBreakdown:
    def test_empty_when_no_games_started(self, client, db_session):
        """Returns empty list when no games have started yet."""
        from datetime import datetime, timedelta

        token = _register_and_login(client, email="breakdown_empty@example.com")
        headers = _authed(token)
        pool_id = _create_pool(client, headers)
        entry_id = _create_entry(client, headers, pool_id)

        _seed_team(db_session, 1, "New England Patriots", "NE")
        # Game starts in the future
        future_time = datetime.utcnow() + timedelta(hours=2)
        _seed_schedule(
            db_session,
            1001,
            week_num=5,
            home_team_id=1,
            away_team_id=2,
            start_time=future_time,
        )

        # Plant a pick with team_id set
        create_resp = _create_pick(client, headers, entry_id, week=5, team="NE")
        pick_id = create_resp.json()["id"]
        pick = db_session.query(models.Pick).filter(models.Pick.id == pick_id).first()
        pick.team_id = 1
        db_session.commit()

        resp = client.get(f"/picks/pool/{pool_id}/week/5/breakdown", headers=headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_returns_counts_for_started_games(self, client, db_session):
        """Returns correct counts when some games have started."""
        from datetime import datetime, timedelta

        token = _register_and_login(client, email="breakdown_counts@example.com")
        headers = _authed(token)
        pool_id = _create_pool(client, headers)
        entry1 = _create_entry(client, headers, pool_id, name="Entry 1")
        entry2 = _create_entry(client, headers, pool_id, name="Entry 2")

        _seed_team(db_session, 10, "Kansas City Chiefs", "KC")
        _seed_team(db_session, 11, "Philadelphia Eagles", "PHI")
        # Seed with future start_time so picks are allowed
        future_time = datetime.utcnow() + timedelta(hours=2)
        _seed_schedule(
            db_session,
            1002,
            week_num=6,
            home_team_id=10,
            away_team_id=11,
            start_time=future_time,
        )

        for entry_id, team_abbrv, team_id in [(entry1, "KC", 10), (entry2, "KC", 10)]:
            resp = _create_pick(client, headers, entry_id, week=6, team=team_abbrv)
            assert resp.status_code == 200, f"Pick creation failed: {resp.text}"
            pick = (
                db_session.query(models.Pick)
                .filter(models.Pick.id == resp.json()["id"])
                .first()
            )
            pick.team_id = team_id
            db_session.commit()

        # Move game start_time to the past so breakdown reveals it
        game = (
            db_session.query(models.Schedule)
            .filter(models.Schedule.game_id == 1002)
            .first()
        )
        game.start_time = datetime.utcnow() - timedelta(hours=1)
        db_session.commit()

        resp = client.get(f"/picks/pool/{pool_id}/week/6/breakdown", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["team_abbrv"] == "KC"
        assert data[0]["count"] == 2

    def test_eliminated_entries_excluded(self, client, db_session):
        """Eliminated entries are not counted in the breakdown."""
        from datetime import datetime, timedelta

        token = _register_and_login(client, email="breakdown_elim@example.com")
        headers = _authed(token)
        pool_id = _create_pool(client, headers)
        alive_entry = _create_entry(client, headers, pool_id, name="Alive")
        dead_entry = _create_entry(client, headers, pool_id, name="Dead")

        _seed_team(db_session, 20, "Buffalo Bills", "BUF")
        _seed_team(db_session, 21, "Miami Dolphins", "MIA")
        future_time = datetime.utcnow() + timedelta(hours=2)
        _seed_schedule(
            db_session,
            1003,
            week_num=7,
            home_team_id=20,
            away_team_id=21,
            start_time=future_time,
        )

        for entry_id, team_abbrv, team_id in [
            (alive_entry, "BUF", 20),
            (dead_entry, "BUF", 20),
        ]:
            resp = _create_pick(client, headers, entry_id, week=7, team=team_abbrv)
            assert resp.status_code == 200, f"Pick creation failed: {resp.text}"
            pick = (
                db_session.query(models.Pick)
                .filter(models.Pick.id == resp.json()["id"])
                .first()
            )
            pick.team_id = team_id
            db_session.commit()

        # Eliminate the dead entry
        entry = (
            db_session.query(models.Entry).filter(models.Entry.id == dead_entry).first()
        )
        entry.alive = False
        db_session.commit()

        # Move game start_time to the past so breakdown reveals it
        game = (
            db_session.query(models.Schedule)
            .filter(models.Schedule.game_id == 1003)
            .first()
        )
        game.start_time = datetime.utcnow() - timedelta(hours=1)
        db_session.commit()

        resp = client.get(f"/picks/pool/{pool_id}/week/7/breakdown", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["count"] == 1  # only the alive entry

    def test_sorted_by_count_descending(self, client, db_session):
        """Results are ordered from most picks to fewest."""
        from datetime import datetime, timedelta
        import uuid as uuid_mod

        token = _register_and_login(client, email="breakdown_sort@example.com")
        headers = _authed(token)
        pool_id = _create_pool(client, headers)

        _seed_team(db_session, 30, "Dallas Cowboys", "DAL")
        _seed_team(db_session, 31, "New York Giants", "NYG")
        future_time = datetime.utcnow() + timedelta(hours=2)
        _seed_schedule(
            db_session,
            1004,
            week_num=8,
            home_team_id=30,
            away_team_id=31,
            start_time=future_time,
        )

        # 2 entries pick DAL, 1 picks NYG
        for i, (team_abbrv, team_id) in enumerate(
            [("DAL", 30), ("DAL", 30), ("NYG", 31)]
        ):
            token_i = _register_and_login(
                client, email=f"breakdown_sort_{i}@example.com"
            )
            headers_i = _authed(token_i)
            entry_id = _create_entry(client, headers_i, pool_id, name=f"Entry {i}")
            resp = _create_pick(client, headers_i, entry_id, week=8, team=team_abbrv)
            assert resp.status_code == 200, f"Pick creation failed: {resp.text}"
            pick = (
                db_session.query(models.Pick)
                .filter(models.Pick.id == resp.json()["id"])
                .first()
            )
            pick.team_id = team_id
            db_session.commit()

        # Move game start_time to the past so breakdown reveals it
        game = (
            db_session.query(models.Schedule)
            .filter(models.Schedule.game_id == 1004)
            .first()
        )
        game.start_time = datetime.utcnow() - timedelta(hours=1)
        db_session.commit()

        resp = client.get(f"/picks/pool/{pool_id}/week/8/breakdown", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data[0]["team_abbrv"] == "DAL"
        assert data[0]["count"] == 2
        assert data[1]["team_abbrv"] == "NYG"
        assert data[1]["count"] == 1
