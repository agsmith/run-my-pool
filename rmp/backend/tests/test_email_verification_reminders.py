from datetime import datetime, timedelta, timezone
import uuid

import models
from email_verification_reminders import deliver_due_verification_reminders


def _unverified_user(db, email, created_at):
    user = models.User(
        id=str(uuid.uuid4()),
        email=email,
        hashed_password="unused",
        email_verified=False,
        is_active=True,
        created_at=created_at,
    )
    db.add(user)
    db.commit()
    return user


def _token(db, user, created_at, expires_at):
    token = models.EmailVerificationToken(
        token_digest=str(uuid.uuid4()),
        user_id=user.id,
        created_at=created_at,
        expires_at=expires_at,
    )
    db.add(token)
    db.commit()
    return token


def test_sends_one_reminder_and_does_not_repeat(db_session, monkeypatch):
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    user = _unverified_user(
        db_session, "reminder@example.com", now - timedelta(hours=25)
    )
    _token(
        db_session,
        user,
        now - timedelta(hours=25),
        now - timedelta(hours=1),
    )
    sent_to = []
    monkeypatch.setattr(
        "email_verification_reminders.send_email_verification_reminder",
        lambda recipient, token: sent_to.append((recipient, token)) or "message-1",
    )

    assert deliver_due_verification_reminders(db_session, now) == (1, 0)
    assert deliver_due_verification_reminders(db_session, now + timedelta(hours=1)) == (0, 0)
    assert sent_to[0][0] == "reminder@example.com"
    assert db_session.query(models.EmailVerificationToken).filter_by(
        user_id=user.id
    ).count() == 2
    assert db_session.query(models.AuditLog).filter_by(
        action="EMAIL_VERIFICATION_REMINDER_SENT"
    ).count() == 1


def test_skips_accounts_that_are_not_due(db_session, monkeypatch):
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    young = _unverified_user(db_session, "young@example.com", now - timedelta(hours=23))
    _token(db_session, young, now - timedelta(hours=23), now + timedelta(hours=1))
    old_with_valid_link = _unverified_user(
        db_session, "valid@example.com", now - timedelta(hours=30)
    )
    _token(db_session, old_with_valid_link, now - timedelta(hours=1), now + timedelta(hours=23))
    monkeypatch.setattr(
        "email_verification_reminders.send_email_verification_reminder",
        lambda *_: (_ for _ in ()).throw(AssertionError("must not send")),
    )

    assert deliver_due_verification_reminders(db_session, now) == (0, 0)


def test_failed_delivery_removes_new_token_so_job_can_retry(db_session, monkeypatch):
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    user = _unverified_user(db_session, "retry@example.com", now - timedelta(hours=25))
    _token(db_session, user, now - timedelta(hours=25), now - timedelta(hours=1))
    monkeypatch.setattr(
        "email_verification_reminders.send_email_verification_reminder",
        lambda *_: (_ for _ in ()).throw(RuntimeError("SES unavailable")),
    )

    assert deliver_due_verification_reminders(db_session, now) == (0, 1)
    assert db_session.query(models.EmailVerificationToken).filter_by(
        user_id=user.id
    ).count() == 1
