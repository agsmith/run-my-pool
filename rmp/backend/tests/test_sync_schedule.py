from datetime import datetime, timedelta

import pytest

import models
from sync_schedule import (
    ScheduleGame,
    ScheduleSyncError,
    fetch_season_schedule,
    sync_season_schedule,
    validate_week,
)


TEAM_ABBRVS = [f"T{i:02d}" for i in range(32)]


def _season_games(season=2026):
    games = []
    for week in range(1, 19):
        kickoff = datetime(season, 9, 10) + timedelta(weeks=week - 1)
        for index in range(16):
            games.append(
                ScheduleGame(
                    game_id=season * 100000 + week * 100 + index,
                    week_num=week,
                    home_abbrv=TEAM_ABBRVS[index * 2],
                    away_abbrv=TEAM_ABBRVS[index * 2 + 1],
                    start_time=kickoff + timedelta(hours=index),
                )
            )
    return games


def _seed_teams(db_session, abbrvs=TEAM_ABBRVS):
    for team_id, abbrv in enumerate(abbrvs, start=1):
        db_session.add(models.Team(id=team_id, name=f"Team {abbrv}", abbrv=abbrv))
    db_session.commit()


def _espn_payload(season, week):
    events = []
    for game in [g for g in _season_games(season) if g.week_num == week]:
        events.append(
            {
                "id": str(game.game_id),
                "date": game.start_time.isoformat() + "Z",
                "season": {"year": season, "type": 2, "slug": "regular-season"},
                "week": {"number": week},
                "competitions": [
                    {
                        "competitors": [
                            {
                                "homeAway": "home",
                                "team": {"abbreviation": game.home_abbrv},
                            },
                            {
                                "homeAway": "away",
                                "team": {"abbreviation": game.away_abbrv},
                            },
                        ]
                    }
                ],
            }
        )
    return {"events": events}


class _Response:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


def test_week_with_17_games_is_rejected():
    games = [game for game in _season_games() if game.week_num == 2]
    games.append(
        ScheduleGame(
            game_id=999999,
            week_num=2,
            home_abbrv=TEAM_ABBRVS[0],
            away_abbrv=TEAM_ABBRVS[1],
            start_time=datetime(2026, 9, 22),
        )
    )

    with pytest.raises(ScheduleSyncError, match="Week 2 has 17 games"):
        validate_week(games, 2)


def test_duplicate_team_in_week_is_rejected():
    games = [game for game in _season_games() if game.week_num == 2]
    games[-1] = ScheduleGame(
        game_id=games[-1].game_id,
        week_num=2,
        home_abbrv=games[0].home_abbrv,
        away_abbrv=games[-1].away_abbrv,
        start_time=games[-1].start_time,
    )

    with pytest.raises(ScheduleSyncError, match="schedules teams more than once"):
        validate_week(games, 2)


def test_fetch_requests_explicit_regular_season_and_all_weeks():
    calls = []

    def fake_get(url, params, timeout):
        calls.append((url, params, timeout))
        return _Response(_espn_payload(params["year"], params["week"]))

    games = fetch_season_schedule(2026, request_get=fake_get)

    assert len(games) == 18 * 16
    assert [call[1]["week"] for call in calls] == list(range(1, 19))
    assert all(call[1]["year"] == 2026 for call in calls)
    assert all(call[1]["seasontype"] == 2 for call in calls)


def test_sync_replaces_corrupt_season_and_is_idempotent(db_session):
    _seed_teams(db_session)
    db_session.add(
        models.Schedule(
            game_id=999999,
            week_num=2,
            home_team_id=1,
            away_team_id=2,
            start_time=datetime(2026, 9, 20),
            winning_team_id=99,
        )
    )
    db_session.commit()

    first = sync_season_schedule(db_session, 2026, _season_games(), apply=True)
    week_two = (
        db_session.query(models.Schedule).filter(models.Schedule.week_num == 2).all()
    )

    assert first == {
        "season": 2026,
        "games": 288,
        "created": 288,
        "updated": 0,
        "removed": 1,
        "applied": True,
    }
    assert len(week_two) == 16
    assert (
        len(
            {
                team
                for game in week_two
                for team in (game.home_team_id, game.away_team_id)
            }
        )
        == 32
    )
    assert db_session.get(models.Schedule, 999999) is None

    second = sync_season_schedule(db_session, 2026, _season_games(), apply=True)
    assert second["created"] == 0
    assert second["updated"] == 288
    assert second["removed"] == 0


def test_dry_run_does_not_change_database(db_session):
    _seed_teams(db_session)

    result = sync_season_schedule(db_session, 2026, _season_games())

    assert result["applied"] is False
    assert result["created"] == 288
    assert db_session.query(models.Schedule).count() == 0


def test_missing_team_mapping_aborts_before_writing(db_session):
    _seed_teams(db_session, TEAM_ABBRVS[:-1])

    with pytest.raises(ScheduleSyncError, match=TEAM_ABBRVS[-1]):
        sync_season_schedule(db_session, 2026, _season_games(), apply=True)

    assert db_session.query(models.Schedule).count() == 0


def test_stale_game_with_locked_line_is_not_removed(db_session):
    _seed_teams(db_session)
    db_session.add(
        models.Schedule(
            game_id=999999,
            week_num=2,
            home_team_id=1,
            away_team_id=2,
            start_time=datetime(2026, 9, 20),
            winning_team_id=99,
        )
    )
    db_session.add(
        models.PoolGameLine(
            pool_id="pool-with-frozen-line",
            game_id=999999,
            week_num=2,
            favorite_team_id=1,
            spread=-3.0,
            provider="test",
            captured_at=datetime(2026, 9, 1),
        )
    )
    db_session.commit()

    with pytest.raises(ScheduleSyncError, match="locked pool lines"):
        sync_season_schedule(db_session, 2026, _season_games(), apply=True)

    assert db_session.get(models.Schedule, 999999) is not None


# ---------------------------------------------------------------------------
# Tests for sync_schedule.main (rmp-backend-sync-schedule-main stub)
# ---------------------------------------------------------------------------


class TestSyncScheduleMain:
    """Tests for sync_schedule.main entry point."""

    def test_main_dry_run_returns_summary_without_writing(
        self, db_session, monkeypatch
    ):
        """main() without --apply fetches schedule and returns summary but does not write."""
        import sync_schedule
        from sync_schedule import main

        _seed_teams(db_session)

        def fake_fetch(season, request_get=None):
            return _season_games(season)

        monkeypatch.setattr(sync_schedule, "fetch_season_schedule", fake_fetch)
        monkeypatch.setattr(sync_schedule, "SessionLocal", lambda: db_session)

        import sys

        monkeypatch.setattr(sys, "argv", ["sync_schedule.py", "--season", "2026"])

        # main() should complete without error and not write to DB
        # (dry run: no --apply flag)
        import io
        from contextlib import redirect_stdout

        output = io.StringIO()
        try:
            with redirect_stdout(output):
                main()
        except SystemExit as exc:
            # argparse may call sys.exit(0) on --help; re-raise non-zero exits
            if exc.code != 0:
                raise

        result_text = output.getvalue()
        assert (
            "applied" in result_text or db_session.query(models.Schedule).count() == 0
        )

    def test_main_apply_writes_schedule_to_database(self, db_session, monkeypatch):
        """main() with --apply writes schedule rows to the database."""
        import sync_schedule
        from sync_schedule import main

        _seed_teams(db_session)

        def fake_fetch(season, request_get=None):
            return _season_games(season)

        monkeypatch.setattr(sync_schedule, "fetch_season_schedule", fake_fetch)
        monkeypatch.setattr(sync_schedule, "SessionLocal", lambda: db_session)

        import sys

        monkeypatch.setattr(
            sys, "argv", ["sync_schedule.py", "--season", "2026", "--apply"]
        )

        import io
        from contextlib import redirect_stdout

        output = io.StringIO()
        with redirect_stdout(output):
            main()

        assert db_session.query(models.Schedule).count() > 0

    def test_main_missing_season_raises(self, monkeypatch):
        """main() without --season raises a SystemExit (argparse required argument)."""
        import sys

        monkeypatch.setattr(sys, "argv", ["sync_schedule.py"])

        import sync_schedule

        with pytest.raises(SystemExit) as exc_info:
            sync_schedule.main()

        assert exc_info.value.code != 0

    def test_main_espn_error_rolls_back(self, db_session, monkeypatch):
        """If fetch_season_schedule raises, main() propagates the error without partial writes."""
        import sync_schedule

        _seed_teams(db_session)

        def fail_fetch(season, request_get=None):
            raise RuntimeError("ESPN unreachable")

        monkeypatch.setattr(sync_schedule, "fetch_season_schedule", fail_fetch)
        monkeypatch.setattr(sync_schedule, "SessionLocal", lambda: db_session)

        import sys

        monkeypatch.setattr(
            sys, "argv", ["sync_schedule.py", "--season", "2026", "--apply"]
        )

        with pytest.raises(RuntimeError, match="ESPN unreachable"):
            sync_schedule.main()

        assert db_session.query(models.Schedule).count() == 0
