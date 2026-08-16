import uuid
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.orm import Session

import models
from audit_utils import log_admin_action
from odds_service import freeze_week_lines
from schedule import current_season_games, current_season_week


def pool_week_lock_time(pool: models.Pool, games):
    """Return the configured weekly deadline as naive UTC."""
    if not games:
        return None
    if pool.lock_day_of_week is None or pool.lock_time_of_day is None or not pool.lock_timezone:
        return pool.lock_time
    try:
        pool_tz = ZoneInfo(pool.lock_timezone)
    except ZoneInfoNotFoundError:
        return pool.lock_time
    kickoff_local = games[0].start_time.replace(tzinfo=timezone.utc).astimezone(pool_tz)
    week_start = kickoff_local.date() - timedelta(days=(kickoff_local.weekday() - 1) % 7)
    target_date = week_start + timedelta(days=(pool.lock_day_of_week - 1) % 7)
    return datetime.combine(target_date, pool.lock_time_of_day, tzinfo=pool_tz).astimezone(timezone.utc).replace(tzinfo=None)


def lock_pool_week(
    db: Session, pool: models.Pool, week: int, actor_id: str, now=None,
    games_provider=current_season_games, line_freezer=freeze_week_lines,
    log_skipped_defaults=True,
):
    """Idempotently freeze a week and create locked defaults for missing picks."""
    now = now or datetime.now(timezone.utc).replace(tzinfo=None)
    games = games_provider(db, week)
    if pool.pool_type == "pickem":
        entry_ids = [row[0] for row in db.query(models.Entry.id).filter(models.Entry.pool_id == pool.id)]
        if entry_ids:
            db.query(models.Pick).filter(
                models.Pick.entry_id.in_(entry_ids), models.Pick.week == week,
                models.Pick.locked == False,  # noqa: E712
            ).update({"locked": True}, synchronize_session="fetch")
        db.commit()
        return 0
    frozen_lines = line_freezer(db, pool.id, week, games, captured_at=now)
    line_ranked_teams = [
        line.favorite_team.abbrv
        for line in sorted(frozen_lines, key=lambda item: (-(item.spread or 0), item.favorite_team_id or 0))
        if line.favorite_team is not None
    ]
    alive_entries = db.query(models.Entry).filter(
        models.Entry.pool_id == pool.id, models.Entry.alive == True  # noqa: E712
    ).all()
    alive_ids = {entry.id for entry in alive_entries}
    if alive_ids:
        db.query(models.Pick).filter(
            models.Pick.entry_id.in_(alive_ids), models.Pick.week == week,
            models.Pick.locked == False,  # noqa: E712
        ).update({"locked": True}, synchronize_session="fetch")
    existing = db.query(models.Pick).filter(
        models.Pick.entry_id.in_(alive_ids), models.Pick.week == week
    ).all() if alive_ids else []
    existing_entry_ids = {pick.entry_id for pick in existing}
    popularity = {}
    for pick in existing:
        popularity[pick.team] = popularity.get(pick.team, 0) + 1
    popular_teams = [team for team, _ in sorted(popularity.items(), key=lambda item: (-item[1], item[0]))]
    created = 0
    for entry in alive_entries:
        if entry.id in existing_entry_ids:
            continue
        used = {pick.team for pick in db.query(models.Pick).filter(models.Pick.entry_id == entry.id)}
        candidate = next((team for team in line_ranked_teams + popular_teams if team not in used), None)
        if candidate is None:
            if log_skipped_defaults:
                log_admin_action(db=db, action="AUTO_PICK_SKIPPED", admin_user_id=actor_id,
                    details=f"No available team for entry {entry.id} in week {week}",
                    target_entity_type="entry", target_entity_id=entry.id,
                    additional_data={"pool_id": pool.id, "week": week})
            continue
        pick = models.Pick(id=str(uuid.uuid4()), entry_id=entry.id, week=week, team=candidate,
                           locked=True, created_at=now, updated_at=now)
        db.add(pick)
        db.flush()
        entry_owner = db.query(models.User).filter(models.User.id == entry.user_id).first()
        log_admin_action(db=db, action="AUTO_PICK", admin_user_id=actor_id,
            details=f"Auto-picked {candidate} for entry {entry.id} in week {week}",
            target_entity_type="pick", target_entity_id=pick.id,
            additional_data={"pool_id": pool.id, "entry_id": entry.id, "week": week,
                             "entry_name": entry.name, "user_id": entry.user_id,
                             "user_email": entry_owner.email if entry_owner else None,
                             "team": candidate, "reason": "no_pick_at_lock"})
        created += 1
    db.commit()
    return created


def process_due_weekly_locks(db: Session, now=None):
    """Process every recurring pool whose current-week deadline has passed."""
    now = now or datetime.now(timezone.utc).replace(tzinfo=None)
    week = current_season_week(db, now)
    games = current_season_games(db, week)
    processed = 0
    for pool in db.query(models.Pool).filter(
        models.Pool.lock_day_of_week.isnot(None),
        models.Pool.lock_time_of_day.isnot(None),
        models.Pool.lock_timezone.isnot(None),
    ):
        deadline = pool_week_lock_time(pool, games)
        if deadline is None or deadline > now:
            continue
        alive_ids = [row[0] for row in db.query(models.Entry.id).filter(
            models.Entry.pool_id == pool.id, models.Entry.alive == True  # noqa: E712
        )]
        unlocked_or_missing = any(
            not db.query(models.Pick.id).filter(
                models.Pick.entry_id == entry_id, models.Pick.week == week,
                models.Pick.locked == True,  # noqa: E712
            ).first() for entry_id in alive_ids
        )
        if unlocked_or_missing:
            lock_pool_week(db, pool, week, pool.owner_id, now, log_skipped_defaults=False)
            processed += 1
    return processed
