from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import models
import schemas
import deps
from typing import List
from audit_utils import log_delete_operation, log_update_operation, log_admin_action

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/", response_model=List[schemas.UserOut])
def list_users(skip: int = 0, limit: int = 100, db: Session = Depends(deps.get_db)):
    return db.query(models.User).offset(skip).limit(limit).all()

@router.get("/{user_id}", response_model=schemas.UserOut)
def get_user(user_id: int, db: Session = Depends(deps.get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.delete("/{user_id}")
def delete_user(user_id: int, db: Session = Depends(deps.get_db), current_user: models.User = Depends(deps.get_current_user)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Log user deletion
    log_delete_operation(
        db=db,
        entity_type="user",
        entity_id=str(user.id),
        user_id=current_user.id,
        entity_data={
            "email": user.email,
            "role": user.role.value if user.role else "USER",
            "deleted_by": current_user.email
        }
    )
    
    db.delete(user)
    db.commit()
    return {"ok": True}

@router.patch("/{user_id}/email")
def update_email(user_id: int, email: str, db: Session = Depends(deps.get_db), current_user: models.User = Depends(deps.get_current_user)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    old_email = user.email
    user.email = email
    db.commit()
    db.refresh(user)
    
    # Log email update
    log_admin_action(
        db=db,
        action="UPDATE_USER_EMAIL",
        admin_user_id=current_user.id,
        details=f"Updated user email from {old_email} to {email}",
        target_entity_type="user",
        target_entity_id=str(user.id),
        additional_data={
            "old_email": old_email,
            "new_email": email,
            "updated_by": current_user.email
        }
    )
    
    return user

@router.patch("/{user_id}/password")
def reset_password(user_id: int, password: str, db: Session = Depends(deps.get_db), current_user: models.User = Depends(deps.get_current_user)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.hashed_password = password  # Should hash in real impl
    db.commit()
    db.refresh(user)
    
    # Log password reset
    log_admin_action(
        db=db,
        action="RESET_USER_PASSWORD",
        admin_user_id=current_user.id,
        details=f"Reset password for user {user.email}",
        target_entity_type="user",
        target_entity_id=str(user.id),
        additional_data={
            "target_user_email": user.email,
            "reset_by": current_user.email
        }
    )
    
    return user
