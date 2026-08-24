from contextlib import contextmanager
from datetime import datetime, timezone

import pytest
import requests

import models
import result_updater
from services.job_lock import advisory_job_lock
from services.nfl_results import NflGameResult, ResultProviderError, parse_scoreboard
from services.scoring import (
    ScoringDiscrepancy,
    _allowed_survivor_losses,
    _reconcile_survivor_entries,
    apply_final_results,
)


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


def test_survivor_mulligan_keeps_entry_alive_after_first_loss(db_session):
    _, survivor_entry, _ = _seed_scoring(db_session)
    survivor_entry.pool.survivor_mulligans = 1
    db_session.commit()

    summary = apply_final_results(db_session, [_result()])
    db_session.commit()

    assert db_session.get(models.Pick, "survivor-pick").result == "loss"
    assert survivor_entry.alive is True
    assert summary.entries_changed == 0


def test_survivor_entry_is_eliminated_when_losses_exceed_mulligans(db_session):
    _, survivor_entry, _ = _seed_scoring(db_session)
    survivor_entry.pool.survivor_mulligans = 1
    db_session.add(models.Pick(
        id="survivor-prior-loss",
        entry_id=survivor_entry.id,
        week=0,
        team="NYG",
        result="loss",
    ))
    db_session.commit()

    summary = apply_final_results(db_session, [_result()])
    db_session.commit()

    assert survivor_entry.alive is False
    assert summary.entries_changed == 1


def test_duplicate_loss_rows_in_one_week_only_consume_one_mulligan(db_session):
    _, survivor_entry, _ = _seed_scoring(db_session)
    survivor_entry.pool.survivor_mulligans = 1
    db_session.add_all([
        models.Pick(
            id="survivor-duplicate-loss-a",
            entry_id=survivor_entry.id,
            week=0,
            team="NYG",
            result="loss",
        ),
        models.Pick(
            id="survivor-duplicate-loss-b",
            entry_id=survivor_entry.id,
            week=0,
            team="NYJ",
            result="loss",
        ),
    ])
    db_session.commit()

    # Dallas wins week 1, so the duplicated historical week remains the entry's
    # only distinct losing week and consumes exactly one mulligan.
    summary = apply_final_results(db_session, [_result(home_score=17, away_score=24)])
    db_session.commit()

    assert survivor_entry.alive is True
    assert summary.entries_changed == 0


def test_reconciler_ignores_non_survivor_entries(db_session):
    _, _, pickem_entry = _seed_scoring(db_session)
    pickem_entry.alive = False
    db_session.commit()

    assert _reconcile_survivor_entries(db_session, {pickem_entry.id}) == 0
    assert pickem_entry.alive is False


@pytest.mark.parametrize(
    ("stored_value", "expected"),
    [(-100, 0), (0, 0), (2, 2), (100, 3)],
)
def test_mulligan_allowance_fails_safe_for_corrupted_values(stored_value, expected):
    pool = models.Pool(survivor_mulligans=stored_value)
    assert _allowed_survivor_losses(pool) == expected


def test_score_correction_restores_mulligan_entry_below_loss_limit(db_session):
    _, survivor_entry, _ = _seed_scoring(db_session)
    survivor_entry.pool.survivor_mulligans = 1
    db_session.add(models.Pick(
        id="survivor-correction-prior-loss",
        entry_id=survivor_entry.id,
        week=0,
        team="NYG",
        result="loss",
    ))
    db_session.commit()

    apply_final_results(db_session, [_result()])
    db_session.commit()
    assert survivor_entry.alive is False

    summary = apply_final_results(db_session, [_result(home_score=17, away_score=24)])
    db_session.commit()

    assert db_session.get(models.Pick, "survivor-pick").result == "win"
    assert survivor_entry.alive is True
    assert summary.entries_changed == 1


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


# ---------------------------------------------------------------------------
# Tests for fetch_scoreboard (rmp-backend-services-nfl-results-fetch-scoreboard stub)
# ---------------------------------------------------------------------------


class TestFetchScoreboard:
    """Tests for services.nfl_results.fetch_scoreboard HTTP layer."""

    def _make_response(self, payload, status_code=200):
        class FakeResponse:
            def raise_for_status(self_inner):
                if status_code != 200:
                    raise Exception(f"HTTP {status_code}")

            def json(self_inner):
                return payload

        return FakeResponse()

    def test_fetch_scoreboard_returns_parsed_results_on_success(self):
        """Happy path: valid ESPN response returns list of NflGameResult."""
        from services.nfl_results import fetch_scoreboard, NflGameResult
        import requests

        payload = {
            "events": [
                {
                    "id": "401777001",
                    "status": {"type": {"name": "STATUS_FINAL"}},
                    "competitions": [
                        {
                            "competitors": [
                                {
                                    "homeAway": "home",
                                    "score": "28",
                                    "team": {"abbreviation": "KC"},
                                },
                                {
                                    "homeAway": "away",
                                    "score": "17",
                                    "team": {"abbreviation": "LV"},
                                },
                            ]
                        }
                    ],
                }
            ]
        }

        fake_session = type(
            "S",
            (),
            {
                "get": lambda self, url, params, timeout: self._resp,
                "_resp": self._make_response(payload),
            },
        )()

        results = fetch_scoreboard(2025, 1, session=fake_session)
        assert len(results) == 1
        assert results[0].home_abbreviation == "KC"
        assert results[0].status == "final"
        assert results[0].home_score == 28

    def test_fetch_scoreboard_raises_on_http_error(self):
        """ResultProviderError raised when ESPN API returns non-200."""
        from services.nfl_results import fetch_scoreboard, ResultProviderError

        class FailingSession:
            def get(self, url, params, timeout):
                class R:
                    def raise_for_status(self):
                        raise requests.HTTPError("503 Service Unavailable")

                    def json(self):
                        return {}

                return R()

        with pytest.raises(ResultProviderError):
            fetch_scoreboard(2025, 1, session=FailingSession())

    def test_fetch_scoreboard_raises_on_malformed_json(self):
        """ResultProviderError raised when ESPN API returns malformed JSON."""
        from services.nfl_results import fetch_scoreboard, ResultProviderError

        class BadJsonSession:
            def get(self, url, params, timeout):
                class R:
                    def raise_for_status(self):
                        pass

                    def json(self):
                        raise ValueError("bad json")

                return R()

        with pytest.raises(ResultProviderError):
            fetch_scoreboard(2025, 1, session=BadJsonSession())

    def test_fetch_scoreboard_returns_empty_list_for_no_games(self):
        """Empty events list returns an empty result list without error."""
        from services.nfl_results import fetch_scoreboard

        class EmptySession:
            def get(self, url, params, timeout):
                class R:
                    def raise_for_status(self):
                        pass

                    def json(self):
                        return {"events": []}

                return R()

        results = fetch_scoreboard(2025, 18, session=EmptySession())
        assert results == []

    def test_fetch_scoreboard_handles_week_18(self):
        """Week 18 (last regular season week) is handled identically to other weeks."""
        from services.nfl_results import fetch_scoreboard

        payload = {"events": []}

        class W18Session:
            def get(self, url, params, timeout):
                assert params["week"] == 18

                class R:
                    def raise_for_status(self):
                        pass

                    def json(self):
                        return payload

                return R()

        results = fetch_scoreboard(2025, 18, session=W18Session())
        assert results == []


# ---------------------------------------------------------------------------
# Tests for apply_final_results edge cases
# (rmp-backend-services-scoring-apply-final-results stub)
# ---------------------------------------------------------------------------


class TestApplyFinalResultsEdgeCases:
    """Additional edge-case tests for services.scoring.apply_final_results."""

    def test_apply_empty_results_returns_zero_summary(self, db_session):
        """Passing an empty list of results returns a ScoringSummary with all zeros."""
        from services.scoring import apply_final_results

        summary = apply_final_results(db_session, [])
        assert summary.final_games == 0
        assert summary.picks_changed == 0
        assert summary.entries_changed == 0

    def test_apply_non_final_games_are_skipped(self, db_session):
        """Non-final game results (scheduled, in_progress) are not scored."""
        from services.nfl_results import NflGameResult
        from services.scoring import apply_final_results

        scheduled_result = NflGameResult(
            game_id=99999,
            season=2026,
            week=1,
            status="scheduled",
            home_abbreviation="KC",
            away_abbreviation="LV",
            home_score=None,
            away_score=None,
        )

        summary = apply_final_results(db_session, [scheduled_result])
        assert summary.final_games == 0

    def test_apply_results_idempotent_second_call(self, db_session):
        """Calling apply_final_results twice with the same data does not double-update picks."""
        _seed_scoring(db_session)
        from services.scoring import apply_final_results

        result = _result()  # from module-level _result() helper
        summary1 = apply_final_results(db_session, [result])
        db_session.flush()
        summary2 = apply_final_results(db_session, [result])

        # Second call: game already final, scores unchanged — games_changed should be 0
        assert summary2.games_changed == 0


# ---------------------------------------------------------------------------
# Tests for result_updater.main edge cases
# (rmp-backend-result-updater-main stub)
# ---------------------------------------------------------------------------


def test_main_dry_run_does_not_persist_picks(db_session, monkeypatch):
    """main() with --dry-run rolls back DB changes so picks are not persisted."""
    _seed_scoring(db_session)
    monkeypatch.setattr(result_updater, "SessionLocal", lambda: db_session)
    monkeypatch.setattr(
        result_updater, "fetch_scoreboard", lambda season, week: [_result()]
    )

    exit_code = result_updater.main(
        ["--run-id", "dry-run-test", "--season", "2026", "--week", "1", "--dry-run"]
    )

    assert exit_code == 0
    record = db_session.get(models.UpdaterRun, "dry-run-test")
    assert record.status == "dry_run"


def test_main_requires_both_season_and_week_together(db_session, monkeypatch):
    """main() exits non-zero if --season is provided without --week."""
    monkeypatch.setattr(result_updater, "SessionLocal", lambda: db_session)

    with pytest.raises(SystemExit) as exc_info:
        result_updater.main(["--season", "2026"])

    assert exc_info.value.code != 0


def test_main_custom_run_id_is_persisted(db_session, monkeypatch):
    """main() uses the provided --run-id and persists a record under that ID."""
    _seed_scoring(db_session)
    monkeypatch.setattr(result_updater, "SessionLocal", lambda: db_session)
    monkeypatch.setattr(
        result_updater, "fetch_scoreboard", lambda season, week: [_result()]
    )

    exit_code = result_updater.main(
        ["--run-id", "custom-id-999", "--season", "2026", "--week", "1"]
    )

    assert exit_code == 0
    assert db_session.get(models.UpdaterRun, "custom-id-999") is not None
