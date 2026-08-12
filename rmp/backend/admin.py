"""
Admin endpoints for administrative operations
"""

import csv
import io
import json
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from datetime import datetime, timezone
from typing import Optional
import uuid
from pydantic import EmailStr

import models
import schemas
import deps
import auth
from audit_utils import log_admin_action
from odds_service import freeze_week_lines
from schedule import current_season_games, current_season_week
from weekly_locks import lock_pool_week
from platform_admin import is_bootstrap_super_admin, is_platform_super_admin

router = APIRouter(prefix="/admin", tags=["admin"])


def _csv_safe(value: str) -> str:
    """Prevent spreadsheet software from interpreting user data as formulas."""
    text = str(value or "")
    if text.lstrip().startswith(("=", "+", "-", "@", "\t", "\r")):
        return f"'{text}"
    return text


def verify_admin_access(pool_id: str, current_user: models.User, db: Session) -> bool:
    """Verify if user has admin access to the pool"""
    if is_platform_super_admin(current_user):
        return db.query(models.Pool.id).filter(models.Pool.id == pool_id).first() is not None
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


def require_pool_owner(pool_id: str, current_user: models.User, db: Session) -> models.Pool:
    """Return the pool when the caller owns it; delegated admins cannot grant access."""
    pool = db.query(models.Pool).filter(models.Pool.id == pool_id).first()
    if not pool:
        raise HTTPException(status_code=404, detail="Pool not found")
    if pool.owner_id != current_user.id and not is_platform_super_admin(current_user):
        raise HTTPException(status_code=403, detail="Only the league owner can manage administrators")
    return pool


def find_user_by_email(email: str, db: Session) -> models.User:
    user = (
        db.query(models.User)
        .filter(func.lower(models.User.email) == email.strip().lower())
        .first()
    )
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def is_pool_participant(db: Session, pool_id: str, user_id: str) -> bool:
    """Include owners, delegated admins, members, and users with entries."""
    return bool(
        db.query(models.Pool).filter(
            models.Pool.id == pool_id,
            models.Pool.owner_id == user_id,
        ).first()
        or db.query(models.PoolAdmin).filter(
            models.PoolAdmin.pool_id == pool_id,
            models.PoolAdmin.user_id == user_id,
        ).first()
        or db.query(models.PoolMember).filter(
            models.PoolMember.pool_id == pool_id,
            models.PoolMember.user_id == user_id,
        ).first()
        or db.query(models.Entry).filter(
            models.Entry.pool_id == pool_id,
            models.Entry.user_id == user_id,
        ).first()
    )


def require_pool_participant_by_email(
    db: Session, pool_id: str, email: str
) -> models.User:
    user = find_user_by_email(email, db)
    if not is_pool_participant(db, pool_id, user.id):
        raise HTTPException(status_code=404, detail="User not found in this league")
    return user


def require_pool_participant_by_id(
    db: Session, pool_id: str, user_id: str
) -> models.User:
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user or not is_pool_participant(db, pool_id, user.id):
        raise HTTPException(status_code=404, detail="User not found in this league")
    return user


@router.put(
    "/pools/{pool_id}/admins",
    response_model=schemas.LeagueAdminAssignmentOut,
)
def grant_pool_admin(
    pool_id: str,
    assignment: schemas.LeagueAdminAssignment,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
):
    """Grant league-specific administrator access to an existing participant."""
    pool = require_pool_owner(pool_id, current_user, db)
    user = require_pool_participant_by_email(db, pool_id, assignment.email)
    if user.id == pool.owner_id:
        raise HTTPException(status_code=400, detail="The league owner already has administrator access")

    existing = db.query(models.PoolAdmin).filter(
        models.PoolAdmin.pool_id == pool_id,
        models.PoolAdmin.user_id == user.id,
    ).first()
    if existing:
        return {"pool_id": pool_id, "user_id": user.id, "email": user.email, "is_admin": True, "changed": False}

    db.add(models.PoolAdmin(pool_id=pool_id, user_id=user.id))
    db.commit()
    log_admin_action(
        db=db,
        action="GRANT_LEAGUE_ADMIN",
        admin_user_id=current_user.id,
        details=f"Granted league administrator access to {user.email}",
        target_entity_type="user",
        target_entity_id=user.id,
        additional_data={"pool_id": pool_id, "username": user.email, "admin_email": current_user.email},
    )
    return {"pool_id": pool_id, "user_id": user.id, "email": user.email, "is_admin": True, "changed": True}


@router.delete(
    "/pools/{pool_id}/admins",
    response_model=schemas.LeagueAdminAssignmentOut,
)
def revoke_pool_admin(
    pool_id: str,
    email: str,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
):
    """Revoke delegated administrator access without changing membership."""
    pool = require_pool_owner(pool_id, current_user, db)
    user = require_pool_participant_by_email(db, pool_id, email)
    if user.id == pool.owner_id:
        raise HTTPException(status_code=400, detail="League owner access cannot be revoked")

    existing = db.query(models.PoolAdmin).filter(
        models.PoolAdmin.pool_id == pool_id,
        models.PoolAdmin.user_id == user.id,
    ).first()
    if not existing:
        return {"pool_id": pool_id, "user_id": user.id, "email": user.email, "is_admin": False, "changed": False}

    db.delete(existing)
    db.commit()
    log_admin_action(
        db=db,
        action="REVOKE_LEAGUE_ADMIN",
        admin_user_id=current_user.id,
        details=f"Revoked league administrator access from {user.email}",
        target_entity_type="user",
        target_entity_id=user.id,
        additional_data={"pool_id": pool_id, "username": user.email, "admin_email": current_user.email},
    )
    return {"pool_id": pool_id, "user_id": user.id, "email": user.email, "is_admin": False, "changed": True}


@router.put(
    "/pools/{pool_id}/owner",
    response_model=schemas.LeagueOwnershipTransferOut,
)
def transfer_pool_ownership(
    pool_id: str,
    transfer: schemas.LeagueOwnershipTransfer,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
):
    """Transfer sole league ownership and retain the previous owner as an admin."""
    pool = require_pool_owner(pool_id, current_user, db)
    new_owner = require_pool_participant_by_email(db, pool_id, transfer.email)
    if new_owner.id == pool.owner_id:
        raise HTTPException(status_code=400, detail="This user already owns the league")

    previous_owner_id = pool.owner_id
    previous_owner_email = current_user.email
    for user_id in (previous_owner_id, new_owner.id):
        existing_admin = db.query(models.PoolAdmin).filter(
            models.PoolAdmin.pool_id == pool_id,
            models.PoolAdmin.user_id == user_id,
        ).first()
        if not existing_admin:
            db.add(models.PoolAdmin(pool_id=pool_id, user_id=user_id))

    pool.owner_id = new_owner.id
    pool.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
    log_admin_action(
        db=db,
        action="TRANSFER_LEAGUE_OWNERSHIP",
        admin_user_id=current_user.id,
        details=f"Transferred league ownership from {previous_owner_email} to {new_owner.email}",
        target_entity_type="pool",
        target_entity_id=pool_id,
        additional_data={
            "pool_id": pool_id,
            "previous_owner_id": previous_owner_id,
            "previous_owner_email": previous_owner_email,
            "owner_id": new_owner.id,
            "owner_email": new_owner.email,
        },
    )
    return {
        "pool_id": pool_id,
        "previous_owner_id": previous_owner_id,
        "previous_owner_email": previous_owner_email,
        "owner_id": new_owner.id,
        "owner_email": new_owner.email,
    }


@router.get(
    "/pools/{pool_id}/users-overview",
    response_model=schemas.LeagueAdminUserOverview,
)
def pool_users_overview(
    pool_id: str,
    week: Optional[int] = None,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
):
    """Return commissioner-level participation totals without exposing picks."""
    if not verify_admin_access(pool_id, current_user, db):
        raise HTTPException(status_code=403, detail="Admin access required")
    pool = db.query(models.Pool).filter(models.Pool.id == pool_id).first()
    if not pool:
        raise HTTPException(status_code=404, detail="Pool not found")

    selected_week = week if week is not None else current_season_week(db)
    if selected_week < 1 or selected_week > 18:
        raise HTTPException(status_code=400, detail="Week must be between 1 and 18")

    entries = db.query(models.Entry).filter(models.Entry.pool_id == pool_id).all()
    member_ids = {
        user_id for (user_id,) in db.query(models.PoolMember.user_id)
        .filter(models.PoolMember.pool_id == pool_id).all()
    }
    member_ids.update(entry.user_id for entry in entries)
    admin_ids = {
        user_id for (user_id,) in db.query(models.PoolAdmin.user_id)
        .filter(models.PoolAdmin.pool_id == pool_id).all()
    }
    member_ids.update(admin_ids)
    if pool.owner_id:
        member_ids.add(pool.owner_id)

    users = (
        db.query(models.User)
        .filter(models.User.id.in_(member_ids or [""]))
        .order_by(models.User.email)
        .all()
    )
    entries_by_user = {}
    alive_entry_ids = set()
    for entry in entries:
        entries_by_user.setdefault(entry.user_id, []).append(entry)
        if entry.alive:
            alive_entry_ids.add(entry.id)
    picked_entry_ids = {
        entry_id for (entry_id,) in db.query(models.Pick.entry_id)
        .filter(
            models.Pick.entry_id.in_(alive_entry_ids or [""]),
            models.Pick.week == selected_week,
        )
        .distinct()
        .all()
    }

    result = []
    for user in users:
        user_entries = entries_by_user.get(user.id, [])
        surviving = [entry for entry in user_entries if entry.alive]
        picked_count = sum(entry.id in picked_entry_ids for entry in surviving)
        if user.id == pool.owner_id:
            admin_role = "Owner"
        elif user.id in admin_ids:
            admin_role = "League admin"
        else:
            admin_role = "Member"
        result.append({
            "id": user.id,
            "email": user.email,
            "total_entries": len(user_entries),
            "surviving_entries": len(surviving),
            "picked_entries": picked_count,
            "has_current_week_pick": picked_count > 0,
            "all_surviving_entries_picked": bool(surviving) and picked_count == len(surviving),
            "is_admin": admin_role != "Member",
            "admin_role": admin_role,
        })
    return {
        "pool_id": pool_id,
        "current_week": selected_week,
        "total_users": len(result),
        "users": result,
    }


@router.patch(
    "/pools/{pool_id}/users/{user_id}/email",
    response_model=schemas.UserOut,
)
def update_pool_user_email(
    pool_id: str,
    user_id: str,
    email: EmailStr,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
):
    """Change a participant's login email within a league admin's scope."""
    if not verify_admin_access(pool_id, current_user, db):
        raise HTTPException(status_code=403, detail="Admin access required")
    user = require_pool_participant_by_id(db, pool_id, user_id)
    if is_bootstrap_super_admin(user):
        raise HTTPException(status_code=400, detail="The initial super admin email cannot be changed")
    normalized_email = str(email).strip().lower()
    duplicate = db.query(models.User).filter(
        func.lower(models.User.email) == normalized_email,
        models.User.id != user.id,
    ).first()
    if duplicate:
        raise HTTPException(status_code=409, detail="An account with that email address already exists")

    old_email = user.email
    user.email = normalized_email
    db.commit()
    db.refresh(user)
    log_admin_action(
        db=db,
        action="UPDATE_USER_EMAIL",
        admin_user_id=current_user.id,
        details=f"Updated user email from {old_email} to {normalized_email}",
        target_entity_type="user",
        target_entity_id=user.id,
        additional_data={
            "pool_id": pool_id,
            "old_email": old_email,
            "new_email": normalized_email,
            "updated_by": current_user.email,
        },
    )
    return user


@router.get(
    "/pools/{pool_id}/auto-picks",
    response_model=list[schemas.LeagueAutoPickOut],
)
def pool_auto_picks(
    pool_id: str,
    week: Optional[int] = None,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
):
    """List system-generated picks for users in a managed league."""
    if not verify_admin_access(pool_id, current_user, db):
        raise HTTPException(status_code=403, detail="Admin access required")
    if week is not None and (week < 1 or week > 18):
        raise HTTPException(status_code=400, detail="Week must be between 1 and 18")

    entries = db.query(models.Entry).filter(models.Entry.pool_id == pool_id).all()
    entries_by_id = {entry.id: entry for entry in entries}
    user_ids = {entry.user_id for entry in entries if entry.user_id}
    users_by_id = {
        user.id: user for user in db.query(models.User).filter(models.User.id.in_(user_ids or [""])).all()
    }
    result = []
    logs = db.query(models.AuditLog).filter(
        models.AuditLog.action == "ADMIN_AUTO_PICK"
    ).order_by(models.AuditLog.created_at.desc()).all()
    for log in logs:
        try:
            payload = json.loads(log.details or "{}")
        except (TypeError, json.JSONDecodeError):
            continue
        data = payload.get("additional_data") or {}
        if data.get("pool_id") != pool_id:
            continue
        log_week = data.get("week")
        if not isinstance(log_week, int) or (week is not None and log_week != week):
            continue
        entry_id = data.get("entry_id") or ""
        entry = entries_by_id.get(entry_id)
        user_id = data.get("user_id") or (entry.user_id if entry else None)
        user = users_by_id.get(user_id)
        result.append({
            "audit_id": log.id,
            "week": log_week,
            "user_id": user_id,
            "user_email": data.get("user_email") or (user.email if user else "Unknown user"),
            "entry_id": entry_id,
            "entry_name": data.get("entry_name") or (entry.name if entry else "Unknown entry"),
            "team": data.get("team") or "Unknown",
            "created_at": log.created_at,
        })
    return result


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

    new_owner = require_pool_participant_by_email(
        db, pool_id, transfer_data.to_email
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
    membership = db.query(models.PoolMember).filter(
        models.PoolMember.pool_id == pool_id,
        models.PoolMember.user_id == new_owner.id,
    ).first()
    if not membership:
        db.add(models.PoolMember(
            pool_id=pool_id,
            user_id=new_owner.id,
            joined_at=datetime.now(timezone.utc).replace(tzinfo=None),
        ))
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


@router.get("/pools/{pool_id}/entries")
def search_entries_admin(
    pool_id: str,
    username: Optional[str] = None,
    entry_name: Optional[str] = None,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
):
    """Search pool entries with owner information for commissioner workflows."""
    if not verify_admin_access(pool_id, current_user, db):
        raise HTTPException(status_code=403, detail="Admin access required")

    query = (
        db.query(models.Entry, models.User)
        .join(models.User, models.User.id == models.Entry.user_id)
        .filter(models.Entry.pool_id == pool_id)
    )
    if username:
        query = query.filter(models.User.email.ilike(f"%{username.strip()}%"))
    if entry_name:
        query = query.filter(models.Entry.name.ilike(f"%{entry_name.strip()}%"))

    rows = query.order_by(models.User.email, models.Entry.name).limit(200).all()
    locked_users = {
        item.user_id
        for item in db.query(models.PoolUserLock).filter(models.PoolUserLock.pool_id == pool_id).all()
    }
    return [
        {
            "id": entry.id,
            "name": entry.name,
            "user_id": user.id,
            "owner_email": user.email,
            "locked": user.id in locked_users,
        }
        for entry, user in rows
    ]


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

    db.query(models.Pick).filter(models.Pick.entry_id == entry_id).delete(
        synchronize_session=False
    )
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

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if pool.lock_time is None or pool.lock_time > now:
        pool.lock_time = now
    auto_picks_created = lock_pool_week(
        db, pool, week, current_user.id, now,
        games_provider=current_season_games,
        line_freezer=freeze_week_lines,
    )

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


@router.patch("/pools/{pool_id}/entries/{entry_id}/weeks/{week}/pick", response_model=schemas.PickOut)
def correct_entry_pick(
    pool_id: str,
    entry_id: str,
    week: int,
    correction: schemas.AdminPickCorrection,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
):
    """Correct the existing pick for an entry/week without requiring its pick ID."""
    if not verify_admin_access(pool_id, current_user, db):
        raise HTTPException(status_code=403, detail="Admin access required")
    if week not in range(1, 19):
        raise HTTPException(status_code=400, detail="Week must be between 1 and 18")

    entry = db.query(models.Entry).filter(
        models.Entry.id == entry_id,
        models.Entry.pool_id == pool_id,
    ).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found in this pool")
    pick = db.query(models.Pick).filter(
        models.Pick.entry_id == entry_id,
        models.Pick.week == week,
    ).first()
    if not pick:
        raise HTTPException(status_code=404, detail="No pick exists for this entry and week")

    conflict = db.query(models.Pick).filter(
        models.Pick.entry_id == entry_id,
        models.Pick.team == correction.team.upper(),
        models.Pick.id != pick.id,
    ).first()
    if conflict:
        raise HTTPException(status_code=400, detail=f"Team {correction.team.upper()} already used in week {conflict.week}")

    old_team = pick.team
    pick.team = correction.team.upper()
    pick.locked = True
    pick.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
    db.refresh(pick)
    log_admin_action(
        db=db,
        action="ADMIN_PICK_EDIT",
        admin_user_id=current_user.id,
        details=f"Changed pick from {old_team} to {pick.team} for entry {entry.name} week {week}",
        target_entity_type="pick",
        target_entity_id=pick.id,
        additional_data={
            "pool_id": pool_id,
            "entry_id": entry_id,
            "entry_name": entry.name,
            "week": week,
            "old_team": old_team,
            "new_team": pick.team,
            "reason": correction.reason,
            "admin_email": current_user.email,
        },
    )
    return pick


# ---------------------------------------------------------------------------
# Pool user lock helpers and endpoints
# ---------------------------------------------------------------------------


def is_user_locked_in_pool(db: Session, pool_id: str, user_id: str) -> bool:
    """Return True if the user has an active lock record for this pool."""
    return (
        db.query(models.PoolUserLock)
        .filter(
            models.PoolUserLock.pool_id == pool_id,
            models.PoolUserLock.user_id == user_id,
        )
        .first()
    ) is not None


@router.get("/pools/{pool_id}/user-lock")
def get_user_lock_by_email(
    pool_id: str,
    email: str,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
):
    if not verify_admin_access(pool_id, current_user, db):
        raise HTTPException(status_code=403, detail="Admin access required")
    user = require_pool_participant_by_email(db, pool_id, email)
    lock = db.query(models.PoolUserLock).filter(
        models.PoolUserLock.pool_id == pool_id,
        models.PoolUserLock.user_id == user.id,
    ).first()
    return {
        "user_id": user.id,
        "email": user.email,
        "locked": lock is not None,
        "reason": lock.reason if lock else None,
    }


@router.post("/pools/{pool_id}/users/password-reset")
def send_pool_user_password_reset(
    pool_id: str,
    request: schemas.ForgotPasswordRequest,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
):
    """Send a reset link only for a participant in the admin's selected league."""
    if not verify_admin_access(pool_id, current_user, db):
        raise HTTPException(status_code=403, detail="Admin access required")
    require_pool_participant_by_email(db, pool_id, request.email)
    return auth.forgot_password(request, db)


@router.put("/pools/{pool_id}/user-lock")
def set_user_lock_by_email(
    pool_id: str,
    request: schemas.PoolUserLockByEmail,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
):
    if not verify_admin_access(pool_id, current_user, db):
        raise HTTPException(status_code=403, detail="Admin access required")
    user = require_pool_participant_by_email(db, pool_id, request.email)
    lock = db.query(models.PoolUserLock).filter(
        models.PoolUserLock.pool_id == pool_id,
        models.PoolUserLock.user_id == user.id,
    ).first()
    if request.locked and not lock:
        lock = models.PoolUserLock(
            pool_id=pool_id,
            user_id=user.id,
            locked_at=datetime.now(timezone.utc).replace(tzinfo=None),
            reason=request.reason,
        )
        db.add(lock)
    elif request.locked and lock:
        lock.reason = request.reason
    elif not request.locked and lock:
        db.delete(lock)
    db.commit()
    log_admin_action(
        db=db,
        action="LOCK_USER_IN_POOL" if request.locked else "UNLOCK_USER_IN_POOL",
        admin_user_id=current_user.id,
        details=f"{'Locked' if request.locked else 'Unlocked'} user {user.email} in pool {pool_id}",
        target_entity_type="user",
        target_entity_id=user.id,
        additional_data={"pool_id": pool_id, "reason": request.reason, "admin_email": current_user.email},
    )
    return {"user_id": user.id, "email": user.email, "locked": request.locked, "reason": request.reason if request.locked else None}


@router.post(
    "/pools/{pool_id}/users/{user_id}/lock",
    response_model=schemas.PoolUserLockOut,
)
def lock_user_in_pool(
    pool_id: str,
    user_id: str,
    lock_data: schemas.PoolUserLockCreate,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
):
    """Lock a user within a specific pool (admin only). The user can still log in
    and access other pools — only this pool's entries and picks are blocked."""
    if not verify_admin_access(pool_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
        )

    # Check pool exists
    pool = db.query(models.Pool).filter(models.Pool.id == pool_id).first()
    if not pool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Pool not found"
        )

    target_user = require_pool_participant_by_id(db, pool_id, user_id)

    # Check not already locked
    if is_user_locked_in_pool(db, pool_id, user_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User is already locked in this pool",
        )

    lock = models.PoolUserLock(
        pool_id=pool_id,
        user_id=user_id,
        locked_at=datetime.now(timezone.utc).replace(tzinfo=None),
        reason=lock_data.reason,
    )
    db.add(lock)
    db.commit()
    db.refresh(lock)

    log_admin_action(
        db=db,
        action="LOCK_USER_IN_POOL",
        admin_user_id=current_user.id,
        details=f"Locked user {target_user.email} in pool {pool_id}",
        target_entity_type="user",
        target_entity_id=user_id,
        additional_data={"pool_id": pool_id, "reason": lock_data.reason},
    )

    return lock


@router.delete("/pools/{pool_id}/users/{user_id}/lock")
def unlock_user_in_pool(
    pool_id: str,
    user_id: str,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
):
    """Remove a pool-scoped user lock (admin only)."""
    if not verify_admin_access(pool_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
        )

    lock = (
        db.query(models.PoolUserLock)
        .filter(
            models.PoolUserLock.pool_id == pool_id,
            models.PoolUserLock.user_id == user_id,
        )
        .first()
    )
    if not lock:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User is not locked in this pool",
        )

    db.delete(lock)
    db.commit()

    log_admin_action(
        db=db,
        action="UNLOCK_USER_IN_POOL",
        admin_user_id=current_user.id,
        details=f"Unlocked user {user_id} in pool {pool_id}",
        target_entity_type="user",
        target_entity_id=user_id,
        additional_data={"pool_id": pool_id},
    )

    return {"message": f"User {user_id} unlocked in pool {pool_id}"}


@router.get("/pools/{pool_id}/export/entries.csv")
def export_entries_csv(
    pool_id: str,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
):
    """Download a CSV of all user emails and entry names for a pool (admin only)."""
    if not verify_admin_access(pool_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
        )

    rows = (
        db.query(models.User.email, models.Entry.name)
        .join(models.Entry, models.Entry.user_id == models.User.id)
        .filter(models.Entry.pool_id == pool_id)
        .order_by(models.User.email, models.Entry.name)
        .all()
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["email", "entry_name"])
    for email, entry_name in rows:
        writer.writerow([_csv_safe(email), _csv_safe(entry_name)])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=entries.csv"},
    )
