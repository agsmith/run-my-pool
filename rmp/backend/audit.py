from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
import models
import schemas
import deps
from typing import List, Optional
from datetime import datetime, time

router = APIRouter(prefix="/audit", tags=["audit"])

@router.get("/", response_model=List[schemas.AuditLogOut])
def list_audit_logs(
    skip: int = 0,
    limit: int = Query(default=100, ge=1, le=500),
    user_id: Optional[str] = None,
    action: Optional[str] = None,
    pool_id: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_user),
):
    """Return newest audit events first with filters used by the admin console."""
    query = db.query(models.AuditLog)
    if user_id:
        query = query.filter(models.AuditLog.user_id == user_id)
    if action:
        pattern = f"%{action}%"
        query = query.filter(models.AuditLog.action.ilike(pattern))
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
