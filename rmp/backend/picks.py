from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import and_, case, func, or_
from typing import List
import uuid
from datetime import datetime, timezone

from deps import get_db, get_current_user
from models import Pick, Entry, Schedule, Team, Pool, User
from schemas import (
    LeaderboardEntryOut,
    PickBreakdownItem,
    PickCreate,
    PickEmStandingOut,
    PickOut,
    PickUpdate,
)
from audit_utils import log_create_operation, log_update_operation, log_delete_operation
from admin import is_user_locked_in_pool
from pool_access import is_pool_participant
from schedule import current_season_games
from weekly_locks import pool_week_lock_time
from public_identity import display_name_from_email, public_display_name

router = APIRouter()


def _team_name(db: Session, abbreviation: str):
    """Return a display name for an audited team, falling back to its code."""
    team = db.query(Team).filter(Team.abbrv == abbreviation).first()
    return team.name if team else abbreviation


def _pick_audit_context(entry: Entry, current_user):
    """Capture labels that remain useful even if related records later change."""
    return {
        "entry_id": entry.id,
        "entry_name": entry.name,
        "pool_id": entry.pool_id,
        "username": current_user.email,
    }


def _is_pickem(pool: Pool) -> bool:
    return bool(pool and pool.pool_type == "pickem")


def _pickem_game_and_team(db: Session, pick: PickCreate):
    if pick.game_id is None:
        raise HTTPException(status_code=400, detail="Pick 'Em selections require a game_id")
    game = db.query(Schedule).filter(
        Schedule.game_id == pick.game_id,
        Schedule.week_num == pick.week,
    ).first()
    if not game:
        raise HTTPException(status_code=400, detail="Game is not scheduled for this week")
    team = db.query(Team).filter(Team.abbrv == pick.team).first()
    if not team or team.id not in {game.home_team_id, game.away_team_id}:
        raise HTTPException(status_code=400, detail="Selected team is not playing in this game")
    return game, team


# ---------------------------------------------------------------------------
# Lock enforcement helpers
# ---------------------------------------------------------------------------


def _get_effective_lock_time(db: Session, pool: Pool, team_abbrev: str, week: int):
    """
    Return the effective lock time for a pick on a given team/week combination.

    For teams whose game kicks off before the pool lock_time (e.g. Thursday night
    games before Sunday 1pm ET), the effective lock is the game's start_time.
    For all other games the effective lock is pool.lock_time.

    Returns None if neither a pool lock_time nor a game start_time is set.
    """
    team = db.query(Team).filter(Team.abbrv == team_abbrev).first()
    game = None
    if team:
        game = (
            db.query(Schedule)
            .filter(
                Schedule.week_num == week,
                or_(
                    Schedule.home_team_id == team.id,
                    Schedule.away_team_id == team.id,
                ),
            )
            # Schedule rows are retained across seasons, while picks identify a
            # week but not a season. Prefer the newest matching game so an old
            # season's kickoff cannot incorrectly lock the current season.
            .order_by(Schedule.start_time.desc())
            .first()
        )

    candidates = []
    recurring_lock = None
    if (
        pool.lock_day_of_week is not None
        and pool.lock_time_of_day is not None
        and pool.lock_timezone
    ):
        # Derive the pool-wide deadline from the week's schedule, not from the
        # submitted team. Otherwise an unknown or unscheduled team could make
        # the deadline disappear and bypass a recurring lock.
        recurring_lock = pool_week_lock_time(pool, current_season_games(db, week))

    if recurring_lock is not None:
        candidates.append(recurring_lock)
    elif pool.lock_time is not None:
        # Existing pools retain their absolute lock until recurring settings
        # are saved by an admin.
        candidates.append(pool.lock_time)
    if game is not None and game.start_time is not None:
        candidates.append(game.start_time)

    return min(candidates) if candidates else None


def _validate_survivor_team(db: Session, pool: Pool, team: Team | None, week: int) -> None:
    """Reject fabricated or unscheduled Survivor teams for every lock configuration."""
    games = current_season_games(db, week)
    # Legacy pools and isolated environments can predate schedule ingestion.
    # Preserve that workflow only while no slate exists; once any current slate
    # is loaded, every selection must resolve to a team playing that week.
    if not games:
        if (
            pool.lock_day_of_week is not None
            and pool.lock_time_of_day is not None
            and pool.lock_timezone
        ):
            detail = (
                "Selected team is not recognized"
                if team is None
                else "Selected team is not scheduled for this week"
            )
            raise HTTPException(status_code=400, detail=detail)
        return
    if team is None:
        raise HTTPException(status_code=400, detail="Selected team is not recognized")
    scheduled_team_ids = {
        team_id
        for game in games
        for team_id in (game.home_team_id, game.away_team_id)
    }
    if team.id not in scheduled_team_ids:
        raise HTTPException(status_code=400, detail="Selected team is not scheduled for this week")


def _check_pick_lock(db: Session, pool: Pool, team_abbrev: str, week: int) -> None:
    """
    Raise HTTP 423 if the effective lock time for this pick has already passed.

    For updates, pass the *existing* pick's team — the slot is locked at the
    kickoff of the game already selected, regardless of any new proposed team.
    """
    effective_lock = _get_effective_lock_time(db, pool, team_abbrev, week)
    if effective_lock is None:
        return  # no lock configured — allow the pick

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if effective_lock <= now:
        raise HTTPException(
            status_code=423,
            detail="This pick is locked. The game has started or the pool lock time has passed.",
        )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/picks/create", response_model=PickOut)
async def create_pick(
    pick: PickCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    # Verify the entry belongs to the current user
    entry = (
        db.query(Entry)
        .filter(Entry.id == pick.entry_id, Entry.user_id == current_user.id)
        # Serialize writes for one entry. This closes the check-then-insert race
        # that could otherwise create multiple Survivor rows for the same week.
        .with_for_update()
        .first()
    )
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Entry not found or doesn't belong to you",
        )

    # Reject picks on eliminated entries
    if not entry.alive:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Entry has been eliminated",
        )

    # Reject picks if user is locked in this pool
    if is_user_locked_in_pool(db, entry.pool_id, current_user.id):
        raise HTTPException(
            status_code=423,
            detail="Your account is locked in this pool. Contact the pool admin.",
        )

    # Fetch the pool for lock time enforcement
    pool = db.query(Pool).filter(Pool.id == entry.pool_id).first()

    pickem = _is_pickem(pool)
    game = None
    selected_team = db.query(Team).filter(Team.abbrv == pick.team).first()
    if pickem:
        game, selected_team = _pickem_game_and_team(db, pick)
    elif pool and pool.pool_type == "survivor":
        _validate_survivor_team(db, pool, selected_team, pick.week)

    # Survivor has one selection per week; Pick 'Em has one per scheduled game.
    existing_pick = (
        db.query(Pick)
        .filter(
            Pick.entry_id == pick.entry_id,
            Pick.week == pick.week,
            *((Pick.game_id == pick.game_id,) if pickem else (Pick.game_id.is_(None),)),
        )
        .first()
    )

    if existing_pick:
        # Lock check uses the EXISTING pick's team — the slot was locked at that
        # game's kickoff regardless of what new team is proposed.
        if existing_pick.locked:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot update a locked pick",
            )
        if pool:
            _check_pick_lock(db, pool, existing_pick.team, pick.week)

        # Update existing pick
        old_team = existing_pick.team
        existing_pick.team = pick.team
        existing_pick.team_id = selected_team.id if selected_team else None
        existing_pick.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(existing_pick)

        # Log pick update
        log_update_operation(
            db=db,
            entity_type="pick",
            entity_id=existing_pick.id,
            user_id=current_user.id,
            changes={
                "old_team": old_team,
                "old_team_name": _team_name(db, old_team),
                "new_team": pick.team,
                "new_team_name": _team_name(db, pick.team),
                "week": pick.week,
                **_pick_audit_context(entry, current_user),
            },
        )

        return existing_pick

    if pickem and pool.pickem_games_per_week:
        weekly_pick_count = (
            db.query(func.count(Pick.id))
            .filter(Pick.entry_id == pick.entry_id, Pick.week == pick.week)
            .scalar()
            or 0
        )
        if weekly_pick_count >= pool.pickem_games_per_week:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"This pool requires {pool.pickem_games_per_week} Pick 'Em selections per week",
            )

    # New pick — check pool lock time and per-game start_time
    if pool:
        _check_pick_lock(db, pool, pick.team, pick.week)

    # Check if the team has already been used in this entry
    team_already_used = (not pickem) and (
        db.query(Pick)
        .filter(and_(Pick.entry_id == pick.entry_id, Pick.team == pick.team))
        .first()
    )

    if team_already_used:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Team {pick.team} has already been selected in this entry",
        )

    # Create new pick
    db_pick = Pick(
        id=str(uuid.uuid4()),
        entry_id=pick.entry_id,
        week=pick.week,
        game_id=pick.game_id if pickem else None,
        team=pick.team,
        team_id=selected_team.id if selected_team else None,
        locked=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    db.add(db_pick)
    db.commit()
    db.refresh(db_pick)

    # Log pick creation
    log_create_operation(
        db=db,
        entity_type="pick",
        entity_id=db_pick.id,
        user_id=current_user.id,
        entity_data={
            "team": pick.team,
            "team_name": _team_name(db, pick.team),
            "week": pick.week,
            **_pick_audit_context(entry, current_user),
        },
    )

    return db_pick


@router.get("/picks/pool/{pool_id}/standings", response_model=List[PickEmStandingOut])
def get_pickem_standings(
    pool_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    pool = db.query(Pool).filter(Pool.id == pool_id).first()
    if not pool:
        raise HTTPException(status_code=404, detail="Pool not found")
    if not is_pool_participant(db, pool_id, current_user.id):
        raise HTTPException(status_code=403, detail="Pool membership required")
    if not _is_pickem(pool):
        raise HTTPException(status_code=400, detail="Standings are only available for Pick 'Em pools")

    rows = (
        db.query(
            Entry.id,
            Entry.name,
            Entry.user_id,
            User.email,
            func.sum(case((Pick.result == "win", 1), else_=0)).label("points"),
            func.count(Pick.id).label("picks_made"),
            func.sum(case((Pick.result.in_(["win", "loss"]), 1), else_=0)).label("possible_points"),
        )
        .join(User, User.id == Entry.user_id)
        .outerjoin(Pick, Pick.entry_id == Entry.id)
        .filter(Entry.pool_id == pool_id)
        .group_by(Entry.id, Entry.name, Entry.user_id, User.email)
        .all()
    )
    ordered = sorted(rows, key=lambda row: (-int(row.points or 0), row.name.casefold(), row.id))
    return [
        {
            "rank": index + 1,
            "entry_id": row.id,
            "entry_name": row.name,
            "user_id": row.user_id,
            "user_display_name": display_name_from_email(row.email),
            "points": int(row.points or 0),
            "possible_points": int(row.possible_points or 0),
            "picks_made": int(row.picks_made or 0),
        }
        for index, row in enumerate(ordered)
    ]


@router.get(
    "/picks/pool/{pool_id}/leaderboard",
    response_model=List[LeaderboardEntryOut],
)
def get_pool_leaderboard(
    pool_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Rank every pool entry using only selections that members may see."""
    pool = db.query(Pool).filter(Pool.id == pool_id).first()
    if not pool:
        raise HTTPException(status_code=404, detail="Pool not found")
    if not is_pool_participant(db, pool_id, current_user.id):
        raise HTTPException(status_code=403, detail="Pool membership required")
    if pool.pool_type not in {"survivor", "pickem"}:
        raise HTTPException(
            status_code=400,
            detail="Leaderboards are only available for Survivor and Pick 'Em pools",
        )

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    entries = (
        db.query(Entry)
        .options(selectinload(Entry.picks), selectinload(Entry.user))
        .filter(Entry.pool_id == pool_id)
        .order_by(Entry.name, Entry.id)
        .all()
    )
    weeks = {pick.week for entry in entries for pick in entry.picks}
    revealed_weeks = {
        week
        for week in weeks
        if (deadline := pool_week_lock_time(pool, current_season_games(db, week)))
        is not None
        and deadline <= now
    }

    rows = []
    for entry in entries:
        visible_picks = sorted(
            (
                pick
                for pick in entry.picks
                if pick.week in revealed_weeks
                or pick.locked
                or pick.result in {"win", "loss"}
            ),
            key=lambda pick: (pick.week, pick.game_id or 0, pick.id),
        )
        rows.append(
            {
                "entry": entry,
                "correct_picks": sum(pick.result == "win" for pick in visible_picks),
                "completed_picks": sum(
                    pick.result in {"win", "loss"} for pick in visible_picks
                ),
                "picks": visible_picks,
            }
        )

    rows.sort(
        key=lambda row: (
            -row["correct_picks"],
            -row["completed_picks"],
            row["entry"].name.casefold(),
            row["entry"].id,
        )
    )
    return [
        {
            "rank": index + 1,
            "entry_id": row["entry"].id,
            "entry_name": row["entry"].name,
            "user_id": row["entry"].user_id,
            "user_display_name": public_display_name(row["entry"].user),
            "correct_picks": row["correct_picks"],
            "completed_picks": row["completed_picks"],
            "alive": row["entry"].alive,
            "picks": [
                {"week": pick.week, "team": pick.team, "result": pick.result}
                for pick in row["picks"]
            ],
        }
        for index, row in enumerate(rows)
    ]


@router.get("/picks/entry/{entry_id}", response_model=List[PickOut])
async def get_picks_for_entry(
    entry_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)
):
    # Verify the entry belongs to the current user
    entry = (
        db.query(Entry)
        .filter(Entry.id == entry_id, Entry.user_id == current_user.id)
        .first()
    )
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Entry not found or doesn't belong to you",
        )

    picks = db.query(Pick).filter(Pick.entry_id == entry_id).order_by(Pick.week).all()
    return picks


@router.put("/picks/{pick_id}", response_model=PickOut)
async def update_pick(
    pick_id: str,
    pick_update: PickUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    # Get the pick and verify ownership through entry
    pick = (
        db.query(Pick)
        .join(Entry)
        .filter(Pick.id == pick_id, Entry.user_id == current_user.id)
        .with_for_update()
        .first()
    )

    if not pick:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pick not found or doesn't belong to you",
        )

    # Reject picks on eliminated entries
    entry = db.query(Entry).filter(Entry.id == pick.entry_id).first()
    if entry and not entry.alive:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Entry has been eliminated",
        )

    # Reject if user is locked in this pool
    if entry and is_user_locked_in_pool(db, entry.pool_id, current_user.id):
        raise HTTPException(
            status_code=423,
            detail="Your account is locked in this pool. Contact the pool admin.",
        )

    # Check if pick is locked (explicit flag)
    if pick.locked:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot update a locked pick",
        )

    # Lock check uses the EXISTING pick's team — the slot is locked at that
    # game's kickoff regardless of any new proposed team.
    if entry:
        pool = db.query(Pool).filter(Pool.id == entry.pool_id).first()
        if pool:
            _check_pick_lock(db, pool, pick.team, pick.week)
    else:
        pool = None

    # If updating team, check if the new team is already used in this entry
    if pick_update.team and pick_update.team != pick.team and _is_pickem(pool):
        game = db.query(Schedule).filter(Schedule.game_id == pick.game_id).first()
        team = db.query(Team).filter(Team.abbrv == pick_update.team).first()
        if not game or not team or team.id not in {game.home_team_id, game.away_team_id}:
            raise HTTPException(status_code=400, detail="Selected team is not playing in this game")
        pick.team_id = team.id
    elif pick_update.team and pick_update.team != pick.team:
        team = db.query(Team).filter(Team.abbrv == pick_update.team).first()
        if pool and pool.pool_type == "survivor":
            _validate_survivor_team(db, pool, team, pick.week)
            pick.team_id = team.id if team else None
        team_already_used = (
            db.query(Pick)
            .filter(
                and_(
                    Pick.entry_id == pick.entry_id,
                    Pick.team == pick_update.team,
                    Pick.id != pick_id,
                )
            )
            .first()
        )

        if team_already_used:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Team {pick_update.team} has already been selected in this entry",
            )

    # Capture changes for audit log
    changes = {}
    for field, value in pick_update.model_dump(exclude_unset=True).items():
        old_value = getattr(pick, field)
        if old_value != value:
            changes[field] = {"old": old_value, "new": value}
        setattr(pick, field, value)

    pick.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(pick)

    # Log pick update if there were changes
    if changes:
        changes["context"] = {
            "week": pick.week,
            **_pick_audit_context(entry, current_user),
        }
        if "team" in changes:
            changes["context"].update(
                {
                    "old_team_name": _team_name(db, changes["team"]["old"]),
                    "new_team_name": _team_name(db, changes["team"]["new"]),
                }
            )
        log_update_operation(
            db=db,
            entity_type="pick",
            entity_id=pick.id,
            user_id=current_user.id,
            changes=changes,
        )

    return pick


@router.delete("/picks/{pick_id}")
async def delete_pick(
    pick_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)
):
    # Get the pick and verify ownership through entry
    pick = (
        db.query(Pick)
        .join(Entry)
        .filter(Pick.id == pick_id, Entry.user_id == current_user.id)
        .first()
    )

    if not pick:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pick not found or doesn't belong to you",
        )

    # Check if pick is locked
    if pick.locked:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete a locked pick",
        )

    # The background sweep materializes the locked flag, but it is not the
    # security boundary. Enforce the calculated deadline on every mutation so
    # a delayed or failed worker cannot create a deletion window.
    entry = pick.entry
    pool = db.query(Pool).filter(Pool.id == entry.pool_id).first()
    if not entry.alive:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Entry has been eliminated",
        )
    if is_user_locked_in_pool(db, entry.pool_id, current_user.id):
        raise HTTPException(
            status_code=423,
            detail="Your account is locked in this pool. Contact the pool admin.",
        )
    if pool:
        _check_pick_lock(db, pool, pick.team, pick.week)

    # Log pick deletion before deleting
    log_delete_operation(
        db=db,
        entity_type="pick",
        entity_id=pick.id,
        user_id=current_user.id,
        entity_data={
            "team": pick.team,
            "team_name": _team_name(db, pick.team),
            "week": pick.week,
            **_pick_audit_context(entry, current_user),
        },
    )

    db.delete(pick)
    db.commit()
    return {"message": "Pick deleted successfully"}


@router.get(
    "/picks/pool/{pool_id}/week/{week}/breakdown",
    response_model=List[PickBreakdownItem],
)
def get_pick_breakdown(
    pool_id: str,
    week: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Return per-team pick counts and per-user entry counts for surviving entries.
    Configured pools reveal every pick once the weekly pool deadline passes.
    Legacy pools without a weekly deadline retain kickoff-based revealing.
    """
    if not is_pool_participant(db, pool_id, current_user.id):
        raise HTTPException(status_code=403, detail="League membership required")
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    pool = db.query(Pool).filter(Pool.id == pool_id).first()
    if not pool:
        raise HTTPException(status_code=404, detail="Pool not found")
    deadline = pool_week_lock_time(pool, current_season_games(db, week))
    if deadline is not None and deadline > now:
        return []

    # Subquery: team IDs with a game that has already started this week
    started_home = db.query(Schedule.home_team_id).filter(
        Schedule.week_num == week, Schedule.start_time < now
    )
    started_away = db.query(Schedule.away_team_id).filter(
        Schedule.week_num == week, Schedule.start_time < now
    )
    started_team_ids = started_home.union(started_away).subquery()

    filters = [Entry.pool_id == pool_id, Entry.alive == True, Pick.week == week]  # noqa: E712
    if deadline is None:
        filters.append(Pick.team_id.in_(started_team_ids))

    rows = (
        db.query(
            Pick.team,
            Team.id.label("team_id"),
            Team.name.label("team_name"),
            Team.abbrv.label("team_abbrv"),
            Team.logo.label("team_logo"),
            func.count(Pick.id).label("count"),
        )
        .join(Entry, Pick.entry_id == Entry.id)
        .join(Team, Team.abbrv == Pick.team)
        .filter(*filters)
        .group_by(Pick.team, Team.id, Team.name, Team.abbrv, Team.logo)
        .order_by(func.count(Pick.id).desc())
        .all()
    )

    user_rows = (
        db.query(Pick.team, User.id, User.email, func.count(Pick.id).label("entry_count"))
        .join(Entry, Pick.entry_id == Entry.id)
        .join(User, Entry.user_id == User.id)
        .join(Team, Team.abbrv == Pick.team)
        .filter(*filters)
        .group_by(Pick.team, User.id, User.email)
        .order_by(Pick.team, User.email)
        .all()
    )
    users_by_team = {}
    for row in user_rows:
        users_by_team.setdefault(row.team, []).append({
            "user_id": row.id,
            "display_name": display_name_from_email(row.email),
            "entry_count": row.entry_count,
        })

    return [
        PickBreakdownItem(
            team=row.team,
            team_id=row.team_id,
            team_name=row.team_name,
            team_abbrv=row.team_abbrv,
            team_logo=row.team_logo,
            count=row.count,
            users=users_by_team.get(row.team, []),
        )
        for row in rows
    ]
