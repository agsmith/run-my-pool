from datetime import datetime, timedelta
from unittest.mock import patch

import models
from pool_reports import (
    build_member_recap,
    build_owner_report,
    deliver_due_reports,
    deliver_member_recaps,
    latest_completed_week,
)


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


def _member(client, db_session, pool_id, email="recap.member@example.com"):
    headers = _register(client, email)
    user = db_session.query(models.User).filter_by(email=email).one()
    db_session.add(models.PoolMember(
        pool_id=pool_id, user_id=user.id, joined_at=datetime(2026, 8, 1),
    ))
    db_session.commit()
    return headers, user


def _final_week(db_session, week=1, status="final"):
    db_session.add_all([
        models.Team(id=9101, name="Buffalo Bills", abbrv="BUF"),
        models.Team(id=9102, name="Miami Dolphins", abbrv="MIA"),
    ])
    db_session.add(models.Schedule(
        game_id=9191, season=2026, week_num=week, home_team_id=9102,
        away_team_id=9101, start_time=datetime(2026, 9, 10), status=status,
    ))
    db_session.commit()


def test_member_controls_only_their_pool_scoped_recap_preference(client, db_session):
    owner = _register(client, "recap.owner@example.com")
    pool = _pool(client, owner, "Member Recap Pool")
    member_headers, member = _member(client, db_session, pool["id"])

    initial = client.get(f"/pools/{pool['id']}/member-recap-preference", headers=member_headers)
    assert initial.status_code == 200
    assert initial.json()["enabled"] is False
    updated = client.put(
        f"/pools/{pool['id']}/member-recap-preference",
        json={"enabled": True}, headers=member_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["enabled"] is True
    membership = db_session.query(models.PoolMember).filter_by(pool_id=pool["id"], user_id=member.id).one()
    assert membership.weekly_recap_enabled is True
    assert db_session.query(models.AuditLog).filter_by(action="MEMBER_WEEKLY_RECAP_PREFERENCE_UPDATED").count() == 1

    outsider = _register(client, "recap.outsider@example.com")
    assert client.get(f"/pools/{pool['id']}/member-recap-preference", headers=outsider).status_code == 403


def test_completed_week_requires_every_game_to_be_final(db_session):
    _final_week(db_session, status="in_progress")
    assert latest_completed_week(db_session) is None
    game = db_session.get(models.Schedule, 9191)
    game.status = "final"
    db_session.commit()
    assert latest_completed_week(db_session) == (2026, 1)


@patch("pool_reports.send_member_weekly_recap", return_value="ses-message-1")
def test_member_recap_is_personal_and_delivered_once_per_completed_week(send_recap, client, db_session):
    owner = _register(client, "recap.delivery.owner@example.com")
    pool_data = _pool(client, owner, "Weekly Results Pool")
    _, member = _member(client, db_session, pool_data["id"], "recap.delivery.member@example.com")
    membership = db_session.query(models.PoolMember).filter_by(pool_id=pool_data["id"], user_id=member.id).one()
    membership.weekly_recap_enabled = True
    entry = models.Entry(id="member-recap-entry", user_id=member.id, pool_id=pool_data["id"], name="Brave Otters", alive=True)
    owner_user = db_session.query(models.User).filter_by(email="recap.delivery.owner@example.com").one()
    other_entry = models.Entry(id="owner-private-entry", user_id=owner_user.id, pool_id=pool_data["id"], name="Do Not Reveal", alive=True)
    db_session.add_all([entry, other_entry])
    db_session.add(models.Pick(id="member-recap-pick", entry_id=entry.id, week=1, team="BUF", locked=True, result="win"))
    db_session.commit()
    _final_week(db_session)

    recap = build_member_recap(db_session, db_session.get(models.Pool, pool_data["id"]), member, 2026, 1)
    assert recap["entries"] == [{"entry_name": "Brave Otters", "pick": "BUF", "result": "win"}]
    assert "Do Not Reveal" not in str(recap)
    assert recap["remaining_entries"] == 1
    assert recap["pool_remaining_entries"] == 2

    assert deliver_member_recaps(db_session, datetime(2026, 9, 15, 14, 0)) == (1, 0)
    assert deliver_member_recaps(db_session, datetime(2026, 9, 16, 14, 0)) == (0, 0)
    assert send_recap.call_count == 1
    delivery = db_session.query(models.MemberRecapDelivery).one()
    assert delivery.status == "sent"
    assert delivery.message_id == "ses-message-1"


@patch("pool_reports.send_member_weekly_recap", side_effect=RuntimeError("SES unavailable"))
def test_failed_member_recap_is_recorded_for_retry(send_recap, client, db_session):
    owner = _register(client, "recap.failure.owner@example.com")
    pool_data = _pool(client, owner, "Failed Recap Pool")
    _, member = _member(client, db_session, pool_data["id"], "recap.failure.member@example.com")
    membership = db_session.query(models.PoolMember).filter_by(pool_id=pool_data["id"], user_id=member.id).one()
    membership.weekly_recap_enabled = True
    db_session.commit()
    _final_week(db_session)

    assert deliver_member_recaps(db_session, datetime(2026, 9, 15, 14, 0)) == (0, 1)
    delivery = db_session.query(models.MemberRecapDelivery).one()
    assert delivery.status == "failed"
    assert delivery.error == "SES unavailable"
