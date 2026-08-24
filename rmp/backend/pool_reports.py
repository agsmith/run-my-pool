"""Owner-facing pool health reports and weekly delivery job."""

import logging
import sys
import uuid
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
from email_service import send_member_weekly_recap, send_pool_owner_report
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


def _require_member(db: Session, pool_id: str, user: models.User) -> tuple[models.Pool, models.PoolMember]:
    pool = db.get(models.Pool, pool_id)
    if pool is None:
        raise HTTPException(status_code=404, detail="Pool not found")
    membership = db.query(models.PoolMember).filter(
        models.PoolMember.pool_id == pool_id,
        models.PoolMember.user_id == user.id,
    ).first()
    if membership is None:
        raise HTTPException(status_code=403, detail="Pool membership required")
    if pool.pool_type == "squares":
        raise HTTPException(status_code=400, detail="Weekly recaps are available for Survivor and Pick 'Em pools")
    return pool, membership


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


@router.get("/{pool_id}/member-recap-preference", response_model=schemas.MemberRecapPreferenceOut)
def get_member_recap_preference(pool_id: str, db: Session = Depends(deps.get_db), current_user: models.User = Depends(deps.get_current_user)):
    pool, membership = _require_member(db, pool_id, current_user)
    return {"pool_id": pool.id, "enabled": membership.weekly_recap_enabled}


@router.put("/{pool_id}/member-recap-preference", response_model=schemas.MemberRecapPreferenceOut)
def set_member_recap_preference(pool_id: str, update: schemas.MemberRecapPreferenceUpdate, db: Session = Depends(deps.get_db), current_user: models.User = Depends(deps.get_current_user)):
    pool, membership = _require_member(db, pool_id, current_user)
    changed = membership.weekly_recap_enabled != update.enabled
    membership.weekly_recap_enabled = update.enabled
    db.commit()
    if changed:
        create_audit_log(
            db, "MEMBER_WEEKLY_RECAP_PREFERENCE_UPDATED",
            f"{'Enabled' if update.enabled else 'Disabled'} weekly member recaps for {pool.name}",
            user_id=current_user.id, entity_type="pool", entity_id=pool.id,
            additional_data={"pool_id": pool.id, "enabled": update.enabled},
        )
    return {"pool_id": pool.id, "enabled": membership.weekly_recap_enabled}


def latest_completed_week(db: Session) -> tuple[int, int] | None:
    """Return the newest season/week whose entire scheduled slate is final."""
    candidates = db.query(models.Schedule.season, models.Schedule.week_num).distinct().order_by(
        models.Schedule.season.desc(), models.Schedule.week_num.desc()
    ).all()
    for season, week in candidates:
        statuses = [status for (status,) in db.query(models.Schedule.status).filter(
            models.Schedule.season == season, models.Schedule.week_num == week
        ).all()]
        if statuses and all((status or "").lower() == "final" for status in statuses):
            return season, week
    return None


def build_member_recap(db: Session, pool: models.Pool, user: models.User, season: int, week: int) -> dict:
    entries = db.query(models.Entry).filter(
        models.Entry.pool_id == pool.id, models.Entry.user_id == user.id
    ).order_by(models.Entry.name.asc()).all()
    entry_ids = [entry.id for entry in entries]
    picks = db.query(models.Pick).filter(
        models.Pick.entry_id.in_(entry_ids), models.Pick.week == week
    ).all() if entry_ids else []
    picks_by_entry: dict[str, list[models.Pick]] = {}
    for pick in picks:
        picks_by_entry.setdefault(pick.entry_id, []).append(pick)
    entry_rows = []
    for entry in entries:
        entry_picks = picks_by_entry.get(entry.id, [])
        if pool.pool_type == "pickem":
            pick_label = ", ".join(pick.team for pick in entry_picks) or None
            wins = sum(1 for pick in entry_picks if pick.result == "win")
            losses = sum(1 for pick in entry_picks if pick.result == "loss")
            result = f"{wins} correct, {losses} incorrect" if entry_picks else "no pick"
        else:
            pick = entry_picks[0] if entry_picks else None
            pick_label = pick.team if pick else None
            result = (pick.result or "pending") if pick else "no pick"
        entry_rows.append({"entry_name": entry.name, "pick": pick_label, "result": result})
    pool_entries = db.query(models.Entry).filter(models.Entry.pool_id == pool.id).all()
    return {
        "pool_id": pool.id, "pool_name": pool.name, "pool_type": pool.pool_type,
        "season": season, "week": week, "entries": entry_rows,
        "wins": sum(1 for pick in picks if pick.result == "win"),
        "losses": sum(1 for pick in picks if pick.result == "loss"),
        "pending": sum(1 for pick in picks if pick.result not in {"win", "loss"}) + sum(1 for entry in entries if not picks_by_entry.get(entry.id)),
        "remaining_entries": sum(1 for entry in entries if entry.alive),
        "total_entries": len(entries),
        "pool_remaining_entries": sum(1 for entry in pool_entries if entry.alive),
        "pool_total_entries": len(pool_entries),
    }


def deliver_member_recaps(db: Session, now: datetime | None = None) -> tuple[int, int]:
    completed = latest_completed_week(db)
    if completed is None:
        return 0, 0
    season, week = completed
    memberships = db.query(models.PoolMember).join(
        models.Pool, models.Pool.id == models.PoolMember.pool_id
    ).filter(
        models.PoolMember.weekly_recap_enabled.is_(True),
        models.Pool.pool_type.in_(["survivor", "pickem"]),
        models.Pool.billing_season == season,
    ).all()
    sent = failed = 0
    attempted_at = now or _utcnow()
    for membership in memberships:
        user = db.get(models.User, membership.user_id)
        pool = db.get(models.Pool, membership.pool_id)
        if user is None or pool is None or not user.is_active:
            continue
        delivery = db.query(models.MemberRecapDelivery).filter_by(
            pool_id=pool.id, user_id=user.id, season=season, week_num=week
        ).first()
        if delivery and delivery.status == "sent":
            continue
        if delivery is None:
            delivery = models.MemberRecapDelivery(
                id=str(uuid.uuid4()), pool_id=pool.id, user_id=user.id,
                season=season, week_num=week, status="pending", attempted_at=attempted_at,
            )
            db.add(delivery)
        else:
            delivery.status = "pending"
            delivery.attempted_at = attempted_at
            delivery.error = None
        db.commit()
        try:
            message_id = send_member_weekly_recap(user.email, build_member_recap(db, pool, user, season, week))
            delivery.status = "sent"
            delivery.message_id = message_id
            delivery.sent_at = attempted_at
            db.commit()
            sent += 1
        except Exception as exc:
            db.rollback()
            delivery = db.get(models.MemberRecapDelivery, delivery.id)
            delivery.status = "failed"
            delivery.error = str(exc)[:255]
            db.commit()
            failed += 1
            logger.exception("member_weekly_recap_failed", extra={"event": "member_weekly_recap_failed", "pool_id": pool.id, "user_id": user.id, "week": week})
    return sent, failed


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
            owner_sent, owner_failed = deliver_due_reports(db)
            member_sent, member_failed = deliver_member_recaps(db)
        log_event(logger, logging.INFO, "weekly_pool_reports_completed", owner_sent=owner_sent, owner_failed=owner_failed, member_sent=member_sent, member_failed=member_failed)
        return 1 if owner_failed or member_failed else 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
