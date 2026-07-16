from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, or_
from typing import List
import uuid
from datetime import datetime, timezone

from deps import get_db, get_current_user
from models import Pick, Entry, Schedule, Team
from schemas import PickCreate, PickUpdate, PickOut, PickBreakdownItem
from audit_utils import log_create_operation, log_update_operation, log_delete_operation

router = APIRouter()


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
        .first()
    )
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Entry not found or doesn't belong to you",
        )

    # Check if a pick already exists for this entry and week
    existing_pick = (
        db.query(Pick)
        .filter(and_(Pick.entry_id == pick.entry_id, Pick.week == pick.week))
        .first()
    )

    if existing_pick:
        # Update existing pick
        old_team = existing_pick.team
        existing_pick.team = pick.team
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
                "new_team": pick.team,
                "week": pick.week,
                "entry_id": pick.entry_id,
            },
        )

        return existing_pick

    # Check if the team has already been used in this entry
    team_already_used = (
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
        team=pick.team,
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
        entity_data={"team": pick.team, "week": pick.week, "entry_id": pick.entry_id},
    )

    return db_pick


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
            detail="Cannot update a locked pick",
        )

    # If updating team, check if the new team is already used in this entry
    if pick_update.team and pick_update.team != pick.team:
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

    # Log pick deletion before deleting
    log_delete_operation(
        db=db,
        entity_type="pick",
        entity_id=pick.id,
        user_id=current_user.id,
        entity_data={"team": pick.team, "week": pick.week, "entry_id": pick.entry_id},
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
    Return per-team pick counts for alive entries in a pool/week.
    Only includes teams whose game has already kicked off (Schedule.start_time < now).
    Returns an empty list if no games have started yet.
    """
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    # Subquery: team IDs with a game that has already started this week
    started_home = db.query(Schedule.home_team_id).filter(
        Schedule.week_num == week, Schedule.start_time < now
    )
    started_away = db.query(Schedule.away_team_id).filter(
        Schedule.week_num == week, Schedule.start_time < now
    )
    started_team_ids = started_home.union(started_away).subquery()

    rows = (
        db.query(
            Pick.team,
            Pick.team_id,
            Team.name.label("team_name"),
            Team.abbrv.label("team_abbrv"),
            Team.logo.label("team_logo"),
            func.count(Pick.id).label("count"),
        )
        .join(Entry, Pick.entry_id == Entry.id)
        .join(Team, Pick.team_id == Team.id)
        .filter(
            Entry.pool_id == pool_id,
            Entry.alive == True,
            Pick.week == week,
            Pick.team_id.in_(started_team_ids),
        )
        .group_by(Pick.team, Pick.team_id, Team.name, Team.abbrv, Team.logo)
        .order_by(func.count(Pick.id).desc())
        .all()
    )

    return [
        PickBreakdownItem(
            team=row.team,
            team_id=row.team_id,
            team_name=row.team_name,
            team_abbrv=row.team_abbrv,
            team_logo=row.team_logo,
            count=row.count,
        )
        for row in rows
    ]
