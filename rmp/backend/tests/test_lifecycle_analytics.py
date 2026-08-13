import logging


def test_lifecycle_event_is_logged_without_personal_data(client, caplog):
    caplog.set_level(logging.INFO, logger="runmypool.lifecycle")

    response = client.post(
        "/analytics/events",
        json={
            "event": "plan_selected",
            "session_id": "12345678-1234-1234-1234-123456789abc",
            "page": "pricing",
            "plan": "pro",
            "source": "pricing",
        },
    )

    assert response.status_code == 204
    record = next(
        record for record in caplog.records if record.name == "runmypool.lifecycle"
    )
    assert record.event == "customer_lifecycle_event"
    assert record.lifecycle_event == "plan_selected"
    assert record.plan == "pro"
    assert not hasattr(record, "email")


def test_lifecycle_event_rejects_unknown_events_and_fields(client):
    response = client.post(
        "/analytics/events",
        json={
            "event": "password_entered",
            "session_id": "12345678-1234-1234-1234-123456789abc",
            "page": "home",
            "email": "must-not-be-accepted@example.com",
        },
    )

    assert response.status_code == 422


def test_lifecycle_event_rejects_unbounded_session_identifiers(client):
    response = client.post(
        "/analytics/events",
        json={"event": "landing_view", "session_id": "../../bad", "page": "home"},
    )

    assert response.status_code == 422


def test_duplicate_lifecycle_event_is_accepted_but_logged_once(client, caplog):
    caplog.set_level(logging.INFO, logger="runmypool.lifecycle")
    payload = {
        "event": "pricing_view",
        "session_id": "dedupe-session-1234567890",
        "page": "pricing",
    }

    first = client.post("/analytics/events", json=payload)
    second = client.post("/analytics/events", json=payload)

    assert first.status_code == 204
    assert second.status_code == 204
    records = [
        record
        for record in caplog.records
        if record.name == "runmypool.lifecycle"
        and getattr(record, "lifecycle_event", None) == "pricing_view"
    ]
    assert len(records) == 1


def test_lifecycle_event_rate_limits_each_observed_client(client):
    headers = {"x-forwarded-for": "198.51.100.72"}
    for index in range(120):
        response = client.post(
            "/analytics/events",
            headers=headers,
            json={
                "event": "landing_view",
                "session_id": f"rate-session-{index:04d}",
                "page": "home",
            },
        )
        assert response.status_code == 204

    blocked = client.post(
        "/analytics/events",
        headers=headers,
        json={
            "event": "landing_view",
            "session_id": "rate-session-blocked",
            "page": "home",
        },
    )
    assert blocked.status_code == 429


def test_lifecycle_event_rejects_oversized_declared_body(client):
    response = client.post(
        "/analytics/events",
        headers={"content-length": "2049", "x-forwarded-for": "198.51.100.73"},
        content=b"{}",
    )

    assert response.status_code == 413


def test_buy_stage_payment_event_is_allowlisted(client):
    response = client.post(
        "/analytics/events",
        headers={"x-forwarded-for": "198.51.100.74"},
        json={
            "event": "payment_confirmed",
            "session_id": "paid-session-1234567890",
            "page": "billing_success",
            "plan": "commissioner",
            "source": "pricing",
        },
    )

    assert response.status_code == 204


def test_get_stage_launch_event_is_allowlisted(client):
    response = client.post(
        "/analytics/events",
        headers={"x-forwarded-for": "198.51.100.75"},
        json={
            "event": "pool_launch_checklist_view",
            "session_id": "launch-session-1234567890",
            "page": "pool_home",
        },
    )

    assert response.status_code == 204


def test_get_stage_member_onboarding_event_is_allowlisted(client):
    response = client.post(
        "/analytics/events",
        headers={"x-forwarded-for": "198.51.100.76"},
        json={
            "event": "member_onboarding_view",
            "session_id": "member-session-1234567890",
            "page": "pool_home",
        },
    )

    assert response.status_code == 204
