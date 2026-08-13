from contextlib import contextmanager
from datetime import datetime, timezone

import pytest

import models
import result_updater
from services.job_lock import advisory_job_lock
from services.nfl_results import NflGameResult, ResultProviderError, parse_scoreboard
from services.scoring import ScoringDiscrepancy, apply_final_results


def _scoreboard_event(*, status="STATUS_FINAL", home_score="24", away_score="17"):
    return {
        "events": [
            {
                "id": "401000001",
                "status": {"type": {"name": status}},
                "competitions": [
                    {
                        "competitors": [
                            {
                                "homeAway": "home",
                                "score": home_score,
                                "team": {"abbreviation": "WSH"},
                            },
                            {
                                "homeAway": "away",
                                "score": away_score,
                                "team": {"abbreviation": "DAL"},
                            },
                        ]
                    }
                ],
            }
        ]
    }


def _seed_scoring(db):
    home = models.Team(id=1, name="Washington Commanders", abbrv="WAS")
    away = models.Team(id=2, name="Dallas Cowboys", abbrv="DAL")
    user = models.User(
        id="user-1", email="scores@example.com", hashed_password="unused"
    )
    survivor = models.Pool(
        id="survivor-pool",
        name="Survivor Scoring",
        owner_id=user.id,
        pool_type="survivor",
    )
    pickem = models.Pool(
        id="pickem-pool", name="Pickem Scoring", owner_id=user.id, pool_type="pickem"
    )
    survivor_entry = models.Entry(
        id="survivor-entry",
        user_id=user.id,
        pool_id=survivor.id,
        name="Survivor",
        alive=True,
    )
    pickem_entry = models.Entry(
        id="pickem-entry", user_id=user.id, pool_id=pickem.id, name="Pickem", alive=True
    )
    game = models.Schedule(
        game_id=401000001,
        season=2026,
        week_num=1,
        home_team_id=home.id,
        away_team_id=away.id,
        start_time=datetime(2026, 9, 13, 17),
    )
    other_game = models.Schedule(
        game_id=401000002,
        season=2026,
        week_num=1,
        home_team_id=home.id,
        away_team_id=away.id,
        start_time=datetime(2026, 9, 20, 17),
    )
    picks = [
        models.Pick(
            id="survivor-pick",
            entry_id=survivor_entry.id,
            week=1,
            team="DAL",
            team_id=away.id,
        ),
        models.Pick(
            id="pickem-home",
            entry_id=pickem_entry.id,
            week=1,
            game_id=game.game_id,
            team="WAS",
            team_id=home.id,
        ),
        models.Pick(
            id="pickem-other-game",
            entry_id=pickem_entry.id,
            week=1,
            game_id=other_game.game_id,
            team="DAL",
            team_id=away.id,
        ),
    ]
    db.add_all(
        [
            home,
            away,
            user,
            survivor,
            pickem,
            survivor_entry,
            pickem_entry,
            game,
            other_game,
            *picks,
        ]
    )
    db.commit()
    return game, survivor_entry, pickem_entry


def _result(home_score=24, away_score=17):
    return NflGameResult(
        game_id=401000001,
        season=2026,
        week=1,
        status="final",
        home_abbreviation="WSH",
        away_abbreviation="DAL",
        home_score=home_score,
        away_score=away_score,
    )


def test_parse_final_scoreboard_and_washington_alias():
    result = parse_scoreboard(_scoreboard_event(), season=2026, week=1)[0]
    assert result.game_id == 401000001
    assert result.status == "final"
    assert result.home_abbreviation == "WSH"
    assert result.home_score == 24
    assert result.away_score == 17


def test_parse_rejects_final_game_without_score():
    with pytest.raises(ResultProviderError, match="missing a score"):
        parse_scoreboard(_scoreboard_event(home_score=None), season=2026, week=1)


def test_apply_results_scores_both_pool_types_by_exact_game(db_session):
    game, survivor_entry, pickem_entry = _seed_scoring(db_session)

    summary = apply_final_results(db_session, [_result()])
    db_session.commit()

    assert summary.games_changed == 1
    assert summary.picks_changed == 2
    assert summary.entries_changed == 1
    assert game.winning_team_id == 1
    assert game.home_score == 24
    assert survivor_entry.alive is False
    assert pickem_entry.alive is True
    assert db_session.get(models.Pick, "pickem-home").result == "win"
    assert db_session.get(models.Pick, "pickem-other-game").result is None


def test_identical_rerun_is_idempotent(db_session):
    _seed_scoring(db_session)
    apply_final_results(db_session, [_result()])
    db_session.commit()

    summary = apply_final_results(db_session, [_result()])
    db_session.commit()

    assert summary.games_changed == 0
    assert summary.picks_changed == 0
    assert summary.entries_changed == 0


def test_official_correction_reconciles_picks_and_survivor(db_session):
    _, survivor_entry, _ = _seed_scoring(db_session)
    apply_final_results(db_session, [_result()])
    db_session.commit()
    assert survivor_entry.alive is False

    summary = apply_final_results(db_session, [_result(home_score=17, away_score=24)])
    db_session.commit()

    assert summary.games_changed == 1
    assert summary.picks_changed == 2
    assert summary.entries_changed == 1
    assert survivor_entry.alive is True
    assert db_session.get(models.Pick, "survivor-pick").result == "win"
    assert db_session.get(models.Pick, "pickem-home").result == "loss"


def test_final_tie_awards_no_pickem_point_and_eliminates_survivor(db_session):
    game, survivor_entry, pickem_entry = _seed_scoring(db_session)

    apply_final_results(db_session, [_result(home_score=20, away_score=20)])
    db_session.commit()

    assert game.winning_team_id is None
    assert db_session.get(models.Pick, "survivor-pick").result == "loss"
    assert db_session.get(models.Pick, "pickem-home").result == "loss"
    assert survivor_entry.alive is False
    assert pickem_entry.alive is True


def test_unknown_game_fails_before_any_updates(db_session):
    game, _, _ = _seed_scoring(db_session)
    unknown = NflGameResult(
        game_id=999999,
        season=2026,
        week=1,
        status="final",
        home_abbreviation="WSH",
        away_abbreviation="DAL",
        home_score=10,
        away_score=7,
    )

    with pytest.raises(ScoringDiscrepancy, match="Unknown provider game IDs"):
        apply_final_results(db_session, [unknown])

    assert game.status == "scheduled"
    assert game.winning_team_id is None


def test_candidate_contexts_use_schedule_window(db_session):
    _seed_scoring(db_session)
    contexts = result_updater.candidate_contexts(
        db_session,
        now=datetime(2026, 9, 13, 20, tzinfo=timezone.utc),
    )
    assert contexts == [(2026, 1)]


def test_candidate_contexts_require_complete_override(db_session):
    with pytest.raises(ValueError, match="supplied together"):
        result_updater.candidate_contexts(db_session, season=2026)


def test_sqlite_job_lock_is_available(db_session):
    with advisory_job_lock(db_session.get_bind(), "test-lock") as acquired:
        assert acquired is True


def test_dry_run_records_summary_without_scoring_changes(db_session, monkeypatch):
    game, survivor_entry, _ = _seed_scoring(db_session)
    run_id = "dry-run-id"
    result_updater.create_run_record(
        db_session, run_id=run_id, season=2026, week=1, dry_run=True
    )
    monkeypatch.setattr(
        result_updater, "fetch_scoreboard", lambda season, week: [_result()]
    )

    summary = result_updater.run_update(
        db_session, run_id=run_id, season=2026, week=1, dry_run=True
    )

    db_session.expire_all()
    assert summary.games_changed == 1
    assert db_session.get(models.Schedule, game.game_id).status == "scheduled"
    assert db_session.get(models.Entry, survivor_entry.id).alive is True
    record = db_session.get(models.UpdaterRun, run_id)
    assert record.status == "dry_run"
    assert record.games_changed == 1


def test_writer_run_persists_results_and_audit(db_session, monkeypatch):
    game, survivor_entry, _ = _seed_scoring(db_session)
    run_id = "writer-run-id"
    result_updater.create_run_record(
        db_session, run_id=run_id, season=2026, week=1, dry_run=False
    )
    monkeypatch.setattr(
        result_updater, "fetch_scoreboard", lambda season, week: [_result()]
    )

    result_updater.run_update(db_session, run_id=run_id, season=2026, week=1)

    assert game.status == "final"
    assert survivor_entry.alive is False
    assert db_session.get(models.UpdaterRun, run_id).status == "succeeded"


def test_no_candidate_games_is_audited(db_session):
    run_id = "no-games-id"
    result_updater.create_run_record(
        db_session, run_id=run_id, season=None, week=None, dry_run=False
    )
    summary = result_updater.run_update(db_session, run_id=run_id)
    assert summary.final_games == 0
    assert db_session.get(models.UpdaterRun, run_id).status == "no_games"


def test_main_lock_skip_exits_successfully(db_session, monkeypatch):
    @contextmanager
    def unavailable_lock(engine, name):
        yield False

    monkeypatch.setattr(result_updater, "SessionLocal", lambda: db_session)
    monkeypatch.setattr(result_updater, "advisory_job_lock", unavailable_lock)

    assert result_updater.main(["--run-id", "locked-run"]) == 0
    assert db_session.get(models.UpdaterRun, "locked-run").status == "lock_skipped"


def test_main_failure_is_audited_and_exits_nonzero(db_session, monkeypatch):
    _seed_scoring(db_session)
    monkeypatch.setattr(result_updater, "SessionLocal", lambda: db_session)
    monkeypatch.setattr(
        result_updater,
        "fetch_scoreboard",
        lambda season, week: (_ for _ in ()).throw(RuntimeError("provider down")),
    )

    exit_code = result_updater.main(
        ["--run-id", "failed-run", "--season", "2026", "--week", "1"]
    )

    assert exit_code == 1
    record = db_session.get(models.UpdaterRun, "failed-run")
    assert record.status == "failed"
    assert record.error == "provider down"
