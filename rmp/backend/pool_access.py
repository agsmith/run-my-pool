from sqlalchemy.orm import Session

import entitlements
import models


def is_pool_participant(db: Session, pool_id: str, user_id: str) -> bool:
    """Return whether a user may access player-facing data for a pool."""
    pool = db.query(models.Pool).filter(models.Pool.id == pool_id).first()
    if not pool:
        return False
    if (
        pool.pool_type == "squares"
        and entitlements.pool_plan(db, pool) == "free"
        and pool.owner_id != user_id
    ):
        return False
    return bool(
        pool.owner_id == user_id
        or db.query(models.PoolAdmin.pool_id).filter(
            models.PoolAdmin.pool_id == pool_id, models.PoolAdmin.user_id == user_id
        ).first()
        or db.query(models.PoolMember.pool_id).filter(
            models.PoolMember.pool_id == pool_id, models.PoolMember.user_id == user_id
        ).first()
        or db.query(models.Entry.id).filter(
            models.Entry.pool_id == pool_id, models.Entry.user_id == user_id
        ).first()
    )
