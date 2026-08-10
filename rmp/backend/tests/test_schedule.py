"""
Tests for the /schedule endpoints.

Routes under test:
  GET /schedule/week/{week_num}   — games for a given week (no auth required)
  GET /schedule/teams/{week_num}  — unique teams playing that week (no auth required)
  GET /schedule/                  — all games ordered by week_num, start_time (no auth required)
"""

import pytest
from datetime import datetime

import models


# ---------------------------------------------------------------------------
# Shared fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def schedule_with_teams(client, db_session):
    """
    Seed two Team rows and one Schedule row so schedule endpoint tests have
    real data to assert against.

    Yields nothing — callers rely on the side-effects in the database.
    """
    ne = models.Team(id=1, name="New England Patriots", abbrv="NE", logo="ne.svg")
    gb = models.Team(id=2, name="Green Bay Packers", abbrv="GB", logo="gb.svg")
    db_session.add_all([ne, gb])
    db_session.flush()

    game = models.Schedule(
        game_id=1001,
        week_num=1,
        home_team_id=1,
        away_team_id=2,
        start_time=datetime(2024, 9, 8, 13, 0),
        winning_team_id=99,
    )
    db_session.add(game)
    db_session.commit()

    yield


# ---------------------------------------------------------------------------
# Test class
# ---------------------------------------------------------------------------


class TestScheduleEndpoints:
    """Integration tests for the schedule router."""

    # ------------------------------------------------------------------
    # GET /schedule/week/{week_num}
    # ------------------------------------------------------------------

    def test_get_schedule_for_week_returns_games(self, client, schedule_with_teams):
        """Week 1 returns the seeded game with correct home-team abbreviation."""
        response = client.get("/schedule/week/1")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1

        game = data[0]
        assert game["game_id"] == 1001
        assert game["week_num"] == 1
        assert game["home_team"]["abbrv"] == "NE"
        assert game["away_team"]["abbrv"] == "GB"
        assert game["winning_team_id"] == 99

    def test_get_schedule_for_week_empty(self, client):
        """A week with no games returns an empty list, not an error."""
        response = client.get("/schedule/week/99")

        assert response.status_code == 200
        assert response.json() == []

    # ------------------------------------------------------------------
    # GET /schedule/teams/{week_num}
    # ------------------------------------------------------------------

    def test_get_teams_for_week_returns_both_teams(self, client, schedule_with_teams):
        """Week 1 exposes both the home and away teams as distinct entries."""
        response = client.get("/schedule/teams/1")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2

        abbrvs = {team["abbrv"] for team in data}
        assert abbrvs == {"NE", "GB"}

    def test_get_teams_for_week_empty(self, client):
        """A week with no games returns an empty teams list."""
        response = client.get("/schedule/teams/99")

        assert response.status_code == 200
        assert response.json() == []

    # ------------------------------------------------------------------
    # GET /schedule/
    # ------------------------------------------------------------------

    def test_get_all_schedules(self, client, schedule_with_teams):
        """The all-schedules endpoint returns at least the seeded game."""
        response = client.get("/schedule/")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

        game_ids = [g["game_id"] for g in data]
        assert 1001 in game_ids

    def test_matchups_only_returns_newest_season(self, client, db_session, monkeypatch):
        ne = models.Team(id=71, name="New England", abbrv="NE2")
        gb = models.Team(id=72, name="Green Bay", abbrv="GB2")
        db_session.add_all([ne, gb])
        db_session.add_all([
            models.Schedule(game_id=7101, week_num=4, home_team_id=71, away_team_id=72, start_time=datetime(2025, 9, 1)),
            models.Schedule(game_id=7102, week_num=4, home_team_id=71, away_team_id=72, start_time=datetime(2026, 9, 1)),
        ])
        db_session.commit()
        monkeypatch.setattr("schedule.fetch_week_lines", lambda games: {})

        response = client.get("/schedule/week/4/matchups")
        assert response.status_code == 200
        assert [game["game_id"] for game in response.json()] == [7102]
