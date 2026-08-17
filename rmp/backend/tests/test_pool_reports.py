from datetime import datetime, timedelta
from unittest.mock import patch

import models
from pool_reports import build_owner_report, deliver_due_reports


def _register(client, email):
    password = "Pass1234!"
    assert client.post("/auth/register", json={"email": email, "password": password}).status_code == 200
    token = client.post("/auth/login", json={"email": email, "password": password}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _pool(client, headers, name="Report Pool"):
    response = client.post("/pools/create", json={"name": name, "pool_type": "survivor"}, headers=headers)
    assert response.status_code == 200
    return response.json()


def test_owner_can_opt_in_preview_and_audit(client, db_session):
    owner = _register(client, "report.owner@example.com")
    pool = _pool(client, owner)

    initial = client.get(f"/pools/{pool['id']}/owner-report-preference", headers=owner)
    assert initial.status_code == 200
    assert initial.json()["enabled"] is False

    updated = client.put(
        f"/pools/{pool['id']}/owner-report-preference",
        json={"enabled": True, "frequency": "weekly"}, headers=owner,
    )
    assert updated.status_code == 200
    assert updated.json()["enabled"] is True
    preview = client.get(f"/pools/{pool['id']}/owner-report-preview", headers=owner)
    assert preview.status_code == 200
    assert preview.json()["pool_name"] == "Report Pool"
    assert preview.json()["members"] == 1
    assert db_session.query(models.AuditLog).filter(models.AuditLog.action == "OWNER_POOL_REPORT_PREFERENCE_UPDATED").count() == 1


def test_non_owner_cannot_view_or_change_owner_reports(client):
    owner = _register(client, "report.owner2@example.com")
    other = _register(client, "report.other@example.com")
    pool = _pool(client, owner, "Private Owner Report")
    for method, path, body in [
        (client.get, "owner-report-preference", None),
        (client.get, "owner-report-preview", None),
        (client.put, "owner-report-preference", {"enabled": True, "frequency": "weekly"}),
    ]:
        response = method(f"/pools/{pool['id']}/{path}", headers=other, **({"json": body} if body else {}))
        assert response.status_code == 403


def test_report_counts_engagement_results_and_popular_locked_picks(client, db_session):
    owner_headers = _register(client, "report.stats@example.com")
    pool_data = _pool(client, owner_headers, "Stats Report Pool")
    owner = db_session.query(models.User).filter(models.User.email == "report.stats@example.com").one()
    entry_a = models.Entry(id="report-entry-a", user_id=owner.id, pool_id=pool_data["id"], name="A", alive=True)
    entry_b = models.Entry(id="report-entry-b", user_id=owner.id, pool_id=pool_data["id"], name="B", alive=False)
    db_session.add_all([entry_a, entry_b])
    db_session.add_all([
        models.Pick(id="report-pick-a", entry_id=entry_a.id, week=1, team="BUF", locked=True, result="win"),
        models.Pick(id="report-pick-b", entry_id=entry_b.id, week=1, team="BUF", locked=True, result="loss"),
    ])
    db_session.commit()

    report = build_owner_report(db_session, db_session.get(models.Pool, pool_data["id"]))
    assert report["total_entries"] == 2
    assert report["remaining_entries"] == 1
    assert report["eliminated_entries"] == 1
    assert report["weekly_wins"] == 1
    assert report["weekly_losses"] == 1
    assert report["popular_locked_picks"] == [{"team": "BUF", "picks": 2}]


@patch("pool_reports.send_pool_owner_report")
def test_delivery_sends_due_reports_once_per_week(send_report, client, db_session):
    owner_headers = _register(client, "report.delivery@example.com")
    pool_data = _pool(client, owner_headers, "Delivery Report Pool")
    pool = db_session.get(models.Pool, pool_data["id"])
    pool.owner_reports_enabled = True
    pool.owner_reports_frequency = "weekly"
    pool.owner_reports_last_sent_at = None
    db_session.commit()
    now = datetime(2026, 9, 15, 14, 0)

    assert deliver_due_reports(db_session, now) == (1, 0)
    assert send_report.call_count == 1
    assert deliver_due_reports(db_session, now + timedelta(days=1)) == (0, 0)
    assert send_report.call_count == 1


@patch("pool_reports.send_pool_owner_report", side_effect=RuntimeError("SES unavailable"))
def test_delivery_records_failure_without_advancing_timestamp(send_report, client, db_session):
    owner_headers = _register(client, "report.failure@example.com")
    pool_data = _pool(client, owner_headers, "Failure Report Pool")
    pool = db_session.get(models.Pool, pool_data["id"])
    pool.owner_reports_enabled = True
    db_session.commit()

    assert deliver_due_reports(db_session, datetime(2026, 9, 15, 14, 0)) == (0, 1)
    assert pool.owner_reports_last_sent_at is None
