"""Send a one-time join reminder six days before the NFL regular season."""

import logging
import sys
import uuid
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

import models
from app_logging import log_event
from audit_utils import create_audit_log
from database import SessionLocal, engine
from email_service import send_season_join_reminder
from schedule import football_season
from services.job_lock import advisory_job_lock

logger = logging.getLogger("runmypool.season_join_reminders")
LOCK_NAME = "runmypool:season-join-reminders"
EASTERN = ZoneInfo("America/New_York")
REMINDER_LEAD_DAYS = 6


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def upcoming_regular_season_start(
    db: Session, now: datetime
) -> tuple[int, datetime] | None:
    """Return the next regular-season Week 1 kickoff from the stored schedule."""
    games = (
        db.query(models.Schedule)
        .filter(models.Schedule.week_num == 1, models.Schedule.start_time >= now)
        .order_by(models.Schedule.start_time.asc())
        .all()
    )
    for game in games:
        # NFL preseason also numbers its opening slate Week 1. Regular-season
        # Week 1 begins in September; excluding earlier rows prevents mistimed mail.
        if game.start_time.month >= 9:
            return football_season(game.start_time), game.start_time
    return None


def deliver_due_season_join_reminders(
    db: Session, now: datetime | None = None
) -> tuple[int, int]:
    """Return ``(sent, failed)`` for eligible accounts at the six-day mark."""
    current = now or _utcnow()
    season_info = upcoming_regular_season_start(db, current)
    if season_info is None:
        return 0, 0
    season, kickoff = season_info
    kickoff_date = kickoff.replace(tzinfo=timezone.utc).astimezone(EASTERN).date()
    current_date = current.replace(tzinfo=timezone.utc).astimezone(EASTERN).date()
    if current_date != kickoff_date - timedelta(days=REMINDER_LEAD_DAYS):
        return 0, 0

    has_membership = (
        db.query(models.PoolMember)
        .filter(models.PoolMember.user_id == models.User.id)
        .exists()
    )
    owns_pool = (
        db.query(models.Pool).filter(models.Pool.owner_id == models.User.id).exists()
    )
    administers_pool = (
        db.query(models.PoolAdmin)
        .filter(models.PoolAdmin.user_id == models.User.id)
        .exists()
    )
    candidates = (
        db.query(models.User)
        .filter(
            models.User.email_verified.is_(True),
            models.User.is_active.is_(True),
            ~has_membership,
            ~owns_pool,
            ~administers_pool,
        )
        .order_by(models.User.created_at.asc(), models.User.id.asc())
        .all()
    )
    sent = 0
    failed = 0

    for user in candidates:
        delivery = (
            db.query(models.SeasonJoinReminderDelivery)
            .filter_by(user_id=user.id, season=season)
            .first()
        )
        if delivery is not None and delivery.status == "sent":
            continue
        if delivery is None:
            delivery = models.SeasonJoinReminderDelivery(
                id=str(uuid.uuid4()),
                user_id=user.id,
                season=season,
                status="pending",
                attempted_at=current,
            )
            db.add(delivery)
        else:
            delivery.status = "pending"
            delivery.attempted_at = current
            delivery.error = None
        db.flush()

        try:
            message_id = send_season_join_reminder(user.email, season)
            delivery.status = "sent"
            delivery.message_id = message_id
            delivery.sent_at = current
            create_audit_log(
                db=db,
                action="SEASON_JOIN_REMINDER_SENT",
                details=f"Sent {season} preseason pool join reminder",
                entity_type="user",
                entity_id=user.id,
                additional_data={"season": season, "message_id": message_id},
            )
            db.commit()
            sent += 1
        except Exception as exc:
            db.rollback()
            delivery = (
                db.query(models.SeasonJoinReminderDelivery)
                .filter_by(user_id=user.id, season=season)
                .first()
            )
            if delivery is not None:
                delivery.status = "failed"
                delivery.attempted_at = current
                delivery.error = type(exc).__name__[:255]
                db.commit()
            failed += 1
            logger.exception("Failed to send season join reminder for user %s", user.id)

    return sent, failed


def main() -> int:
    with advisory_job_lock(engine, LOCK_NAME) as acquired:
        if not acquired:
            log_event(logger, logging.INFO, "season_join_reminder_job_already_running")
            return 0
        db = SessionLocal()
        try:
            sent, failed = deliver_due_season_join_reminders(db)
            log_event(
                logger,
                logging.INFO if failed == 0 else logging.ERROR,
                "season_join_reminder_job_completed",
                sent=sent,
                failed=failed,
            )
            return 1 if failed else 0
        finally:
            db.close()


if __name__ == "__main__":
    sys.exit(main())
