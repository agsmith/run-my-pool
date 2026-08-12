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
from schedule import current_season_week


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
        assert game["start_time"].endswith("Z")

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

    def test_matchups_are_ordered_by_largest_spread_with_pending_lines_last(
        self, client, db_session, monkeypatch
    ):
        home = models.Team(id=73, name="Home", abbrv="H73")
        away = models.Team(id=74, name="Away", abbrv="A74")
        db_session.add_all([home, away])
        db_session.add_all([
            models.Schedule(
                game_id=7301, week_num=5, home_team_id=73, away_team_id=74,
                start_time=datetime(2026, 9, 1, 17),
            ),
            models.Schedule(
                game_id=7302, week_num=5, home_team_id=73, away_team_id=74,
                start_time=datetime(2026, 9, 1, 18),
            ),
            models.Schedule(
                game_id=7303, week_num=5, home_team_id=73, away_team_id=74,
                start_time=datetime(2026, 9, 1, 19),
            ),
        ])
        db_session.commit()
        monkeypatch.setattr("schedule.fetch_week_lines", lambda games: {
            7301: {"spread": 3.5, "details": "H73 -3.5", "provider": "ESPN"},
            7302: {"spread": 10.0, "details": "H73 -10", "provider": "ESPN"},
        })

        response = client.get("/schedule/week/5/matchups")

        assert response.status_code == 200
        assert [game["game_id"] for game in response.json()] == [7302, 7301, 7303]

    def test_week_endpoints_exclude_preseason_games(self, client, db_session, monkeypatch):
        home = models.Team(id=81, name="Home", abbrv="HME")
        away = models.Team(id=82, name="Away", abbrv="AWY")
        db_session.add_all([home, away])
        db_session.add_all([
            models.Schedule(game_id=8101, week_num=2, home_team_id=81, away_team_id=82, start_time=datetime(2026, 8, 16, 17, 0)),
            models.Schedule(game_id=8102, week_num=2, home_team_id=81, away_team_id=82, start_time=datetime(2026, 9, 13, 17, 0)),
        ])
        db_session.commit()
        monkeypatch.setattr("schedule.fetch_week_lines", lambda games: {})

        schedule_response = client.get("/schedule/week/2")
        matchup_response = client.get("/schedule/week/2/matchups")

        assert [game["game_id"] for game in schedule_response.json()] == [8102]
        assert [game["game_id"] for game in matchup_response.json()] == [8102]

    def test_current_season_week_uses_newest_schedule_boundaries(self, client, db_session):
        home = models.Team(id=91, name="Home", abbrv="H91")
        away = models.Team(id=92, name="Away", abbrv="A92")
        db_session.add_all([home, away])
        db_session.add_all([
            models.Schedule(game_id=9101, week_num=1, home_team_id=91, away_team_id=92, start_time=datetime(2025, 9, 8)),
            models.Schedule(game_id=9201, week_num=1, home_team_id=91, away_team_id=92, start_time=datetime(2026, 9, 14)),
            models.Schedule(game_id=9202, week_num=2, home_team_id=91, away_team_id=92, start_time=datetime(2026, 9, 21)),
        ])
        db_session.commit()

        assert current_season_week(db_session, datetime(2026, 8, 15)) == 1
        assert current_season_week(db_session, datetime(2026, 9, 16)) == 2
        assert current_season_week(db_session, datetime(2027, 2, 1)) == 2
