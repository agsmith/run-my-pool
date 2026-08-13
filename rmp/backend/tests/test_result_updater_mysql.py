"""MySQL-only integration gates for updater locking and transaction behavior."""

import os
import threading
from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import models
from services.job_lock import advisory_job_lock
from services.nfl_results import NflGameResult
from services.scoring import ScoringDiscrepancy, apply_final_results

MYSQL_URL = os.getenv("MYSQL_INTEGRATION_URL")
pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def mysql_engine():
    if not MYSQL_URL:
        pytest.skip("MYSQL_INTEGRATION_URL is required for MySQL integration tests")
    engine = create_engine(
        MYSQL_URL,
        pool_pre_ping=True,
        pool_size=2,
        max_overflow=0,
    )
    models.Base.metadata.drop_all(engine)
    models.Base.metadata.create_all(engine)
    try:
        yield engine
    finally:
        models.Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture
def mysql_session(mysql_engine):
    models.Base.metadata.drop_all(mysql_engine)
    models.Base.metadata.create_all(mysql_engine)
    session = sessionmaker(bind=mysql_engine, expire_on_commit=False)()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def _seed_game(db):
    home = models.Team(id=101, name="Buffalo Bills", abbrv="BUF")
    away = models.Team(id=102, name="Miami Dolphins", abbrv="MIA")
    user = models.User(
        id="mysql-user", email="mysql@example.com", hashed_password="unused"
    )
    pool = models.Pool(
        id="mysql-pool",
        name="MySQL Survivor",
        owner_id=user.id,
        pool_type="survivor",
    )
    entry = models.Entry(
        id="mysql-entry",
        user_id=user.id,
        pool_id=pool.id,
        name="Entry",
        alive=True,
    )
    game = models.Schedule(
        game_id=401999001,
        season=2026,
        week_num=1,
        home_team_id=home.id,
        away_team_id=away.id,
        start_time=datetime(2026, 9, 13, 17),
    )
    pick = models.Pick(
        id="mysql-pick",
        entry_id=entry.id,
        week=1,
        team="MIA",
        team_id=away.id,
    )
    db.add_all([home, away, user, pool, entry, game, pick])
    db.commit()
    return game, entry, pick


def _home_win():
    return NflGameResult(
        game_id=401999001,
        season=2026,
        week=1,
        status="final",
        home_abbreviation="BUF",
        away_abbreviation="MIA",
        home_score=27,
        away_score=20,
    )


def test_mysql_named_lock_allows_exactly_one_runner(mysql_engine):
    first_has_lock = threading.Event()
    release_first = threading.Event()
    outcomes = []

    def first_runner():
        with advisory_job_lock(mysql_engine, "runmypool:test-lock") as acquired:
            outcomes.append(("first", acquired))
            first_has_lock.set()
            release_first.wait(timeout=5)

    thread = threading.Thread(target=first_runner)
    thread.start()
    assert first_has_lock.wait(timeout=5)
    with advisory_job_lock(mysql_engine, "runmypool:test-lock") as acquired:
        outcomes.append(("second", acquired))
    release_first.set()
    thread.join(timeout=5)

    assert outcomes == [("first", True), ("second", False)]


def test_mysql_scoring_commit_and_idempotent_rerun(mysql_session):
    game, entry, pick = _seed_game(mysql_session)

    first = apply_final_results(mysql_session, [_home_win()])
    mysql_session.commit()
    second = apply_final_results(mysql_session, [_home_win()])
    mysql_session.commit()

    assert first.games_changed == 1
    assert first.picks_changed == 1
    assert first.entries_changed == 1
    assert second.games_changed == 0
    assert second.picks_changed == 0
    assert second.entries_changed == 0
    assert game.winning_team_id == 101
    assert pick.result == "loss"
    assert entry.alive is False


def test_mysql_discrepancy_rolls_back_entire_transaction(mysql_session):
    game, entry, pick = _seed_game(mysql_session)
    invalid = NflGameResult(
        game_id=401999001,
        season=2025,
        week=1,
        status="final",
        home_abbreviation="BUF",
        away_abbreviation="MIA",
        home_score=27,
        away_score=20,
    )

    with pytest.raises(ScoringDiscrepancy):
        apply_final_results(mysql_session, [invalid])
    mysql_session.rollback()
    mysql_session.refresh(game)
    mysql_session.refresh(entry)
    mysql_session.refresh(pick)

    assert game.status == "scheduled"
    assert game.winning_team_id is None
    assert pick.result is None
    assert entry.alive is True
