from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
import models
import schemas
import deps
from typing import List
from audit_utils import log_delete_operation, log_update_operation, log_admin_action

router = APIRouter(prefix="/users", tags=["users"])


def _require_admin(current_user: models.User) -> None:
    """Raise HTTP 403 if the current user is not POOL_ADMIN or SUPER_ADMIN."""
    if current_user.role not in (
        models.UserRole.POOL_ADMIN,
        models.UserRole.SUPER_ADMIN,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )


def _managed_user_ids(db: Session, current_user: models.User) -> set:
    """Return users participating in leagues the pool admin can manage."""
    pool_ids = {
        pool_id
        for (pool_id,) in db.query(models.Pool.id)
        .filter(models.Pool.owner_id == current_user.id)
        .all()
    }
    pool_ids.update(
        pool_id
        for (pool_id,) in db.query(models.PoolAdmin.pool_id)
        .filter(models.PoolAdmin.user_id == current_user.id)
        .all()
    )
    if not pool_ids:
        return set()

    user_ids = {
        user_id
        for (user_id,) in db.query(models.PoolMember.user_id)
        .filter(models.PoolMember.pool_id.in_(pool_ids))
        .all()
    }
    user_ids.update(
        user_id
        for (user_id,) in db.query(models.Entry.user_id)
        .filter(models.Entry.pool_id.in_(pool_ids))
        .distinct()
        .all()
    )
    user_ids.update(
        user_id
        for (user_id,) in db.query(models.PoolAdmin.user_id)
        .filter(models.PoolAdmin.pool_id.in_(pool_ids))
        .all()
    )
    user_ids.update(
        owner_id
        for (owner_id,) in db.query(models.Pool.owner_id)
        .filter(models.Pool.id.in_(pool_ids))
        .all()
        if owner_id
    )
    return user_ids


def _admin_user_query(db: Session, current_user: models.User):
    _require_admin(current_user)
    query = db.query(models.User)
    if current_user.role == models.UserRole.SUPER_ADMIN:
        return query
    return query.filter(models.User.id.in_(_managed_user_ids(db, current_user) or [""]))


def _get_managed_user(db: Session, current_user: models.User, user_id: str) -> models.User:
    user = _admin_user_query(db, current_user).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("/admin-dashboard", response_model=schemas.AdminUserDashboardOut)
def admin_user_dashboard(
    search: str = "",
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
):
    """User directory scoped to leagues the administrator can manage."""
    safe_limit = min(max(limit, 1), 500)
    safe_skip = max(skip, 0)
    base_query = _admin_user_query(db, current_user)
    query = base_query
    if search.strip():
        query = query.filter(func.lower(models.User.email).contains(search.strip().lower()))

    users = query.order_by(models.User.created_at.desc(), models.User.email.asc()).offset(safe_skip).limit(safe_limit).all()
    return {
        "total": base_query.count(),
        "active": base_query.filter(models.User.is_active.is_(True)).count(),
        "locked": base_query.filter(models.User.is_active.is_(False)).count(),
        "pool_admins": base_query.filter(models.User.role == models.UserRole.POOL_ADMIN).count(),
        "super_admins": base_query.filter(models.User.role == models.UserRole.SUPER_ADMIN).count(),
        "users": users,
    }


@router.get("/", response_model=List[schemas.UserOut])
def list_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
):
    return _admin_user_query(db, current_user).offset(skip).limit(limit).all()


@router.get("/{user_id}", response_model=schemas.UserOut)
def get_user(
    user_id: str,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
):
    return _get_managed_user(db, current_user, user_id)


@router.delete("/{user_id}")
def delete_user(
    user_id: str,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
):
    user = _get_managed_user(db, current_user, user_id)

    # Log user deletion
    log_delete_operation(
        db=db,
        entity_type="user",
        entity_id=str(user.id),
        user_id=current_user.id,
        entity_data={
            "email": user.email,
            "role": user.role.value if user.role else "USER",
            "deleted_by": current_user.email,
        },
    )

    db.delete(user)
    db.commit()
    return {"ok": True}


@router.patch("/{user_id}/email")
def update_email(
    user_id: str,
    email: str,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
):
    user = _get_managed_user(db, current_user, user_id)

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
            "updated_by": current_user.email,
        },
    )

    return user
