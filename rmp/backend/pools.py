from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import models
import schemas
import deps
from datetime import datetime, timezone
import uuid
from audit_utils import log_create_operation, log_update_operation, log_delete_operation
from auth import get_password_hash, verify_password

router = APIRouter(prefix="/pools", tags=["pools"])

MIN_JOIN_PASSWORD_LENGTH = 6


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


@router.post("/create", response_model=schemas.PoolOut)
def create_pool(
    pool: schemas.PoolCreate,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
):
    """Create a new pool with the current user as the owner/admin."""
    try:
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
        if pool.is_private:
            join_password_hash = get_password_hash(
                _validate_join_password(pool.join_password)
            )

        db_pool = models.Pool(
            id=str(uuid.uuid4()),
            name=pool.name,
            description=pool.description,
            lock_time=lock_time,
            is_private=pool.is_private,
            join_password_hash=join_password_hash,
            owner_id=current_user.id,
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
            updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )

        db.add(db_pool)
        db.commit()
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
                "name": pool.name,
                "description": pool.description,
                "is_private": pool.is_private,
                "owner_email": current_user.email,
            },
        )

        return db_pool
    except HTTPException:
        raise
    except Exception as e:
        print(f"Create pool error: {str(e)}")
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
    except Exception as e:
        print(f"Get my pools error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve pools")


@router.get("/", response_model=List[schemas.PoolOut])
def list_pools(skip: int = 0, limit: int = 100, db: Session = Depends(deps.get_db)):
    return db.query(models.Pool).offset(skip).limit(limit).all()


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

        # TODO: Check if user has access to this pool (owner or member)
        # For now, allow access to any pool

        return pool
    except HTTPException:
        raise
    except Exception as e:
        print(f"Get pool error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve pool")


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
            pool.name = pool_update.name
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
        target_is_private = (
            pool_update.is_private
            if pool_update.is_private is not None
            else pool.is_private
        )
        if target_is_private:
            if pool_update.join_password is not None:
                pool.join_password_hash = get_password_hash(
                    _validate_join_password(pool_update.join_password)
                )
            elif pool_update.is_private is True and not pool.join_password_hash:
                raise HTTPException(
                    status_code=400,
                    detail="Set a join password before making this pool private",
                )
        else:
            pool.join_password_hash = None
        pool.is_private = target_is_private

        pool.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)

        db.commit()
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
    return {"message": "Pool joined successfully", "pool_id": pool_id}


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

        if pool.owner_id != current_user.id:
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

        return {
            "pool_id": pool_id,
            "is_owner": is_owner,
            "is_admin": is_admin,
            "has_admin_access": is_owner or is_admin,
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Check pool admin error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to check admin status")
