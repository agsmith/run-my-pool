"""Unit tests for helpers.py — shared utility functions used in test and production code."""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

import models


# ---------------------------------------------------------------------------
# simulate_game_result
# ---------------------------------------------------------------------------


class TestSimulateGameResult:
    """Tests for helpers.simulate_game_result."""

    def test_simulate_game_result_home_win(self, db_session):
        """Happy path: home team wins and pick results are updated correctly."""
        from helpers import simulate_game_result

        home = models.Team(id=10, name="Home Team", abbrv="HOM")
        away = models.Team(id=11, name="Away Team", abbrv="AWY")
        user = models.User(
            id="u-helpers-1", email="helpers1@example.com", hashed_password="x"
        )
        pool = models.Pool(
            id="p-helpers-1", name="H-Pool", owner_id=user.id, pool_type="survivor"
        )
        entry = models.Entry(
            id="e-helpers-1", user_id=user.id, pool_id=pool.id, name="E1", alive=True
        )
        game = models.Schedule(
            game_id=90001,
            season=2026,
            week_num=1,
            home_team_id=home.id,
            away_team_id=away.id,
            start_time=datetime(2026, 9, 10, 13),
        )
        pick = models.Pick(
            id="pick-helpers-1",
            entry_id=entry.id,
            week=1,
            team=home.abbrv,
            team_id=home.id,
            locked=False,
        )
        for obj in (home, away, user, pool, entry, game, pick):
            db_session.add(obj)
        db_session.commit()

        simulate_game_result(db_session, game_id=90001, winner_team_id=home.id)

        db_session.refresh(pick)
        assert pick.result == "win"

    def test_simulate_game_result_away_win(self, db_session):
        """Away team win eliminates an entry that picked the home team."""
        from helpers import simulate_game_result

        home = models.Team(id=12, name="Home2", abbrv="HM2")
        away = models.Team(id=13, name="Away2", abbrv="AW2")
        user = models.User(
            id="u-helpers-2", email="helpers2@example.com", hashed_password="x"
        )
        pool = models.Pool(
            id="p-helpers-2", name="H-Pool2", owner_id=user.id, pool_type="survivor"
        )
        entry = models.Entry(
            id="e-helpers-2", user_id=user.id, pool_id=pool.id, name="E2", alive=True
        )
        game = models.Schedule(
            game_id=90002,
            season=2026,
            week_num=2,
            home_team_id=home.id,
            away_team_id=away.id,
            start_time=datetime(2026, 9, 17, 13),
        )
        pick = models.Pick(
            id="pick-helpers-2",
            entry_id=entry.id,
            week=2,
            team=home.abbrv,
            team_id=home.id,
            locked=False,
        )
        for obj in (home, away, user, pool, entry, game, pick):
            db_session.add(obj)
        db_session.commit()

        simulate_game_result(db_session, game_id=90002, winner_team_id=away.id)

        db_session.refresh(entry)
        assert entry.alive is False

    def test_simulate_game_result_invalid_game_raises(self, db_session):
        """Passing a non-existent game_id raises ValueError."""
        from helpers import simulate_game_result

        with pytest.raises(ValueError, match="not found"):
            simulate_game_result(db_session, game_id=999999, winner_team_id=1)

    def test_simulate_game_result_invalid_team_raises(self, db_session):
        """Passing a team not in the game raises ValueError."""
        from helpers import simulate_game_result

        home = models.Team(id=14, name="Home3", abbrv="HM3")
        away = models.Team(id=15, name="Away3", abbrv="AW3")
        game = models.Schedule(
            game_id=90003,
            season=2026,
            week_num=3,
            home_team_id=home.id,
            away_team_id=away.id,
            start_time=datetime(2026, 9, 24, 13),
        )
        for obj in (home, away, game):
            db_session.add(obj)
        db_session.commit()

        with pytest.raises(ValueError, match="not playing"):
            simulate_game_result(db_session, game_id=90003, winner_team_id=999)


# ---------------------------------------------------------------------------
# simulate_week_results
# ---------------------------------------------------------------------------


class TestSimulateWeekResults:
    """Tests for helpers.simulate_week_results."""

    def test_simulate_week_results_home_wins(self, db_session):
        """All home teams win when home_team_wins=True (default)."""
        from helpers import simulate_week_results

        home = models.Team(id=20, name="H4", abbrv="H04")
        away = models.Team(id=21, name="A4", abbrv="A04")
        user = models.User(
            id="u-week-1", email="week1@example.com", hashed_password="x"
        )
        pool = models.Pool(
            id="p-week-1", name="WP1", owner_id=user.id, pool_type="survivor"
        )
        entry = models.Entry(
            id="e-week-1", user_id=user.id, pool_id=pool.id, name="W1", alive=True
        )
        game = models.Schedule(
            game_id=90010,
            season=2026,
            week_num=4,
            home_team_id=home.id,
            away_team_id=away.id,
            start_time=datetime(2026, 10, 1, 13),
        )
        pick = models.Pick(
            id="pick-week-1",
            entry_id=entry.id,
            week=4,
            team=home.abbrv,
            team_id=home.id,
            locked=False,
        )
        for obj in (home, away, user, pool, entry, game, pick):
            db_session.add(obj)
        db_session.commit()

        simulate_week_results(db_session, week=4, home_team_wins=True)

        db_session.refresh(pick)
        assert pick.result == "win"

    def test_simulate_week_no_games_is_noop(self, db_session):
        """Calling simulate_week_results for a week with no games completes without error."""
        from helpers import simulate_week_results

        simulate_week_results(db_session, week=99)  # no games seeded for week 99


# ---------------------------------------------------------------------------
# advance_time
# ---------------------------------------------------------------------------


class TestAdvanceTime:
    """Tests for helpers.advance_time context manager."""

    def test_advance_time_patches_datetime_now(self):
        """advance_time returns the target time inside the context."""
        from helpers import advance_time

        target = datetime(2026, 9, 15, 12, 0, 0)
        import entries as entries_module

        with advance_time(target):
            result = entries_module.datetime.now()
        assert result == target

    def test_advance_time_restores_after_context(self):
        """datetime.now() returns actual time after leaving the context."""
        from helpers import advance_time
        import entries as entries_module

        target = datetime(2020, 1, 1, 0, 0, 0)
        with advance_time(target):
            inside = entries_module.datetime.now()
        outside = entries_module.datetime.now()

        assert inside == target
        # Outside should be close to actual now (not the mocked value)
        assert outside != target


# ---------------------------------------------------------------------------
# get_alive_entries / get_entry_used_teams
# ---------------------------------------------------------------------------


class TestQueryHelpers:
    """Tests for helpers.get_alive_entries and get_entry_used_teams."""

    def test_get_alive_entries_returns_only_alive(self, db_session):
        from helpers import get_alive_entries

        user = models.User(id="u-qa-1", email="qa1@example.com", hashed_password="x")
        pool = models.Pool(
            id="p-qa-1", name="QA1", owner_id=user.id, pool_type="survivor"
        )
        alive = models.Entry(
            id="e-qa-alive", user_id=user.id, pool_id=pool.id, name="Alive", alive=True
        )
        dead = models.Entry(
            id="e-qa-dead", user_id=user.id, pool_id=pool.id, name="Dead", alive=False
        )
        for obj in (user, pool, alive, dead):
            db_session.add(obj)
        db_session.commit()

        result = get_alive_entries(db_session, "p-qa-1")
        ids = {e.id for e in result}
        assert "e-qa-alive" in ids
        assert "e-qa-dead" not in ids

    def test_get_alive_entries_empty_pool(self, db_session):
        from helpers import get_alive_entries

        result = get_alive_entries(db_session, "nonexistent-pool")
        assert result == []

    def test_get_entry_used_teams_returns_all_picks(self, db_session):
        from helpers import get_entry_used_teams

        user = models.User(id="u-qa-2", email="qa2@example.com", hashed_password="x")
        pool = models.Pool(
            id="p-qa-2", name="QA2", owner_id=user.id, pool_type="survivor"
        )
        entry = models.Entry(
            id="e-qa-2", user_id=user.id, pool_id=pool.id, name="E2", alive=True
        )
        pick1 = models.Pick(
            id="pick-qa-1", entry_id=entry.id, week=1, team="NE", locked=False
        )
        pick2 = models.Pick(
            id="pick-qa-2", entry_id=entry.id, week=2, team="KC", locked=False
        )
        for obj in (user, pool, entry, pick1, pick2):
            db_session.add(obj)
        db_session.commit()

        teams = get_entry_used_teams(db_session, entry.id)
        assert "NE" in teams
        assert "KC" in teams

    def test_get_entry_used_teams_empty_entry(self, db_session):
        from helpers import get_entry_used_teams

        result = get_entry_used_teams(db_session, "nonexistent-entry")
        assert result == set()
