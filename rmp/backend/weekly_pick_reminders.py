"""Send Friday reminders for entries without a pick in the current NFL week."""

import logging
import sys
import uuid
from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy.orm import Session

import models
from app_logging import log_event
from audit_utils import create_audit_log
from database import SessionLocal, engine
from email_service import send_weekly_pick_reminder
from schedule import current_season_games, current_season_week, football_season
from season_join_reminders import EASTERN
from services.job_lock import advisory_job_lock
from weekly_locks import pool_week_lock_time

logger = logging.getLogger("runmypool.weekly_pick_reminders")
LOCK_NAME = "runmypool:weekly-pick-reminders"
ENTRY_POOL_TYPES = ("survivor", "pickem")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _missing_pick_groups(db: Session, week: int, now: datetime, games) -> dict:
    """Return eligible missing-pick counts grouped by user and pool."""
    pools = (
        db.query(models.Pool).filter(models.Pool.pool_type.in_(ENTRY_POOL_TYPES)).all()
    )
    grouped = defaultdict(list)
    users = {
        user.id: user
        for user in db.query(models.User)
        .filter(
            models.User.email_verified.is_(True),
            models.User.is_active.is_(True),
        )
        .all()
    }
    for pool in pools:
        deadline = pool_week_lock_time(pool, games)
        if deadline is not None and deadline <= now:
            continue
        if not any(game.start_time > now for game in games):
            continue
        locked_users = {
            row[0]
            for row in db.query(models.PoolUserLock.user_id).filter(
                models.PoolUserLock.pool_id == pool.id
            )
        }
        entries = db.query(models.Entry).filter(models.Entry.pool_id == pool.id).all()
        entry_ids = [entry.id for entry in entries]
        picked_entry_ids = (
            {
                row[0]
                for row in db.query(models.Pick.entry_id).filter(
                    models.Pick.entry_id.in_(entry_ids), models.Pick.week == week
                )
            }
            if entry_ids
            else set()
        )
        missing_by_user = defaultdict(int)
        for entry in entries:
            if entry.user_id in locked_users:
                continue
            if pool.pool_type == "survivor" and not entry.alive:
                continue
            if entry.id not in picked_entry_ids:
                missing_by_user[entry.user_id] += 1
        for user_id, count in missing_by_user.items():
            user = users.get(user_id)
            if user is None:
                continue
            grouped[user_id].append(
                {
                    "id": pool.id,
                    "name": pool.name,
                    "pool_type": pool.pool_type,
                    "missing_entries": count,
                }
            )
    return {user_id: (users[user_id], rows) for user_id, rows in grouped.items()}


def deliver_due_weekly_pick_reminders(
    db: Session, now: datetime | None = None
) -> tuple[int, int]:
    current = now or _utcnow()
    eastern_now = current.replace(tzinfo=timezone.utc).astimezone(EASTERN)
    if eastern_now.weekday() != 4:
        return 0, 0
    week = current_season_week(db, current)
    games = current_season_games(db, week)
    if not games:
        return 0, 0
    season = football_season(games[0].start_time)
    season_games = (
        db.query(models.Schedule.game_id)
        .filter(
            models.Schedule.season == season,
            models.Schedule.start_time <= current,
        )
        .first()
    )
    if season_games is None:
        return 0, 0

    sent = 0
    failed = 0
    for user, pools in _missing_pick_groups(db, week, current, games).values():
        delivery = (
            db.query(models.WeeklyPickReminderDelivery)
            .filter_by(user_id=user.id, season=season, week_num=week)
            .first()
        )
        if delivery is not None and delivery.status == "sent":
            continue
        if delivery is None:
            delivery = models.WeeklyPickReminderDelivery(
                id=str(uuid.uuid4()),
                user_id=user.id,
                season=season,
                week_num=week,
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
            message_id = send_weekly_pick_reminder(user.email, season, week, pools)
            delivery.status = "sent"
            delivery.message_id = message_id
            delivery.sent_at = current
            create_audit_log(
                db=db,
                action="WEEKLY_PICK_REMINDER_SENT",
                details=f"Sent {season} Week {week} missing-pick reminder",
                entity_type="user",
                entity_id=user.id,
                additional_data={
                    "season": season,
                    "week": week,
                    "message_id": message_id,
                    "pool_ids": [pool["id"] for pool in pools],
                },
            )
            db.commit()
            sent += 1
        except Exception as exc:
            db.rollback()
            delivery = (
                db.query(models.WeeklyPickReminderDelivery)
                .filter_by(user_id=user.id, season=season, week_num=week)
                .first()
            )
            if delivery is not None:
                delivery.status = "failed"
                delivery.attempted_at = current
                delivery.error = type(exc).__name__[:255]
                db.commit()
            failed += 1
            logger.exception("Failed to send weekly pick reminder for user %s", user.id)
    return sent, failed


def main() -> int:
    with advisory_job_lock(engine, LOCK_NAME) as acquired:
        if not acquired:
            log_event(logger, logging.INFO, "weekly_pick_reminder_job_already_running")
            return 0
        db = SessionLocal()
        try:
            sent, failed = deliver_due_weekly_pick_reminders(db)
            log_event(
                logger,
                logging.INFO if failed == 0 else logging.ERROR,
                "weekly_pick_reminder_job_completed",
                sent=sent,
                failed=failed,
            )
            return 1 if failed else 0
        finally:
            db.close()


if __name__ == "__main__":
    sys.exit(main())
