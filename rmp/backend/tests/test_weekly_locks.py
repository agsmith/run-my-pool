from datetime import datetime, time, timedelta

import models
import weekly_locks


def test_due_recurring_pool_is_processed(db_session, monkeypatch):
    owner = models.User(
        id="weekly-worker-owner",
        email="weekly.worker@example.com",
        hashed_password="unused",
        is_active=True,
    )
    pool = models.Pool(
        id="weekly-worker-pool",
        name="Weekly Worker Pool",
        owner_id=owner.id,
        lock_day_of_week=6,
        lock_time_of_day=time(13, 0),
        lock_timezone="America/New_York",
    )
    entry = models.Entry(
        id="weekly-worker-entry",
        pool_id=pool.id,
        user_id=owner.id,
        name="Entry 1",
        alive=True,
    )
    db_session.add_all([owner, pool, entry])
    db_session.commit()

    called = []
    now = datetime.utcnow()
    monkeypatch.setattr(weekly_locks, "current_season_week", lambda db, current: 4)
    monkeypatch.setattr(weekly_locks, "current_season_games", lambda db, week: [object()])
    monkeypatch.setattr(weekly_locks, "pool_week_lock_time", lambda candidate, games: now - timedelta(minutes=1))
    monkeypatch.setattr(
        weekly_locks,
        "lock_pool_week",
        lambda db, candidate, week, actor_id, current, **kwargs: called.append(
            (candidate.id, week, actor_id, kwargs["log_skipped_defaults"])
        ),
    )

    assert weekly_locks.process_due_weekly_locks(db_session, now) == 1
    assert called == [(pool.id, 4, owner.id, False)]
