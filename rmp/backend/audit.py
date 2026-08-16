from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
import models
import schemas
import deps
from typing import List, Optional
from datetime import datetime, time
from platform_admin import is_platform_super_admin

router = APIRouter(prefix="/audit", tags=["audit"])


def _require_audit_scope(db: Session, current_user: models.User, pool_id: Optional[str]):
    if is_platform_super_admin(current_user):
        return
    if not pool_id:
        raise HTTPException(status_code=403, detail="A league is required")
    has_access = db.query(models.Pool).filter(
        models.Pool.id == pool_id,
        models.Pool.owner_id == current_user.id,
    ).first() or db.query(models.PoolAdmin).filter(
        models.PoolAdmin.pool_id == pool_id,
        models.PoolAdmin.user_id == current_user.id,
    ).first()
    if not has_access:
        raise HTTPException(status_code=403, detail="Admin access required")


def _pool_audit_query(db: Session, pool_id: str):
    return db.query(models.AuditLog).filter(
        models.AuditLog.details.contains(f'"pool_id": "{pool_id}"')
    )


@router.get("/filter-options", response_model=schemas.AuditFilterOptions)
def audit_filter_options(
    pool_id: str,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_user),
):
    """Return exact event and actor choices available within one pool."""
    _require_audit_scope(db, current_user, pool_id)
    scoped = _pool_audit_query(db, pool_id)
    event_types = [
        action for (action,) in scoped.with_entities(models.AuditLog.action)
        .distinct().order_by(models.AuditLog.action).all()
    ]
    actor_ids = {
        user_id for (user_id,) in scoped.with_entities(models.AuditLog.user_id)
        .filter(models.AuditLog.user_id.isnot(None)).distinct().all()
    }
    users = db.query(models.User).filter(
        models.User.id.in_(actor_ids or [""])
    ).order_by(models.User.email).all()
    includes_system_events = scoped.filter(models.AuditLog.user_id.is_(None)).first() is not None
    return {
        "event_types": event_types,
        "users": [{"id": user.id, "email": user.email} for user in users],
        "includes_system_events": includes_system_events,
    }

@router.get("/", response_model=List[schemas.AuditLogOut])
def list_audit_logs(
    skip: int = 0,
    limit: int = Query(default=100, ge=1, le=500),
    user_id: Optional[str] = None,
    username: Optional[str] = None,
    action: Optional[str] = None,
    event_type: Optional[str] = None,
    pool_id: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_user),
):
    """Return newest audit events first with filters used by the admin console."""
    _require_audit_scope(db, current_user, pool_id)
    query = db.query(models.AuditLog)
    if user_id:
        query = query.filter(
            models.AuditLog.user_id.is_(None)
            if user_id == "__system__"
            else models.AuditLog.user_id == user_id
        )
    if username:
        matching_user_ids = [
            user_id
            for (user_id,) in (
                db.query(models.User.id)
                .filter(models.User.email.ilike(f"%{username.strip()}%"))
                .all()
            )
        ]
        query = query.filter(models.AuditLog.user_id.in_(matching_user_ids))
    if action:
        pattern = f"%{action}%"
        query = query.filter(models.AuditLog.action.ilike(pattern))
    if event_type:
        query = query.filter(models.AuditLog.action == event_type)
    if pool_id:
        # Pool context is stored in the structured audit details JSON. Quoting
        # the value avoids partial UUID matches while remaining DB portable.
        query = query.filter(models.AuditLog.details.contains(f'"pool_id": "{pool_id}"'))
    if date_from:
        query = query.filter(models.AuditLog.created_at >= date_from)
    if date_to:
        query = query.filter(models.AuditLog.created_at <= date_to)

    logs = (
        query.order_by(models.AuditLog.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    # Audit rows intentionally retain the immutable user ID. Resolve all users
    # in one query so clients can display a useful account name for every event,
    # including historical events whose JSON payload predates username context.
    user_ids = {log.user_id for log in logs if log.user_id}
    usernames = {}
    if user_ids:
        usernames = dict(
            db.query(models.User.id, models.User.email)
            .filter(models.User.id.in_(user_ids))
            .all()
        )

    return [
        schemas.AuditLogOut(
            id=log.id,
            user_id=log.user_id,
            username=usernames.get(log.user_id),
            action=log.action,
            details=log.details,
            created_at=log.created_at,
        )
        for log in logs
    ]
