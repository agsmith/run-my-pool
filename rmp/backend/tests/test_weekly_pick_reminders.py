from contextlib import contextmanager
from datetime import datetime, timedelta
import uuid

import models
import weekly_pick_reminders
from weekly_pick_reminders import deliver_due_weekly_pick_reminders

FRIDAY = datetime(2026, 9, 11, 19, 0)  # 3:00 PM Eastern


def _user(db, email, *, verified=True, active=True):
    user = models.User(
        id=str(uuid.uuid4()),
        email=email,
        hashed_password="unused",
        email_verified=verified,
        is_active=active,
        created_at=datetime(2026, 1, 1),
    )
    db.add(user)
    db.commit()
    return user


def _schedule(db):
    teams = [
        models.Team(id=98101, name="A", abbrv="AAA"),
        models.Team(id=98102, name="B", abbrv="BBB"),
        models.Team(id=98103, name="C", abbrv="CCC"),
        models.Team(id=98104, name="D", abbrv="DDD"),
    ]
    db.add_all(teams)
    db.add_all(
        [
            models.Schedule(
                game_id=9811,
                season=2026,
                week_num=1,
                home_team_id=98101,
                away_team_id=98102,
                start_time=datetime(2026, 9, 10, 20),
                status="final",
            ),
            models.Schedule(
                game_id=9812,
                season=2026,
                week_num=1,
                home_team_id=98103,
                away_team_id=98104,
                start_time=datetime(2026, 9, 13, 17),
                status="scheduled",
            ),
        ]
    )
    db.commit()


def _pool(db, owner, pool_id, pool_type="survivor", lock_time=None):
    pool = models.Pool(
        id=pool_id,
        name=f"Pool {pool_id}",
        owner_id=owner.id,
        pool_type=pool_type,
        survivor_objective="win",
        survivor_mulligans=0,
        lock_time=lock_time,
        created_at=datetime(2026, 1, 1),
    )
    db.add(pool)
    db.commit()
    return pool


def _entry(db, user, pool, name, *, alive=True):
    entry = models.Entry(
        id=str(uuid.uuid4()),
        user_id=user.id,
        pool_id=pool.id,
        name=name,
        alive=alive,
        created_at=datetime(2026, 2, 1),
    )
    db.add(entry)
    db.commit()
    return entry


def _pick(db, entry, week=1):
    db.add(
        models.Pick(
            id=str(uuid.uuid4()),
            entry_id=entry.id,
            week=week,
            team="CCC",
            team_id=98103,
            game_id=9812,
            locked=False,
            created_at=FRIDAY,
        )
    )
    db.commit()


def test_sends_one_consolidated_weekly_reminder_and_deduplicates(
    db_session, monkeypatch
):
    _schedule(db_session)
    owner = _user(db_session, "owner@example.com")
    member = _user(db_session, "member@example.com")
    survivor = _pool(db_session, owner, "survivor")
    pickem = _pool(db_session, owner, "pickem", "pickem")
    _entry(db_session, member, survivor, "One")
    _entry(db_session, member, survivor, "Two")
    _entry(db_session, member, pickem, "Three")
    calls = []
    monkeypatch.setattr(
        weekly_pick_reminders,
        "send_weekly_pick_reminder",
        lambda email, season, week, pools: calls.append((email, season, week, pools))
        or "ses-1",
    )

    assert deliver_due_weekly_pick_reminders(db_session, FRIDAY) == (1, 0)
    assert deliver_due_weekly_pick_reminders(db_session, FRIDAY) == (0, 0)
    assert calls[0][0:3] == ("member@example.com", 2026, 1)
    assert {item["id"]: item["missing_entries"] for item in calls[0][3]} == {
        "survivor": 2,
        "pickem": 1,
    }
    assert db_session.query(models.WeeklyPickReminderDelivery).one().status == "sent"
    assert (
        db_session.query(models.AuditLog)
        .filter_by(action="WEEKLY_PICK_REMINDER_SENT")
        .count()
        == 1
    )


def test_excludes_picked_eliminated_locked_and_ineligible_users(
    db_session, monkeypatch
):
    _schedule(db_session)
    owner = _user(db_session, "owner@example.com")
    member = _user(db_session, "member@example.com")
    locked_member = _user(db_session, "locked@example.com")
    unverified = _user(db_session, "unverified@example.com", verified=False)
    inactive = _user(db_session, "inactive@example.com", active=False)
    pool = _pool(db_session, owner, "pool-1")
    picked = _entry(db_session, member, pool, "Picked")
    _pick(db_session, picked)
    _entry(db_session, member, pool, "Eliminated", alive=False)
    locked = _entry(db_session, locked_member, pool, "Locked user")
    db_session.add(
        models.PoolUserLock(
            pool_id=pool.id,
            user_id=locked_member.id,
            locked_at=FRIDAY,
            reason="admin lock",
        )
    )
    _entry(db_session, unverified, pool, "Unverified")
    _entry(db_session, inactive, pool, "Inactive")
    db_session.commit()
    assert locked.id
    monkeypatch.setattr(
        weekly_pick_reminders,
        "send_weekly_pick_reminder",
        lambda *_: (_ for _ in ()).throw(AssertionError("ineligible recipient")),
    )

    assert deliver_due_weekly_pick_reminders(db_session, FRIDAY) == (0, 0)


def test_excludes_pool_after_its_weekly_deadline(db_session, monkeypatch):
    _schedule(db_session)
    owner = _user(db_session, "owner@example.com")
    member = _user(db_session, "member@example.com")
    pool = _pool(
        db_session, owner, "locked-pool", lock_time=FRIDAY - timedelta(minutes=1)
    )
    _entry(db_session, member, pool, "Missing")
    monkeypatch.setattr(
        weekly_pick_reminders,
        "send_weekly_pick_reminder",
        lambda *_: (_ for _ in ()).throw(AssertionError("locked pool")),
    )
    assert deliver_due_weekly_pick_reminders(db_session, FRIDAY) == (0, 0)


def test_only_runs_friday_during_active_regular_season(db_session, monkeypatch):
    _schedule(db_session)
    monkeypatch.setattr(
        weekly_pick_reminders,
        "send_weekly_pick_reminder",
        lambda *_: (_ for _ in ()).throw(AssertionError("wrong time")),
    )
    assert deliver_due_weekly_pick_reminders(
        db_session, FRIDAY - timedelta(days=1)
    ) == (0, 0)
    assert deliver_due_weekly_pick_reminders(db_session, datetime(2026, 9, 4, 19)) == (
        0,
        0,
    )


def test_friday_without_games_or_remaining_kickoffs_sends_nothing(
    db_session, monkeypatch
):
    monkeypatch.setattr(
        weekly_pick_reminders,
        "send_weekly_pick_reminder",
        lambda *_: (_ for _ in ()).throw(AssertionError("no eligible slate")),
    )
    assert deliver_due_weekly_pick_reminders(db_session, FRIDAY) == (0, 0)

    _schedule(db_session)
    owner = _user(db_session, "owner@example.com")
    member = _user(db_session, "member@example.com")
    pool = _pool(db_session, owner, "pool-1")
    _entry(db_session, member, pool, "Missing")
    assert deliver_due_weekly_pick_reminders(db_session, datetime(2026, 9, 18, 19)) == (
        0,
        0,
    )


def test_failed_delivery_retries_without_persisting_provider_details(
    db_session, monkeypatch
):
    _schedule(db_session)
    owner = _user(db_session, "owner@example.com")
    member = _user(db_session, "member@example.com")
    pool = _pool(db_session, owner, "pool-1")
    _entry(db_session, member, pool, "Missing")
    db_session.add(
        models.WeeklyPickReminderDelivery(
            id=str(uuid.uuid4()),
            user_id=member.id,
            season=2026,
            week_num=1,
            status="failed",
            attempted_at=FRIDAY - timedelta(hours=1),
            error="OldError",
        )
    )
    db_session.commit()
    monkeypatch.setattr(
        weekly_pick_reminders,
        "send_weekly_pick_reminder",
        lambda *_: (_ for _ in ()).throw(RuntimeError("sensitive SES response")),
    )
    assert deliver_due_weekly_pick_reminders(db_session, FRIDAY) == (0, 1)
    delivery = db_session.query(models.WeeklyPickReminderDelivery).one()
    assert delivery.error == "RuntimeError"
    monkeypatch.setattr(
        weekly_pick_reminders,
        "send_weekly_pick_reminder",
        lambda *_: "ses-retry",
    )
    assert deliver_due_weekly_pick_reminders(db_session, FRIDAY) == (1, 0)


def test_main_lock_and_failure_status(db_session, monkeypatch):
    @contextmanager
    def unavailable(*_):
        yield False

    monkeypatch.setattr(weekly_pick_reminders, "advisory_job_lock", unavailable)
    assert weekly_pick_reminders.main() == 0
    assert weekly_pick_reminders._utcnow().tzinfo is None

    @contextmanager
    def available(*_):
        yield True

    closed = []
    monkeypatch.setattr(weekly_pick_reminders, "advisory_job_lock", available)
    monkeypatch.setattr(weekly_pick_reminders, "SessionLocal", lambda: db_session)
    monkeypatch.setattr(
        weekly_pick_reminders,
        "deliver_due_weekly_pick_reminders",
        lambda _: (1, 1),
    )
    monkeypatch.setattr(db_session, "close", lambda: closed.append(True))
    assert weekly_pick_reminders.main() == 1
    assert closed == [True]
