"""MySQL-only concurrency tests for final entitlement capacity slots."""

from datetime import datetime
import os
import threading
import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import entitlements
import models


MYSQL_URL = os.getenv("MYSQL_INTEGRATION_URL")
pytestmark = pytest.mark.skipif(not MYSQL_URL, reason="MYSQL_INTEGRATION_URL is not configured")


@pytest.fixture()
def mysql_sessions():
    engine = create_engine(MYSQL_URL, pool_pre_ping=True)
    models.Base.metadata.drop_all(engine)
    models.Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    yield sessions
    models.Base.metadata.drop_all(engine)
    engine.dispose()


def seed_entitlement(sessions, *, max_pools=1, included_entries=1):
    db = sessions()
    now = datetime(2026, 8, 1)
    user = models.User(id=str(uuid.uuid4()), email=f"mysql-{uuid.uuid4()}@example.com", hashed_password="unused", is_active=True, created_at=now, updated_at=now)
    order = models.BillingOrder(id=str(uuid.uuid4()), user_id=user.id, plan="pro", season=2026, status="paid", order_type="plan", quantity=1, created_at=now, updated_at=now)
    entitlement = models.CommissionerEntitlement(id=str(uuid.uuid4()), user_id=user.id, season=2026, plan="pro", status="active", included_entries=included_entries, entry_block_count=0, max_pools=max_pools, unlimited_entries=False, source_order_id=order.id, activated_at=now, updated_at=now)
    db.add_all([user, order, entitlement])
    db.commit()
    db.close()
    return user.id, entitlement.id


def test_F05_concurrent_requests_cannot_consume_one_pool_slot_twice(mysql_sessions):
    user_id, entitlement_id = seed_entitlement(mysql_sessions)
    barrier = threading.Barrier(2)
    results = []

    def create_pool(number):
        db = mysql_sessions()
        try:
            barrier.wait()
            entitlement = entitlements.entitlement_for_new_pool(db, user_id, 2026)
            db.add(models.Pool(id=str(uuid.uuid4()), name=f"Concurrent {number}", pool_type="survivor", owner_id=user_id, billing_entitlement_id=entitlement.id, billing_season=2026, created_at=datetime(2026, 8, 1), updated_at=datetime(2026, 8, 1)))
            db.commit()
            results.append("created")
        except HTTPException:
            db.rollback()
            results.append("blocked")
        finally:
            db.close()

    threads = [threading.Thread(target=create_pool, args=(number,)) for number in (1, 2)]
    for thread in threads: thread.start()
    for thread in threads: thread.join()

    db = mysql_sessions()
    assert sorted(results) == ["blocked", "created"]
    assert db.query(models.Pool).filter_by(billing_entitlement_id=entitlement_id).count() == 1
    db.close()


def test_F03_concurrent_requests_cannot_exceed_final_entry_slot(mysql_sessions):
    user_id, entitlement_id = seed_entitlement(mysql_sessions)
    db = mysql_sessions()
    pool = models.Pool(id=str(uuid.uuid4()), name="Concurrent Entries", pool_type="survivor", owner_id=user_id, billing_entitlement_id=entitlement_id, billing_season=2026, created_at=datetime(2026, 8, 1), updated_at=datetime(2026, 8, 1))
    db.add(pool); db.commit(); pool_id = pool.id; db.close()
    barrier = threading.Barrier(2)
    results = []

    def create_entry(number):
        session = mysql_sessions()
        try:
            barrier.wait()
            current_pool = session.query(models.Pool).filter_by(id=pool_id).one()
            entitlements.enforce_entry_capacity(session, current_pool)
            session.add(models.Entry(id=str(uuid.uuid4()), user_id=user_id, pool_id=pool_id, name=f"Concurrent Entry {number}", alive=True, created_at=datetime(2026, 8, 1)))
            session.commit(); results.append("created")
        except HTTPException:
            session.rollback(); results.append("blocked")
        finally:
            session.close()

    threads = [threading.Thread(target=create_entry, args=(number,)) for number in (1, 2)]
    for thread in threads: thread.start()
    for thread in threads: thread.join()
    db = mysql_sessions()
    assert sorted(results) == ["blocked", "created"]
    assert db.query(models.Entry).filter_by(pool_id=pool_id).count() == 1
    db.close()
