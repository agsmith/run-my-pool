"""Owner-facing pool health reports and weekly delivery job."""

import logging
import sys
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

import deps
import models
import schemas
from app_logging import log_event
from audit_utils import create_audit_log
from database import SessionLocal, engine
from email_service import send_pool_owner_report
from schedule import current_season_week
from services.job_lock import advisory_job_lock


router = APIRouter(prefix="/pools", tags=["pool reports"])
logger = logging.getLogger("runmypool.pool_reports")
LOCK_NAME = "runmypool:owner-pool-reports"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _require_owner(db: Session, pool_id: str, user: models.User) -> models.Pool:
    pool = db.get(models.Pool, pool_id)
    if pool is None:
        raise HTTPException(status_code=404, detail="Pool not found")
    if pool.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Only the pool owner can manage pool reports")
    return pool


def build_owner_report(db: Session, pool: models.Pool) -> dict:
    entries = db.query(models.Entry).filter(models.Entry.pool_id == pool.id).all()
    entry_ids = [entry.id for entry in entries]
    participant_ids = {pool.owner_id} if pool.owner_id else set()
    participant_ids.update(member.user_id for member in pool.members)
    participant_ids.update(entry.user_id for entry in entries if entry.user_id)

    week = current_season_week(db)
    weekly_picks = (
        db.query(models.Pick)
        .filter(models.Pick.entry_id.in_(entry_ids), models.Pick.week == week)
        .all()
        if entry_ids else []
    )
    season_picks = (
        db.query(models.Pick).filter(models.Pick.entry_id.in_(entry_ids)).count()
        if entry_ids else 0
    )
    entry_by_id = {entry.id: entry for entry in entries}
    engaged_ids = {
        entry_by_id[pick.entry_id].user_id
        for pick in weekly_picks
        if pick.entry_id in entry_by_id and entry_by_id[pick.entry_id].user_id
    }
    eligible_entries = [entry for entry in entries if entry.alive]
    eligible_entry_ids = {entry.id for entry in eligible_entries}
    picked_entry_ids = {
        pick.entry_id for pick in weekly_picks if pick.entry_id in eligible_entry_ids
    }
    popular = (
        db.query(models.Pick.team, func.count(models.Pick.id))
        .filter(
            models.Pick.entry_id.in_(entry_ids),
            models.Pick.week == week,
            models.Pick.locked.is_(True),
        )
        .group_by(models.Pick.team)
        .order_by(func.count(models.Pick.id).desc(), models.Pick.team.asc())
        .limit(5)
        .all()
        if entry_ids else []
    )
    return {
        "pool_id": pool.id,
        "pool_name": pool.name,
        "pool_type": pool.pool_type,
        "week": week,
        "members": len(participant_ids),
        "engaged_members": len(engaged_ids),
        "total_entries": len(entries),
        "remaining_entries": sum(1 for entry in entries if entry.alive),
        "eliminated_entries": sum(1 for entry in entries if not entry.alive),
        "weekly_entries_with_picks": len(picked_entry_ids),
        "weekly_eligible_entries": len(eligible_entries),
        "weekly_picks": len(weekly_picks),
        "weekly_wins": sum(1 for pick in weekly_picks if pick.result == "win"),
        "weekly_losses": sum(1 for pick in weekly_picks if pick.result == "loss"),
        "season_picks": season_picks,
        "forum_messages": db.query(models.MessageBoard).filter(models.MessageBoard.pool_id == pool.id).count(),
        "popular_locked_picks": [{"team": team, "picks": count} for team, count in popular],
    }


@router.get("/{pool_id}/owner-report-preference", response_model=schemas.OwnerReportPreferenceOut)
def get_preference(pool_id: str, db: Session = Depends(deps.get_db), current_user: models.User = Depends(deps.get_current_user)):
    pool = _require_owner(db, pool_id, current_user)
    return {"pool_id": pool.id, "enabled": pool.owner_reports_enabled, "frequency": pool.owner_reports_frequency, "last_sent_at": pool.owner_reports_last_sent_at}


@router.put("/{pool_id}/owner-report-preference", response_model=schemas.OwnerReportPreferenceOut)
def set_preference(pool_id: str, update: schemas.OwnerReportPreferenceUpdate, db: Session = Depends(deps.get_db), current_user: models.User = Depends(deps.get_current_user)):
    pool = _require_owner(db, pool_id, current_user)
    changed = pool.owner_reports_enabled != update.enabled or pool.owner_reports_frequency != update.frequency
    pool.owner_reports_enabled = update.enabled
    pool.owner_reports_frequency = update.frequency
    pool.updated_at = _utcnow()
    db.commit()
    if changed:
        create_audit_log(
            db, "OWNER_POOL_REPORT_PREFERENCE_UPDATED",
            f"{'Enabled' if update.enabled else 'Disabled'} weekly owner reports for {pool.name}",
            user_id=current_user.id, entity_type="pool", entity_id=pool.id,
            additional_data={"pool_id": pool.id, "enabled": update.enabled, "frequency": update.frequency},
        )
    return {"pool_id": pool.id, "enabled": pool.owner_reports_enabled, "frequency": pool.owner_reports_frequency, "last_sent_at": pool.owner_reports_last_sent_at}


@router.get("/{pool_id}/owner-report-preview", response_model=schemas.OwnerPoolReportOut)
def preview_report(pool_id: str, db: Session = Depends(deps.get_db), current_user: models.User = Depends(deps.get_current_user)):
    return build_owner_report(db, _require_owner(db, pool_id, current_user))


def deliver_due_reports(db: Session, now: datetime | None = None) -> tuple[int, int]:
    current = now or _utcnow()
    cutoff = current - timedelta(days=6)
    pools = db.query(models.Pool).filter(
        models.Pool.owner_reports_enabled.is_(True),
        models.Pool.owner_reports_frequency == "weekly",
    ).all()
    sent = failed = 0
    for pool in pools:
        if pool.owner_reports_last_sent_at and pool.owner_reports_last_sent_at > cutoff:
            continue
        owner = db.get(models.User, pool.owner_id)
        if owner is None or not owner.is_active:
            continue
        try:
            send_pool_owner_report(owner.email, build_owner_report(db, pool))
            pool.owner_reports_last_sent_at = current
            db.commit()
            sent += 1
        except Exception:
            db.rollback()
            failed += 1
            logger.exception("owner_pool_report_failed", extra={"event": "owner_pool_report_failed", "pool_id": pool.id})
    return sent, failed


def main() -> int:
    db = SessionLocal()
    try:
        with advisory_job_lock(engine, LOCK_NAME) as acquired:
            if not acquired:
                log_event(logger, logging.INFO, "owner_pool_reports_lock_skipped")
                return 0
            sent, failed = deliver_due_reports(db)
        log_event(logger, logging.INFO, "owner_pool_reports_completed", sent=sent, failed=failed)
        return 1 if failed else 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
