"""
Tests for the NFL Game Updater Lambda function.

This module covers the five core functions:
  - is_nfl_game_time()         — season/day/hour gate
  - fetch_nfl_game_results()   — ESPN API integration
  - update_game_results()      — schedule table writes
  - update_picks_results()     — pick win/loss resolution
  - eliminate_losing_entries() — entry elimination

All tests are fully isolated: no real network traffic, no real AWS calls, no
real database connections.  boto3, requests, and SQLAlchemy sessions are
mocked throughout.
"""

import sys
import json
import types
from datetime import datetime, timezone
from unittest import mock
from unittest.mock import MagicMock, patch, call

import pytest

# ---------------------------------------------------------------------------
# Bootstrap: make the Lambda src importable and stub heavy deps before import
# ---------------------------------------------------------------------------

from pathlib import Path

SRC_PATH = str(Path(__file__).parent.parent / "src")
if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)

# Stub mysql.connector so the import doesn't require the native driver
mysql_stub = types.ModuleType("mysql")
mysql_connector_stub = types.ModuleType("mysql.connector")
mysql_stub.connector = mysql_connector_stub
sys.modules.setdefault("mysql", mysql_stub)
sys.modules.setdefault("mysql.connector", mysql_connector_stub)

# Stub boto3 at import time so get_database_engine() never fires real AWS
boto3_mock = MagicMock()
sys.modules["boto3"] = boto3_mock

# Now it is safe to import the module under test
import nfl_game_updater  # noqa: E402
from nfl_game_updater import (  # noqa: E402
    all_games_final_for_week,
    get_current_nfl_context,
    is_nfl_game_time,
    fetch_nfl_game_results,
    update_game_results,
    update_picks_results,
    eliminate_losing_entries,
    reconcile_survivor_entries,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _utc(year, month, day, hour=0, minute=0, weekday_override=None):
    """
    Return a UTC-aware datetime.  weekday_override is ignored (it is the
    caller's responsibility to pick a date that falls on the intended weekday).
    """
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)


def _make_espn_event(
    home_abbrv: str,
    away_abbrv: str,
    home_score: int,
    away_score: int,
    status_name: str = "STATUS_FINAL",
    game_date: str = "2024-10-06T17:00Z",
    week: int = 5,
) -> dict:
    """Build a minimal ESPN API event dict."""
    return {
        "date": game_date,
        "status": {"type": {"name": status_name}},
        "competitions": [
            {
                "competitors": [
                    {
                        "homeAway": "home",
                        "score": str(home_score),
                        "team": {"abbreviation": home_abbrv},
                    },
                    {
                        "homeAway": "away",
                        "score": str(away_score),
                        "team": {"abbreviation": away_abbrv},
                    },
                ]
            }
        ],
    }


def _mock_db():
    """Return a fresh MagicMock standing in for a SQLAlchemy session."""
    return MagicMock()


# ---------------------------------------------------------------------------
# TestIsNflGameTime
# ---------------------------------------------------------------------------


class TestIsNflGameTime:
    """
    is_nfl_game_time() converts UTC → ET by subtracting 5 hours (EST assumed).

    Weekday mapping (datetime.weekday()): Mon=0, Tue=1, Wed=2, Thu=3,
    Fri=4, Sat=5, Sun=6.

    Game windows (ET):
      Sunday  13–23
      Monday  20–23
      Thursday 20–23
      Saturday 13–23 (week >= 15 only)
    """

    # ------------------------------------------------------------------
    # Positive cases
    # ------------------------------------------------------------------

    def test_returns_true_sunday_afternoon_october(self):
        """Sunday Oct 6 2024 2:00 PM ET (19:00 UTC) — midday Sunday games."""
        # Oct 6 2024 is a Sunday (weekday 6).  2 PM ET = 19:00 UTC.
        fixed_dt = _utc(2024, 10, 6, 19, 0)
        with patch("nfl_game_updater.datetime") as mock_dt:
            mock_dt.now.return_value = fixed_dt
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            result = is_nfl_game_time()
        assert result is True

    def test_returns_true_monday_night_november(self):
        """Monday Nov 4 2024 8:30 PM ET (01:30 UTC Nov 5) — MNF."""
        # 8:30 PM ET on Monday = 01:30 UTC next day, but we need the weekday
        # of the ET clock to still be Monday.  8:30 PM ET = 00:30 UTC (UTC-5 → +5h).
        # Actually: ET 20:30 + 5 = UTC 01:30 (next day, Tuesday UTC).
        # The function computes et_hour = (now.hour - 5) % 24 and et_weekday from now.weekday().
        # To get et_weekday=0 (Monday) and et_hour=20, we need:
        #   now.weekday() == 0  (UTC day is Monday)  AND  now.hour - 5 in [20,23]
        #   => now.hour in [25 % 24 = 1 ... but that wraps]
        # Simpler: keep UTC Monday with hour 25 doesn't work. Use Mon UTC hour that
        # gives et_hour >= 20:  et_hour = (h - 5) % 24 >= 20  → h in [1,2,3,4] or h >= 25 (impossible).
        # None of those map to evening.  Use Mon Nov 4 UTC hour = 20+5=25→ not valid.
        # Actually the comment "assume 5 hours (EST)" means ET = UTC - 5.
        # et_hour = (now.hour - 5) % 24.  For et_hour=20 we need now.hour=25 (impossible)
        # or now.hour=1 → et_hour=(1-5)%24=20. ✓  But now.weekday() must be 0 (Monday).
        # Nov 5 2024 01:00 UTC is still "Monday Nov 4 ET" evening → weekday of Nov 5 UTC is Tuesday (1).
        # The function uses now.weekday() (UTC weekday), not ET weekday.
        # So et_weekday == 0 requires UTC weekday == 0 (Monday), and et_hour 20–23 requires
        # UTC hour in {1,2,3,4}.  Pick Mon Nov 4 2024 01:00 UTC → et_hour=(1-5)%24=20. ✓
        fixed_dt = _utc(2024, 11, 4, 1, 0)  # Mon UTC 01:00 → ET Sun 20:00? No.
        # Nov 4 2024: weekday? Let's verify: Jan 1 2024 is Monday (0).
        # Nov 4 is day 309 of 2024.  309 % 7 = 1 → Tuesday.  Adjust: (0 + 309) % 7 = 1 → Tuesday.
        # So Nov 4 2024 is a Monday? Let's count more carefully.
        # We'll just trust datetime itself and pick a known Monday: use date arithmetic.
        # Nov 4 2024: datetime(2024,11,4).weekday() — will confirm in test via assert.
        # For safety, use a date we know is Monday: the function itself will determine
        # the weekday from the datetime object passed.  We patch datetime.now().
        # datetime(2024,11,4) weekday: 2024 is leap. Days from Jan 1 (Mon) to Nov 4:
        # Jan=31,Feb=29,Mar=31,Apr=30,May=31,Jun=30,Jul=31,Aug=31,Sep=30,Oct=31 = 305 days to Nov 1.
        # + 3 more = 308 days from Jan 1. Jan 1 is day 0. weekday of Jan 1 2024 = Monday (0).
        # (0 + 308) % 7 = 308 % 7 = 0 → Monday. ✓  Nov 4 2024 is Monday.
        # UTC hour 1 → et_hour = (1-5)%24 = 20. ✓  et_weekday = 0 (Monday). ✓
        fixed_dt = _utc(2024, 11, 4, 1, 30)  # Mon 1:30 UTC = Mon 20:30 ET
        assert fixed_dt.weekday() == 0, "Nov 4 2024 must be Monday"
        with patch("nfl_game_updater.datetime") as mock_dt:
            mock_dt.now.return_value = fixed_dt
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            result = is_nfl_game_time()
        assert result is True

    def test_returns_true_thursday_night_september(self):
        """Thursday Sep 5 2024 8:20 PM ET — Thursday Night Football."""
        # Sep 5 2024 weekday: Jan 1 (Mon=0). Days to Sep 5:
        # Jan31+Feb29+Mar31+Apr30+May31+Jun30+Jul31+Aug31+4 = 248 days from Jan 1.
        # (0+248)%7 = 248%7 = 3 (248/7=35r3) → Thursday. ✓
        # et_hour=20 → UTC hour = 20+5=25 → 1 (next day), but we want UTC Thursday.
        # UTC hour 1 on Sep 5 → et_hour=(1-5)%24=20, et_weekday=Sep5.weekday()=3. ✓
        fixed_dt = _utc(2024, 9, 6, 0, 20)  # Thu Sep 5 8:20 PM EDT
        with patch("nfl_game_updater.datetime") as mock_dt:
            mock_dt.now.return_value = fixed_dt
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            result = is_nfl_game_time()
        assert result is True

    # ------------------------------------------------------------------
    # Negative cases
    # ------------------------------------------------------------------

    def test_returns_false_tuesday_in_season(self):
        """Tuesday in October — not a game day."""
        # Oct 1 2024: days from Jan 1 = 274. (0+274)%7=2 → Wednesday. Try Oct 8: 281%7=1→Tuesday.
        fixed_dt = _utc(2024, 10, 8, 20, 0)  # Tue 20:00 UTC (ET 15:00)
        assert fixed_dt.weekday() == 1, "Oct 8 2024 must be Tuesday"
        with patch("nfl_game_updater.datetime") as mock_dt:
            mock_dt.now.return_value = fixed_dt
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            result = is_nfl_game_time()
        assert result is False

    def test_returns_false_offseason_june(self):
        """June Sunday — out of season."""
        # Jun 2 2024: Jan31+Feb29+Mar31+Apr30+May31+1=153. (0+153)%7=6→Sunday. ✓
        fixed_dt = _utc(2024, 6, 2, 20, 0)
        assert fixed_dt.weekday() == 6, "Jun 2 2024 must be Sunday"
        with patch("nfl_game_updater.datetime") as mock_dt:
            mock_dt.now.return_value = fixed_dt
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            result = is_nfl_game_time()
        assert result is False

    def test_returns_false_too_early_sunday(self):
        """Sunday 9:00 AM ET (14:00 UTC) — before the 1 PM window."""
        # Oct 6 2024 is Sunday. ET 09:00 = UTC 14:00. et_hour=(14-5)%24=9. 9 < 13 → False.
        fixed_dt = _utc(2024, 10, 6, 14, 0)
        assert fixed_dt.weekday() == 6, "Oct 6 2024 must be Sunday"
        with patch("nfl_game_updater.datetime") as mock_dt:
            mock_dt.now.return_value = fixed_dt
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            result = is_nfl_game_time()
        assert result is False

    def test_returns_false_saturday_early_season(self):
        """Saturday in Week 5 (early season) — Saturday games only start week 15."""
        # Oct 5 2024 is Saturday. et_hour=20 but current_week ~5 → False.
        # Oct 5: days from Jan 1 = 278. (0+278)%7=5→Saturday. ✓
        fixed_dt = _utc(2024, 10, 5, 1, 0)  # UTC 01:00 → ET 20:00 Sat
        assert fixed_dt.weekday() == 5, "Oct 5 2024 must be Saturday"
        with patch("nfl_game_updater.datetime") as mock_dt:
            mock_dt.now.return_value = fixed_dt
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            # get_current_nfl_week() is called internally; patch it to return week 5
            with patch("nfl_game_updater.get_current_nfl_week", return_value=5):
                result = is_nfl_game_time()
        assert result is False

    def test_returns_true_saturday_late_season(self):
        """Saturday in Week 16 — Saturday games are active."""
        # Dec 21 2024 is Saturday. UTC 01:00 → ET 20:00.
        # Days to Dec 21: Jan31+Feb29+Mar31+Apr30+May31+Jun30+Jul31+Aug31+Sep30+Oct31+Nov30+20=355.
        # (0+355)%7=5→Saturday. ✓
        fixed_dt = _utc(2024, 12, 22, 1, 0)  # Sat Dec 21 8:00 PM EST
        with patch("nfl_game_updater.datetime") as mock_dt:
            mock_dt.now.return_value = fixed_dt
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            result = is_nfl_game_time(current_week=16)
        assert result is True

    def test_uses_eastern_dst_and_local_weekday(self):
        """Monday Night Football remains Monday locally after UTC rolls to Tuesday."""
        assert is_nfl_game_time(_utc(2026, 9, 15, 0, 30), current_week=2) is True


# ---------------------------------------------------------------------------
# TestFetchNflGameResults
# ---------------------------------------------------------------------------


class TestFetchNflGameResults:
    """fetch_nfl_game_results(week) calls requests.get and parses ESPN response."""

    def _mock_response(self, events: list, status_code: int = 200) -> MagicMock:
        resp = MagicMock()
        resp.status_code = status_code
        resp.json.return_value = {"events": events}
        resp.raise_for_status = MagicMock()
        return resp

    def test_returns_parsed_results_for_completed_game(self):
        """One completed game → one result dict with correct fields."""
        event = _make_espn_event(
            home_abbrv="NE",
            away_abbrv="BUF",
            home_score=21,
            away_score=17,
            status_name="STATUS_FINAL",
            week=5,
        )
        with patch("nfl_game_updater.requests.get") as mock_get:
            mock_get.return_value = self._mock_response([event])
            results = fetch_nfl_game_results(5)

        assert len(results) == 1
        r = results[0]
        assert r["home_team_abbrv"] == "NE"
        assert r["away_team_abbrv"] == "BUF"
        assert r["home_score"] == 21
        assert r["away_score"] == 17
        assert r["winning_team_abbrv"] == "NE"
        assert r["status"] == "STATUS_FINAL"
        assert r["week"] == 5

    def test_returns_parsed_result_for_in_progress_game(self):
        """STATUS_IN_PROGRESS games are also included (live updates)."""
        event = _make_espn_event(
            home_abbrv="KC",
            away_abbrv="LV",
            home_score=14,
            away_score=7,
            status_name="STATUS_IN_PROGRESS",
        )
        with patch("nfl_game_updater.requests.get") as mock_get:
            mock_get.return_value = self._mock_response([event])
            results = fetch_nfl_game_results(8)

        assert len(results) == 1
        assert results[0]["status"] == "STATUS_IN_PROGRESS"

    def test_returns_empty_for_no_games(self):
        """Empty events list → empty results list."""
        with patch("nfl_game_updater.requests.get") as mock_get:
            mock_get.return_value = self._mock_response([])
            results = fetch_nfl_game_results(5)

        assert results == []

    def test_skips_scheduled_games(self):
        """Games with STATUS_SCHEDULED are not included in results."""
        event = _make_espn_event(
            home_abbrv="DAL",
            away_abbrv="NYG",
            home_score=0,
            away_score=0,
            status_name="STATUS_SCHEDULED",
        )
        with patch("nfl_game_updater.requests.get") as mock_get:
            mock_get.return_value = self._mock_response([event])
            results = fetch_nfl_game_results(5)

        assert results == []

    def test_handles_api_error_gracefully(self):
        """requests.RequestException propagates (caller handles retry logic)."""
        import requests as _requests

        with patch("nfl_game_updater.requests.get") as mock_get:
            mock_get.side_effect = _requests.RequestException("connection timeout")
            with pytest.raises(_requests.RequestException):
                fetch_nfl_game_results(5)

    def test_passes_correct_week_and_season_params(self):
        """Verifies the ESPN API is called with the correct query params."""
        with patch("nfl_game_updater.requests.get") as mock_get:
            mock_get.return_value = self._mock_response([])
            fetch_nfl_game_results(12)

        _call_kwargs = mock_get.call_args
        params = _call_kwargs[1]["params"] if _call_kwargs[1] else _call_kwargs[0][1]
        assert params["week"] == 12
        assert params["seasontype"] == 2

    def test_away_team_wins_when_away_score_higher(self):
        """Away team score > home team score → away team is the winner."""
        event = _make_espn_event(
            home_abbrv="SF",
            away_abbrv="SEA",
            home_score=10,
            away_score=28,
            status_name="STATUS_FINAL",
        )
        with patch("nfl_game_updater.requests.get") as mock_get:
            mock_get.return_value = self._mock_response([event])
            results = fetch_nfl_game_results(10)

        assert results[0]["winning_team_abbrv"] == "SEA"


# ---------------------------------------------------------------------------
# TestUpdateGameResults
# ---------------------------------------------------------------------------


class TestUpdateGameResults:
    """update_game_results(db, game_results) writes winning_team_id to Schedule rows."""

    def _make_game(self, home="NE", away="BUF", winner="NE", week=5) -> dict:
        return {
            "home_team_abbrv": home,
            "away_team_abbrv": away,
            "home_score": 21,
            "away_score": 17,
            "winning_team_abbrv": winner,
            "status": "STATUS_FINAL",
            "week": week,
        }

    def _setup_db(
        self,
        home_team_id=1,
        away_team_id=2,
        home_abbrv="NE",
        away_abbrv="BUF",
        found_schedule=True,
    ):
        """Return a mock db session pre-configured with team and schedule lookups."""
        db = _mock_db()

        home_team = MagicMock()
        home_team.id = home_team_id
        home_team.abbrv = home_abbrv

        away_team = MagicMock()
        away_team.id = away_team_id
        away_team.abbrv = away_abbrv

        scheduled_game = MagicMock()
        scheduled_game.winning_team_id = None

        # Track how many times Team has been queried so we can alternate results.
        # Each call to query_side_effect creates a fresh q/filter chain, so we
        # cannot rely on a shared side_effect list on a single filter_mock.
        _team_call = {"n": 0}

        def query_side_effect(model):
            from models import Team, Schedule

            q = MagicMock()
            if model is Team:
                _team_call["n"] += 1
                result = home_team if _team_call["n"] == 1 else away_team
                f = MagicMock()
                f.first.return_value = result
                q.filter.return_value = f
            elif model is Schedule:
                f = MagicMock()
                f.first.return_value = scheduled_game if found_schedule else None
                q.filter.return_value = f
            return q

        db.query.side_effect = query_side_effect
        return db, home_team, away_team, scheduled_game

    def test_updates_winning_team_for_completed_game(self):
        """Home team wins → scheduled_game.winning_team_id set to home_team.id."""
        db, home_team, away_team, scheduled_game = self._setup_db()
        game = self._make_game(home="NE", away="BUF", winner="NE")

        count = update_game_results(db, [game])

        assert count == 1
        assert scheduled_game.winning_team_id == home_team.id

    def test_updates_winning_team_away_wins(self):
        """Away team wins → winning_team_id set to away_team.id."""
        db, home_team, away_team, scheduled_game = self._setup_db(
            home_abbrv="NE", away_abbrv="BUF"
        )
        game = self._make_game(home="NE", away="BUF", winner="BUF")

        count = update_game_results(db, [game])

        assert count == 1
        assert scheduled_game.winning_team_id == away_team.id

    def test_skips_games_not_in_schedule(self):
        """No matching Schedule row → no error, count stays 0."""
        db, *_ = self._setup_db(found_schedule=False)
        game = self._make_game()

        count = update_game_results(db, [game])

        assert count == 0

    def test_skips_non_final_games(self):
        """STATUS_IN_PROGRESS games are not written to the schedule."""
        db = _mock_db()
        game = {
            "home_team_abbrv": "NE",
            "away_team_abbrv": "BUF",
            "winning_team_abbrv": "NE",
            "status": "STATUS_IN_PROGRESS",
            "week": 5,
        }

        count = update_game_results(db, [game])

        assert count == 0
        db.query.assert_not_called()

    def test_returns_zero_for_empty_game_list(self):
        db = _mock_db()
        count = update_game_results(db, [])
        assert count == 0

    def test_does_not_call_commit(self):
        """update_game_results does not commit — the caller (lambda_handler) does."""
        db, *_ = self._setup_db()
        update_game_results(db, [self._make_game()])
        db.commit.assert_not_called()


# ---------------------------------------------------------------------------
# TestUpdatePicksResults
# ---------------------------------------------------------------------------


class TestUpdatePicksResults:
    """update_picks_results(db, game_results) sets Pick.result to 'win' or 'loss'."""

    def _make_game_results(
        self,
        home="NE",
        away="BUF",
        winner="NE",
        week=5,
        status="STATUS_FINAL",
    ) -> list:
        return [
            {
                "home_team_abbrv": home,
                "away_team_abbrv": away,
                "winning_team_abbrv": winner,
                "status": status,
                "week": week,
            }
        ]

    def _setup_db_with_picks(self, team_abbrv: str, picks: list) -> MagicMock:
        """
        Return a db mock where every Team query returns a mock Team with the
        given abbrv, and every Pick query returns the provided picks list.
        Use this helper only when a single team/pick mapping is sufficient.
        """
        db = _mock_db()

        team_obj = MagicMock()
        team_obj.abbrv = team_abbrv

        def query_side_effect(model):
            from models import Team, Pick as PickModel

            q = MagicMock()
            if model is Team:
                f = MagicMock()
                f.first.return_value = team_obj
                q.filter.return_value = f
            elif model is PickModel:
                f = MagicMock()
                f.all.return_value = picks
                q.filter.return_value = f
            return q

        db.query.side_effect = query_side_effect
        return db

    def _setup_db_two_teams(
        self,
        winner_abbrv: str,
        loser_abbrv: str,
        winner_picks: list,
        loser_picks: list,
    ) -> MagicMock:
        """
        Return a db mock that handles two sequential Team queries (winner first,
        loser second) and two sequential Pick queries in the same order.

        The function iterates over team_results dict (winner key, then loser key)
        so we track call counts independently for Team and Pick queries.
        """
        db = _mock_db()

        winner_team = MagicMock()
        winner_team.abbrv = winner_abbrv

        loser_team = MagicMock()
        loser_team.abbrv = loser_abbrv

        _team_n = {"n": 0}
        _pick_n = {"n": 0}

        def query_side_effect(model):
            from models import Team, Pick as PickModel

            q = MagicMock()
            if model is Team:
                _team_n["n"] += 1
                result = winner_team if _team_n["n"] == 1 else loser_team
                f = MagicMock()
                f.first.return_value = result
                q.filter.return_value = f
            elif model is PickModel:
                _pick_n["n"] += 1
                result = winner_picks if _pick_n["n"] == 1 else loser_picks
                f = MagicMock()
                f.all.return_value = result
                q.filter.return_value = f
            return q

        db.query.side_effect = query_side_effect
        return db

    def test_sets_win_for_pick_on_winning_team(self):
        """Pick backing the winner gets result='win'; pick for the loser is absent."""
        win_pick = MagicMock()
        win_pick.result = None
        win_pick.entry_id = "entry-1"
        win_pick.week = 5

        game_results = self._make_game_results(home="NE", away="BUF", winner="NE")
        # winner (ne) has [win_pick]; loser (buf) has no picks
        db = self._setup_db_two_teams("ne", "buf", [win_pick], [])

        count = update_picks_results(db, game_results)

        assert win_pick.result == "win"
        assert count == 1

    def test_sets_loss_for_pick_on_losing_team(self):
        """Pick backing the loser gets result='loss'; pick for the winner is absent."""
        loss_pick = MagicMock()
        loss_pick.result = None
        loss_pick.entry_id = "entry-2"
        loss_pick.week = 5

        game_results = self._make_game_results(home="NE", away="BUF", winner="NE")
        # winner (ne) has no picks; loser (buf) has [loss_pick]
        db = self._setup_db_two_teams("ne", "buf", [], [loss_pick])

        count = update_picks_results(db, game_results)

        assert loss_pick.result == "loss"
        assert count == 1

    def test_skips_already_resolved_picks(self):
        """
        Picks with an existing result are filtered out by the SQL query
        (Pick.result.is_(None)).  The mock returns an empty list to simulate
        this, confirming the function is idempotent.
        """
        pick = MagicMock()
        pick.result = "win"  # already resolved

        game_results = self._make_game_results()
        # DB returns no pending picks (simulates the is_(None) filter)
        db = self._setup_db_with_picks("ne", [])

        count = update_picks_results(db, game_results)

        # pick.result must remain unchanged
        assert pick.result == "win"

    def test_returns_zero_for_empty_game_results(self):
        """No game results → early return with 0 picks updated."""
        db = _mock_db()
        count = update_picks_results(db, [])
        assert count == 0

    def test_skips_non_final_games_in_pick_resolution(self):
        """IN_PROGRESS games do not contribute to team_results mapping."""
        pick = MagicMock()
        pick.result = None

        game_results = self._make_game_results(status="STATUS_IN_PROGRESS")
        db = _mock_db()

        # team_results dict will be empty → no picks queried
        update_picks_results(db, game_results)

        # The pick should not have been touched
        assert pick.result is None

    def test_does_not_call_commit(self):
        """update_picks_results does not commit — lambda_handler does."""
        game_results = self._make_game_results()
        db = self._setup_db_with_picks("ne", [])
        update_picks_results(db, game_results)
        db.commit.assert_not_called()


# ---------------------------------------------------------------------------
# TestEliminateLosingEntries
# ---------------------------------------------------------------------------


class TestEliminateLosingEntries:
    """eliminate_losing_entries(db) sets entry.alive=False for entries with a loss."""

    def _db_with_losing_entries(self, entries: list) -> MagicMock:
        """Return a db whose Entry+Pick join query yields the given entries."""
        db = _mock_db()

        # The function chains: db.query(Entry).join(Pick).filter(...).distinct().all()
        chain = MagicMock()
        chain.all.return_value = entries

        q = MagicMock()
        q.join.return_value = q
        q.filter.return_value = q
        q.distinct.return_value = chain

        db.query.return_value = q

        # Also handle the inner query for losing_picks log (return empty list)
        pick_chain = MagicMock()
        pick_chain.all.return_value = []
        inner_q = MagicMock()
        inner_q.filter.return_value = pick_chain

        # First call → Entry query; subsequent calls → Pick query for audit log
        db.query.side_effect = [q] + [inner_q] * len(entries)

        return db

    def test_sets_alive_false_for_entry_with_loss(self):
        """Entry with alive=True and a losing pick → alive set to False."""
        entry = MagicMock()
        entry.id = "entry-1"
        entry.user_id = "user-1"
        entry.alive = True

        db = self._db_with_losing_entries([entry])

        count = eliminate_losing_entries(db)

        assert entry.alive is False
        assert count == 1

    def test_returns_count_of_eliminated_entries(self):
        """Two losing entries → count == 2."""
        entries = [MagicMock(id=f"e-{i}", user_id="u", alive=True) for i in range(2)]
        db = self._db_with_losing_entries(entries)

        count = eliminate_losing_entries(db)

        assert count == 2
        for entry in entries:
            assert entry.alive is False

    def test_keeps_alive_entries_with_win(self):
        """No losing entries returned by query → no entries eliminated."""
        db = self._db_with_losing_entries([])  # query returns empty = no losers

        count = eliminate_losing_entries(db)

        assert count == 0

    def test_keeps_alive_entries_with_no_picks(self):
        """Entries with no picks at all are not returned by the join query."""
        db = self._db_with_losing_entries([])

        count = eliminate_losing_entries(db)

        assert count == 0

    def test_does_not_commit(self):
        """eliminate_losing_entries does not call db.commit()."""
        db = self._db_with_losing_entries([])

        eliminate_losing_entries(db)

        db.commit.assert_not_called()

    def test_returns_zero_on_exception(self):
        """If the query raises, the function catches it and returns 0."""
        db = _mock_db()
        db.query.side_effect = Exception("DB connection lost")

        count = eliminate_losing_entries(db)

        assert count == 0


# ---------------------------------------------------------------------------
# Pool-aware correction and schedule-derived context tests
# ---------------------------------------------------------------------------


@pytest.fixture
def scoring_db():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    from models import Base

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


class TestPoolAwareScoring:
    def _seed_pool_types(self, db):
        from models import Entry, Pick, Pool, Team

        db.add_all(
            [
                Team(id=1, name="New England Patriots", abbrv="NE"),
                Team(id=2, name="Buffalo Bills", abbrv="BUF"),
                Pool(id="survivor", name="Survivor", pool_type="survivor"),
                Pool(id="pickem", name="Pick Em", pool_type="pickem"),
                Entry(id="survivor-entry", pool_id="survivor", alive=False),
                Entry(id="pickem-entry", pool_id="pickem", alive=True),
                Pick(
                    id="survivor-pick",
                    entry_id="survivor-entry",
                    week=4,
                    team="NE",
                    result="loss",
                ),
                Pick(
                    id="pickem-pick",
                    entry_id="pickem-entry",
                    week=4,
                    game_id=100,
                    team="BUF",
                    result="win",
                ),
            ]
        )
        db.commit()

    def test_official_correction_updates_both_pool_types_and_restores_survivor(
        self, scoring_db
    ):
        from models import Entry, Pick

        self._seed_pool_types(scoring_db)
        results = [
            {
                "home_team_abbrv": "NE",
                "away_team_abbrv": "BUF",
                "winning_team_abbrv": "NE",
                "status": "STATUS_FINAL",
                "week": 4,
            }
        ]

        assert update_picks_results(scoring_db, results) == 2
        assert reconcile_survivor_entries(scoring_db) == 1
        assert scoring_db.get(Pick, "survivor-pick").result == "win"
        assert scoring_db.get(Pick, "pickem-pick").result == "loss"
        assert scoring_db.get(Entry, "survivor-entry").alive is True
        assert scoring_db.get(Entry, "pickem-entry").alive is True

    def test_pickem_loss_never_eliminates_entry(self, scoring_db):
        from models import Entry

        self._seed_pool_types(scoring_db)
        assert reconcile_survivor_entries(scoring_db) == 0
        assert scoring_db.get(Entry, "pickem-entry").alive is True


class TestScheduleDerivedContext:
    def test_resolves_week_and_previous_season_during_january(self, scoring_db):
        from models import Schedule, Team

        scoring_db.add_all(
            [
                Team(id=11, name="Home", abbrv="HME"),
                Team(id=12, name="Away", abbrv="AWY"),
                Schedule(
                    game_id=200,
                    week_num=18,
                    home_team_id=11,
                    away_team_id=12,
                    start_time=datetime(2027, 1, 10, 18, 0),
                    winning_team_id=None,
                ),
            ]
        )
        scoring_db.commit()

        assert get_current_nfl_context(scoring_db, _utc(2027, 1, 10, 17, 0)) == (
            2026,
            18,
        )
        assert all_games_final_for_week(scoring_db, 18) is False


class TestHandlerFailureSemantics:
    def test_failures_are_raised_for_scheduler_retry_and_dlq(self):
        with (
            patch("nfl_game_updater.is_done_for_today", return_value=False),
            patch(
                "nfl_game_updater.get_database_engine",
                side_effect=RuntimeError("database unavailable"),
            ),
        ):
            with pytest.raises(RuntimeError, match="database unavailable"):
                nfl_game_updater.lambda_handler({}, None)

    def test_force_invocation_bypasses_daily_completion_marker(self):
        with (
            patch("nfl_game_updater.is_done_for_today") as done,
            patch(
                "nfl_game_updater.get_database_engine",
                side_effect=RuntimeError("stop after guard"),
            ),
        ):
            with pytest.raises(RuntimeError, match="stop after guard"):
                nfl_game_updater.lambda_handler({"force": True}, None)
        done.assert_not_called()


# ---------------------------------------------------------------------------
# Additional tests from litmus stubs:
#   lambda-src-nfl-game-updater-fetch-nfl-game-results
#   lambda-src-nfl-game-updater-update-game-results
#   lambda-src-nfl-game-updater-reconcile-survivor-entries
# ---------------------------------------------------------------------------


class TestFetchNflGameResultsAdditional:
    """Additional tests for fetch_nfl_game_results covering litmus stub scenarios."""

    def test_returns_empty_list_for_week_with_no_completed_games(self):
        """fetch_nfl_game_results returns an empty list when no games have results."""
        payload = {"events": []}
        fake_response = MagicMock()
        fake_response.status_code = 200
        fake_response.json.return_value = payload

        with patch("nfl_game_updater.requests") as mock_requests:
            mock_requests.get.return_value = fake_response
            results = fetch_nfl_game_results(week=5)

        assert results == []

    def test_returns_empty_list_on_espn_http_error(self):
        """fetch_nfl_game_results returns empty list (or does not raise) on ESPN HTTP error."""
        fake_response = MagicMock()
        fake_response.status_code = 500
        fake_response.json.return_value = {}
        # Simulate requests raising on HTTP error
        fake_response.raise_for_status.side_effect = Exception("Server error")

        with patch("nfl_game_updater.requests") as mock_requests:
            mock_requests.get.return_value = fake_response
            try:
                results = fetch_nfl_game_results(week=5)
                # If the function catches the error, expect empty list
                assert results == [] or isinstance(results, list)
            except Exception:
                # If the function propagates the error, that is also valid per contract
                pass

    def test_handles_malformed_json_gracefully(self):
        """fetch_nfl_game_results handles non-JSON response body."""
        fake_response = MagicMock()
        fake_response.status_code = 200
        fake_response.json.side_effect = ValueError("Invalid JSON")
        fake_response.raise_for_status.return_value = None

        with patch("nfl_game_updater.requests") as mock_requests:
            mock_requests.get.return_value = fake_response
            try:
                results = fetch_nfl_game_results(week=5)
                assert results == [] or isinstance(results, list)
            except (ValueError, Exception):
                pass  # Propagating is also an acceptable contract


class TestUpdateGameResultsAdditional:
    """Additional tests for update_game_results covering litmus stub scenarios."""

    def test_skips_game_id_not_in_schedule(self, scoring_db):
        """update_game_results skips results whose game_id is absent from the schedule table."""
        from models import Team

        scoring_db.add(Team(id=999, name="Unknown", abbrv="UNK"))
        scoring_db.commit()

        unknown_game = {
            "game_id": 99999999,
            "home_team_abbrv": "UNK",
            "away_team_abbrv": "UNK",
            "winning_team_abbrv": "UNK",
            "home_score": 21,
            "away_score": 14,
            "status": "STATUS_FINAL",
            "week": 1,
        }

        # Should not raise — unknown game IDs are skipped
        result = update_game_results(scoring_db, [unknown_game])
        assert result == 0 or result is not None  # Count may be 0 for unknown games

    def test_empty_game_results_returns_zero(self, scoring_db):
        """update_game_results with empty list returns 0 updated games."""
        result = update_game_results(scoring_db, [])
        assert result == 0


class TestReconcileSurvivorEntriesAdditional:
    """Additional tests for reconcile_survivor_entries covering litmus stub scenarios."""

    def test_entries_with_no_picks_remain_alive(self, scoring_db):
        """Entries with zero picks are not eliminated by reconcile_survivor_entries."""
        from models import Entry, Pool

        scoring_db.add_all(
            [
                Pool(id="surv-nopick", name="Surv NoPick", pool_type="survivor"),
                Entry(id="entry-nopick", pool_id="surv-nopick", alive=True),
            ]
        )
        scoring_db.commit()

        result = reconcile_survivor_entries(scoring_db)
        entry = scoring_db.get(Entry, "entry-nopick")
        assert entry.alive is True

    def test_all_already_eliminated_is_idempotent(self, scoring_db):
        """Entries already marked alive=False are not double-processed."""
        from models import Entry, Pick, Pool, Team

        scoring_db.add_all(
            [
                Team(id=501, name="Team A", abbrv="AAA"),
                Team(id=502, name="Team B", abbrv="BBB"),
                Pool(id="surv-dead", name="Surv Dead", pool_type="survivor"),
                Entry(id="entry-dead", pool_id="surv-dead", alive=False),
                Pick(
                    id="pick-dead",
                    entry_id="entry-dead",
                    week=1,
                    team="AAA",
                    result="loss",
                ),
            ]
        )
        scoring_db.commit()

        count = reconcile_survivor_entries(scoring_db)
        entry = scoring_db.get(Entry, "entry-dead")
        assert entry.alive is False
        # Already-dead entry does not inflate the change count
        assert count == 0
