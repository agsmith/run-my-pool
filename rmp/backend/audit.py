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

    return (
        query.order_by(models.AuditLog.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
