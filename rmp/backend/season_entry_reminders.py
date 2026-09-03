"""Send entry reminders five days before the NFL regular season."""

import logging
import sys
import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_
from sqlalchemy.orm import Session

import models
from app_logging import log_event
from audit_utils import create_audit_log
from database import SessionLocal, engine
from email_service import send_season_entry_reminder
from season_join_reminders import EASTERN, upcoming_regular_season_start
from services.job_lock import advisory_job_lock

logger = logging.getLogger("runmypool.season_entry_reminders")
LOCK_NAME = "runmypool:season-entry-reminders"
REMINDER_LEAD_DAYS = 5
ENTRY_POOL_TYPES = ("survivor", "pickem")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _eligible_missing_entry_pools(
    db: Session,
) -> dict[str, tuple[models.User, list[dict]]]:
    """Group joined, entry-less pools by eligible verified user."""
    rows = (
        db.query(models.User, models.Pool)
        .join(models.PoolMember, models.PoolMember.user_id == models.User.id)
        .join(models.Pool, models.Pool.id == models.PoolMember.pool_id)
        .outerjoin(
            models.Entry,
            and_(
                models.Entry.user_id == models.User.id,
                models.Entry.pool_id == models.Pool.id,
            ),
        )
        .filter(
            models.User.email_verified.is_(True),
            models.User.is_active.is_(True),
            models.Pool.pool_type.in_(ENTRY_POOL_TYPES),
            models.Entry.id.is_(None),
        )
        .order_by(models.User.id.asc(), models.Pool.name.asc(), models.Pool.id.asc())
        .all()
    )
    grouped = defaultdict(list)
    users = {}
    for user, pool in rows:
        users[user.id] = user
        grouped[user.id].append({"id": pool.id, "name": pool.name})
    return {user_id: (users[user_id], pools) for user_id, pools in grouped.items()}


def deliver_due_season_entry_reminders(
    db: Session, now: datetime | None = None
) -> tuple[int, int]:
    """Return ``(sent, failed)`` for eligible members at the five-day mark."""
    current = now or _utcnow()
    season_info = upcoming_regular_season_start(db, current)
    if season_info is None:
        return 0, 0
    season, kickoff = season_info
    kickoff_date = kickoff.replace(tzinfo=timezone.utc).astimezone(EASTERN).date()
    current_date = current.replace(tzinfo=timezone.utc).astimezone(EASTERN).date()
    if current_date != kickoff_date - timedelta(days=REMINDER_LEAD_DAYS):
        return 0, 0

    sent = 0
    failed = 0
    for user, pools in _eligible_missing_entry_pools(db).values():
        delivery = (
            db.query(models.SeasonEntryReminderDelivery)
            .filter_by(user_id=user.id, season=season)
            .first()
        )
        if delivery is not None and delivery.status == "sent":
            continue
        if delivery is None:
            delivery = models.SeasonEntryReminderDelivery(
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
            message_id = send_season_entry_reminder(user.email, season, pools)
            delivery.status = "sent"
            delivery.message_id = message_id
            delivery.sent_at = current
            create_audit_log(
                db=db,
                action="SEASON_ENTRY_REMINDER_SENT",
                details=f"Sent {season} preseason entry reminder",
                entity_type="user",
                entity_id=user.id,
                additional_data={
                    "season": season,
                    "message_id": message_id,
                    "pool_ids": [pool["id"] for pool in pools],
                },
            )
            db.commit()
            sent += 1
        except Exception as exc:
            db.rollback()
            delivery = (
                db.query(models.SeasonEntryReminderDelivery)
                .filter_by(user_id=user.id, season=season)
                .first()
            )
            if delivery is not None:
                delivery.status = "failed"
                delivery.attempted_at = current
                delivery.error = type(exc).__name__[:255]
                db.commit()
            failed += 1
            logger.exception(
                "Failed to send season entry reminder for user %s", user.id
            )
    return sent, failed


def main() -> int:
    with advisory_job_lock(engine, LOCK_NAME) as acquired:
        if not acquired:
            log_event(logger, logging.INFO, "season_entry_reminder_job_already_running")
            return 0
        db = SessionLocal()
        try:
            sent, failed = deliver_due_season_entry_reminders(db)
            log_event(
                logger,
                logging.INFO if failed == 0 else logging.ERROR,
                "season_entry_reminder_job_completed",
                sent=sent,
                failed=failed,
            )
            return 1 if failed else 0
        finally:
            db.close()


if __name__ == "__main__":
    sys.exit(main())
