"""
Admin endpoints for administrative operations
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import models
import schemas
import deps
from audit_utils import log_admin_action
from typing import Optional

router = APIRouter(prefix="/admin", tags=["admin"])

def verify_admin_access(pool_id: str, current_user: models.User, db: Session) -> bool:
    """Verify if user has admin access to the pool"""
    # Check if user owns the pool
    pool = db.query(models.Pool).filter(models.Pool.id == pool_id).first()
    if pool and pool.owner_id == current_user.id:
        return True
    
    # Check if user is a pool admin
    pool_admin = db.query(models.PoolAdmin).filter(
        models.PoolAdmin.pool_id == pool_id,
        models.PoolAdmin.user_id == current_user.id
    ).first()
    
    return pool_admin is not None

@router.post("/pools/{pool_id}/transfer-entry")
def transfer_entry(
    pool_id: str,
    transfer_data: schemas.EntryTransfer,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """Transfer entry ownership from one user to another (admin only)"""
    
    # Verify admin access
    if not verify_admin_access(pool_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only pool owners and admins can transfer entries"
        )
    
    # Find the entry
    entry = db.query(models.Entry).filter(
        models.Entry.id == transfer_data.entry_id,
        models.Entry.pool_id == pool_id
    ).first()
    
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Entry not found in this pool"
        )
    
    # Find current owner
    current_owner = db.query(models.User).filter(models.User.id == entry.user_id).first()
    if not current_owner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Current entry owner not found"
        )
    
    # Find new owner by username
    new_owner = db.query(models.User).filter(models.User.username == transfer_data.to_username).first()
    if not new_owner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{transfer_data.to_username}' not found"
        )
    
    # Check if new owner already has an entry with the same name in this pool
    existing_entry = db.query(models.Entry).filter(
        models.Entry.pool_id == pool_id,
        models.Entry.user_id == new_owner.id,
        models.Entry.name == entry.name
    ).first()
    
    if existing_entry:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User '{transfer_data.to_username}' already has an entry named '{entry.name}' in this pool"
        )
    
    # Store old owner info for audit log
    old_user_id = entry.user_id
    old_username = current_owner.username
    
    # Transfer the entry
    entry.user_id = new_owner.id
    db.commit()
    db.refresh(entry)
    
    # Log the transfer
    log_admin_action(
        db=db,
        action="TRANSFER_ENTRY",
        admin_user_id=current_user.id,
        details=f"Transferred entry '{entry.name}' from {old_username} to {transfer_data.to_username}",
        target_entity_type="entry",
        target_entity_id=entry.id,
        additional_data={
            "entry_name": entry.name,
            "from_user_id": old_user_id,
            "from_username": old_username,
            "to_user_id": new_owner.id,
            "to_username": transfer_data.to_username,
            "pool_id": pool_id,
            "admin_email": current_user.email
        }
    )
    
    return {
        "message": f"Entry '{entry.name}' successfully transferred from {old_username} to {transfer_data.to_username}",
        "entry_id": entry.id,
        "from_user": old_username,
        "to_user": transfer_data.to_username
    }

@router.delete("/pools/{pool_id}/entries/{entry_id}")
def delete_entry_admin(
    pool_id: str,
    entry_id: str,
    reason: Optional[str] = None,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """Delete any entry in a pool (admin only)"""
    
    # Verify admin access
    if not verify_admin_access(pool_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only pool owners and admins can delete entries"
        )
    
    # Find the entry
    entry = db.query(models.Entry).filter(
        models.Entry.id == entry_id,
        models.Entry.pool_id == pool_id
    ).first()
    
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Entry not found in this pool"
        )
    
    # Get entry owner info for logging
    entry_owner = db.query(models.User).filter(models.User.id == entry.user_id).first()
    owner_username = entry_owner.username if entry_owner else "unknown"
    
    # Store entry info for audit log before deletion
    entry_name = entry.name
    entry_user_id = entry.user_id
    
    # Delete the entry (this will cascade to delete related picks)
    db.delete(entry)
    db.commit()
    
    # Log the deletion
    log_admin_action(
        db=db,
        action="DELETE_ENTRY",
        admin_user_id=current_user.id,
        details=f"Admin deleted entry '{entry_name}' owned by {owner_username}" + (f" - Reason: {reason}" if reason else ""),
        target_entity_type="entry",
        target_entity_id=entry_id,
        additional_data={
            "entry_name": entry_name,
            "entry_owner_id": entry_user_id,
            "entry_owner_username": owner_username,
            "pool_id": pool_id,
            "admin_email": current_user.email,
            "reason": reason
        }
    )
    
    return {
        "message": f"Entry '{entry_name}' owned by {owner_username} has been deleted",
        "entry_name": entry_name,
        "owner": owner_username
    }
