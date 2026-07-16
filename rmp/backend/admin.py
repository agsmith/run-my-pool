"""
Admin endpoints for administrative operations
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from datetime import datetime, timezone
from typing import Optional
import uuid

import models
import schemas
import deps
from audit_utils import log_admin_action

router = APIRouter(prefix="/admin", tags=["admin"])


def verify_admin_access(pool_id: str, current_user: models.User, db: Session) -> bool:
    """Verify if user has admin access to the pool"""
    pool = db.query(models.Pool).filter(models.Pool.id == pool_id).first()
    if pool and pool.owner_id == current_user.id:
        return True
    pool_admin = (
        db.query(models.PoolAdmin)
        .filter(
            models.PoolAdmin.pool_id == pool_id,
            models.PoolAdmin.user_id == current_user.id,
        )
        .first()
    )
    return pool_admin is not None


@router.post("/pools/{pool_id}/transfer-entry")
def transfer_entry(
    pool_id: str,
    transfer_data: schemas.EntryTransfer,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
):
    """Transfer entry ownership from one user to another (admin only)"""
    if not verify_admin_access(pool_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only pool owners and admins can transfer entries",
        )

    entry = (
        db.query(models.Entry)
        .filter(
            models.Entry.id == transfer_data.entry_id,
            models.Entry.pool_id == pool_id,
        )
        .first()
    )
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found in this pool"
        )

    current_owner = (
        db.query(models.User).filter(models.User.id == entry.user_id).first()
    )
    if not current_owner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Current entry owner not found",
        )

    new_owner = (
        db.query(models.User)
        .filter(models.User.email == transfer_data.to_email)
        .first()
    )
    if not new_owner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{transfer_data.to_email}' not found",
        )

    existing_entry = (
        db.query(models.Entry)
        .filter(
            models.Entry.pool_id == pool_id,
            models.Entry.user_id == new_owner.id,
            models.Entry.name == entry.name,
        )
        .first()
    )
    if existing_entry:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User '{transfer_data.to_email}' already has an entry named '{entry.name}' in this pool",
        )

    old_user_id = entry.user_id
    old_email = current_owner.email

    entry.user_id = new_owner.id
    db.commit()
    db.refresh(entry)

    log_admin_action(
        db=db,
        action="TRANSFER_ENTRY",
        admin_user_id=current_user.id,
        details=f"Transferred entry '{entry.name}' from {old_email} to {transfer_data.to_email}",
        target_entity_type="entry",
        target_entity_id=entry.id,
        additional_data={
            "entry_name": entry.name,
            "from_user_id": old_user_id,
            "from_email": old_email,
            "to_user_id": new_owner.id,
            "to_email": transfer_data.to_email,
            "pool_id": pool_id,
            "admin_email": current_user.email,
        },
    )

    return {
        "message": f"Entry '{entry.name}' successfully transferred from {old_email} to {transfer_data.to_email}",
        "entry_id": entry.id,
        "from_user": old_email,
        "to_user": transfer_data.to_email,
    }


@router.delete("/pools/{pool_id}/entries/{entry_id}")
def delete_entry_admin(
    pool_id: str,
    entry_id: str,
    reason: Optional[str] = None,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
):
    """Delete any entry in a pool (admin only)"""
    if not verify_admin_access(pool_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only pool owners and admins can delete entries",
        )

    entry = (
        db.query(models.Entry)
        .filter(
            models.Entry.id == entry_id,
            models.Entry.pool_id == pool_id,
        )
        .first()
    )
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found in this pool"
        )

    entry_owner = db.query(models.User).filter(models.User.id == entry.user_id).first()
    owner_email = entry_owner.email if entry_owner else "unknown"

    entry_name = entry.name
    entry_user_id = entry.user_id

    db.delete(entry)
    db.commit()

    log_admin_action(
        db=db,
        action="DELETE_ENTRY",
        admin_user_id=current_user.id,
        details=f"Admin deleted entry '{entry_name}' owned by {owner_email}"
        + (f" - Reason: {reason}" if reason else ""),
        target_entity_type="entry",
        target_entity_id=entry_id,
        additional_data={
            "entry_name": entry_name,
            "entry_owner_id": entry_user_id,
            "entry_owner_email": owner_email,
            "pool_id": pool_id,
            "admin_email": current_user.email,
            "reason": reason,
        },
    )

    return {
        "message": f"Entry '{entry_name}' owned by {owner_email} has been deleted",
        "entry_name": entry_name,
        "owner": owner_email,
    }


@router.post("/pools/{pool_id}/lock-week/{week}")
def lock_week(
    pool_id: str,
    week: int,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
):
    """Lock the current week for a pool and auto-pick for entries with no pick."""
    if not verify_admin_access(pool_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
        )

    pool = db.query(models.Pool).filter(models.Pool.id == pool_id).first()
    if not pool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Pool not found"
        )

    # Lock the pool if not already locked in the past
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if pool.lock_time is None or pool.lock_time > now:
        pool.lock_time = now

    # All alive entries in the pool
    alive_entries = (
        db.query(models.Entry)
        .filter(models.Entry.pool_id == pool_id, models.Entry.alive == True)  # noqa: E712
        .all()
    )
    alive_ids = {e.id for e in alive_entries}

    # Entries that already have a pick for this week
    existing_pick_entry_ids = {
        p.entry_id
        for p in db.query(models.Pick)
        .filter(models.Pick.entry_id.in_(alive_ids), models.Pick.week == week)
        .all()
    }

    entries_needing_pick = [
        e for e in alive_entries if e.id not in existing_pick_entry_ids
    ]

    # Popularity map: team → count of alive picks this week
    popularity: dict[str, int] = {}
    for p in (
        db.query(models.Pick)
        .filter(models.Pick.entry_id.in_(alive_ids), models.Pick.week == week)
        .all()
    ):
        popularity[p.team] = popularity.get(p.team, 0) + 1

    # Stable sort: descending popularity, then alphabetical for tie-breaking
    ranked_teams = sorted(popularity.items(), key=lambda x: (-x[1], x[0]))

    auto_picks_created = 0
    for entry in entries_needing_pick:
        # Teams already used by this entry across all weeks
        used_teams = {
            p.team
            for p in db.query(models.Pick)
            .filter(models.Pick.entry_id == entry.id)
            .all()
        }

        candidate = next(
            (team for team, _ in ranked_teams if team not in used_teams),
            None,
        )
        if candidate is None:
            # No valid team available — skip
            log_admin_action(
                db=db,
                action="AUTO_PICK_SKIPPED",
                admin_user_id=current_user.id,
                details=f"No available team for entry {entry.id} in week {week} — all popular teams already used",
                target_entity_type="entry",
                target_entity_id=entry.id,
                additional_data={"pool_id": pool_id, "week": week},
            )
            continue

        db_pick = models.Pick(
            id=str(uuid.uuid4()),
            entry_id=entry.id,
            week=week,
            team=candidate,
            locked=True,
            created_at=now,
            updated_at=now,
        )
        db.add(db_pick)
        db.flush()  # get the id before logging

        log_admin_action(
            db=db,
            action="AUTO_PICK",
            admin_user_id=current_user.id,
            details=f"Auto-picked {candidate} for entry {entry.id} in week {week}",
            target_entity_type="pick",
            target_entity_id=db_pick.id,
            additional_data={
                "pool_id": pool_id,
                "entry_id": entry.id,
                "week": week,
                "team": candidate,
                "reason": "no_pick_at_lock",
            },
        )
        auto_picks_created += 1

    db.commit()

    return {
        "message": f"Week {week} locked",
        "pool_id": pool_id,
        "auto_picks_created": auto_picks_created,
    }


@router.patch("/pools/{pool_id}/picks/{pick_id}", response_model=schemas.PickOut)
def admin_update_pick(
    pool_id: str,
    pick_id: str,
    pick_update: schemas.AdminPickUpdate,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
):
    """Admin override: change the team on any pick, locked or not."""
    if not verify_admin_access(pool_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
        )

    pick = (
        db.query(models.Pick)
        .join(models.Entry)
        .filter(models.Pick.id == pick_id, models.Entry.pool_id == pool_id)
        .first()
    )
    if not pick:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Pick not found in this pool"
        )

    # Enforce team uniqueness across other weeks for this entry
    conflict = (
        db.query(models.Pick)
        .filter(
            models.Pick.entry_id == pick.entry_id,
            models.Pick.team == pick_update.team,
            models.Pick.id != pick_id,
        )
        .first()
    )
    if conflict:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Team {pick_update.team} already used by this entry in week {conflict.week}",
        )

    old_team = pick.team
    pick.team = pick_update.team
    pick.locked = True
    pick.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
    db.refresh(pick)

    log_admin_action(
        db=db,
        action="ADMIN_PICK_EDIT",
        admin_user_id=current_user.id,
        details=f"Changed pick from {old_team} to {pick_update.team} for entry {pick.entry_id} week {pick.week}",
        target_entity_type="pick",
        target_entity_id=pick_id,
        additional_data={
            "pool_id": pool_id,
            "entry_id": pick.entry_id,
            "week": pick.week,
            "old_team": old_team,
            "new_team": pick_update.team,
            "admin_email": current_user.email,
        },
    )

    return pick
