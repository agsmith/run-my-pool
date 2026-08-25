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
    # Every API container runs the lock sweep. Serialize one pool's work so
    # overlapping workers cannot both observe a missing Survivor pick and
    # create duplicate defaults (MySQL permits duplicate NULL game_id values).
    locked_pool = db.query(models.Pool).filter(
        models.Pool.id == pool.id
    ).with_for_update().one_or_none()
    if locked_pool is not None:
        pool = locked_pool
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
    ranked_lines = sorted(
        frozen_lines,
        key=lambda item: (-(item.spread or 0), item.favorite_team_id or 0),
    )
    line_ranked_teams = []
    for line in ranked_lines:
        candidate_team = line.favorite_team
        if getattr(pool, "survivor_objective", "win") == "lose":
            candidate_team = None
            favorite_team_id = getattr(line, "favorite_team_id", None)
            game = next(
                (
                    game
                    for game in games
                    if getattr(game, "game_id", None) == getattr(line, "game_id", None)
                ),
                getattr(line, "game", None),
            )
            if game is not None and favorite_team_id in {
                game.home_team_id,
                game.away_team_id,
            }:
                underdog_id = (
                    game.away_team_id
                    if favorite_team_id == game.home_team_id
                    else game.home_team_id
                )
                candidate_team = db.query(models.Team).filter(
                    models.Team.id == underdog_id
                ).first()
        if candidate_team is not None:
            line_ranked_teams.append(candidate_team.abbrv)
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
    losers_survivor = getattr(pool, "survivor_objective", "win") == "lose"
    fallback_teams = popular_teams
    if losers_survivor:
        scheduled_teams = []
        for game in sorted(
            games,
            key=lambda item: (
                getattr(item, "start_time", datetime.min),
                getattr(item, "game_id", 0),
            ),
        ):
            for team_id in (
                getattr(game, "away_team_id", None),
                getattr(game, "home_team_id", None),
            ):
                team = db.query(models.Team).filter(models.Team.id == team_id).first()
                if team is not None and team.abbrv not in scheduled_teams:
                    scheduled_teams.append(team.abbrv)
        fallback_teams = scheduled_teams
    created = 0
    for entry in alive_entries:
        if entry.id in existing_entry_ids:
            continue
        used = {pick.team for pick in db.query(models.Pick).filter(models.Pick.entry_id == entry.id)}
        candidate = next(
            (team for team in line_ranked_teams + fallback_teams if team not in used),
            None,
        )
        if candidate is None:
            if log_skipped_defaults:
                log_admin_action(db=db, action="AUTO_PICK_SKIPPED", admin_user_id=actor_id,
                    details=f"No available team for entry {entry.id} in week {week}",
                    target_entity_type="entry", target_entity_id=entry.id,
                    additional_data={"pool_id": pool.id, "week": week,
                                     "survivor_objective": pool.survivor_objective})
            continue
        candidate_team = db.query(models.Team).filter(
            models.Team.abbrv == candidate
        ).first()
        pick = models.Pick(id=str(uuid.uuid4()), entry_id=entry.id, week=week, team=candidate,
                           team_id=candidate_team.id if candidate_team else None,
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
                             "team": candidate, "reason": "no_pick_at_lock",
                             "survivor_objective": pool.survivor_objective})
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
