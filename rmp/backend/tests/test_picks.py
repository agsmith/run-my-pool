"""
Tests for /picks/* endpoints.

Covers: create (upsert + team uniqueness), list by entry, update, delete.
All locking enforcement is tested by setting Pick.locked=True directly via
the db_session fixture — no HTTP-level lock endpoint exists.
"""

import pytest
import models
from datetime import datetime, timedelta


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

    @pytest.fixture(autouse=True)
    def survivor_schedule(self, db_session, request):
        """Give generic Survivor CRUD tests a real, current-season slate."""
        if "pickem" in request.node.name:
            return
        kickoff = datetime(datetime.utcnow().year + 1, 9, 1, 17)
        season = kickoff.year
        teams = [
            models.Team(id=9801, name="New England Patriots", abbrv="NE"),
            models.Team(id=9802, name="Green Bay Packers", abbrv="GB"),
            models.Team(id=9803, name="Kansas City Chiefs", abbrv="KC"),
            models.Team(id=9804, name="Miami Dolphins", abbrv="MIA"),
        ]
        db_session.add_all(teams)
        for week in range(1, 19):
            db_session.add(models.Schedule(
                game_id=980000 + week,
                season=season,
                week_num=week,
                home_team_id=9801,
                away_team_id=9802,
                start_time=kickoff,
            ))
        db_session.add(models.Schedule(
            game_id=980100,
            season=season,
            week_num=1,
            home_team_id=9803,
            away_team_id=9804,
            start_time=kickoff + timedelta(hours=3),
        ))
        db_session.commit()

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

    def test_survivor_rejects_fabricated_team_even_without_pool_lock(self, client):
        token = _register_and_login(client, email="picks_fake_team@example.com")
        headers = _authed(token)
        pool_id = _create_pool(client, headers)
        entry_id = _create_entry(client, headers, pool_id)

        response = _create_pick(client, headers, entry_id, week=1, team="FAKE")

        assert response.status_code == 400
        assert response.json()["detail"] == "Selected team is not recognized"

    def test_pickem_requires_one_valid_selection_per_game(self, client, db_session):
        token = _register_and_login(client, email="pickem.picks@example.com")
        headers = _authed(token)
        pool = client.post(
            "/pools/create",
            json={"name": "All Games Pool", "pool_type": "pickem"},
            headers=headers,
        ).json()
        entry_id = _create_entry(client, headers, pool["id"])
        ne = models.Team(id=9911, name="New England Patriots", abbrv="NE")
        gb = models.Team(id=9912, name="Green Bay Packers", abbrv="GB")
        db_session.add_all([ne, gb])
        db_session.flush()
        game = models.Schedule(
            game_id=99101, week_num=3, home_team_id=ne.id, away_team_id=gb.id,
            start_time=datetime(datetime.utcnow().year + 1, 9, 20, 17),
        )
        db_session.add(game)
        db_session.commit()

        missing_game = _create_pick(client, headers, entry_id, week=3, team="NE")
        assert missing_game.status_code == 400
        created = client.post(
            "/picks/create",
            json={"entry_id": entry_id, "week": 3, "game_id": 99101, "team": "NE"},
            headers=headers,
        )
        assert created.status_code == 200
        assert created.json()["game_id"] == 99101

        changed = client.post(
            "/picks/create",
            json={"entry_id": entry_id, "week": 3, "game_id": 99101, "team": "GB"},
            headers=headers,
        )
        assert changed.status_code == 200
        assert changed.json()["id"] == created.json()["id"]
        assert changed.json()["team"] == "GB"

    def test_pickem_standings_rank_each_correct_pick_as_one_point(self, client, db_session):
        token = _register_and_login(client, email="pickem.standings@example.com")
        headers = _authed(token)
        pool = client.post(
            "/pools/create",
            json={"name": "Season Points Pool", "pool_type": "pickem"},
            headers=headers,
        ).json()
        entry_id = _create_entry(client, headers, pool["id"], "First Place")
        db_session.add_all([
            models.Pick(id="standing-win", entry_id=entry_id, week=1, team="NE", result="win"),
            models.Pick(id="standing-loss", entry_id=entry_id, week=1, team="GB", result="loss"),
        ])
        db_session.commit()

        response = client.get(f"/picks/pool/{pool['id']}/standings", headers=headers)
        assert response.status_code == 200
        assert response.json()[0]["entry_name"] == "First Place"
        assert response.json()[0]["rank"] == 1
        assert response.json()[0]["points"] == 1
        assert response.json()[0]["possible_points"] == 2

    @pytest.mark.parametrize("pool_type", ["survivor", "pickem"])
    def test_pool_leaderboard_ranks_all_entries_without_revealing_unlocked_picks(
        self, client, db_session, pool_type
    ):
        token = _register_and_login(
            client, email=f"{pool_type}.leaderboard@example.com"
        )
        headers = _authed(token)
        pool = client.post(
            "/pools/create",
            json={"name": f"{pool_type.title()} Leaderboard", "pool_type": pool_type},
            headers=headers,
        ).json()
        owner_entry_id = _create_entry(client, headers, pool["id"], "Two Wins")
        member = models.User(
            id=f"{pool_type}-leaderboard-member",
            email=f"member.{pool_type}@example.com",
            hashed_password="unused",
            is_active=True,
            email_verified=True,
        )
        member_entry = models.Entry(
            id=f"{pool_type}-member-entry",
            pool_id=pool["id"],
            user_id=member.id,
            name="One Win",
            alive=False,
        )
        db_session.add_all([member, member_entry])
        db_session.flush()
        db_session.add_all(
            [
                models.Pick(id=f"{pool_type}-win-1", entry_id=owner_entry_id, week=1, team="BUF", result="win"),
                models.Pick(id=f"{pool_type}-win-2", entry_id=owner_entry_id, week=2, team="MIA", result="win"),
                models.Pick(id=f"{pool_type}-hidden", entry_id=owner_entry_id, week=3, team="GB", result=None, locked=False),
                models.Pick(id=f"{pool_type}-locked", entry_id=owner_entry_id, week=4, team="NYJ", result=None, locked=True),
                models.Pick(id=f"{pool_type}-member-win", entry_id=member_entry.id, week=1, team="CHI", result="win"),
                models.Pick(id=f"{pool_type}-member-loss", entry_id=member_entry.id, week=2, team="DAL", result="loss"),
            ]
        )
        db_session.commit()

        response = client.get(
            f"/picks/pool/{pool['id']}/leaderboard", headers=headers
        )

        assert response.status_code == 200
        rows = response.json()
        assert [row["entry_name"] for row in rows] == ["Two Wins", "One Win"]
        assert rows[0]["rank"] == 1
        assert rows[0]["correct_picks"] == 2
        assert rows[0]["completed_picks"] == 2
        assert [pick["team"] for pick in rows[0]["picks"]] == ["BUF", "MIA", "NYJ"]
        assert rows[1]["rank"] == 2
        assert rows[1]["alive"] is False
        assert rows[1]["user_display_name"] == f"member.{pool_type}"
        assert "user_email" not in rows[1]

    def test_pool_leaderboard_requires_membership(self, client):
        owner_token = _register_and_login(client, email="leaderboard.owner@example.com")
        pool_id = _create_pool(client, _authed(owner_token))
        outsider_token = _register_and_login(client, email="leaderboard.outsider@example.com")

        response = client.get(
            f"/picks/pool/{pool_id}/leaderboard", headers=_authed(outsider_token)
        )

        assert response.status_code == 403

    def test_pickem_fixed_slate_rejects_extra_game_but_allows_changing_a_pick(self, client, db_session):
        token = _register_and_login(client, email="pickem.limit@example.com")
        headers = _authed(token)
        pool = client.post(
            "/pools/create",
            json={"name": "One Game Pool", "pool_type": "pickem", "pickem_games_per_week": 1},
            headers=headers,
        ).json()
        entry_id = _create_entry(client, headers, pool["id"])
        teams = [
            models.Team(id=9921, name="Buffalo Bills", abbrv="BUF"),
            models.Team(id=9922, name="Miami Dolphins", abbrv="MIA"),
            models.Team(id=9923, name="Green Bay Packers", abbrv="GB"),
            models.Team(id=9924, name="Chicago Bears", abbrv="CHI"),
        ]
        db_session.add_all(teams)
        db_session.flush()
        kickoff = datetime(datetime.utcnow().year + 1, 9, 20, 17)
        db_session.add_all([
            models.Schedule(game_id=99201, week_num=4, home_team_id=9922, away_team_id=9921, start_time=kickoff),
            models.Schedule(game_id=99202, week_num=4, home_team_id=9924, away_team_id=9923, start_time=kickoff + timedelta(hours=3)),
        ])
        db_session.commit()

        first = client.post("/picks/create", json={"entry_id": entry_id, "week": 4, "game_id": 99201, "team": "BUF"}, headers=headers)
        assert first.status_code == 200
        changed = client.post("/picks/create", json={"entry_id": entry_id, "week": 4, "game_id": 99201, "team": "MIA"}, headers=headers)
        assert changed.status_code == 200
        extra = client.post("/picks/create", json={"entry_id": entry_id, "week": 4, "game_id": 99202, "team": "GB"}, headers=headers)
        assert extra.status_code == 400
        assert "requires 1 Pick 'Em selections" in extra.json()["detail"]

    def test_pickem_sunday_slate_rejects_monday_game_server_side(self, client, db_session):
        token = _register_and_login(client, email="pickem.sunday@example.com")
        headers = _authed(token)
        pool = client.post("/pools/create", json={"name": "Sunday Pool", "pool_type": "pickem", "pickem_slate": "sunday"}, headers=headers).json()
        entry_id = _create_entry(client, headers, pool["id"])
        teams = [models.Team(id=9931, name="Buffalo", abbrv="BUF"), models.Team(id=9932, name="Miami", abbrv="MIA")]
        db_session.add_all(teams)
        future = datetime(2099, 9, 1)
        monday = future + timedelta(days=(0 - future.weekday()) % 7)
        db_session.add(models.Schedule(game_id=99301, week_num=5, home_team_id=9932, away_team_id=9931, start_time=monday.replace(hour=20, minute=15)))
        db_session.commit()

        response = client.post("/picks/create", json={"entry_id": entry_id, "week": 5, "game_id": 99301, "team": "BUF"}, headers=headers)

        assert response.status_code == 400
        assert "not included" in response.json()["detail"]

    @pytest.mark.parametrize("slate", ["sunday", "sunday_monday"])
    def test_day_based_pickem_slate_rejects_configurable_game_count(self, client, slate):
        token = _register_and_login(client, email=f"pickem.invalid-count.{slate}@example.com")
        response = client.post(
            "/pools/create",
            json={
                "name": f"Invalid {slate} Count",
                "pool_type": "pickem",
                "pickem_slate": slate,
                "pickem_games_per_week": 5,
            },
            headers=_authed(token),
        )

        assert response.status_code == 422
        assert "require picks for every eligible game" in response.text

    def test_sunday_monday_tiebreaker_is_private_then_ranks_closest_after_lock(self, client, db_session):
        token = _register_and_login(client, email="pickem.tiebreak@example.com")
        headers = _authed(token)
        pool = client.post("/pools/create", json={"name": "Sunday Monday Pool", "pool_type": "pickem", "pickem_slate": "sunday_monday"}, headers=headers).json()
        entry_id = _create_entry(client, headers, pool["id"], "Close Guess")
        user = db_session.query(models.User).filter(models.User.email == "pickem.tiebreak@example.com").one()
        second = models.Entry(id="tb-second-entry", user_id=user.id, pool_id=pool["id"], name="Far Guess", alive=True)
        teams = [models.Team(id=9941, name="Tiebreak Away", abbrv="TBA"), models.Team(id=9942, name="Tiebreak Home", abbrv="TBH")]
        db_session.add_all([second, *teams])
        future = datetime(2099, 9, 1)
        monday = future + timedelta(days=(0 - future.weekday()) % 7)
        game = models.Schedule(game_id=99401, week_num=6, home_team_id=9942, away_team_id=9941, start_time=monday.replace(hour=20, minute=15))
        db_session.add(game)
        db_session.commit()

        saved = client.put(f"/picks/entry/{entry_id}/tiebreaker", json={"week": 6, "predicted_total": 44}, headers=headers)
        assert saved.status_code == 200
        db_session.add(models.PickEmTiebreaker(id="tb-second", entry_id=second.id, week=6, predicted_total=60, created_at=datetime.utcnow(), updated_at=datetime.utcnow()))
        db_pool = db_session.query(models.Pool).filter(models.Pool.id == pool["id"]).one()
        db_pool.lock_time = datetime.utcnow() - timedelta(hours=4)
        game.home_score, game.away_score = 24, 21
        db_session.commit()

        standings = client.get(f"/picks/pool/{pool['id']}/weekly-standings/6", headers=headers)
        assert standings.status_code == 200
        assert [row["entry_name"] for row in standings.json()] == ["Close Guess", "Far Guess"]
        assert standings.json()[0]["actual_total"] == 45
        assert standings.json()[0]["tiebreak_difference"] == 1

        locked_update = client.put(f"/picks/entry/{entry_id}/tiebreaker", json={"week": 6, "predicted_total": 45}, headers=headers)
        assert locked_update.status_code == 423

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

    def test_survivor_update_rejects_fabricated_team(self, client, db_session):
        token = _register_and_login(client, email="picks_update_fake@example.com")
        headers = _authed(token)
        pool_id = _create_pool(client, headers)
        entry_id = _create_entry(client, headers, pool_id)
        created = _create_pick(client, headers, entry_id, week=1, team="NE")

        response = client.put(
            f"/picks/{created.json()['id']}",
            json={"team": "FAKE"},
            headers=headers,
        )

        assert response.status_code == 400
        db_session.expire_all()
        assert db_session.get(models.Pick, created.json()["id"]).team == "NE"

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
    def test_requires_pool_membership(self, client):
        owner_token = _register_and_login(client, email="breakdown_owner@example.com")
        outsider_token = _register_and_login(client, email="breakdown_outsider@example.com")
        pool_id = _create_pool(client, _authed(owner_token))

        response = client.get(
            f"/picks/pool/{pool_id}/week/1/breakdown",
            headers=_authed(outsider_token),
        )

        assert response.status_code == 403
        assert response.json()["detail"] == "League membership required"

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

    def test_weekly_lock_reveals_all_surviving_picks_and_groups_users(self, client, db_session):
        from datetime import datetime, timedelta

        owner_token = _register_and_login(client, "reveal.owner@example.com")
        member_token = _register_and_login(client, "reveal.member@example.com")
        owner_headers = _authed(owner_token)
        member_headers = _authed(member_token)
        pool_id = _create_pool(client, owner_headers)
        assert client.post(f"/pools/{pool_id}/join", json={}, headers=member_headers).status_code == 200

        owner_entry_1 = _create_entry(client, owner_headers, pool_id, "Owner One")
        owner_entry_2 = _create_entry(client, owner_headers, pool_id, "Owner Two")
        member_entry = _create_entry(client, member_headers, pool_id, "Member")
        eliminated_entry = _create_entry(client, member_headers, pool_id, "Eliminated")
        _seed_team(db_session, 30, "Buffalo Bills", "BUF")
        _seed_team(db_session, 31, "Miami Dolphins", "MIA")
        _seed_schedule(db_session, 1030, 9, 30, 31, datetime.utcnow() + timedelta(days=2))
        for entry_id in (owner_entry_1, owner_entry_2, member_entry, eliminated_entry):
            entry_headers = owner_headers if entry_id in (owner_entry_1, owner_entry_2) else member_headers
            assert _create_pick(client, entry_headers, entry_id, 9, "BUF").status_code == 200
        eliminated = db_session.query(models.Entry).filter(models.Entry.id == eliminated_entry).one()
        eliminated.alive = False
        db_session.commit()

        pool = db_session.query(models.Pool).filter(models.Pool.id == pool_id).one()
        pool.lock_time = datetime.utcnow() + timedelta(hours=1)
        db_session.commit()
        assert client.get(f"/picks/pool/{pool_id}/week/9/breakdown", headers=member_headers).json() == []

        pool.lock_time = datetime.utcnow() - timedelta(seconds=1)
        db_session.commit()
        response = client.get(f"/picks/pool/{pool_id}/week/9/breakdown", headers=member_headers)

        assert response.status_code == 200
        item = response.json()[0]
        assert item["team_abbrv"] == "BUF"
        assert item["count"] == 3
        assert item["users"] == [
            {"user_id": item["users"][0]["user_id"], "display_name": "reveal.member", "entry_count": 1},
            {"user_id": item["users"][1]["user_id"], "display_name": "reveal.owner", "entry_count": 2},
        ]
        assert sum(user["entry_count"] for user in item["users"]) == item["count"]

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
