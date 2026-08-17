from datetime import datetime
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
    monkeypatch.setenv("STRIPE_PRICE_SQUARES_PLUS", "price_squares_plus")
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
    def test_squares_plus_uses_ten_dollar_stripe_price(self, client, monkeypatch):
        token = _register_and_login(client, "squares-plus@example.com")
        response, captured = _checkout(client, monkeypatch, token, plan="squares-plus")

        assert response.status_code == 200
        assert captured["line_items"] == [{"price": "price_squares_plus", "quantity": 1}]

    def test_squares_plus_upgrades_to_commish_for_twenty_nine_dollars(
        self, client, db_session, monkeypatch
    ):
        token = _register_and_login(client, "squares-plus-upgrade@example.com")
        user = db_session.query(models.User).filter_by(email="squares-plus-upgrade@example.com").one()
        now = datetime(2026, 8, 1)
        order = models.BillingOrder(
            id="squares-plus-paid-order", user_id=user.id, season=2026,
            plan="squares-plus", status="paid", created_at=now, updated_at=now,
        )
        db_session.add(order)
        db_session.add(models.CommissionerEntitlement(
            id="squares-plus-paid-entitlement", user_id=user.id, season=2026,
            plan="squares-plus", status="active", included_entries=100, max_pools=1,
            unlimited_entries=False, source_order_id=order.id, activated_at=now, updated_at=now,
        ))
        db_session.commit()

        response, captured = _checkout(client, monkeypatch, token, plan="commissioner")

        assert response.status_code == 200
        assert captured["line_items"][0]["price_data"]["unit_amount"] == 2900

    def test_checkout_requires_authentication(self, client):
        response = client.post(
            "/billing/checkout-session", json={"plan": "club", "season": 2026}
        )
        assert response.status_code in (401, 403)

    def test_checkout_uses_server_side_price_and_order_metadata(
        self, client, db_session, monkeypatch
    ):
        token = _register_and_login(client)
        response, captured = _checkout(client, monkeypatch, token)

        assert response.status_code == 200
        assert response.json()["checkout_url"] == "https://checkout.stripe.com/test"
        assert captured["mode"] == "payment"
        assert captured["line_items"] == [{"price": "price_club", "quantity": 1}]
        assert captured["success_url"].endswith("session_id={CHECKOUT_SESSION_ID}")
        assert "/checkout/success?" in captured["success_url"]
        assert captured["cancel_url"].endswith("/pricing?checkout=cancelled&plan=club")
        assert captured["metadata"]["plan"] == "club"
        order = db_session.query(models.BillingOrder).one()
        assert captured["metadata"]["order_id"] == order.id
        assert order.status == "pending"

    def test_legacy_billing_success_redirects_to_frontend_checkout_page(self, client):
        response = client.get(
            "/billing/success?session_id=cs_test_existing", follow_redirects=False
        )

        assert response.status_code == 307
        assert response.headers["location"] == (
            "https://runmypool.net/checkout/success?session_id=cs_test_existing"
        )

    def test_unknown_plan_is_rejected_before_contacting_stripe(
        self, client, monkeypatch
    ):
        token = _register_and_login(client)
        _configure_stripe(monkeypatch)
        response = client.post(
            "/billing/checkout-session",
            json={"plan": "custom-price", "season": 2026},
            headers=_headers(token),
        )
        assert response.status_code == 400

    def test_club_can_upgrade_to_club_unlimited_for_difference(
        self, client, db_session, monkeypatch
    ):
        token = _register_and_login(client, "club-owner@example.com")
        user = (
            db_session.query(models.User)
            .filter(models.User.email == "club-owner@example.com")
            .one()
        )
        order = models.BillingOrder(
            id="club-order",
            user_id=user.id,
            season=2026,
            plan="club",
            status="paid",
            created_at=datetime(2026, 8, 1),
            updated_at=datetime(2026, 8, 1),
        )
        db_session.add(order)
        db_session.add(
            models.CommissionerEntitlement(
                id="club-entitlement",
                user_id=user.id,
                season=2026,
                plan="club",
                status="active",
                included_entries=500,
                max_pools=5,
                unlimited_entries=False,
                source_order_id=order.id,
                activated_at=datetime(2026, 8, 1),
                updated_at=datetime(2026, 8, 1),
            )
        )
        db_session.commit()
        response, captured = _checkout(
            client, monkeypatch, token, plan="club-unlimited"
        )

        assert response.status_code == 200
        assert captured["line_items"][0]["price_data"]["unit_amount"] == 12000
        assert db_session.query(models.BillingOrder).count() == 2

    def test_lower_paid_tier_cannot_skip_directly_to_club_unlimited(
        self, client, db_session, monkeypatch
    ):
        token = _register_and_login(client, "pro-owner@example.com")
        user = (
            db_session.query(models.User).filter_by(email="pro-owner@example.com").one()
        )
        order = models.BillingOrder(
            id="pro-order",
            user_id=user.id,
            season=2026,
            plan="pro",
            status="paid",
            created_at=datetime(2026, 8, 1),
            updated_at=datetime(2026, 8, 1),
        )
        db_session.add_all(
            [
                order,
                models.CommissionerEntitlement(
                    id="pro-entitlement",
                    user_id=user.id,
                    season=2026,
                    plan="pro",
                    status="active",
                    included_entries=150,
                    max_pools=1,
                    unlimited_entries=False,
                    source_order_id=order.id,
                    activated_at=datetime(2026, 8, 1),
                    updated_at=datetime(2026, 8, 1),
                ),
            ]
        )
        db_session.commit()
        _configure_stripe(monkeypatch)

        response = client.post(
            "/billing/checkout-session",
            json={"plan": "club-unlimited", "season": 2026},
            headers=_headers(token),
        )

        assert response.status_code == 409
        assert "upgrade from Club" in response.json()["detail"]

    def test_paid_webhook_activates_entitlement_once(
        self, client, db_session, monkeypatch
    ):
        token = _register_and_login(client)
        checkout_response, captured = _checkout(
            client, monkeypatch, token, plan="club-unlimited"
        )
        assert checkout_response.status_code == 200
        order_id = captured["metadata"]["order_id"]
        event = {
            "id": "evt_paid_123",
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_test_123",
                    "payment_status": "paid",
                    "payment_intent": "pi_test_123",
                    "customer": "cus_test_123",
                    "amount_total": 24900,
                    "currency": "usd",
                    "metadata": {"order_id": order_id},
                }
            },
        }
        monkeypatch.setattr(
            "billing.stripe.Webhook.construct_event",
            lambda payload, signature, secret: event,
        )

        first = client.post(
            "/billing/webhook", content=b"{}", headers={"stripe-signature": "valid"}
        )
        second = client.post(
            "/billing/webhook", content=b"{}", headers={"stripe-signature": "valid"}
        )

        assert first.status_code == 200
        assert second.json()["duplicate"] is True
        entitlement = db_session.query(models.CommissionerEntitlement).one()
        assert entitlement.plan == "club-unlimited"
        assert entitlement.unlimited_entries is True
        assert entitlement.max_pools is None
        assert db_session.query(models.StripeWebhookEvent).count() == 1

    def test_paid_webhook_persists_entitlement_on_existing_pool(
        self, client, db_session, monkeypatch
    ):
        token = _register_and_login(client, "existing-pool-owner@example.com")
        pool_response = client.post(
            "/pools/create",
            json={"name": "Existing Paid Pool"},
            headers=_headers(token),
        )
        assert pool_response.status_code == 200

        _, captured = _checkout(client, monkeypatch, token, plan="commissioner")
        event = {
            "id": "evt_attach_existing_pool",
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_test_123",
                    "payment_status": "paid",
                    "metadata": {"order_id": captured["metadata"]["order_id"]},
                }
            },
        }
        monkeypatch.setattr(
            "billing.stripe.Webhook.construct_event",
            lambda payload, signature, secret: event,
        )

        response = client.post(
            "/billing/webhook", content=b"{}", headers={"stripe-signature": "valid"}
        )

        assert response.status_code == 200
        entitlement = db_session.query(models.CommissionerEntitlement).one()
        pool = db_session.query(models.Pool).filter_by(name="Existing Paid Pool").one()
        assert pool.billing_entitlement_id == entitlement.id
        assert pool.billing_season == 2026

    def test_new_pool_persists_active_paid_entitlement(self, client, db_session):
        token = _register_and_login(client, "paid-before-pool@example.com")
        user = (
            db_session.query(models.User)
            .filter_by(email="paid-before-pool@example.com")
            .one()
        )
        order = models.BillingOrder(
            id="paid-before-pool-order",
            user_id=user.id,
            season=2026,
            plan="pro",
            status="paid",
            created_at=datetime(2026, 8, 1),
            updated_at=datetime(2026, 8, 1),
        )
        entitlement = models.CommissionerEntitlement(
            id="paid-before-pool-entitlement",
            user_id=user.id,
            season=2026,
            plan="pro",
            status="active",
            included_entries=150,
            max_pools=1,
            unlimited_entries=False,
            source_order_id=order.id,
            activated_at=datetime(2026, 8, 1),
            updated_at=datetime(2026, 8, 1),
        )
        db_session.add_all([order, entitlement])
        db_session.commit()

        response = client.post(
            "/pools/create", json={"name": "New Paid Pool"}, headers=_headers(token)
        )

        assert response.status_code == 200
        assert response.json()["billing_entitlement_id"] == entitlement.id
        assert response.json()["billing_season"] == 2026

    def test_squares_plus_rejects_survivor_and_pickem_pool_creation(
        self, client, db_session
    ):
        token = _register_and_login(client, "squares-only-owner@example.com")
        user = (
            db_session.query(models.User)
            .filter_by(email="squares-only-owner@example.com")
            .one()
        )
        now = datetime(2026, 8, 1)
        order = models.BillingOrder(
            id="squares-only-order",
            user_id=user.id,
            season=2026,
            plan="squares-plus",
            status="paid",
            created_at=now,
            updated_at=now,
        )
        entitlement = models.CommissionerEntitlement(
            id="squares-only-entitlement",
            user_id=user.id,
            season=2026,
            plan="squares-plus",
            status="active",
            included_entries=100,
            max_pools=1,
            unlimited_entries=False,
            source_order_id=order.id,
            activated_at=now,
            updated_at=now,
        )
        db_session.add_all([order, entitlement])
        db_session.commit()

        survivor = client.post(
            "/pools/create",
            json={"name": "Blocked Survivor", "pool_type": "survivor"},
            headers=_headers(token),
        )
        pickem = client.post(
            "/pools/create",
            json={"name": "Blocked Pick Em", "pool_type": "pickem"},
            headers=_headers(token),
        )

        assert survivor.status_code == 409
        assert pickem.status_code == 409
        assert "supports one Squares board" in survivor.json()["detail"]
        assert "supports one Squares board" in pickem.json()["detail"]
        assert db_session.query(models.Pool).filter_by(owner_id=user.id).count() == 0

    def test_paid_plan_pool_limit_is_enforced_server_side(self, client, db_session):
        token = _register_and_login(client, "one-pool-plan@example.com")
        user = (
            db_session.query(models.User)
            .filter_by(email="one-pool-plan@example.com")
            .one()
        )
        order = models.BillingOrder(
            id="one-pool-order",
            user_id=user.id,
            season=2026,
            plan="commissioner",
            status="paid",
            created_at=datetime(2026, 8, 1),
            updated_at=datetime(2026, 8, 1),
        )
        db_session.add(order)
        db_session.add(
            models.CommissionerEntitlement(
                id="one-pool-entitlement",
                user_id=user.id,
                season=2026,
                plan="commissioner",
                status="active",
                included_entries=50,
                max_pools=1,
                unlimited_entries=False,
                source_order_id=order.id,
                activated_at=datetime(2026, 8, 1),
                updated_at=datetime(2026, 8, 1),
            )
        )
        db_session.commit()

        first = client.post(
            "/pools/create", json={"name": "Allowed Pool"}, headers=_headers(token)
        )
        second = client.post(
            "/pools/create", json={"name": "Blocked Pool"}, headers=_headers(token)
        )

        assert first.status_code == 200
        assert second.status_code == 409
        assert "allows 1 active pool" in second.json()["detail"]

    def test_entry_limit_uses_persisted_pool_entitlement(self, client, db_session):
        token = _register_and_login(client, "capacity-owner@example.com")
        user = (
            db_session.query(models.User)
            .filter_by(email="capacity-owner@example.com")
            .one()
        )
        order = models.BillingOrder(
            id="capacity-order",
            user_id=user.id,
            season=2026,
            plan="commissioner",
            status="paid",
            created_at=datetime(2026, 8, 1),
            updated_at=datetime(2026, 8, 1),
        )
        db_session.add(order)
        db_session.add(
            models.CommissionerEntitlement(
                id="capacity-entitlement",
                user_id=user.id,
                season=2026,
                plan="commissioner",
                status="active",
                included_entries=2,
                max_pools=1,
                unlimited_entries=False,
                source_order_id=order.id,
                activated_at=datetime(2026, 8, 1),
                updated_at=datetime(2026, 8, 1),
            )
        )
        db_session.commit()
        pool = client.post(
            "/pools/create", json={"name": "Capacity Pool"}, headers=_headers(token)
        ).json()

        first = client.post(
            "/entries/create",
            json={"pool_id": pool["id"], "name": "One"},
            headers=_headers(token),
        )
        second = client.post(
            "/entries/create",
            json={"pool_id": pool["id"], "name": "Two"},
            headers=_headers(token),
        )
        blocked = client.post(
            "/entries/create",
            json={"pool_id": pool["id"], "name": "Three"},
            headers=_headers(token),
        )

        assert first.status_code == second.status_code == 200
        assert blocked.status_code == 409
        assert "plan limit of 2 entries" in blocked.json()["detail"]

    def test_unpaid_completed_webhook_does_not_activate_access(
        self, client, db_session, monkeypatch
    ):
        token = _register_and_login(client)
        _, captured = _checkout(client, monkeypatch, token)
        event = {
            "id": "evt_unpaid_123",
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_test_123",
                    "payment_status": "unpaid",
                    "metadata": {"order_id": captured["metadata"]["order_id"]},
                }
            },
        }
        monkeypatch.setattr(
            "billing.stripe.Webhook.construct_event",
            lambda payload, signature, secret: event,
        )

        response = client.post(
            "/billing/webhook", content=b"{}", headers={"stripe-signature": "valid"}
        )

        assert response.status_code == 200
        assert db_session.query(models.CommissionerEntitlement).count() == 0
        assert db_session.query(models.BillingOrder).one().status == "pending"

    def test_invalid_webhook_signature_is_rejected(self, client, monkeypatch):
        _configure_stripe(monkeypatch)

        def reject(*args):
            raise ValueError("bad signature")

        monkeypatch.setattr("billing.stripe.Webhook.construct_event", reject)
        response = client.post(
            "/billing/webhook", content=b"{}", headers={"stripe-signature": "invalid"}
        )
        assert response.status_code == 400

    def test_session_status_is_scoped_to_the_authenticated_user(
        self, client, monkeypatch
    ):
        owner_token = _register_and_login(client, "billing-owner@example.com")
        other_token = _register_and_login(client, "billing-other@example.com")
        checkout_response, _ = _checkout(client, monkeypatch, owner_token)
        session_id = checkout_response.json()["session_id"]

        owner = client.get(
            f"/billing/session/{session_id}", headers=_headers(owner_token)
        )
        other = client.get(
            f"/billing/session/{session_id}", headers=_headers(other_token)
        )

        assert owner.status_code == 200
        assert owner.json()["status"] == "pending"
        assert other.status_code == 404

    def test_billing_overview_is_scoped_to_authenticated_user(
        self, client, db_session, monkeypatch
    ):
        owner_token = _register_and_login(client, "overview-owner@example.com")
        other_token = _register_and_login(client, "overview-other@example.com")
        _, captured = _checkout(client, monkeypatch, owner_token, plan="pro")
        order = (
            db_session.query(models.BillingOrder)
            .filter(models.BillingOrder.id == captured["metadata"]["order_id"])
            .one()
        )
        order.status = "paid"
        order.amount_total = 7900
        order.currency = "usd"
        order.paid_at = datetime(2026, 8, 12)
        db_session.add(
            models.CommissionerEntitlement(
                id="overview-entitlement",
                user_id=order.user_id,
                season=2026,
                plan="pro",
                status="active",
                included_entries=150,
                max_pools=1,
                unlimited_entries=False,
                source_order_id=order.id,
                activated_at=datetime(2026, 8, 12),
                updated_at=datetime(2026, 8, 12),
            )
        )
        db_session.commit()

        owner = client.get(
            "/billing/overview?season=2026", headers=_headers(owner_token)
        )
        other = client.get(
            "/billing/overview?season=2026", headers=_headers(other_token)
        )

        assert owner.status_code == 200
        assert owner.json()["entitlement"]["plan"] == "pro"
        assert owner.json()["orders"][0]["amount_total"] == 7900
        assert owner.json()["orders"][0]["created_at"] is not None
        assert other.status_code == 200
        assert other.json() == {
            "season": 2026,
            "entitlement": None,
            "orders": [],
            "used_entries": 0,
        }

    def test_billing_overview_requires_authentication(self, client):
        response = client.get("/billing/overview?season=2026")
        assert response.status_code in (401, 403)

    def test_upgrade_checkout_charges_only_plan_difference(
        self, client, db_session, monkeypatch
    ):
        token = _register_and_login(client, "upgrade-owner@example.com")
        user = (
            db_session.query(models.User)
            .filter_by(email="upgrade-owner@example.com")
            .one()
        )
        paid_order = models.BillingOrder(
            id="commissioner-order",
            user_id=user.id,
            season=2026,
            plan="commissioner",
            status="paid",
            created_at=datetime(2026, 8, 1),
            updated_at=datetime(2026, 8, 1),
        )
        db_session.add(paid_order)
        db_session.add(
            models.CommissionerEntitlement(
                id="commissioner-entitlement",
                user_id=user.id,
                season=2026,
                plan="commissioner",
                status="active",
                included_entries=50,
                max_pools=1,
                unlimited_entries=False,
                source_order_id=paid_order.id,
                activated_at=datetime(2026, 8, 1),
                updated_at=datetime(2026, 8, 1),
            )
        )
        db_session.commit()

        response, captured = _checkout(client, monkeypatch, token, plan="pro")

        assert response.status_code == 200
        assert captured["line_items"] == [
            {
                "price_data": {
                    "currency": "usd",
                    "unit_amount": 4000,
                    "product_data": {
                        "name": "Run My Pool commissioner to pro upgrade (2026)"
                    },
                },
                "quantity": 1,
            }
        ]
        order = db_session.query(models.BillingOrder).filter_by(status="pending").one()
        assert order.order_type == "plan"
        assert order.quantity == 1

    def test_club_entry_blocks_require_active_club(self, client, monkeypatch):
        token = _register_and_login(client, "not-club@example.com")
        _configure_stripe(monkeypatch)

        response = client.post(
            "/billing/checkout-session",
            json={"order_type": "entry_blocks", "quantity": 1, "season": 2026},
            headers=_headers(token),
        )

        assert response.status_code == 409
        assert "active Club plan" in response.json()["detail"]

    def test_club_entry_blocks_charge_by_quantity_and_fulfill_once(
        self, client, db_session, monkeypatch
    ):
        token = _register_and_login(client, "club-blocks@example.com")
        user = (
            db_session.query(models.User)
            .filter_by(email="club-blocks@example.com")
            .one()
        )
        paid_order = models.BillingOrder(
            id="original-club-order",
            user_id=user.id,
            season=2026,
            plan="club",
            status="paid",
            created_at=datetime(2026, 8, 1),
            updated_at=datetime(2026, 8, 1),
        )
        entitlement = models.CommissionerEntitlement(
            id="club-block-entitlement",
            user_id=user.id,
            season=2026,
            plan="club",
            status="active",
            included_entries=500,
            entry_block_count=0,
            max_pools=5,
            unlimited_entries=False,
            source_order_id=paid_order.id,
            activated_at=datetime(2026, 8, 1),
            updated_at=datetime(2026, 8, 1),
        )
        db_session.add_all([paid_order, entitlement])
        db_session.commit()
        _configure_stripe(monkeypatch)
        captured = {}
        monkeypatch.setattr(
            "billing.stripe.checkout.Session.create",
            lambda **kwargs: captured.update(kwargs)
            or SimpleNamespace(
                id="cs_blocks", url="https://checkout.stripe.com/blocks"
            ),
        )

        checkout_response = client.post(
            "/billing/checkout-session",
            json={"order_type": "entry_blocks", "quantity": 3, "season": 2026},
            headers=_headers(token),
        )
        assert checkout_response.status_code == 200
        assert captured["line_items"][0]["price_data"]["unit_amount"] == 2500
        assert captured["line_items"][0]["quantity"] == 3
        assert (
            captured["cancel_url"] == "https://runmypool.net/profile?checkout=cancelled"
        )
        order_id = checkout_response.json()["order_id"]

        def event(event_id):
            return {
                "id": event_id,
                "type": "checkout.session.completed",
                "data": {
                    "object": {
                        "id": "cs_blocks",
                        "payment_status": "paid",
                        "amount_total": 7500,
                        "currency": "usd",
                        "metadata": {"order_id": order_id},
                    }
                },
            }

        monkeypatch.setattr(
            "billing.stripe.Webhook.construct_event",
            lambda payload, signature, secret: event("evt_blocks_1"),
        )
        first = client.post(
            "/billing/webhook", content=b"{}", headers={"stripe-signature": "valid"}
        )
        monkeypatch.setattr(
            "billing.stripe.Webhook.construct_event",
            lambda payload, signature, secret: event("evt_blocks_2"),
        )
        second = client.post(
            "/billing/webhook", content=b"{}", headers={"stripe-signature": "valid"}
        )

        assert first.status_code == second.status_code == 200
        db_session.refresh(entitlement)
        assert entitlement.entry_block_count == 3
        assert entitlement.included_entries == 800
        order = db_session.query(models.BillingOrder).filter_by(id=order_id).one()
        assert order.order_type == "entry_blocks"
        assert order.quantity == 3
        assert order.amount_total == 7500
        audits = (
            db_session.query(models.AuditLog)
            .filter_by(action="BILLING_ENTRY_CAPACITY_ADDED")
            .all()
        )
        assert len(audits) == 1
        assert '"new_capacity": 800' in audits[0].details
