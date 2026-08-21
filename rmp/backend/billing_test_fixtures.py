"""Reusable factories for payment and entitlement contract tests."""

from datetime import datetime
import uuid

import models


PLAN_CAPACITY = {
    "squares-plus": (100, 1, False),
    "commissioner": (50, 1, False),
    "pro": (150, 3, False),
    "club": (500, 5, False),
    "club-unlimited": (None, None, True),
}


def register_and_login(client, email="billing@example.com", password="Test1234!"):
    client.post("/auth/register", json={"email": email, "password": password})
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


def configure_stripe(monkeypatch):
    values = {
        "STRIPE_SECRET_KEY": "sk_test_example",
        "STRIPE_WEBHOOK_SECRET": "whsec_example",
        "STRIPE_PRICE_SQUARES_PLUS": "price_squares_plus",
        "STRIPE_PRICE_COMMISSIONER": "price_commissioner",
        "STRIPE_PRICE_PRO": "price_pro",
        "STRIPE_PRICE_CLUB": "price_club",
        "STRIPE_PRICE_CLUB_UNLIMITED": "price_unlimited",
        "FRONTEND_URL": "https://runmypool.net",
    }
    for key, value in values.items():
        monkeypatch.setenv(key, value)


def grant_entitlement(db, user, plan, *, season=2026):
    included_entries, max_pools, unlimited = PLAN_CAPACITY[plan]
    now = datetime(2026, 8, 1)
    order = models.BillingOrder(
        id=str(uuid.uuid4()), user_id=user.id, season=season, plan=plan,
        status="paid", order_type="plan", quantity=1, created_at=now,
        updated_at=now, paid_at=now,
    )
    entitlement = models.CommissionerEntitlement(
        id=str(uuid.uuid4()), user_id=user.id, season=season, plan=plan,
        status="active", included_entries=included_entries, max_pools=max_pools,
        unlimited_entries=unlimited, entry_block_count=0,
        source_order_id=order.id, activated_at=now, updated_at=now,
    )
    db.add_all([order, entitlement])
    db.commit()
    return entitlement


def checkout_event(order_id, *, event_id="evt_test", event_type="checkout.session.completed", payment_status="paid", amount_total=3900):
    return {
        "id": event_id,
        "type": event_type,
        "data": {"object": {
            "id": "cs_test_matrix", "payment_status": payment_status,
            "payment_intent": "pi_test_matrix", "customer": "cus_test_matrix",
            "amount_total": amount_total, "currency": "usd",
            "metadata": {"order_id": order_id},
        }},
    }
