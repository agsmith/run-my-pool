from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import models
import schemas
import deps
from datetime import datetime
import uuid

router = APIRouter(prefix="/entries", tags=["entries"])

@router.post("/create", response_model=schemas.EntryOut)
def create_entry(
    entry: schemas.EntryCreate, 
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """Create a new entry for the current user in a pool."""
    try:
        # Verify the pool exists
        pool = db.query(models.Pool).filter(models.Pool.id == entry.pool_id).first()
        if not pool:
            raise HTTPException(status_code=404, detail="Pool not found")
        
        # Check if user already has an entry with this name in this pool
        existing_entry = db.query(models.Entry).filter(
            models.Entry.user_id == current_user.id,
            models.Entry.pool_id == entry.pool_id,
            models.Entry.name == entry.name
        ).first()
        
        if existing_entry:
            raise HTTPException(status_code=400, detail="You already have an entry with this name in this pool")
        
        db_entry = models.Entry(
            id=str(uuid.uuid4()),
            name=entry.name,
            user_id=current_user.id,
            pool_id=entry.pool_id,
            alive=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.add(db_entry)
        db.commit()
        db.refresh(db_entry)
        
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
    current_user: models.User = Depends(deps.get_current_user)
):
    """Get all entries for the current user in a specific pool."""
    try:
        entries = db.query(models.Entry).filter(
            models.Entry.user_id == current_user.id,
            models.Entry.pool_id == pool_id
        ).all()
        
        return entries
    except Exception as e:
        print(f"Get user entries error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve entries")

@router.get("/", response_model=List[schemas.EntryOut])
def list_entries(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """Get all entries for the current user."""
    try:
        entries = db.query(models.Entry).filter(
            models.Entry.user_id == current_user.id
        ).offset(skip).limit(limit).all()
        
        return entries
    except Exception as e:
        print(f"List entries error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve entries")

@router.get("/{entry_id}", response_model=schemas.EntryOut)
def get_entry(
    entry_id: str, 
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """Get a specific entry (only if owned by current user)."""
    try:
        entry = db.query(models.Entry).filter(
            models.Entry.id == entry_id,
            models.Entry.user_id == current_user.id
        ).first()
        
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
    current_user: models.User = Depends(deps.get_current_user)
):
    """Update an entry (only if owned by current user)."""
    try:
        entry = db.query(models.Entry).filter(
            models.Entry.id == entry_id,
            models.Entry.user_id == current_user.id
        ).first()
        
        if not entry:
            raise HTTPException(status_code=404, detail="Entry not found")
        
        if entry_update.name is not None:
            entry.name = entry_update.name
        
        entry.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(entry)
        
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
    current_user: models.User = Depends(deps.get_current_user)
):
    """Delete an entry (only if owned by current user)."""
    try:
        entry = db.query(models.Entry).filter(
            models.Entry.id == entry_id,
            models.Entry.user_id == current_user.id
        ).first()
        
        if not entry:
            raise HTTPException(status_code=404, detail="Entry not found")
        
        db.delete(entry)
        db.commit()
        
        return {"message": "Entry deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Delete entry error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete entry")
