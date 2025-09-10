from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import models
import schemas
import deps
from datetime import datetime
import uuid

router = APIRouter(prefix="/pools", tags=["pools"])

@router.post("/create", response_model=schemas.PoolOut)
def create_pool(
    pool: schemas.PoolCreate, 
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """Create a new pool with the current user as the owner/admin."""
    try:
        # Parse lock_time if provided
        lock_time = None
        if pool.lock_time:
            try:
                # Handle various datetime formats
                time_str = pool.lock_time.strip()
                
                # If it's ISO format with 'T', convert to MySQL format
                if 'T' in time_str:
                    # Remove 'Z' timezone indicator if present
                    time_str = time_str.replace('Z', '')
                    # Split at 'T' to separate date and time
                    date_part, time_part = time_str.split('T')
                    # Remove milliseconds if present
                    if '.' in time_part:
                        time_part = time_part.split('.')[0]
                    # Combine date and time with space
                    time_str = f"{date_part} {time_part}"
                
                # Add seconds if not present (HTML5 datetime-local doesn't include seconds)
                if len(time_str.split(' ')[1].split(':')) == 2:
                    time_str += ':00'
                
                # Parse the datetime string
                lock_time = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
                
            except (ValueError, TypeError) as e:
                raise HTTPException(status_code=400, detail=f"Invalid lock_time format. Use YYYY-MM-DD HH:MM:SS or ISO format: {str(e)}")
        
        db_pool = models.Pool(
            id=str(uuid.uuid4()),
            name=pool.name,
            description=pool.description,
            lock_time=lock_time,
            is_private=pool.is_private,
            owner_id=current_user.id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.add(db_pool)
        db.commit()
        db.refresh(db_pool)
        
        # Add the pool creator as a pool admin
        pool_admin = models.PoolAdmin(
            pool_id=db_pool.id,
            user_id=current_user.id
        )
        db.add(pool_admin)
        db.commit()
        
        return db_pool
    except Exception as e:
        print(f"Create pool error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create pool")

@router.get("/my-pools", response_model=List[schemas.PoolOut])
def get_my_pools(
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """Get all pools where the current user is the owner or a member."""
    try:
        # Get pools where user is the owner
        owned_pools = db.query(models.Pool).filter(
            models.Pool.owner_id == current_user.id
        ).all()
        
        # TODO: Add pools where user is a member (requires pool membership table)
        # For now, just return owned pools
        
        return owned_pools
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
    current_user: models.User = Depends(deps.get_current_user)
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
    current_user: models.User = Depends(deps.get_current_user)
):
    """Update a pool (only by the pool owner)."""
    try:
        pool = db.query(models.Pool).filter(models.Pool.id == pool_id).first()
        
        if not pool:
            raise HTTPException(status_code=404, detail="Pool not found")
        
        if pool.owner_id != current_user.id:
            raise HTTPException(status_code=403, detail="Only pool owner can update the pool")
        
        # Update fields if provided
        if pool_update.name is not None:
            pool.name = pool_update.name
        if pool_update.description is not None:
            pool.description = pool_update.description
        if pool_update.lock_time is not None:
            pool.lock_time = pool_update.lock_time
        if pool_update.is_private is not None:
            pool.is_private = pool_update.is_private
        
        pool.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(pool)
        
        return pool
    except HTTPException:
        raise
    except Exception as e:
        print(f"Update pool error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update pool")

@router.delete("/{pool_id}")
def delete_pool(
    pool_id: str,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """Delete a pool (only by the pool owner)."""
    try:
        pool = db.query(models.Pool).filter(models.Pool.id == pool_id).first()
        
        if not pool:
            raise HTTPException(status_code=404, detail="Pool not found")
        
        if pool.owner_id != current_user.id:
            raise HTTPException(status_code=403, detail="Only pool owner can delete the pool")
        
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
    current_user: models.User = Depends(deps.get_current_user)
):
    """Check if the current user is an admin of the specified pool."""
    try:
        # Check if user is pool owner
        pool = db.query(models.Pool).filter(models.Pool.id == pool_id).first()
        if not pool:
            raise HTTPException(status_code=404, detail="Pool not found")
        
        is_owner = pool.owner_id == current_user.id
        
        # Check if user is in pool_admins table
        pool_admin = db.query(models.PoolAdmin).filter(
            models.PoolAdmin.pool_id == pool_id,
            models.PoolAdmin.user_id == current_user.id
        ).first()
        
        is_admin = pool_admin is not None
        
        return {
            "pool_id": pool_id,
            "is_owner": is_owner,
            "is_admin": is_admin,
            "has_admin_access": is_owner or is_admin
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Check pool admin error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to check admin status")
