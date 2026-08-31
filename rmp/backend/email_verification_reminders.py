"""Send one automatic verification reminder after an account is 24 hours old."""

import logging
import sys
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

import models
from app_logging import log_event
from audit_utils import create_audit_log
from auth import _create_email_verification_token
from database import SessionLocal, engine
from email_service import send_email_verification_reminder
from services.job_lock import advisory_job_lock


logger = logging.getLogger("runmypool.email_verification_reminders")
LOCK_NAME = "runmypool:email-verification-reminders"
REMINDER_AGE = timedelta(hours=24)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def deliver_due_verification_reminders(
    db: Session, now: datetime | None = None
) -> tuple[int, int]:
    """Return ``(sent, failed)`` for reminders due at ``now``.

    A user is eligible only when the original verification token is the sole
    token in their history and has expired. Creating the reminder token makes
    the history count two, which permanently prevents duplicate automatic
    reminders while still allowing an administrator to resend manually.
    """
    current = now or _utcnow()
    cutoff = current - REMINDER_AGE
    candidates = (
        db.query(models.User)
        .filter(
            models.User.email_verified.is_(False),
            models.User.is_active.is_(True),
            models.User.created_at <= cutoff,
        )
        .order_by(models.User.created_at.asc())
        .all()
    )
    sent = 0
    failed = 0

    for candidate in candidates:
        user = (
            db.query(models.User)
            .filter(models.User.id == candidate.id)
            .with_for_update()
            .first()
        )
        if (
            user is None
            or user.email_verified
            or not user.is_active
            or user.created_at is None
            or user.created_at > cutoff
        ):
            continue

        tokens = (
            db.query(models.EmailVerificationToken)
            .filter(models.EmailVerificationToken.user_id == user.id)
            .order_by(models.EmailVerificationToken.created_at.desc())
            .all()
        )
        if len(tokens) != 1:
            continue
        original = tokens[0]
        if original.used_at is not None or original.expires_at > current:
            continue

        raw_token, token_digest, _ = _create_email_verification_token(db, user)
        try:
            message_id = send_email_verification_reminder(user.email, raw_token)
            create_audit_log(
                db=db,
                action="EMAIL_VERIFICATION_REMINDER_SENT",
                details=f"Sent automatic email verification reminder to {user.email}",
                entity_type="user",
                entity_id=user.id,
                additional_data={"message_id": message_id},
            )
            sent += 1
        except Exception:
            db.rollback()
            db.query(models.EmailVerificationToken).filter(
                models.EmailVerificationToken.token_digest == token_digest
            ).delete(synchronize_session=False)
            db.commit()
            failed += 1
            logger.exception(
                "Failed to send email verification reminder for user %s", user.id
            )

    return sent, failed


def main() -> int:
    with advisory_job_lock(engine, LOCK_NAME) as acquired:
        if not acquired:
            log_event(logger, logging.INFO, "verification_reminder_job_already_running")
            return 0
        db = SessionLocal()
        try:
            sent, failed = deliver_due_verification_reminders(db)
            log_event(
                logger,
                logging.INFO if failed == 0 else logging.ERROR,
                "verification_reminder_job_completed",
                sent=sent,
                failed=failed,
            )
            return 1 if failed else 0
        finally:
            db.close()


if __name__ == "__main__":
    sys.exit(main())
