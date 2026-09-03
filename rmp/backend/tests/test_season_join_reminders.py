from datetime import datetime, timedelta
from contextlib import contextmanager
import uuid

import models
import season_join_reminders
from season_join_reminders import (
    deliver_due_season_join_reminders,
    upcoming_regular_season_start,
)


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


def _schedule(db, kickoff=datetime(2026, 9, 10, 20, 0), *, week=1, game_id=9001):
    home = models.Team(id=game_id * 10, name="Home", abbrv=f"H{game_id}")
    away = models.Team(id=game_id * 10 + 1, name="Away", abbrv=f"A{game_id}")
    db.add_all([home, away])
    db.add(
        models.Schedule(
            game_id=game_id,
            season=2026,
            week_num=week,
            home_team_id=home.id,
            away_team_id=away.id,
            start_time=kickoff,
            status="scheduled",
        )
    )
    db.commit()


def _pool(db, owner, pool_id):
    pool = models.Pool(
        id=pool_id,
        name=f"Pool {pool_id}",
        owner_id=owner.id,
        pool_type="survivor",
        survivor_objective="win",
        survivor_mulligans=0,
        created_at=datetime(2026, 1, 1),
    )
    db.add(pool)
    db.commit()
    return pool


def test_sends_exactly_once_six_days_before_week_one(db_session, monkeypatch):
    _schedule(db_session)
    eligible = _user(db_session, "eligible@example.com")
    sent = []
    monkeypatch.setattr(
        season_join_reminders,
        "send_season_join_reminder",
        lambda recipient, season: sent.append((recipient, season)) or "ses-1",
    )
    now = datetime(2026, 9, 4, 14, 0)

    assert deliver_due_season_join_reminders(db_session, now) == (1, 0)
    assert deliver_due_season_join_reminders(db_session, now) == (0, 0)
    assert sent == [("eligible@example.com", 2026)]
    delivery = db_session.query(models.SeasonJoinReminderDelivery).one()
    assert delivery.user_id == eligible.id
    assert delivery.status == "sent"
    assert delivery.message_id == "ses-1"
    assert (
        db_session.query(models.AuditLog)
        .filter_by(action="SEASON_JOIN_REMINDER_SENT")
        .count()
        == 1
    )


def test_skips_unverified_inactive_members_owners_and_admins(db_session, monkeypatch):
    _schedule(db_session)
    unverified = _user(db_session, "unverified@example.com", verified=False)
    inactive = _user(db_session, "inactive@example.com", active=False)
    member = _user(db_session, "member@example.com")
    owner = _user(db_session, "owner@example.com")
    admin = _user(db_session, "admin@example.com")
    member_pool = _pool(db_session, owner, "member-pool")
    admin_pool = _pool(
        db_session, _user(db_session, "owner2@example.com"), "admin-pool"
    )
    db_session.add(
        models.PoolMember(
            pool_id=member_pool.id, user_id=member.id, joined_at=datetime(2026, 1, 2)
        )
    )
    db_session.add(models.PoolAdmin(pool_id=admin_pool.id, user_id=admin.id))
    db_session.commit()
    monkeypatch.setattr(
        season_join_reminders,
        "send_season_join_reminder",
        lambda *_: (_ for _ in ()).throw(AssertionError("ineligible recipient")),
    )

    assert deliver_due_season_join_reminders(
        db_session, datetime(2026, 9, 4, 14, 0)
    ) == (0, 0)
    assert {unverified.email, inactive.email, member.email, owner.email, admin.email}


def test_uses_regular_season_schedule_and_only_runs_on_target_date(
    db_session, monkeypatch
):
    _schedule(db_session, datetime(2026, 8, 13, 20, 0), game_id=8001)
    _schedule(db_session, datetime(2026, 9, 10, 20, 0), game_id=9002)
    _user(db_session, "waiting@example.com")
    monkeypatch.setattr(
        season_join_reminders,
        "send_season_join_reminder",
        lambda *_: (_ for _ in ()).throw(AssertionError("wrong day")),
    )

    assert upcoming_regular_season_start(db_session, datetime(2026, 8, 1)) == (
        2026,
        datetime(2026, 9, 10, 20, 0),
    )
    assert deliver_due_season_join_reminders(
        db_session, datetime(2026, 9, 3, 14, 0)
    ) == (0, 0)
    assert deliver_due_season_join_reminders(
        db_session, datetime(2026, 9, 5, 14, 0)
    ) == (0, 0)


def test_failed_send_is_retried_without_exposing_error_details(db_session, monkeypatch):
    _schedule(db_session)
    _user(db_session, "retry@example.com")
    now = datetime(2026, 9, 4, 14, 0)
    monkeypatch.setattr(
        season_join_reminders,
        "send_season_join_reminder",
        lambda *_: (_ for _ in ()).throw(RuntimeError("secret provider response")),
    )

    assert deliver_due_season_join_reminders(db_session, now) == (0, 1)
    # A failed pre-send transaction does not create a sent marker, allowing the
    # Step Functions retry to attempt this recipient again.
    monkeypatch.setattr(
        season_join_reminders,
        "send_season_join_reminder",
        lambda *_: "ses-retry",
    )
    assert deliver_due_season_join_reminders(
        db_session, now + timedelta(minutes=1)
    ) == (1, 0)
    delivery = db_session.query(models.SeasonJoinReminderDelivery).one()
    assert delivery.status == "sent"
    assert delivery.error is None


def test_failed_existing_delivery_records_only_exception_type(db_session, monkeypatch):
    _schedule(db_session)
    user = _user(db_session, "failed-again@example.com")
    now = datetime(2026, 9, 4, 14, 0)
    db_session.add(
        models.SeasonJoinReminderDelivery(
            id=str(uuid.uuid4()),
            user_id=user.id,
            season=2026,
            status="failed",
            attempted_at=now - timedelta(hours=1),
            error="PreviousError",
        )
    )
    db_session.commit()
    monkeypatch.setattr(
        season_join_reminders,
        "send_season_join_reminder",
        lambda *_: (_ for _ in ()).throw(RuntimeError("sensitive provider detail")),
    )

    assert deliver_due_season_join_reminders(db_session, now) == (0, 1)
    delivery = db_session.query(models.SeasonJoinReminderDelivery).one()
    assert delivery.status == "failed"
    assert delivery.error == "RuntimeError"
    assert "sensitive" not in delivery.error


def test_no_schedule_means_no_delivery(db_session, monkeypatch):
    _user(db_session, "waiting@example.com")
    monkeypatch.setattr(
        season_join_reminders,
        "send_season_join_reminder",
        lambda *_: (_ for _ in ()).throw(AssertionError("no schedule")),
    )
    assert deliver_due_season_join_reminders(
        db_session, datetime(2026, 9, 4, 14, 0)
    ) == (0, 0)


def test_main_skips_concurrent_run(monkeypatch):
    @contextmanager
    def unavailable_lock(*_):
        yield False

    monkeypatch.setattr(season_join_reminders, "advisory_job_lock", unavailable_lock)
    assert season_join_reminders.main() == 0


def test_main_returns_failure_status_and_closes_session(db_session, monkeypatch):
    @contextmanager
    def available_lock(*_):
        yield True

    closed = []
    monkeypatch.setattr(season_join_reminders, "advisory_job_lock", available_lock)
    monkeypatch.setattr(season_join_reminders, "SessionLocal", lambda: db_session)
    monkeypatch.setattr(
        season_join_reminders,
        "deliver_due_season_join_reminders",
        lambda _: (2, 1),
    )
    monkeypatch.setattr(db_session, "close", lambda: closed.append(True))

    assert season_join_reminders.main() == 1
    assert closed == [True]
