from types import SimpleNamespace

import models


def _register_and_login(client, email="billing@example.com", password="Test1234!"):
    client.post("/auth/register", json={"email": email, "password": password})
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]


def _headers(token):
    return {"Authorization": f"Bearer {token}"}


def _configure_stripe(monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_example")
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_example")
    monkeypatch.setenv("STRIPE_PRICE_COMMISSIONER", "price_commissioner")
    monkeypatch.setenv("STRIPE_PRICE_PRO", "price_pro")
    monkeypatch.setenv("STRIPE_PRICE_CLUB", "price_club")
    monkeypatch.setenv("STRIPE_PRICE_CLUB_UNLIMITED", "price_unlimited")
    monkeypatch.setenv("FRONTEND_URL", "https://runmypool.net")


def _checkout(client, monkeypatch, token, plan="club"):
    _configure_stripe(monkeypatch)
    captured = {}

    def create_session(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(id="cs_test_123", url="https://checkout.stripe.com/test")

    monkeypatch.setattr("billing.stripe.checkout.Session.create", create_session)
    response = client.post(
        "/billing/checkout-session",
        json={"plan": plan, "season": 2026},
        headers=_headers(token),
    )
    return response, captured


class TestCommissionerBilling:
    def test_checkout_requires_authentication(self, client):
        response = client.post("/billing/checkout-session", json={"plan": "club", "season": 2026})
        assert response.status_code in (401, 403)

    def test_checkout_uses_server_side_price_and_order_metadata(self, client, db_session, monkeypatch):
        token = _register_and_login(client)
        response, captured = _checkout(client, monkeypatch, token)

        assert response.status_code == 200
        assert response.json()["checkout_url"] == "https://checkout.stripe.com/test"
        assert captured["mode"] == "payment"
        assert captured["line_items"] == [{"price": "price_club", "quantity": 1}]
        assert captured["success_url"].endswith("session_id={CHECKOUT_SESSION_ID}")
        assert captured["metadata"]["plan"] == "club"
        order = db_session.query(models.BillingOrder).one()
        assert captured["metadata"]["order_id"] == order.id
        assert order.status == "pending"

    def test_unknown_plan_is_rejected_before_contacting_stripe(self, client, monkeypatch):
        token = _register_and_login(client)
        _configure_stripe(monkeypatch)
        response = client.post(
            "/billing/checkout-session",
            json={"plan": "custom-price", "season": 2026},
            headers=_headers(token),
        )
        assert response.status_code == 400

    def test_paid_webhook_activates_entitlement_once(self, client, db_session, monkeypatch):
        token = _register_and_login(client)
        checkout_response, captured = _checkout(client, monkeypatch, token, plan="club-unlimited")
        assert checkout_response.status_code == 200
        order_id = captured["metadata"]["order_id"]
        event = {
            "id": "evt_paid_123",
            "type": "checkout.session.completed",
            "data": {"object": {
                "id": "cs_test_123",
                "payment_status": "paid",
                "payment_intent": "pi_test_123",
                "customer": "cus_test_123",
                "amount_total": 24900,
                "currency": "usd",
                "metadata": {"order_id": order_id},
            }},
        }
        monkeypatch.setattr("billing.stripe.Webhook.construct_event", lambda payload, signature, secret: event)

        first = client.post("/billing/webhook", content=b"{}", headers={"stripe-signature": "valid"})
        second = client.post("/billing/webhook", content=b"{}", headers={"stripe-signature": "valid"})

        assert first.status_code == 200
        assert second.json()["duplicate"] is True
        entitlement = db_session.query(models.CommissionerEntitlement).one()
        assert entitlement.plan == "club-unlimited"
        assert entitlement.unlimited_entries is True
        assert entitlement.max_pools is None
        assert db_session.query(models.StripeWebhookEvent).count() == 1

    def test_unpaid_completed_webhook_does_not_activate_access(self, client, db_session, monkeypatch):
        token = _register_and_login(client)
        _, captured = _checkout(client, monkeypatch, token)
        event = {
            "id": "evt_unpaid_123",
            "type": "checkout.session.completed",
            "data": {"object": {"id": "cs_test_123", "payment_status": "unpaid", "metadata": {"order_id": captured["metadata"]["order_id"]}}},
        }
        monkeypatch.setattr("billing.stripe.Webhook.construct_event", lambda payload, signature, secret: event)

        response = client.post("/billing/webhook", content=b"{}", headers={"stripe-signature": "valid"})

        assert response.status_code == 200
        assert db_session.query(models.CommissionerEntitlement).count() == 0
        assert db_session.query(models.BillingOrder).one().status == "pending"

    def test_invalid_webhook_signature_is_rejected(self, client, monkeypatch):
        _configure_stripe(monkeypatch)

        def reject(*args):
            raise ValueError("bad signature")

        monkeypatch.setattr("billing.stripe.Webhook.construct_event", reject)
        response = client.post("/billing/webhook", content=b"{}", headers={"stripe-signature": "invalid"})
        assert response.status_code == 400

    def test_session_status_is_scoped_to_the_authenticated_user(self, client, monkeypatch):
        owner_token = _register_and_login(client, "billing-owner@example.com")
        other_token = _register_and_login(client, "billing-other@example.com")
        checkout_response, _ = _checkout(client, monkeypatch, owner_token)
        session_id = checkout_response.json()["session_id"]

        owner = client.get(f"/billing/session/{session_id}", headers=_headers(owner_token))
        other = client.get(f"/billing/session/{session_id}", headers=_headers(other_token))

        assert owner.status_code == 200
        assert owner.json()["status"] == "pending"
        assert other.status_code == 404
