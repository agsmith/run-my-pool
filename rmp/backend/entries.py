from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import models
import schemas
import deps
from datetime import datetime, timezone
import uuid
from audit_utils import (
    log_create_operation,
    log_update_operation,
    log_delete_operation,
    log_admin_action,
)
from admin import is_user_locked_in_pool

router = APIRouter(prefix="/entries", tags=["entries"])


@router.post("/create", response_model=schemas.EntryOut)
def create_entry(
    entry: schemas.EntryCreate,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
):
    """Create a new entry for the current user in a pool."""
    try:
        # Verify the pool exists
        pool = db.query(models.Pool).filter(models.Pool.id == entry.pool_id).first()
        if not pool:
            raise HTTPException(status_code=404, detail="Pool not found")

        # Enforce pool lock time — coerce to datetime if SQLite returned a string
        lock_time = pool.lock_time
        if lock_time is not None:
            if isinstance(lock_time, str):
                try:
                    lock_time = datetime.fromisoformat(lock_time)
                except ValueError:
                    lock_time = None
            if lock_time and lock_time < datetime.now(timezone.utc).replace(
                tzinfo=None
            ):
                raise HTTPException(
                    status_code=423,
                    detail="Pool is locked. Entry creation is not allowed after the lock time.",
                )

        # Check if user already has an entry with this name in this pool
        # Check pool-level user lock
        if is_user_locked_in_pool(db, entry.pool_id, current_user.id):
            raise HTTPException(
                status_code=423,
                detail="Your account is locked in this pool. Contact the pool admin.",
            )

        # Check if user already has an entry with this name in this pool
        existing_entry = (
            db.query(models.Entry)
            .filter(
                models.Entry.user_id == current_user.id,
                models.Entry.pool_id == entry.pool_id,
                models.Entry.name == entry.name,
            )
            .first()
        )

        if existing_entry:
            raise HTTPException(
                status_code=400,
                detail="You already have an entry with this name in this pool",
            )

        db_entry = models.Entry(
            id=str(uuid.uuid4()),
            name=entry.name,
            user_id=current_user.id,
            pool_id=entry.pool_id,
            alive=True,
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
            updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )

        db.add(db_entry)
        db.commit()
        db.refresh(db_entry)

        # Log entry creation
        log_create_operation(
            db=db,
            entity_type="entry",
            entity_id=db_entry.id,
            user_id=current_user.id,
            entity_data={
                "name": entry.name,
                "pool_id": entry.pool_id,
                "user_email": current_user.email,
            },
        )

        return db_entry
    except HTTPException:
        raise
    except Exception as e:
        print(f"Create entry error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create entry")


@router.get("/pool/{pool_id}", response_model=List[schemas.EntryOut])
def get_user_entries_for_pool(
    pool_id: str,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
):
    """Get all entries for the current user in a specific pool."""
    try:
        entries = (
            db.query(models.Entry)
            .filter(
                models.Entry.user_id == current_user.id, models.Entry.pool_id == pool_id
            )
            .all()
        )

        return entries
    except Exception as e:
        print(f"Get user entries error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve entries")


@router.get("/", response_model=List[schemas.EntryOut])
def list_entries(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
):
    """Get all entries for the current user."""
    try:
        entries = (
            db.query(models.Entry)
            .filter(models.Entry.user_id == current_user.id)
            .offset(skip)
            .limit(limit)
            .all()
        )

        return entries
    except Exception as e:
        print(f"List entries error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve entries")


@router.get("/{entry_id}", response_model=schemas.EntryOut)
def get_entry(
    entry_id: str,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
):
    """Get a specific entry (only if owned by current user)."""
    try:
        entry = (
            db.query(models.Entry)
            .filter(
                models.Entry.id == entry_id, models.Entry.user_id == current_user.id
            )
            .first()
        )

        if not entry:
            raise HTTPException(status_code=404, detail="Entry not found")

        return entry
    except HTTPException:
        raise
    except Exception as e:
        print(f"Get entry error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve entry")


@router.put("/{entry_id}", response_model=schemas.EntryOut)
def update_entry(
    entry_id: str,
    entry_update: schemas.EntryUpdate,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
):
    """Update an entry (only if owned by current user)."""
    try:
        entry = (
            db.query(models.Entry)
            .filter(
                models.Entry.id == entry_id, models.Entry.user_id == current_user.id
            )
            .first()
        )

        if not entry:
            raise HTTPException(status_code=404, detail="Entry not found")

        # Track changes for audit log
        changes = {}
        if entry_update.name is not None and entry_update.name != entry.name:
            changes["name"] = {"old": entry.name, "new": entry_update.name}
            entry.name = entry_update.name

        entry.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)

        db.commit()
        db.refresh(entry)

        # Log entry update if there were changes
        if changes:
            log_update_operation(
                db=db,
                entity_type="entry",
                entity_id=entry.id,
                user_id=current_user.id,
                changes=changes,
            )

        return entry
    except HTTPException:
        raise
    except Exception as e:
        print(f"Update entry error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update entry")


@router.delete("/{entry_id}")
def delete_entry(
    entry_id: str,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
):
    """Delete an entry (only if owned by current user)."""
    try:
        entry = (
            db.query(models.Entry)
            .filter(
                models.Entry.id == entry_id, models.Entry.user_id == current_user.id
            )
            .first()
        )

        if not entry:
            raise HTTPException(status_code=404, detail="Entry not found")

        # Enforce pool lock time — coerce to datetime if SQLite returned a string
        pool = db.query(models.Pool).filter(models.Pool.id == entry.pool_id).first()
        if pool and pool.lock_time is not None:
            lock_time = pool.lock_time
            if isinstance(lock_time, str):
                try:
                    lock_time = datetime.fromisoformat(lock_time)
                except ValueError:
                    lock_time = None
            if lock_time and lock_time < datetime.now(timezone.utc).replace(
                tzinfo=None
            ):
                raise HTTPException(
                    status_code=423,
                    detail="Pool is locked. Entry deletion is not allowed after the lock time.",
                )

        # Log entry deletion before deleting
        # Check pool-level user lock
        if is_user_locked_in_pool(db, entry.pool_id, current_user.id):
            raise HTTPException(
                status_code=423,
                detail="Your account is locked in this pool. Contact the pool admin.",
            )

        # Log entry deletion before deleting
        log_delete_operation(
            db=db,
            entity_type="entry",
            entity_id=entry.id,
            user_id=current_user.id,
            entity_data={
                "name": entry.name,
                "pool_id": entry.pool_id,
                "user_email": current_user.email,
            },
        )

        db.delete(entry)
        db.commit()

        return {"message": "Entry deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Delete entry error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete entry")
