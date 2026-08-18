"""Automated contract coverage for the manual payment/entitlement matrix."""

from datetime import datetime
from types import SimpleNamespace
import uuid

import pytest
import models
from billing_test_fixtures import (
    auth_headers as _headers,
    checkout_event,
    configure_stripe as _configure_stripe,
    grant_entitlement,
    register_and_login as _register_and_login,
)


DIRECT_PLANS = [
    ("squares-plus", "price_squares_plus"),
    ("commissioner", "price_commissioner"),
    ("pro", "price_pro"),
    ("club", "price_club"),
    ("club-unlimited", "price_unlimited"),
]


@pytest.mark.parametrize("plan,price_id", DIRECT_PLANS)
def test_C01_C04_direct_plan_checkout_contract(client, db_session, monkeypatch, plan, price_id):
    token = _register_and_login(client, f"direct-{plan}@example.com")
    _configure_stripe(monkeypatch)
    captured = {}
    monkeypatch.setattr("billing.stripe.checkout.Session.create", lambda **kwargs: captured.update(kwargs) or SimpleNamespace(id="cs_direct", url="https://checkout.stripe.com/test"))

    response = client.post("/billing/checkout-session", json={"plan": plan, "season": 2026}, headers=_headers(token))

    assert response.status_code == 200
    assert captured["line_items"] == [{"price": price_id, "quantity": 1}]
    order = db_session.query(models.BillingOrder).one()
    assert captured["customer_email"] == f"direct-{plan}@example.com"
    assert captured["client_reference_id"] == order.user_id
    assert captured["metadata"] == {
        "order_id": order.id, "user_id": order.user_id, "plan": plan,
        "season": "2026", "order_type": "plan", "quantity": "1",
    }
    assert captured["payment_intent_data"]["metadata"] == captured["metadata"]


ALLOWED_UPGRADES = [
    ("squares-plus", "commissioner", 2900),
    ("squares-plus", "pro", 6900),
    ("squares-plus", "club", 11900),
    ("commissioner", "pro", 4000),
    ("commissioner", "club", 9000),
    ("pro", "club", 5000),
    ("club", "club-unlimited", 12000),
]


@pytest.mark.parametrize("current,target,amount", ALLOWED_UPGRADES)
def test_E01_E07_allowed_upgrade_difference(client, db_session, monkeypatch, current, target, amount):
    email = f"{current}-to-{target}@example.com"
    token = _register_and_login(client, email)
    user = db_session.query(models.User).filter_by(email=email).one()
    entitlement = grant_entitlement(db_session, user, current)
    _configure_stripe(monkeypatch)
    captured = {}
    monkeypatch.setattr("billing.stripe.checkout.Session.create", lambda **kwargs: captured.update(kwargs) or SimpleNamespace(id="cs_upgrade", url="https://checkout.stripe.com/test"))

    response = client.post("/billing/checkout-session", json={"plan": target, "season": 2026}, headers=_headers(token))

    assert response.status_code == 200
    assert captured["line_items"][0]["price_data"]["unit_amount"] == amount
    db_session.refresh(entitlement)
    assert entitlement.plan == current
    assert db_session.query(models.BillingOrder).filter_by(status="pending", plan=target).count() == 1


@pytest.mark.parametrize("current,target", [
    ("commissioner", "commissioner"), ("pro", "commissioner"),
    ("club", "pro"), ("club-unlimited", "club"),
    ("club-unlimited", "club-unlimited"), ("pro", "club-unlimited"),
])
def test_E05_E08_duplicate_downgrade_and_skipped_unlimited_are_blocked(client, db_session, monkeypatch, current, target):
    email = f"blocked-{current}-{target}@example.com"
    token = _register_and_login(client, email)
    user = db_session.query(models.User).filter_by(email=email).one()
    entitlement = grant_entitlement(db_session, user, current)
    _configure_stripe(monkeypatch)
    monkeypatch.setattr("billing.stripe.checkout.Session.create", lambda **kwargs: pytest.fail("Stripe must not be called"))

    response = client.post("/billing/checkout-session", json={"plan": target, "season": 2026}, headers=_headers(token))

    assert response.status_code == 409
    db_session.refresh(entitlement)
    assert entitlement.plan == current
    assert db_session.query(models.BillingOrder).count() == 1


def test_A03_free_plan_rejects_entry_11(client):
    token = _register_and_login(client, "free-boundary@example.com")
    pool = client.post("/pools/create", json={"name": "Free Boundary"}, headers=_headers(token)).json()
    for number in range(1, 11):
        assert client.post("/entries/create", json={"pool_id": pool["id"], "name": f"Entry {number}"}, headers=_headers(token)).status_code == 200
    blocked = client.post("/entries/create", json={"pool_id": pool["id"], "name": "Entry 11"}, headers=_headers(token))
    assert blocked.status_code == 409
    assert "limit of 10 entries" in blocked.json()["detail"]


def test_I04_expired_checkout_marks_pending_order_without_entitlement(client, db_session, monkeypatch):
    token = _register_and_login(client, "expired-checkout@example.com")
    _configure_stripe(monkeypatch)
    monkeypatch.setattr("billing.stripe.checkout.Session.create", lambda **kwargs: SimpleNamespace(id="cs_expired", url="https://checkout.stripe.com/test"))
    checkout = client.post("/billing/checkout-session", json={"plan": "pro", "season": 2026}, headers=_headers(token))
    order = db_session.query(models.BillingOrder).filter_by(id=checkout.json()["order_id"]).one()
    event = checkout_event(order.id, event_id="evt_expired", event_type="checkout.session.expired", payment_status="unpaid")
    monkeypatch.setattr("billing.stripe.Webhook.construct_event", lambda *args: event)

    assert client.post("/billing/webhook", content=b"{}", headers={"stripe-signature": "valid"}).status_code == 200
    db_session.refresh(order)
    assert order.status == "expired"
    assert db_session.query(models.CommissionerEntitlement).count() == 0


def test_I02_distinct_paid_events_for_same_order_fulfill_once(client, db_session, monkeypatch):
    token = _register_and_login(client, "event-idempotency@example.com")
    _configure_stripe(monkeypatch)
    monkeypatch.setattr("billing.stripe.checkout.Session.create", lambda **kwargs: SimpleNamespace(id="cs_idempotent", url="https://checkout.stripe.com/test"))
    checkout = client.post("/billing/checkout-session", json={"plan": "club", "season": 2026}, headers=_headers(token))
    order_id = checkout.json()["order_id"]
    events = iter([checkout_event(order_id, event_id="evt_paid_a", amount_total=12900), checkout_event(order_id, event_id="evt_paid_b", amount_total=12900)])
    monkeypatch.setattr("billing.stripe.Webhook.construct_event", lambda *args: next(events))

    assert client.post("/billing/webhook", content=b"{}", headers={"stripe-signature": "valid"}).status_code == 200
    assert client.post("/billing/webhook", content=b"{}", headers={"stripe-signature": "valid"}).status_code == 200
    assert db_session.query(models.CommissionerEntitlement).count() == 1
    assert db_session.query(models.AuditLog).filter_by(action="BILLING_PLAN_ACTIVATED").count() == 1


def test_F02_club_allows_five_pools_and_rejects_sixth(client, db_session):
    token = _register_and_login(client, "club-pools@example.com")
    user = db_session.query(models.User).filter_by(email="club-pools@example.com").one()
    grant_entitlement(db_session, user, "club")
    for number in range(1, 6):
        response = client.post("/pools/create", json={"name": f"Club Pool {number}"}, headers=_headers(token))
        assert response.status_code == 200
    blocked = client.post("/pools/create", json={"name": "Club Pool 6"}, headers=_headers(token))
    assert blocked.status_code == 409
    assert "allows 5 active pool" in blocked.json()["detail"]


def test_F03_club_entry_500_succeeds_and_501_is_shared_across_pools(client, db_session):
    token = _register_and_login(client, "club-entries@example.com")
    user = db_session.query(models.User).filter_by(email="club-entries@example.com").one()
    entitlement = grant_entitlement(db_session, user, "club")
    pools = []
    for number in range(1, 4):
        pools.append(client.post("/pools/create", json={"name": f"Shared Club {number}"}, headers=_headers(token)).json())
    for number in range(499):
        pool = pools[number % len(pools)]
        db_session.add(models.Entry(id=str(uuid.uuid4()), user_id=user.id, pool_id=pool["id"], name=f"Seed {number}", alive=True, created_at=datetime(2026, 8, 1)))
    db_session.commit()

    allowed = client.post("/entries/create", json={"pool_id": pools[1]["id"], "name": "Entry 500"}, headers=_headers(token))
    blocked = client.post("/entries/create", json={"pool_id": pools[2]["id"], "name": "Entry 501"}, headers=_headers(token))

    assert allowed.status_code == 200
    assert blocked.status_code == 409
    assert "limit of 500 entries" in blocked.json()["detail"]
    assert db_session.query(models.Entry).join(models.Pool).filter(models.Pool.billing_entitlement_id == entitlement.id).count() == 500


def test_F04_club_unlimited_exceeds_five_pools_and_500_entries(client, db_session):
    token = _register_and_login(client, "unlimited-boundary@example.com")
    user = db_session.query(models.User).filter_by(email="unlimited-boundary@example.com").one()
    grant_entitlement(db_session, user, "club-unlimited")
    pools = []
    for number in range(1, 7):
        response = client.post("/pools/create", json={"name": f"Unlimited Pool {number}"}, headers=_headers(token))
        assert response.status_code == 200
        pools.append(response.json())
    for number in range(500):
        db_session.add(models.Entry(id=str(uuid.uuid4()), user_id=user.id, pool_id=pools[number % 6]["id"], name=f"Unlimited Seed {number}", alive=True, created_at=datetime(2026, 8, 1)))
    db_session.commit()
    entry_501 = client.post("/entries/create", json={"pool_id": pools[5]["id"], "name": "Unlimited 501"}, headers=_headers(token))
    assert entry_501.status_code == 200
