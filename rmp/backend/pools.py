from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from typing import List, Optional
import base64
import hashlib
import models
import schemas
import deps
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import uuid
import logging
from audit_utils import create_audit_log, log_create_operation, log_update_operation, log_delete_operation
from auth import SECRET_KEY, get_password_hash, verify_password
from pool_access import is_pool_participant
from schedule import current_season_games, current_season_week
from weekly_locks import pool_week_lock_time
from cryptography.fernet import Fernet, InvalidToken
from app_logging import log_event
from platform_admin import is_platform_super_admin
from email_service import send_pool_invitation_email

logger = logging.getLogger("runmypool.pools")

router = APIRouter(prefix="/pools", tags=["pools"])

MIN_JOIN_PASSWORD_LENGTH = 6
MAX_POOL_NAME_LENGTH = 255
POOL_INVITE_EMAIL_LIMIT = 20


def _password_cipher() -> Fernet:
    key = base64.urlsafe_b64encode(hashlib.sha256(SECRET_KEY.encode("utf-8")).digest())
    return Fernet(key)


def _encrypt_join_password(password: str) -> str:
    return _password_cipher().encrypt(password.encode("utf-8")).decode("ascii")


def _decrypt_join_password(encrypted_password: str) -> str:
    try:
        return _password_cipher().decrypt(encrypted_password.encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError, UnicodeDecodeError):
        raise HTTPException(
            status_code=409,
            detail="The stored league password cannot be displayed. Set a new password.",
        )


def _normalize_pool_name(name: str) -> str:
    """Store a clean display name and reject names with no visible characters."""
    normalized = (name or "").strip()
    if not normalized:
        raise HTTPException(status_code=400, detail="League name is required")
    if len(normalized) > MAX_POOL_NAME_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"League name must be {MAX_POOL_NAME_LENGTH} characters or fewer",
        )
    return normalized


def _pool_name_taken(db: Session, name: str, exclude_pool_id: str = None) -> bool:
    query = db.query(models.Pool.id).filter(
        func.lower(func.trim(models.Pool.name)) == name.casefold()
    )
    if exclude_pool_id is not None:
        query = query.filter(models.Pool.id != exclude_pool_id)
    return query.first() is not None


def _suggest_pool_names(db: Session, requested_name: str, limit: int = 3) -> List[str]:
    """Return deterministic, immediately available alternatives."""
    def with_suffix(suffix: str) -> str:
        return f"{requested_name[:MAX_POOL_NAME_LENGTH - len(suffix)]}{suffix}"

    candidates = [
        with_suffix(" 2026"),
        with_suffix(" Survivor"),
        with_suffix(" League"),
    ]
    candidates.extend(with_suffix(f" {number}") for number in range(2, 100))
    suggestions = []
    for candidate in candidates:
        if not _pool_name_taken(db, candidate):
            suggestions.append(candidate)
        if len(suggestions) == limit:
            break
    return suggestions


def _raise_name_conflict(db: Session, requested_name: str) -> None:
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={
            "code": "league_name_taken",
            "message": "That league name is already in use. Choose a unique name.",
            "suggestions": _suggest_pool_names(db, requested_name),
        },
    )


def _validate_join_password(password: str) -> str:
    password = (password or "").strip()
    if len(password) < MIN_JOIN_PASSWORD_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Private pool passwords must be at least {MIN_JOIN_PASSWORD_LENGTH} characters",
        )
    if len(password.encode("utf-8")) > 72:
        raise HTTPException(
            status_code=400,
            detail="Private pool passwords must be 72 bytes or fewer",
        )
    return password


def _has_admin_access(db: Session, pool: models.Pool, user_id: str) -> bool:
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user and is_platform_super_admin(user):
        return True
    if pool.owner_id == user_id:
        return True
    return db.query(models.PoolAdmin).filter(
        models.PoolAdmin.pool_id == pool.id,
        models.PoolAdmin.user_id == user_id,
    ).first() is not None


def _parse_lock_time(time_str: str):
    """Parse a lock_time string in ISO or 'YYYY-MM-DD HH:MM:SS' format.

    Handles ISO 8601 (with T separator and optional Z), space-separated,
    and two- or three-component time parts. Returns a naive datetime.
    """
    time_str = time_str.strip()
    if "T" in time_str:
        time_str = time_str.replace("Z", "")
        date_part, time_part = time_str.split("T")
        if "." in time_part:
            time_part = time_part.split(".")[0]
        time_str = f"{date_part} {time_part}"
    if len(time_str.split(" ")[1].split(":")) == 2:
        time_str += ":00"
    return datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")


def _parse_time_of_day(value: str) -> time:
    try:
        return time.fromisoformat(value)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Lock time must use HH:MM format")


def _validate_timezone(value: str) -> str:
    try:
        ZoneInfo(value)
    except (ZoneInfoNotFoundError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid lock timezone")
    return value


@router.post("/create", response_model=schemas.PoolOut)
def create_pool(
    pool: schemas.PoolCreate,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
):
    """Create a new pool with the current user as the owner/admin."""
    try:
        pool_name = _normalize_pool_name(pool.name)
        if _pool_name_taken(db, pool_name):
            _raise_name_conflict(db, pool_name)

        # Parse lock_time if provided
        lock_time = None
        if pool.lock_time:
            try:
                lock_time = _parse_lock_time(pool.lock_time)
            except (ValueError, TypeError) as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid lock_time format. Use YYYY-MM-DD HH:MM:SS or ISO format: {str(e)}",
                )

        join_password_hash = None
        join_password_encrypted = None
        if pool.is_private:
            validated_password = _validate_join_password(pool.join_password)
            join_password_hash = get_password_hash(validated_password)
            join_password_encrypted = _encrypt_join_password(validated_password)

        recurring_time = _parse_time_of_day(pool.lock_time_of_day) if pool.lock_time_of_day else None
        recurring_timezone = _validate_timezone(pool.lock_timezone) if pool.lock_timezone else None
        if pool.lock_day_of_week is not None and pool.lock_day_of_week not in range(7):
            raise HTTPException(status_code=400, detail="Lock day must be between 0 and 6")
        join_lock_time = _parse_lock_time(pool.join_lock_time) if pool.join_lock_time else None

        db_pool = models.Pool(
            id=str(uuid.uuid4()),
            name=pool_name,
            description=pool.description,
            pool_type=pool.pool_type,
            pickem_games_per_week=(
                pool.pickem_games_per_week if pool.pool_type == "pickem" else None
            ),
            lock_time=lock_time,
            lock_day_of_week=pool.lock_day_of_week,
            lock_time_of_day=recurring_time,
            lock_timezone=recurring_timezone,
            join_lock_time=join_lock_time,
            is_private=pool.is_private,
            join_password_hash=join_password_hash,
            join_password_encrypted=join_password_encrypted,
            owner_id=current_user.id,
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
            updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )

        db.add(db_pool)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            _raise_name_conflict(db, pool_name)
        db.refresh(db_pool)

        # Add the pool creator as a pool admin
        pool_admin = models.PoolAdmin(pool_id=db_pool.id, user_id=current_user.id)
        pool_member = models.PoolMember(
            pool_id=db_pool.id,
            user_id=current_user.id,
            joined_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        db.add_all([pool_admin, pool_member])
        db.commit()

        # Log pool creation
        log_create_operation(
            db=db,
            entity_type="pool",
            entity_id=db_pool.id,
            user_id=current_user.id,
            entity_data={
                "name": pool_name,
                "description": pool.description,
                "pool_type": pool.pool_type,
                "is_private": pool.is_private,
                "owner_email": current_user.email,
            },
        )
        log_event(
            logger, logging.INFO, "pool_created",
            pool_id=db_pool.id, user_id=current_user.id, is_private=db_pool.is_private,
        )

        return db_pool
    except HTTPException:
        raise
    except Exception:
        logger.exception("pool_creation_failed", extra={"event": "pool_creation_failed", "user_id": current_user.id})
        raise HTTPException(status_code=500, detail="Failed to create pool")


@router.get("/my-pools", response_model=List[schemas.PoolOut])
def get_my_pools(
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
):
    """Get all pools where the current user is the owner or a member."""
    try:
        return (
            db.query(models.Pool)
            .outerjoin(models.PoolMember, models.PoolMember.pool_id == models.Pool.id)
            .filter(
                (models.Pool.owner_id == current_user.id)
                | (models.PoolMember.user_id == current_user.id)
            )
            .distinct()
            .all()
        )
    except Exception:
        logger.exception("my_pools_query_failed", extra={"event": "my_pools_query_failed", "user_id": current_user.id})
        raise HTTPException(status_code=500, detail="Failed to retrieve pools")


@router.get("/{pool_id}/activity-summary")
def get_pool_activity_summary(
    pool_id: str,
    week: Optional[int] = Query(default=None, ge=1, le=18),
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
):
    """Return the signed-in user's participation totals for a pool dashboard."""
    pool = db.query(models.Pool).filter(models.Pool.id == pool_id).first()
    if not pool:
        raise HTTPException(status_code=404, detail="Pool not found")
    if not is_platform_super_admin(current_user) and not is_pool_participant(
        db, pool_id, current_user.id
    ):
        raise HTTPException(status_code=403, detail="League membership required")

    selected_week = week if week is not None else current_season_week(db)
    user_entries = db.query(models.Entry).filter(
        models.Entry.pool_id == pool_id,
        models.Entry.user_id == current_user.id,
    )
    total_entries = user_entries.count()
    entries_remaining = user_entries.filter(models.Entry.alive.is_(True)).count()
    selection_counter = (
        func.count(models.Pick.id)
        if pool.pool_type == "pickem"
        else func.count(func.distinct(models.Pick.entry_id))
    )
    week_selections = (
        db.query(selection_counter)
        .join(models.Entry, models.Entry.id == models.Pick.entry_id)
        .filter(
            models.Entry.pool_id == pool_id,
            models.Entry.user_id == current_user.id,
            models.Entry.alive.is_(True),
            models.Pick.week == selected_week,
            models.Pick.team.isnot(None),
            models.Pick.team != "",
        )
        .scalar()
        or 0
    )
    scheduled_games = (
        min(
            len(current_season_games(db, selected_week)),
            pool.pickem_games_per_week or 16,
        )
        if pool.pool_type == "pickem"
        else 1
    )
    return {
        "pool_type": pool.pool_type,
        "entries_remaining": entries_remaining,
        "total_entries": total_entries,
        "week": selected_week,
        "week_selections": week_selections,
        "week_selection_total": entries_remaining * scheduled_games,
    }


@router.get("/", response_model=List[schemas.PoolOut])
def list_pools(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
):
    """List all leagues for authenticated discovery.

    Private league metadata is visible here, but joining and all participant
    data remain protected by the league password and membership checks.
    """
    return db.query(models.Pool).offset(skip).limit(limit).all()


@router.get("/invite/{pool_id}", response_model=schemas.PoolInviteOut)
def get_pool_invite(
    pool_id: str,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
):
    """Resolve a shared pool UUID without adding private pools to discovery."""
    pool = db.query(models.Pool).filter(models.Pool.id == pool_id).first()
    if not pool:
        raise HTTPException(status_code=404, detail="Pool invitation not found")
    return pool


@router.post("/{pool_id}/invite-email", response_model=schemas.PoolEmailInviteOut)
def email_pool_invitation(
    pool_id: str,
    invitation: schemas.PoolEmailInviteRequest,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
):
    """Allow a pool administrator to send a bounded, password-free SES invitation."""
    pool = db.query(models.Pool).filter(models.Pool.id == pool_id).first()
    if not pool:
        raise HTTPException(status_code=404, detail="Pool not found")
    if not _has_admin_access(db, pool, current_user.id):
        raise HTTPException(status_code=403, detail="Only pool admins can send invitations")

    window_start = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=1)
    recent_sends = db.query(models.AuditLog).filter(
        models.AuditLog.user_id == current_user.id,
        models.AuditLog.action == "POOL_INVITE_EMAIL_REQUESTED",
        models.AuditLog.created_at >= window_start,
    ).count()
    if recent_sends >= POOL_INVITE_EMAIL_LIMIT:
        raise HTTPException(status_code=429, detail="Invitation email limit reached. Try again later.")

    create_audit_log(
        db=db,
        action="POOL_INVITE_EMAIL_REQUESTED",
        details=f"Requested a pool invitation email for pool {pool.id}",
        user_id=current_user.id,
        entity_type="pool",
        entity_id=pool.id,
    )
    try:
        send_pool_invitation_email(str(invitation.email), pool.id, pool.name, pool.is_private)
    except Exception as exc:
        logger.exception(
            "pool_invitation_email_failed",
            extra={"event": "pool_invitation_email_failed", "pool_id": pool.id, "user_id": current_user.id},
        )
        raise HTTPException(status_code=502, detail="Unable to send the invitation email") from exc
    log_event(logger, logging.INFO, "pool_invitation_email_sent", pool_id=pool.id, user_id=current_user.id)
    return {"message": "Invitation email sent"}


@router.get("/{pool_id}", response_model=schemas.PoolOut)
def get_pool(
    pool_id: str,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
):
    """Get a specific pool by ID."""
    try:
        pool = db.query(models.Pool).filter(models.Pool.id == pool_id).first()

        if not pool:
            raise HTTPException(status_code=404, detail="Pool not found")

        if not is_platform_super_admin(current_user) and not is_pool_participant(db, pool_id, current_user.id):
            raise HTTPException(status_code=403, detail="League membership required")

        return pool
    except HTTPException:
        raise
    except Exception as e:
        print(f"Get pool error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve pool")


@router.get("/{pool_id}/lock-status")
def get_pool_lock_status(
    pool_id: str,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
):
    pool = db.query(models.Pool).filter(models.Pool.id == pool_id).first()
    if not pool:
        raise HTTPException(status_code=404, detail="Pool not found")
    if not is_platform_super_admin(current_user) and not is_pool_participant(db, pool_id, current_user.id):
        raise HTTPException(status_code=403, detail="League membership required")
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    weeks = {}
    for week in range(1, 19):
        deadline = pool_week_lock_time(pool, current_season_games(db, week))
        weeks[str(week)] = {
            "locked": bool(deadline and deadline <= now),
            "deadline": f"{deadline.isoformat()}Z" if deadline else None,
        }
    return {"weeks": weeks}


@router.patch("/{pool_id}", response_model=schemas.PoolOut)
def update_pool(
    pool_id: str,
    pool_update: schemas.PoolUpdate,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
):
    """Update a pool (only by the pool owner)."""
    try:
        pool = db.query(models.Pool).filter(models.Pool.id == pool_id).first()

        if not pool:
            raise HTTPException(status_code=404, detail="Pool not found")

        if not _has_admin_access(db, pool, current_user.id):
            raise HTTPException(
                status_code=403, detail="Only pool admins can update the pool"
            )

        # Update fields if provided
        if pool_update.name is not None:
            pool_name = _normalize_pool_name(pool_update.name)
            if _pool_name_taken(db, pool_name, exclude_pool_id=pool.id):
                _raise_name_conflict(db, pool_name)
            pool.name = pool_name
        if pool_update.description is not None:
            pool.description = pool_update.description
        if pool_update.lock_time is not None:
            try:
                pool.lock_time = _parse_lock_time(pool_update.lock_time)
            except (ValueError, TypeError) as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid lock_time format. Use YYYY-MM-DD HH:MM:SS or ISO format: {str(e)}",
                )
        if pool_update.lock_day_of_week is not None:
            if pool_update.lock_day_of_week not in range(7):
                raise HTTPException(status_code=400, detail="Lock day must be between 0 and 6")
            pool.lock_day_of_week = pool_update.lock_day_of_week
        if pool_update.lock_time_of_day is not None:
            pool.lock_time_of_day = _parse_time_of_day(pool_update.lock_time_of_day)
        if pool_update.lock_timezone is not None:
            pool.lock_timezone = _validate_timezone(pool_update.lock_timezone)
        if pool_update.join_lock_time is not None:
            pool.join_lock_time = _parse_lock_time(pool_update.join_lock_time)
        target_is_private = (
            pool_update.is_private
            if pool_update.is_private is not None
            else pool.is_private
        )
        if target_is_private:
            if pool_update.join_password is not None:
                validated_password = _validate_join_password(pool_update.join_password)
                pool.join_password_hash = get_password_hash(validated_password)
                pool.join_password_encrypted = _encrypt_join_password(validated_password)
            elif pool_update.is_private is True and not pool.join_password_hash:
                raise HTTPException(
                    status_code=400,
                    detail="Set a join password before making this pool private",
                )
        else:
            pool.join_password_hash = None
            pool.join_password_encrypted = None
        pool.is_private = target_is_private

        pool.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)

        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            _raise_name_conflict(db, pool.name)
        db.refresh(pool)

        log_update_operation(
            db=db,
            entity_type="pool_access",
            entity_id=pool.id,
            user_id=current_user.id,
            changes={
                "pool_id": pool.id,
                "is_private": pool.is_private,
                "join_password_changed": pool_update.join_password is not None,
                "username": current_user.email,
            },
        )

        return pool
    except HTTPException:
        raise
    except Exception as e:
        print(f"Update pool error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update pool")


@router.post("/{pool_id}/join")
def join_pool(
    pool_id: str,
    join: schemas.PoolJoin,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
):
    """Join a public pool, or a private pool with its join password."""
    pool = db.query(models.Pool).filter(models.Pool.id == pool_id).first()
    if not pool:
        raise HTTPException(status_code=404, detail="Pool not found")

    existing = db.query(models.PoolMember).filter(
        models.PoolMember.pool_id == pool_id,
        models.PoolMember.user_id == current_user.id,
    ).first()
    if existing or pool.owner_id == current_user.id:
        return {"message": "Already joined", "pool_id": pool_id}

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if pool.join_lock_time is not None and pool.join_lock_time <= now:
        raise HTTPException(
            status_code=423,
            detail="League registration is closed. Contact the league admin.",
        )

    if pool.is_private:
        if not pool.join_password_hash:
            raise HTTPException(
                status_code=409,
                detail="This private pool is not accepting members until its admin sets a password",
            )
        supplied_password = (join.password or "").strip()
        if not supplied_password or not verify_password(supplied_password, pool.join_password_hash):
            raise HTTPException(status_code=403, detail="Invalid pool password")

    db.add(models.PoolMember(
        pool_id=pool_id,
        user_id=current_user.id,
        joined_at=datetime.now(timezone.utc).replace(tzinfo=None),
    ))
    db.commit()

    log_create_operation(
        db=db,
        entity_type="pool_membership",
        entity_id=f"{pool_id}:{current_user.id}",
        user_id=current_user.id,
        entity_data={
            "pool_id": pool_id,
            "pool_name": pool.name,
            "username": current_user.email,
        },
    )
    log_event(
        logger,
        logging.INFO,
        "pool_joined",
        pool_id=pool_id,
        user_id=current_user.id,
        is_private=pool.is_private,
    )
    return {"message": "Pool joined successfully", "pool_id": pool_id}


@router.get("/{pool_id}/join-password")
def get_pool_join_password(
    pool_id: str,
    response: Response,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
):
    """Reveal a private league password only to that league's administrators."""
    pool = db.query(models.Pool).filter(models.Pool.id == pool_id).first()
    if not pool:
        raise HTTPException(status_code=404, detail="Pool not found")
    if not _has_admin_access(db, pool, current_user.id):
        raise HTTPException(status_code=403, detail="Only league admins can view the password")
    if not pool.is_private:
        raise HTTPException(status_code=400, detail="Public leagues do not have a join password")
    response.headers["Cache-Control"] = "no-store"
    if not pool.join_password_encrypted:
        return {"available": False, "password": None}
    return {
        "available": True,
        "password": _decrypt_join_password(pool.join_password_encrypted),
    }


@router.delete("/{pool_id}")
def delete_pool(
    pool_id: str,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
):
    """Delete a pool (only by the pool owner)."""
    try:
        pool = db.query(models.Pool).filter(models.Pool.id == pool_id).first()

        if not pool:
            raise HTTPException(status_code=404, detail="Pool not found")

        if pool.owner_id != current_user.id and not is_platform_super_admin(current_user):
            raise HTTPException(
                status_code=403, detail="Only pool owner can delete the pool"
            )

        # TODO: Check if pool has entries before deletion
        # For now, allow deletion

        db.delete(pool)
        db.commit()

        return {"message": "Pool deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Delete pool error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete pool")


@router.get("/{pool_id}/is-admin")
def check_pool_admin(
    pool_id: str,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
):
    """Check if the current user is an admin of the specified pool."""
    try:
        # Check if user is pool owner
        pool = db.query(models.Pool).filter(models.Pool.id == pool_id).first()
        if not pool:
            raise HTTPException(status_code=404, detail="Pool not found")

        is_owner = pool.owner_id == current_user.id

        # Check if user is in pool_admins table
        pool_admin = (
            db.query(models.PoolAdmin)
            .filter(
                models.PoolAdmin.pool_id == pool_id,
                models.PoolAdmin.user_id == current_user.id,
            )
            .first()
        )

        is_admin = pool_admin is not None

        platform_access = is_platform_super_admin(current_user)
        return {
            "pool_id": pool_id,
            "is_owner": is_owner,
            "is_admin": is_admin,
            "has_admin_access": is_owner or is_admin or platform_access,
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Check pool admin error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to check admin status")
