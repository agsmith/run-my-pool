"""Test helpers for scenarios that intentionally create several pools."""

import uuid
from datetime import datetime, timezone

import models
from sqlalchemy import func

from entitlements import current_season
from tests.conftest import TestingSessionLocal


def grant_unlimited_pool_creations(email: str) -> None:
    """Give a test user an unlimited plan without exercising Stripe."""
    db = TestingSessionLocal()
    try:
        user = (
            db.query(models.User)
            .filter(func.lower(models.User.email) == email.strip().lower())
            .one()
        )
        season = current_season()
        existing = (
            db.query(models.CommissionerEntitlement)
            .filter_by(user_id=user.id, season=season)
            .first()
        )
        if existing:
            return

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        order = models.BillingOrder(
            id=str(uuid.uuid4()),
            user_id=user.id,
            season=season,
            plan="club-unlimited",
            status="paid",
            created_at=now,
            updated_at=now,
        )
        db.add(order)
        db.add(
            models.CommissionerEntitlement(
                id=str(uuid.uuid4()),
                user_id=user.id,
                season=season,
                plan="club-unlimited",
                status="active",
                included_entries=None,
                entry_block_count=0,
                max_pools=None,
                unlimited_entries=True,
                source_order_id=order.id,
                activated_at=now,
                updated_at=now,
            )
        )
        db.commit()
    finally:
        db.close()
