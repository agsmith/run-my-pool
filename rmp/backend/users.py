from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
import models
import schemas
import deps
from typing import List
from audit_utils import log_delete_operation, log_update_operation, log_admin_action
from platform_admin import is_bootstrap_super_admin, is_platform_super_admin

router = APIRouter(prefix="/users", tags=["users"])


def _require_admin(current_user: models.User) -> None:
    """Raise HTTP 403 if the current user is not POOL_ADMIN or SUPER_ADMIN."""
    if current_user.role != models.UserRole.POOL_ADMIN and not is_platform_super_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )


def _require_super_admin(current_user: models.User) -> None:
    if not is_platform_super_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Platform admin access required",
        )


def _pool_ids_by_user(db: Session) -> dict[str, set[str]]:
    """Map every user to pools they own, administer, joined, or entered."""
    result: dict[str, set[str]] = {}
    relationships = (
        db.query(models.Pool.owner_id, models.Pool.id).filter(models.Pool.owner_id.isnot(None)).all(),
        db.query(models.PoolAdmin.user_id, models.PoolAdmin.pool_id).all(),
        db.query(models.PoolMember.user_id, models.PoolMember.pool_id).all(),
        db.query(models.Entry.user_id, models.Entry.pool_id).filter(models.Entry.user_id.isnot(None)).all(),
    )
    for rows in relationships:
        for user_id, pool_id in rows:
            result.setdefault(user_id, set()).add(pool_id)
    return result


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
    if is_platform_super_admin(current_user):
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
    unassigned_only: bool = False,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
):
    """User directory scoped to leagues the administrator can manage."""
    safe_limit = min(max(limit, 1), 500)
    safe_skip = max(skip, 0)
    base_query = _admin_user_query(db, current_user)
    pool_ids_by_user = _pool_ids_by_user(db)
    unassigned_ids = {
        user_id for (user_id,) in base_query.with_entities(models.User.id).all()
        if not pool_ids_by_user.get(user_id)
    }
    query = base_query
    if unassigned_only:
        _require_super_admin(current_user)
        query = query.filter(models.User.id.in_(unassigned_ids or [""]))
    if search.strip():
        query = query.filter(func.lower(models.User.email).contains(search.strip().lower()))

    users = query.order_by(models.User.created_at.desc(), models.User.email.asc()).offset(safe_skip).limit(safe_limit).all()
    return {
        "total": base_query.count(),
        "active": base_query.filter(models.User.is_active.is_(True)).count(),
        "locked": base_query.filter(models.User.is_active.is_(False)).count(),
        "pool_admins": base_query.filter(models.User.role == models.UserRole.POOL_ADMIN).count(),
        "super_admins": base_query.filter(models.User.role == models.UserRole.SUPER_ADMIN).count(),
        "unassigned": len(unassigned_ids),
        "users": [
            {
                "id": user.id,
                "email": user.email,
                "role": user.role,
                "is_active": user.is_active,
                "created_at": user.created_at,
                "updated_at": user.updated_at,
                "pool_count": len(pool_ids_by_user.get(user.id, set())),
            }
            for user in users
        ],
    }


@router.patch("/{user_id}/status", response_model=schemas.AdminUserOut)
def update_user_status(
    user_id: str,
    active: bool,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
):
    """Activate or deactivate an account; platform administrators only."""
    _require_super_admin(current_user)
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if is_bootstrap_super_admin(user) and not active:
        raise HTTPException(status_code=400, detail="The initial super admin cannot be deactivated")
    user.is_active = active
    db.commit()
    db.refresh(user)
    log_admin_action(
        db=db,
        action="UPDATE_USER_STATUS",
        admin_user_id=current_user.id,
        details=f"{'Activated' if active else 'Deactivated'} user {user.email}",
        target_entity_type="user",
        target_entity_id=user.id,
        additional_data={"active": active},
    )
    return {
        "id": user.id,
        "email": user.email,
        "role": user.role,
        "is_active": user.is_active,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
        "pool_count": len(_pool_ids_by_user(db).get(user.id, set())),
    }


@router.patch("/{user_id}/super-admin", response_model=schemas.AdminUserOut)
def update_super_admin_access(
    user_id: str,
    enabled: bool,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
):
    """Grant or revoke delegated platform support access."""
    _require_super_admin(current_user)
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not enabled and user.id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot revoke your own super admin access")
    if not enabled and is_bootstrap_super_admin(user):
        raise HTTPException(status_code=400, detail="The initial super admin access cannot be revoked")

    user.role = models.UserRole.SUPER_ADMIN if enabled else models.UserRole.USER
    db.commit()
    db.refresh(user)
    log_admin_action(
        db=db,
        action="UPDATE_SUPER_ADMIN_ACCESS",
        admin_user_id=current_user.id,
        details=f"{'Granted' if enabled else 'Revoked'} super admin access for {user.email}",
        target_entity_type="user",
        target_entity_id=user.id,
        additional_data={"super_admin": enabled},
    )
    return {
        "id": user.id,
        "email": user.email,
        "role": user.role,
        "is_active": user.is_active,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
        "pool_count": len(_pool_ids_by_user(db).get(user.id, set())),
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
    if is_bootstrap_super_admin(user):
        raise HTTPException(status_code=400, detail="The initial super admin cannot be deleted")

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
    if is_bootstrap_super_admin(user):
        raise HTTPException(status_code=400, detail="The initial super admin email cannot be changed")

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
