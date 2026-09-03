from contextlib import contextmanager
from datetime import datetime, timedelta
import uuid

import models
import season_entry_reminders
from season_entry_reminders import deliver_due_season_entry_reminders


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
    home = models.Team(id=97010, name="Home", abbrv="H97")
    away = models.Team(id=97011, name="Away", abbrv="A97")
    db.add_all([home, away])
    db.add(
        models.Schedule(
            game_id=9701,
            season=2026,
            week_num=1,
            home_team_id=home.id,
            away_team_id=away.id,
            start_time=datetime(2026, 9, 10, 20, 0),
            status="scheduled",
        )
    )
    db.commit()


def _pool(db, owner, pool_id, *, pool_type="survivor"):
    pool = models.Pool(
        id=pool_id,
        name=f"Pool {pool_id}",
        owner_id=owner.id,
        pool_type=pool_type,
        survivor_objective="win",
        survivor_mulligans=0,
        created_at=datetime(2026, 1, 1),
    )
    db.add(pool)
    db.commit()
    return pool


def _join(db, user, pool):
    db.add(
        models.PoolMember(
            pool_id=pool.id, user_id=user.id, joined_at=datetime(2026, 2, 1)
        )
    )
    db.commit()


def _entry(db, user, pool, name="Entry"):
    db.add(
        models.Entry(
            id=str(uuid.uuid4()),
            user_id=user.id,
            pool_id=pool.id,
            name=name,
            alive=True,
            created_at=datetime(2026, 2, 2),
        )
    )
    db.commit()


def test_consolidates_missing_entry_pools_and_sends_exactly_once(
    db_session, monkeypatch
):
    _schedule(db_session)
    owner = _user(db_session, "owner@example.com")
    member = _user(db_session, "member@example.com")
    survivor = _pool(db_session, owner, "survivor-pool")
    pickem = _pool(db_session, owner, "pickem-pool", pool_type="pickem")
    _join(db_session, member, survivor)
    _join(db_session, member, pickem)
    calls = []
    monkeypatch.setattr(
        season_entry_reminders,
        "send_season_entry_reminder",
        lambda recipient, season, pools: calls.append((recipient, season, pools))
        or "ses-entry-1",
    )
    now = datetime(2026, 9, 5, 14, 0)

    assert deliver_due_season_entry_reminders(db_session, now) == (1, 0)
    assert deliver_due_season_entry_reminders(db_session, now) == (0, 0)
    assert calls[0][0:2] == ("member@example.com", 2026)
    assert {pool["id"] for pool in calls[0][2]} == {"survivor-pool", "pickem-pool"}
    delivery = db_session.query(models.SeasonEntryReminderDelivery).one()
    assert delivery.status == "sent"
    assert delivery.message_id == "ses-entry-1"
    assert (
        db_session.query(models.AuditLog)
        .filter_by(action="SEASON_ENTRY_REMINDER_SENT")
        .count()
        == 1
    )


def test_only_lists_joined_pools_where_that_user_has_no_entry(db_session, monkeypatch):
    _schedule(db_session)
    owner = _user(db_session, "owner@example.com")
    member = _user(db_session, "member@example.com")
    other = _user(db_session, "other@example.com")
    complete = _pool(db_session, owner, "complete-pool")
    missing = _pool(db_session, owner, "missing-pool")
    for pool in (complete, missing):
        _join(db_session, member, pool)
    _join(db_session, other, missing)
    _entry(db_session, member, complete)
    _entry(db_session, other, missing, "Someone else's entry")
    calls = []
    monkeypatch.setattr(
        season_entry_reminders,
        "send_season_entry_reminder",
        lambda recipient, season, pools: calls.append((recipient, pools)) or "ses-1",
    )

    assert deliver_due_season_entry_reminders(
        db_session, datetime(2026, 9, 5, 14, 0)
    ) == (1, 0)
    assert calls == [
        ("member@example.com", [{"id": "missing-pool", "name": "Pool missing-pool"}])
    ]


def test_skips_unverified_inactive_and_squares_members(db_session, monkeypatch):
    _schedule(db_session)
    owner = _user(db_session, "owner@example.com")
    unverified = _user(db_session, "unverified@example.com", verified=False)
    inactive = _user(db_session, "inactive@example.com", active=False)
    squares_member = _user(db_session, "squares@example.com")
    survivor = _pool(db_session, owner, "survivor-pool")
    squares = _pool(db_session, owner, "squares-pool", pool_type="squares")
    _join(db_session, unverified, survivor)
    _join(db_session, inactive, survivor)
    _join(db_session, squares_member, squares)
    monkeypatch.setattr(
        season_entry_reminders,
        "send_season_entry_reminder",
        lambda *_: (_ for _ in ()).throw(AssertionError("ineligible recipient")),
    )

    assert deliver_due_season_entry_reminders(
        db_session, datetime(2026, 9, 5, 14, 0)
    ) == (0, 0)


def test_only_runs_five_days_before_kickoff(db_session, monkeypatch):
    _schedule(db_session)
    owner = _user(db_session, "owner@example.com")
    member = _user(db_session, "member@example.com")
    pool = _pool(db_session, owner, "pool-1")
    _join(db_session, member, pool)
    monkeypatch.setattr(
        season_entry_reminders,
        "send_season_entry_reminder",
        lambda *_: (_ for _ in ()).throw(AssertionError("wrong day")),
    )

    assert deliver_due_season_entry_reminders(
        db_session, datetime(2026, 9, 4, 14, 0)
    ) == (0, 0)
    assert deliver_due_season_entry_reminders(
        db_session, datetime(2026, 9, 6, 14, 0)
    ) == (0, 0)


def test_failed_delivery_can_retry_and_error_text_is_not_persisted(
    db_session, monkeypatch
):
    _schedule(db_session)
    owner = _user(db_session, "owner@example.com")
    member = _user(db_session, "retry@example.com")
    pool = _pool(db_session, owner, "pool-1")
    _join(db_session, member, pool)
    now = datetime(2026, 9, 5, 14, 0)
    db_session.add(
        models.SeasonEntryReminderDelivery(
            id=str(uuid.uuid4()),
            user_id=member.id,
            season=2026,
            status="failed",
            attempted_at=now - timedelta(hours=1),
            error="PreviousError",
        )
    )
    db_session.commit()
    monkeypatch.setattr(
        season_entry_reminders,
        "send_season_entry_reminder",
        lambda *_: (_ for _ in ()).throw(RuntimeError("sensitive SES response")),
    )

    assert deliver_due_season_entry_reminders(db_session, now) == (0, 1)
    delivery = db_session.query(models.SeasonEntryReminderDelivery).one()
    assert delivery.status == "failed"
    assert delivery.error == "RuntimeError"
    monkeypatch.setattr(
        season_entry_reminders,
        "send_season_entry_reminder",
        lambda *_: "ses-retry",
    )
    assert deliver_due_season_entry_reminders(db_session, now) == (1, 0)
    assert db_session.query(models.SeasonEntryReminderDelivery).one().status == "sent"


def test_no_upcoming_schedule_means_no_delivery(db_session, monkeypatch):
    monkeypatch.setattr(
        season_entry_reminders,
        "send_season_entry_reminder",
        lambda *_: (_ for _ in ()).throw(AssertionError("no schedule")),
    )
    assert deliver_due_season_entry_reminders(
        db_session, datetime(2026, 9, 5, 14, 0)
    ) == (0, 0)


def test_main_lock_and_failure_status(db_session, monkeypatch):
    @contextmanager
    def unavailable(*_):
        yield False

    monkeypatch.setattr(season_entry_reminders, "advisory_job_lock", unavailable)
    assert season_entry_reminders.main() == 0

    @contextmanager
    def available(*_):
        yield True

    closed = []
    monkeypatch.setattr(season_entry_reminders, "advisory_job_lock", available)
    monkeypatch.setattr(season_entry_reminders, "SessionLocal", lambda: db_session)
    monkeypatch.setattr(
        season_entry_reminders,
        "deliver_due_season_entry_reminders",
        lambda _: (1, 1),
    )
    monkeypatch.setattr(db_session, "close", lambda: closed.append(True))
    assert season_entry_reminders.main() == 1
    assert closed == [True]
