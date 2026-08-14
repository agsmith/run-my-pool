"""Server-side commissioner entitlement assignment and capacity enforcement."""

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

import models


FREE_INCLUDED_ENTRIES = 10


def current_season(now: datetime | None = None) -> int:
    current = now or datetime.now(timezone.utc)
    return current.year - (1 if current.month <= 2 else 0)


def active_entitlement(db: Session, user_id: str, season: int):
    return (
        db.query(models.CommissionerEntitlement)
        .filter(
            models.CommissionerEntitlement.user_id == user_id,
            models.CommissionerEntitlement.season == season,
            models.CommissionerEntitlement.status == "active",
        )
        .first()
    )


def assign_owner_pools(db: Session, entitlement) -> list[models.Pool]:
    """Attach unassigned pools to a paid entitlement up to its pool allowance."""
    assigned = (
        db.query(models.Pool)
        .filter(models.Pool.billing_entitlement_id == entitlement.id)
        .count()
    )
    available = None if entitlement.max_pools is None else max(entitlement.max_pools - assigned, 0)
    if available == 0:
        return []
    query = (
        db.query(models.Pool)
        .filter(
            models.Pool.owner_id == entitlement.user_id,
            models.Pool.billing_entitlement_id.is_(None),
        )
        .order_by(models.Pool.created_at.asc(), models.Pool.id.asc())
    )
    pools = query.all() if available is None else query.limit(available).all()
    for pool in pools:
        pool.billing_entitlement_id = entitlement.id
        pool.billing_season = entitlement.season
    return pools


def entitlement_for_new_pool(db: Session, owner_id: str, season: int):
    # Serialize capacity decisions for concurrent pool-creation requests.
    db.query(models.User.id).filter(models.User.id == owner_id).with_for_update().one()
    entitlement = active_entitlement(db, owner_id, season)
    if entitlement:
        used = db.query(models.Pool).filter(
            models.Pool.billing_entitlement_id == entitlement.id
        ).count()
        if entitlement.max_pools is not None and used >= entitlement.max_pools:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Your {entitlement.plan} plan allows {entitlement.max_pools} active pool(s) for {season}.",
            )
        return entitlement

    return None


def enforce_entry_capacity(db: Session, pool: models.Pool) -> None:
    # Serialize count-and-create operations for this pool. Paid Club limits are
    # shared across pools, so lock the entitlement row below as well.
    db.query(models.Pool.id).filter(models.Pool.id == pool.id).with_for_update().one()
    # Reconcile purchases fulfilled before pools stored entitlement IDs. This
    # is intentionally server-side and bounded by the purchased pool count.
    if pool.billing_entitlement_id is None:
        entitlement = active_entitlement(db, pool.owner_id, current_season())
        if entitlement:
            assign_owner_pools(db, entitlement)
            db.flush()
            if pool.billing_entitlement_id == entitlement.id:
                pool.billing_entitlement = entitlement

    entitlement = pool.billing_entitlement
    if entitlement and entitlement.status == "active" and entitlement.season == pool.billing_season:
        db.query(models.CommissionerEntitlement.id).filter(
            models.CommissionerEntitlement.id == entitlement.id
        ).with_for_update().one()
        if entitlement.unlimited_entries or entitlement.included_entries is None:
            return
        pool_ids = db.query(models.Pool.id).filter(
            models.Pool.billing_entitlement_id == entitlement.id
        )
        entry_count = db.query(func.count(models.Entry.id)).filter(
            models.Entry.pool_id.in_(pool_ids)
        ).scalar() or 0
        square_count = db.query(func.count(models.SquareClaim.id)).filter(
            models.SquareClaim.pool_id.in_(pool_ids)
        ).scalar() or 0
        used = entry_count + square_count
        limit = entitlement.included_entries
        plan = entitlement.plan
    else:
        entry_count = db.query(func.count(models.Entry.id)).filter(
            models.Entry.pool_id == pool.id
        ).scalar() or 0
        square_count = db.query(func.count(models.SquareClaim.id)).filter(
            models.SquareClaim.pool_id == pool.id
        ).scalar() or 0
        used = entry_count + square_count
        limit = FREE_INCLUDED_ENTRIES
        plan = "free"

    if used >= limit:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"This pool has reached the {plan} plan limit of {limit} entries or squares. The pool owner must upgrade before another can be created.",
        )
