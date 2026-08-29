"""Platform-wide administration endpoints protected as one RBAC boundary."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

import deps
import models
from platform_admin import require_platform_super_admin


router = APIRouter(
    prefix="/platform-admin",
    tags=["platform-admin"],
    dependencies=[Depends(require_platform_super_admin)],
)


@router.get("/overview")
def overview(db: Session = Depends(deps.get_db)):
    assigned_user_ids = {
        user_id
        for query in (
            db.query(models.PoolMember.user_id), db.query(models.Entry.user_id),
            db.query(models.PoolAdmin.user_id), db.query(models.Pool.owner_id),
        )
        for (user_id,) in query.all()
        if user_id
    }
    return {
        "users": db.query(models.User).count(),
        "unassigned_users": db.query(models.User)
        .filter(~models.User.id.in_(assigned_user_ids or [""]))
        .count(),
        "super_admins": db.query(models.User)
        .filter(models.User.role == models.UserRole.SUPER_ADMIN)
        .count(),
        "pools": db.query(models.Pool).count(),
        "private_pools": db.query(models.Pool).filter(models.Pool.is_private.is_(True)).count(),
        "entries": db.query(models.Entry).count(),
        "audit_events": db.query(models.AuditLog).count(),
    }


@router.get("/metrics")
def metrics(db: Session = Depends(deps.get_db)):
    """Return platform growth totals and rolling 24-hour deltas."""
    window_start = (
        datetime.now(timezone.utc) - timedelta(hours=24)
    ).replace(tzinfo=None)
    memberships = db.query(models.PoolMember)
    return {
        "window_hours": 24,
        "window_started_at": window_start,
        "pools": {
            "total": db.query(models.Pool).count(),
            "new": db.query(models.Pool)
            .filter(models.Pool.created_at >= window_start)
            .count(),
        },
        "memberships": {
            "total": memberships.count(),
            "new": memberships.filter(
                models.PoolMember.joined_at >= window_start
            ).count(),
            "unique_members": db.query(
                func.count(func.distinct(models.PoolMember.user_id))
            ).scalar() or 0,
        },
        "entries": {
            "total": db.query(models.Entry).count(),
            "new": db.query(models.Entry)
            .filter(models.Entry.created_at >= window_start)
            .count(),
        },
        "users": {
            "total": db.query(models.User).count(),
            "new": db.query(models.User)
            .filter(models.User.created_at >= window_start)
            .count(),
        },
    }


@router.get("/pools")
def list_all_pools(
    search: str = "",
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=500, ge=1, le=500),
    db: Session = Depends(deps.get_db),
):
    member_counts = db.query(
        models.PoolMember.pool_id,
        func.count(models.PoolMember.user_id).label("member_count"),
    ).group_by(models.PoolMember.pool_id).subquery()
    entry_counts = db.query(
        models.Entry.pool_id,
        func.count(models.Entry.id).label("entry_count"),
    ).group_by(models.Entry.pool_id).subquery()
    query = db.query(
        models.Pool,
        models.User.email.label("owner_email"),
        func.coalesce(member_counts.c.member_count, 0),
        func.coalesce(entry_counts.c.entry_count, 0),
    ).outerjoin(
        models.User, models.User.id == models.Pool.owner_id
    ).outerjoin(
        member_counts, member_counts.c.pool_id == models.Pool.id
    ).outerjoin(entry_counts, entry_counts.c.pool_id == models.Pool.id)
    if search.strip():
        needle = f"%{search.strip().lower()}%"
        query = query.filter(or_(
            func.lower(models.Pool.name).like(needle),
            func.lower(models.User.email).like(needle),
        ))
    rows = query.order_by(models.Pool.created_at.desc(), models.Pool.name.asc()).offset(skip).limit(limit).all()
    return [{
        "id": pool.id, "name": pool.name, "description": pool.description,
        "is_private": pool.is_private, "owner_id": pool.owner_id,
        "owner_email": owner_email, "member_count": member_count,
        "entry_count": entry_count, "created_at": pool.created_at,
    } for pool, owner_email, member_count, entry_count in rows]


@router.get("/entries")
def list_all_entries(
    search: str = "",
    pool_id: str | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=500, ge=1, le=500),
    db: Session = Depends(deps.get_db),
):
    query = db.query(
        models.Entry, models.User.email, models.Pool.name
    ).outerjoin(
        models.User, models.User.id == models.Entry.user_id
    ).outerjoin(models.Pool, models.Pool.id == models.Entry.pool_id)
    if pool_id:
        query = query.filter(models.Entry.pool_id == pool_id)
    if search.strip():
        needle = f"%{search.strip().lower()}%"
        query = query.filter(or_(
            func.lower(models.Entry.name).like(needle),
            func.lower(models.User.email).like(needle),
            func.lower(models.Pool.name).like(needle),
        ))
    rows = query.order_by(models.Entry.created_at.desc(), models.Entry.name.asc()).offset(skip).limit(limit).all()
    return [{
        "id": entry.id, "name": entry.name, "user_id": entry.user_id,
        "user_email": user_email, "pool_id": entry.pool_id,
        "pool_name": pool_name, "alive": entry.alive,
        "created_at": entry.created_at,
    } for entry, user_email, pool_name in rows]
