"""Platform-wide administration endpoints protected as one RBAC boundary."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

import deps
import models
import schemas
from audit_utils import create_audit_log
from auth import EMAIL_VERIFICATION_RESEND_INTERVAL, _issue_email_verification
from platform_admin import require_platform_super_admin


router = APIRouter(
    prefix="/platform-admin",
    tags=["platform-admin"],
    dependencies=[Depends(require_platform_super_admin)],
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


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
        "unverified_users": db.query(models.User)
        .filter(models.User.email_verified.is_(False))
        .count(),
    }


@router.get(
    "/unverified-users", response_model=schemas.UnverifiedAccountDashboardOut
)
def list_unverified_users(
    search: str = "",
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=500, ge=1, le=500),
    db: Session = Depends(deps.get_db),
):
    query = db.query(models.User).filter(models.User.email_verified.is_(False))
    if search.strip():
        query = query.filter(
            func.lower(models.User.email).like(f"%{search.strip().lower()}%")
        )
    total = query.count()
    users = (
        query.order_by(models.User.created_at.desc(), models.User.email.asc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    user_ids = [user.id for user in users]
    token_rows = (
        db.query(models.EmailVerificationToken)
        .filter(models.EmailVerificationToken.user_id.in_(user_ids))
        .order_by(
            models.EmailVerificationToken.user_id.asc(),
            models.EmailVerificationToken.created_at.desc(),
        )
        .all()
        if user_ids
        else []
    )
    latest_tokens = {}
    token_counts = {}
    for token in token_rows:
        token_counts[token.user_id] = token_counts.get(token.user_id, 0) + 1
        latest_tokens.setdefault(token.user_id, token)

    now = _utcnow()
    records = []
    for user in users:
        token = latest_tokens.get(user.id)
        account_age = max(0, int((now - (user.created_at or now)).total_seconds()))
        token_status = "missing"
        token_age = None
        if token is not None:
            token_age = max(0, int((now - token.created_at).total_seconds()))
            token_status = (
                "valid"
                if token.used_at is None and token.expires_at > now
                else "expired"
            )
        records.append({
            "id": user.id,
            "email": user.email,
            "is_active": user.is_active,
            "created_at": user.created_at,
            "account_age_seconds": account_age,
            "token_created_at": token.created_at if token else None,
            "token_expires_at": token.expires_at if token else None,
            "token_age_seconds": token_age,
            "token_status": token_status,
            "automatic_reminder_due": bool(
                user.is_active
                and account_age >= 24 * 60 * 60
                and token_status == "expired"
                and token_counts.get(user.id, 0) == 1
            ),
        })
    return {"total": total, "users": records}


@router.post("/unverified-users/{user_id}/resend-verification")
def admin_resend_email_verification(
    user_id: str,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(require_platform_super_admin),
):
    target = (
        db.query(models.User)
        .filter(models.User.id == user_id)
        .with_for_update()
        .first()
    )
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")
    if target.email_verified:
        raise HTTPException(status_code=409, detail="This account is already verified")
    if not target.is_active:
        raise HTTPException(status_code=409, detail="Reactivate this account before resending verification")

    now = _utcnow()
    latest = (
        db.query(models.EmailVerificationToken)
        .filter(models.EmailVerificationToken.user_id == target.id)
        .order_by(models.EmailVerificationToken.created_at.desc())
        .first()
    )
    if latest and now - latest.created_at < EMAIL_VERIFICATION_RESEND_INTERVAL:
        retry_after = max(
            1,
            int((EMAIL_VERIFICATION_RESEND_INTERVAL - (now - latest.created_at)).total_seconds()),
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="A verification email was sent recently. Try again shortly.",
            headers={"Retry-After": str(retry_after)},
        )

    message_id = _issue_email_verification(db, target)
    create_audit_log(
        db=db,
        action="ADMIN_RESEND_EMAIL_VERIFICATION",
        details=f"Platform admin resent verification email for {target.email}",
        user_id=current_user.id,
        entity_type="user",
        entity_id=target.id,
        additional_data={"message_id": message_id},
    )
    return {"message": "Verification email sent."}


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
