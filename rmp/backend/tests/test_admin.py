"""
Tests for the /admin endpoints.

Routes under test:
  POST   /admin/pools/{pool_id}/transfer-entry          — transfer entry ownership (admin only)
  DELETE /admin/pools/{pool_id}/entries/{entry_id}      — delete any entry (admin only)
  POST   /admin/pools/{pool_id}/lock-week/{week}        — lock week and auto-pick (admin only)
  PATCH  /admin/pools/{pool_id}/picks/{pick_id}         — admin override a pick (admin only)
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from admin import verify_admin_access
from tests.plan_support import grant_unlimited_pool_creations

# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------


def _register_and_login(client, email="test@example.com", password="Test1234!"):
    """Register a user and return a JWT access token."""
    client.post("/auth/register", json={"email": email, "password": password})
    resp = client.post("/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, f"Login failed: {resp.json()}"
    grant_unlimited_pool_creations(email)
    return resp.json()["access_token"]


def _authed(token):
    """Return Authorization header dict for the given bearer token."""
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Setup helpers
# ---------------------------------------------------------------------------


def _create_pool(client, headers):
    """Create a pool and return its id."""
    resp = client.post(
        "/pools/create",
        json={
            "name": f"Admin Test Pool {uuid.uuid4()}",
            "is_private": False,
            "rule_values": [],
        },
        headers=headers,
    )
    assert resp.status_code == 200, f"Pool creation failed: {resp.json()}"
    return resp.json()["id"]


def _create_entry(client, headers, pool_id, name="Test Entry"):
    """Create an entry in the given pool and return its id."""
    resp = client.post(
        "/entries/create",
        json={"pool_id": pool_id, "name": name},
        headers=headers,
    )
    assert resp.status_code == 200, f"Entry creation failed: {resp.json()}"
    return resp.json()["id"]


def _add_pool_member(db_session, pool_id, email):
    import models as m

    user = db_session.query(m.User).filter(m.User.email == email).one()
    if (
        not db_session.query(m.PoolMember)
        .filter_by(pool_id=pool_id, user_id=user.id)
        .first()
    ):
        db_session.add(
            m.PoolMember(
                pool_id=pool_id,
                user_id=user.id,
                joined_at=datetime.now(timezone.utc).replace(tzinfo=None),
            )
        )
        db_session.commit()
    return user.id


def _create_pick(db_session, entry_id, week, team, locked=False):
    """Directly insert a Pick row and return the model instance."""
    import models as m

    pick = m.Pick(
        id=str(uuid.uuid4()),
        entry_id=entry_id,
        week=week,
        team=team,
        locked=locked,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(pick)
    db_session.commit()
    db_session.refresh(pick)
    return pick


# ---------------------------------------------------------------------------
# Test class — existing endpoints
# ---------------------------------------------------------------------------


class TestAdminEndpoints:
    """Integration tests for the admin router."""

    def test_pool_user_overview_reports_entries_admin_and_week_completion(
        self, client, db_session
    ):
        import models as m

        owner_token = _register_and_login(client, "overview.owner@example.com")
        _register_and_login(client, "overview.member@example.com")
        _register_and_login(client, "overview.outsider@example.com")
        pool_id = _create_pool(client, _authed(owner_token))
        owner = (
            db_session.query(m.User)
            .filter(m.User.email == "overview.owner@example.com")
            .one()
        )
        member = (
            db_session.query(m.User)
            .filter(m.User.email == "overview.member@example.com")
            .one()
        )
        db_session.add(
            m.PoolMember(
                pool_id=pool_id, user_id=member.id, joined_at=datetime.utcnow()
            )
        )
        db_session.add(m.PoolAdmin(pool_id=pool_id, user_id=member.id))
        owner_entry = m.Entry(
            id=str(uuid.uuid4()),
            pool_id=pool_id,
            user_id=owner.id,
            name="Owner",
            alive=True,
        )
        alive_entry = m.Entry(
            id=str(uuid.uuid4()),
            pool_id=pool_id,
            user_id=member.id,
            name="Alive",
            alive=True,
        )
        eliminated_entry = m.Entry(
            id=str(uuid.uuid4()),
            pool_id=pool_id,
            user_id=member.id,
            name="Out",
            alive=False,
        )
        db_session.add_all([owner_entry, alive_entry, eliminated_entry])
        db_session.commit()
        _create_pick(db_session, alive_entry.id, 4, "BUF")

        response = client.get(
            f"/admin/pools/{pool_id}/users-overview?week=4",
            headers=_authed(owner_token),
        )

        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["current_week"] == 4
        assert payload["total_users"] == 2
        users = {user["email"]: user for user in payload["users"]}
        assert set(users) == {
            "overview.owner@example.com",
            "overview.member@example.com",
        }
        assert users["overview.owner@example.com"] == {
            "id": owner.id,
            "email": owner.email,
            "total_entries": 1,
            "surviving_entries": 1,
            "picked_entries": 0,
            "has_current_week_pick": False,
            "all_surviving_entries_picked": False,
            "is_admin": True,
            "admin_role": "Owner",
            "dues_paid": False,
        }
        assert users["overview.member@example.com"]["total_entries"] == 2
        assert users["overview.member@example.com"]["surviving_entries"] == 1
        assert users["overview.member@example.com"]["picked_entries"] == 1
        assert (
            users["overview.member@example.com"]["all_surviving_entries_picked"] is True
        )
        assert users["overview.member@example.com"]["admin_role"] == "Pool admin"
        assert "team" not in users["overview.member@example.com"]

    def test_remove_user_from_pool_deletes_only_pool_scoped_participation(
        self, client, db_session
    ):
        import models as m

        owner_token = _register_and_login(client, "remove.owner@example.com")
        member_token = _register_and_login(client, "remove.member@example.com")
        pool_id = _create_pool(client, _authed(owner_token))
        other_pool_id = _create_pool(client, _authed(owner_token))
        member_id = _add_pool_member(db_session, pool_id, "remove.member@example.com")
        _add_pool_member(db_session, other_pool_id, "remove.member@example.com")
        entry_id = _create_entry(client, _authed(member_token), pool_id, "Remove Me")
        _create_pick(db_session, entry_id, 1, "BUF")
        db_session.add(m.PoolAdmin(pool_id=pool_id, user_id=member_id))
        db_session.add(
            m.PoolUserLock(
                pool_id=pool_id,
                user_id=member_id,
                locked_at=datetime.now(timezone.utc).replace(tzinfo=None),
            )
        )
        db_session.commit()

        response = client.delete(
            f"/admin/pools/{pool_id}/users/{member_id}",
            headers=_authed(owner_token),
        )

        assert response.status_code == 200, response.text
        assert (
            db_session.query(m.User).filter_by(id=member_id).one_or_none() is not None
        )
        assert (
            db_session.query(m.PoolMember)
            .filter_by(pool_id=pool_id, user_id=member_id)
            .one_or_none()
            is None
        )
        assert (
            db_session.query(m.PoolAdmin)
            .filter_by(pool_id=pool_id, user_id=member_id)
            .one_or_none()
            is None
        )
        assert (
            db_session.query(m.PoolUserLock)
            .filter_by(pool_id=pool_id, user_id=member_id)
            .one_or_none()
            is None
        )
        assert (
            db_session.query(m.Entry)
            .filter_by(pool_id=pool_id, user_id=member_id)
            .one_or_none()
            is None
        )
        assert (
            db_session.query(m.Pick).filter_by(entry_id=entry_id).one_or_none() is None
        )
        assert (
            db_session.query(m.PoolMember)
            .filter_by(pool_id=other_pool_id, user_id=member_id)
            .one_or_none()
            is not None
        )
        audit = (
            db_session.query(m.AuditLog)
            .filter_by(action="ADMIN_POOL_USER_REMOVED")
            .order_by(m.AuditLog.created_at.desc())
            .first()
        )
        assert audit is not None
        assert pool_id in audit.details
        assert "remove.member@example.com" in audit.details

    def test_remove_user_from_pool_rejects_pool_owner(self, client, db_session):
        import models as m

        owner_token = _register_and_login(client, "remove.protected.owner@example.com")
        pool_id = _create_pool(client, _authed(owner_token))
        owner = (
            db_session.query(m.User)
            .filter_by(email="remove.protected.owner@example.com")
            .one()
        )

        response = client.delete(
            f"/admin/pools/{pool_id}/users/{owner.id}",
            headers=_authed(owner_token),
        )

        assert response.status_code == 400
        assert "Transfer ownership first" in response.json()["detail"]

    def test_delegated_admin_cannot_remove_another_pool_admin(self, client, db_session):
        import models as m

        owner_token = _register_and_login(client, "remove.admin.owner@example.com")
        delegated_token = _register_and_login(client, "remove.admin.actor@example.com")
        _register_and_login(client, "remove.admin.target@example.com")
        pool_id = _create_pool(client, _authed(owner_token))
        actor_id = _add_pool_member(
            db_session, pool_id, "remove.admin.actor@example.com"
        )
        target_id = _add_pool_member(
            db_session, pool_id, "remove.admin.target@example.com"
        )
        db_session.add_all(
            [
                m.PoolAdmin(pool_id=pool_id, user_id=actor_id),
                m.PoolAdmin(pool_id=pool_id, user_id=target_id),
            ]
        )
        db_session.commit()

        response = client.delete(
            f"/admin/pools/{pool_id}/users/{target_id}",
            headers=_authed(delegated_token),
        )

        assert response.status_code == 403
        assert (
            db_session.query(m.PoolAdmin)
            .filter_by(pool_id=pool_id, user_id=target_id)
            .one_or_none()
            is not None
        )

    def test_pool_admin_can_mark_dues_paid_and_unpaid_with_audit(
        self, client, db_session
    ):
        import json
        import models as m

        owner_token = _register_and_login(client, "dues.owner@example.com")
        admin_token = _register_and_login(client, "dues.admin@example.com")
        _register_and_login(client, "dues.member@example.com")
        pool_id = _create_pool(client, _authed(owner_token))
        admin_id = _add_pool_member(db_session, pool_id, "dues.admin@example.com")
        member_id = _add_pool_member(db_session, pool_id, "dues.member@example.com")
        db_session.add(m.PoolAdmin(pool_id=pool_id, user_id=admin_id))
        db_session.commit()

        paid = client.put(
            f"/admin/pools/{pool_id}/users/{member_id}/dues",
            json={"paid": True},
            headers=_authed(admin_token),
        )
        assert paid.status_code == 200, paid.text
        assert paid.json()["paid"] is True
        overview = client.get(
            f"/admin/pools/{pool_id}/users-overview?week=1",
            headers=_authed(admin_token),
        ).json()
        member = next(user for user in overview["users"] if user["id"] == member_id)
        assert member["dues_paid"] is True

        unpaid = client.put(
            f"/admin/pools/{pool_id}/users/{member_id}/dues",
            json={"paid": False},
            headers=_authed(admin_token),
        )
        assert unpaid.status_code == 200
        assert unpaid.json()["paid"] is False
        audit_rows = (
            db_session.query(m.AuditLog)
            .filter(m.AuditLog.action == "ADMIN_POOL_DUES_STATUS_CHANGED")
            .all()
        )
        assert len(audit_rows) == 2
        changes = [json.loads(row.details)["additional_data"] for row in audit_rows]
        assert [(change["previous_paid"], change["paid"]) for change in changes] == [
            (False, True),
            (True, False),
        ]
        assert all(change["pool_id"] == pool_id for change in changes)

    def test_dues_update_rejects_non_admin_and_user_outside_pool(
        self, client, db_session
    ):
        owner_token = _register_and_login(client, "dues.guard.owner@example.com")
        outsider_token = _register_and_login(client, "dues.guard.outsider@example.com")
        _register_and_login(client, "dues.guard.member@example.com")
        pool_id = _create_pool(client, _authed(owner_token))
        member_id = _add_pool_member(
            db_session, pool_id, "dues.guard.member@example.com"
        )
        import models as m

        outsider = (
            db_session.query(m.User)
            .filter(m.User.email == "dues.guard.outsider@example.com")
            .one()
        )

        forbidden = client.put(
            f"/admin/pools/{pool_id}/users/{member_id}/dues",
            json={"paid": True},
            headers=_authed(outsider_token),
        )
        missing = client.put(
            f"/admin/pools/{pool_id}/users/{outsider.id}/dues",
            json={"paid": True},
            headers=_authed(owner_token),
        )
        assert forbidden.status_code == 403
        assert missing.status_code == 404

    def test_pool_user_overview_rejects_non_admin_and_invalid_week(self, client):
        owner_token = _register_and_login(client, "overview.guard.owner@example.com")
        outsider_token = _register_and_login(
            client, "overview.guard.outsider@example.com"
        )
        pool_id = _create_pool(client, _authed(owner_token))

        forbidden = client.get(
            f"/admin/pools/{pool_id}/users-overview?week=1",
            headers=_authed(outsider_token),
        )
        invalid_week = client.get(
            f"/admin/pools/{pool_id}/users-overview?week=19",
            headers=_authed(owner_token),
        )

        assert forbidden.status_code == 403
        assert invalid_week.status_code == 400

    def test_owner_grants_and_revokes_league_admin_idempotently(
        self, client, db_session
    ):
        import models as m

        owner_token = _register_and_login(client, "grant.owner@example.com")
        member_token = _register_and_login(client, "grant.member@example.com")
        _register_and_login(client, "grant.other@example.com")
        pool_id = _create_pool(client, _authed(owner_token))
        member = (
            db_session.query(m.User)
            .filter(m.User.email == "grant.member@example.com")
            .one()
        )
        other = (
            db_session.query(m.User)
            .filter(m.User.email == "grant.other@example.com")
            .one()
        )
        db_session.add_all(
            [
                m.PoolMember(
                    pool_id=pool_id, user_id=member.id, joined_at=datetime.utcnow()
                ),
                m.PoolMember(
                    pool_id=pool_id, user_id=other.id, joined_at=datetime.utcnow()
                ),
            ]
        )
        db_session.commit()

        granted = client.put(
            f"/admin/pools/{pool_id}/admins",
            json={"email": "GRANT.MEMBER@example.com"},
            headers=_authed(owner_token),
        )
        repeated_grant = client.put(
            f"/admin/pools/{pool_id}/admins",
            json={"email": "grant.member@example.com"},
            headers=_authed(owner_token),
        )
        delegated_grant = client.put(
            f"/admin/pools/{pool_id}/admins",
            json={"email": "grant.other@example.com"},
            headers=_authed(member_token),
        )

        assert granted.status_code == 200, granted.text
        assert granted.json()["changed"] is True
        assert granted.json()["is_admin"] is True
        assert repeated_grant.json()["changed"] is False
        assert delegated_grant.status_code == 403
        assert (
            client.get(
                f"/pools/{pool_id}/is-admin", headers=_authed(member_token)
            ).json()["has_admin_access"]
            is True
        )

        revoked = client.delete(
            f"/admin/pools/{pool_id}/admins?email=grant.member%40example.com",
            headers=_authed(owner_token),
        )
        repeated_revoke = client.delete(
            f"/admin/pools/{pool_id}/admins?email=grant.member%40example.com",
            headers=_authed(owner_token),
        )

        assert revoked.status_code == 200, revoked.text
        assert revoked.json()["changed"] is True
        assert revoked.json()["is_admin"] is False
        assert repeated_revoke.json()["changed"] is False
        assert (
            client.get(
                f"/pools/{pool_id}/is-admin", headers=_authed(member_token)
            ).json()["has_admin_access"]
            is False
        )
        actions = {log.action for log in db_session.query(m.AuditLog).all()}
        assert "ADMIN_GRANT_LEAGUE_ADMIN" in actions
        assert "ADMIN_REVOKE_LEAGUE_ADMIN" in actions

    def test_grant_requires_existing_participant_and_owner_cannot_be_revoked(
        self, client
    ):
        owner_email = "grant.guard.owner@example.com"
        owner_token = _register_and_login(client, owner_email)
        _register_and_login(client, "grant.guard.outsider@example.com")
        pool_id = _create_pool(client, _authed(owner_token))

        nonmember = client.put(
            f"/admin/pools/{pool_id}/admins",
            json={"email": "grant.guard.outsider@example.com"},
            headers=_authed(owner_token),
        )
        revoke_owner = client.delete(
            f"/admin/pools/{pool_id}/admins?email={owner_email}",
            headers=_authed(owner_token),
        )

        assert nonmember.status_code == 404
        assert nonmember.json()["detail"] == "User not found in this pool"
        assert revoke_owner.status_code == 400
        assert "owner access cannot be revoked" in revoke_owner.json()["detail"]

    def test_owner_transfers_ownership_and_remains_league_admin(
        self, client, db_session
    ):
        import models as m

        old_owner_token = _register_and_login(client, "transfer.owner@example.com")
        new_owner_token = _register_and_login(client, "transfer.new@example.com")
        pool_id = _create_pool(client, _authed(old_owner_token))
        old_owner = (
            db_session.query(m.User)
            .filter(m.User.email == "transfer.owner@example.com")
            .one()
        )
        new_owner = (
            db_session.query(m.User)
            .filter(m.User.email == "transfer.new@example.com")
            .one()
        )
        db_session.add(
            m.PoolMember(
                pool_id=pool_id, user_id=new_owner.id, joined_at=datetime.utcnow()
            )
        )
        db_session.commit()

        response = client.put(
            f"/admin/pools/{pool_id}/owner",
            json={"email": "TRANSFER.NEW@example.com"},
            headers=_authed(old_owner_token),
        )

        assert response.status_code == 200, response.text
        assert response.json() == {
            "pool_id": pool_id,
            "previous_owner_id": old_owner.id,
            "previous_owner_email": old_owner.email,
            "owner_id": new_owner.id,
            "owner_email": new_owner.email,
        }
        db_session.expire_all()
        assert db_session.get(m.Pool, pool_id).owner_id == new_owner.id
        old_status = client.get(
            f"/pools/{pool_id}/is-admin", headers=_authed(old_owner_token)
        ).json()
        new_status = client.get(
            f"/pools/{pool_id}/is-admin", headers=_authed(new_owner_token)
        ).json()
        assert old_status == {
            "pool_id": pool_id,
            "is_owner": False,
            "is_admin": True,
            "has_admin_access": True,
        }
        assert new_status["is_owner"] is True
        overview = client.get(
            f"/admin/pools/{pool_id}/users-overview?week=1",
            headers=_authed(old_owner_token),
        ).json()
        roles = {user["email"]: user["admin_role"] for user in overview["users"]}
        assert roles[old_owner.email] == "Pool admin"
        assert roles[new_owner.email] == "Owner"
        assert "ADMIN_TRANSFER_LEAGUE_OWNERSHIP" in {
            log.action for log in db_session.query(m.AuditLog).all()
        }

    def test_ownership_transfer_requires_current_owner_and_participant(self, client):
        owner_email = "transfer.guard.owner@example.com"
        owner_token = _register_and_login(client, owner_email)
        member_token = _register_and_login(client, "transfer.guard.member@example.com")
        _register_and_login(client, "transfer.guard.outsider@example.com")
        pool_id = _create_pool(client, _authed(owner_token))

        delegated = client.put(
            f"/admin/pools/{pool_id}/owner",
            json={"email": owner_email},
            headers=_authed(member_token),
        )
        nonmember = client.put(
            f"/admin/pools/{pool_id}/owner",
            json={"email": "transfer.guard.outsider@example.com"},
            headers=_authed(owner_token),
        )
        same_owner = client.put(
            f"/admin/pools/{pool_id}/owner",
            json={"email": owner_email},
            headers=_authed(owner_token),
        )

        assert delegated.status_code == 403
        assert nonmember.status_code == 404
        assert nonmember.json()["detail"] == "User not found in this pool"
        assert same_owner.status_code == 400
        assert "already owns" in same_owner.json()["detail"]

    def test_admin_searches_entries_with_owner_email(self, client):
        owner_token = _register_and_login(client, "search.owner@example.com")
        headers = _authed(owner_token)
        pool_id = _create_pool(client, headers)
        entry_id = _create_entry(client, headers, pool_id, "Alpha Entry")

        response = client.get(
            f"/admin/pools/{pool_id}/entries?username=search.owner&entry_name=Alpha",
            headers=headers,
        )
        assert response.status_code == 200, response.text
        assert response.json() == [
            {
                "id": entry_id,
                "name": "Alpha Entry",
                "user_id": response.json()[0]["user_id"],
                "owner_email": "search.owner@example.com",
                "manual_participant_name": None,
                "locked": False,
            }
        ]

    def test_commissioner_creates_audited_manual_pickem_entry(self, client, db_session):
        import models as m

        owner_token = _register_and_login(client, "paper.owner@example.com")
        member_token = _register_and_login(client, "paper.member@example.com")
        headers = _authed(owner_token)
        pool_response = client.post(
            "/pools/create",
            json={
                "name": f"Paper Pick Em {uuid.uuid4()}",
                "pool_type": "pickem",
                "is_private": False,
                "rule_values": [],
            },
            headers=headers,
        )
        assert pool_response.status_code == 200, pool_response.text
        pool_id = pool_response.json()["id"]

        forbidden = client.post(
            f"/admin/pools/{pool_id}/manual-pickem-entries",
            json={"participant_name": "Paper Player"},
            headers=_authed(member_token),
        )
        assert forbidden.status_code == 403

        response = client.post(
            f"/admin/pools/{pool_id}/manual-pickem-entries",
            json={"participant_name": "  Paper   Player  "},
            headers=headers,
        )
        assert response.status_code == 200, response.text
        assert response.json()["name"] == "Paper Player"
        assert response.json()["manual_participant_name"] == "Paper Player"

        entry = db_session.query(m.Entry).filter_by(id=response.json()["id"]).one()
        owner = db_session.query(m.User).filter_by(email="paper.owner@example.com").one()
        assert entry.user_id == owner.id
        audit = db_session.query(m.AuditLog).filter(
            m.AuditLog.action == "ADMIN_CREATE_MANUAL_PICKEM_ENTRY",
        ).one()
        assert entry.id in audit.details
        standings = client.get(
            f"/picks/pool/{pool_id}/standings",
            headers=headers,
        )
        assert standings.status_code == 200, standings.text
        assert standings.json()[0]["user_display_name"] == "Paper Player"

    def test_manual_entry_rejects_non_pickem_pool_and_duplicate_name(self, client):
        owner_token = _register_and_login(client, "paper.rules@example.com")
        headers = _authed(owner_token)
        survivor_pool_id = _create_pool(client, headers)
        wrong_type = client.post(
            f"/admin/pools/{survivor_pool_id}/manual-pickem-entries",
            json={"participant_name": "Paper Player"},
            headers=headers,
        )
        assert wrong_type.status_code == 400

        pool_response = client.post(
            "/pools/create",
            json={
                "name": f"Duplicate Paper Pick Em {uuid.uuid4()}",
                "pool_type": "pickem",
                "is_private": False,
                "rule_values": [],
            },
            headers=headers,
        )
        pool_id = pool_response.json()["id"]
        first = client.post(
            f"/admin/pools/{pool_id}/manual-pickem-entries",
            json={"participant_name": "Paper Player"},
            headers=headers,
        )
        duplicate = client.post(
            f"/admin/pools/{pool_id}/manual-pickem-entries",
            json={"participant_name": "paper player"},
            headers=headers,
        )
        assert first.status_code == 200
        assert duplicate.status_code == 409

    def test_weekly_printable_uses_configured_pickem_slate_and_requires_admin(
        self, client, db_session
    ):
        import models as m

        owner_token = _register_and_login(client, "print.owner@example.com")
        member_token = _register_and_login(client, "print.member@example.com")
        headers = _authed(owner_token)
        pool_response = client.post(
            "/pools/create",
            json={
                "name": f"Printable Pick Em {uuid.uuid4()}",
                "pool_type": "pickem",
                "pickem_slate": "sunday_monday",
                "is_private": False,
                "rule_values": [],
            },
            headers=headers,
        )
        pool_id = pool_response.json()["id"]
        teams = [
            m.Team(id=18101 + index, name=name, abbrv=abbrv)
            for index, (name, abbrv) in enumerate(
                [
                    ("Buffalo Bills", "BFX"), ("Miami Dolphins", "MIX"),
                    ("Chicago Bears", "CHX"), ("Green Bay Packers", "GBX"),
                    ("Dallas Cowboys", "DAX"), ("New York Giants", "NYX"),
                ]
            )
        ]
        db_session.add_all(teams)
        sunday = datetime(2099, 9, 6, 17)
        db_session.add_all([
            m.Schedule(game_id=18101, season=2099, week_num=1, away_team_id=18101, home_team_id=18102, start_time=sunday),
            m.Schedule(game_id=18102, season=2099, week_num=1, away_team_id=18103, home_team_id=18104, start_time=sunday + timedelta(days=1, hours=7)),
            m.Schedule(game_id=18103, season=2099, week_num=1, away_team_id=18105, home_team_id=18106, start_time=sunday - timedelta(days=3)),
        ])
        db_session.commit()

        forbidden = client.get(
            f"/admin/pools/{pool_id}/pickem-printable/1",
            headers=_authed(member_token),
        )
        assert forbidden.status_code == 403

        response = client.get(
            f"/admin/pools/{pool_id}/pickem-printable/1",
            headers=headers,
        )
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["requires_tiebreaker"] is True
        assert payload["required_picks"] == 2
        assert [game["game_id"] for game in payload["games"]] == [18101, 18102]

    def test_admin_corrects_pick_by_entry_and_week(self, client, db_session):
        owner_token = _register_and_login(client, "correct.owner@example.com")
        headers = _authed(owner_token)
        pool_id = _create_pool(client, headers)
        entry_id = _create_entry(client, headers, pool_id, "Correction Entry")
        _create_pick(db_session, entry_id, 3, "DAL", locked=True)

        response = client.patch(
            f"/admin/pools/{pool_id}/entries/{entry_id}/weeks/3/pick",
            json={"team": "phi", "reason": "Commissioner correction"},
            headers=headers,
        )
        assert response.status_code == 200, response.text
        assert response.json()["team"] == "PHI"

    def test_admin_delete_entry_removes_its_picks(self, client, db_session):
        import models as m

        owner_token = _register_and_login(client, "cascade.owner@example.com")
        headers = _authed(owner_token)
        pool_id = _create_pool(client, headers)
        entry_id = _create_entry(client, headers, pool_id, "Delete With Picks")
        pick = _create_pick(db_session, entry_id, 2, "BUF")

        response = client.delete(
            f"/admin/pools/{pool_id}/entries/{entry_id}", headers=headers
        )
        assert response.status_code == 200, response.text
        assert db_session.query(m.Entry).filter(m.Entry.id == entry_id).first() is None
        assert db_session.query(m.Pick).filter(m.Pick.id == pick.id).first() is None

    def test_admin_locks_and_unlocks_user_by_email(self, client, db_session):
        owner_token = _register_and_login(client, "email.lock.owner@example.com")
        _register_and_login(client, "email.lock.target@example.com")
        headers = _authed(owner_token)
        pool_id = _create_pool(client, headers)
        _add_pool_member(db_session, pool_id, "email.lock.target@example.com")

        locked = client.put(
            f"/admin/pools/{pool_id}/user-lock",
            json={
                "email": "email.lock.target@example.com",
                "locked": True,
                "reason": "Unpaid",
            },
            headers=headers,
        )
        assert locked.status_code == 200, locked.text
        assert locked.json()["locked"] is True
        status_response = client.get(
            f"/admin/pools/{pool_id}/user-lock?email=email.lock.target%40example.com",
            headers=headers,
        )
        assert status_response.json()["reason"] == "Unpaid"

        unlocked = client.put(
            f"/admin/pools/{pool_id}/user-lock",
            json={"email": "email.lock.target@example.com", "locked": False},
            headers=headers,
        )
        assert unlocked.status_code == 200
        assert unlocked.json()["locked"] is False

    def test_admin_cannot_lookup_or_lock_user_from_another_league(self, client):
        owner_token = _register_and_login(client, "scoped.lock.owner@example.com")
        _register_and_login(client, "scoped.lock.outsider@example.com")
        headers = _authed(owner_token)
        pool_id = _create_pool(client, headers)

        lookup = client.get(
            f"/admin/pools/{pool_id}/user-lock?email=scoped.lock.outsider%40example.com",
            headers=headers,
        )
        update = client.put(
            f"/admin/pools/{pool_id}/user-lock",
            json={"email": "scoped.lock.outsider@example.com", "locked": True},
            headers=headers,
        )
        reset = client.post(
            f"/admin/pools/{pool_id}/users/password-reset",
            json={"email": "scoped.lock.outsider@example.com"},
            headers=headers,
        )

        assert lookup.status_code == 404
        assert update.status_code == 404
        assert reset.status_code == 404

    def test_admin_can_send_password_reset_to_league_member(self, client, db_session):
        owner_token = _register_and_login(client, "scoped.reset.owner@example.com")
        _register_and_login(client, "scoped.reset.member@example.com")
        pool_id = _create_pool(client, _authed(owner_token))
        _add_pool_member(db_session, pool_id, "scoped.reset.member@example.com")

        response = client.post(
            f"/admin/pools/{pool_id}/users/password-reset",
            json={"email": "scoped.reset.member@example.com"},
            headers=_authed(owner_token),
        )

        assert response.status_code == 200

    # ------------------------------------------------------------------
    # POST /admin/pools/{pool_id}/transfer-entry — auth & access guards
    # ------------------------------------------------------------------

    def test_transfer_entry_requires_auth(self, client):
        """POST transfer-entry without a token returns 401 or 403."""
        response = client.post(
            "/admin/pools/some-pool-id/transfer-entry",
            json={"entry_id": "some-entry-id", "to_email": "someone@example.com"},
        )
        assert response.status_code in (401, 403)

    def test_transfer_entry_non_admin_forbidden(self, client):
        """A non-admin user attempting to transfer an entry in another user's pool is denied."""
        # User A owns the pool and creates an entry
        token_a = _register_and_login(client, email="owner_admin@example.com")
        pool_id = _create_pool(client, _authed(token_a))
        entry_id = _create_entry(client, _authed(token_a), pool_id)

        # User B has no admin rights on user A's pool
        token_b = _register_and_login(client, email="intruder_admin@example.com")
        response = client.post(
            f"/admin/pools/{pool_id}/transfer-entry",
            json={"entry_id": entry_id, "to_email": "someone@example.com"},
            headers=_authed(token_b),
        )
        assert response.status_code == 403

    def test_transfer_entry_success(self, client, db_session):
        """Pool owner transfers an entry to a registered recipient — returns 200 with expected fields."""
        # Register owner and recipient
        token_owner = _register_and_login(client, email="transfer_owner@example.com")
        _register_and_login(client, email="transfer_recipient@example.com")

        headers_owner = _authed(token_owner)
        pool_id = _create_pool(client, headers_owner)
        entry_id = _create_entry(client, headers_owner, pool_id)
        _add_pool_member(db_session, pool_id, "transfer_recipient@example.com")

        response = client.post(
            f"/admin/pools/{pool_id}/transfer-entry",
            json={"entry_id": entry_id, "to_email": "transfer_recipient@example.com"},
            headers=headers_owner,
        )

        assert response.status_code == 200, f"Transfer failed: {response.json()}"
        data = response.json()
        assert "entry_id" in data
        assert "from_user" in data
        assert "to_user" in data
        assert data["to_user"] == "transfer_recipient@example.com"

    # ------------------------------------------------------------------
    # DELETE /admin/pools/{pool_id}/entries/{entry_id} — auth & access guards
    # ------------------------------------------------------------------

    def test_delete_entry_admin_requires_auth(self, client):
        """DELETE admin entry without a token returns 401 or 403."""
        response = client.delete("/admin/pools/some-pool-id/entries/some-entry-id")
        assert response.status_code in (401, 403)

    def test_delete_entry_admin_non_admin_forbidden(self, client):
        """A non-admin user cannot delete entries from another user's pool."""
        token_a = _register_and_login(client, email="owner_del@example.com")
        pool_id = _create_pool(client, _authed(token_a))
        entry_id = _create_entry(client, _authed(token_a), pool_id)

        token_b = _register_and_login(client, email="intruder_del@example.com")
        response = client.delete(
            f"/admin/pools/{pool_id}/entries/{entry_id}",
            headers=_authed(token_b),
        )
        assert response.status_code == 403

    def test_delete_entry_admin_not_found(self, client):
        """Pool owner deleting a non-existent entry returns 404."""
        token = _register_and_login(client, email="notfound_del@example.com")
        headers = _authed(token)
        pool_id = _create_pool(client, headers)
        non_existent_entry_id = "00000000-0000-0000-0000-000000000000"

        response = client.delete(
            f"/admin/pools/{pool_id}/entries/{non_existent_entry_id}",
            headers=headers,
        )
        assert response.status_code == 404

    def test_delete_entry_admin_success(self, client):
        """Pool owner can delete their own entry via the admin endpoint — returns 200."""
        token = _register_and_login(client, email="del_success@example.com")
        headers = _authed(token)
        pool_id = _create_pool(client, headers)
        entry_id = _create_entry(client, headers, pool_id)

        response = client.delete(
            f"/admin/pools/{pool_id}/entries/{entry_id}",
            headers=headers,
        )
        assert response.status_code == 200

    # ------------------------------------------------------------------
    # Unit tests for verify_admin_access
    # ------------------------------------------------------------------

    def test_verify_admin_access_pool_owner(self, client, db_session):
        """verify_admin_access returns True when the user is the pool owner."""
        import models as m

        token = _register_and_login(client, email="va_owner@example.com")
        headers = _authed(token)
        pool_id = _create_pool(client, headers)

        # Fetch the user object as it exists in the shared SQLite DB
        pool = db_session.query(m.Pool).filter(m.Pool.id == pool_id).first()
        owner = db_session.query(m.User).filter(m.User.id == pool.owner_id).first()

        result = verify_admin_access(pool_id, owner, db_session)
        assert result is True

    def test_verify_admin_access_non_member(self, client, db_session):
        """verify_admin_access returns False for a user with no relationship to the pool."""
        import models as m

        # Pool owner
        token_a = _register_and_login(client, email="va_owner2@example.com")
        pool_id = _create_pool(client, _authed(token_a))

        # Unrelated user
        _register_and_login(client, email="va_other@example.com")
        other_user = (
            db_session.query(m.User)
            .filter(m.User.email == "va_other@example.com")
            .first()
        )

        result = verify_admin_access(pool_id, other_user, db_session)
        assert result is False


# ---------------------------------------------------------------------------
# Test class — lock-week endpoint
# ---------------------------------------------------------------------------


class TestLockWeek:
    """Integration tests for POST /admin/pools/{pool_id}/lock-week/{week}."""

    def test_lock_week_creates_auto_pick(self, client, db_session):
        """
        Pool with 2 entries: entry A submits pick "NE", entry B submits no pick.
        Admin locks week 1. auto_picks_created == 1. Entry B now has a pick for
        week 1 equal to "NE" (most popular).
        """
        import models as m

        token = _register_and_login(client, email="lock_owner@example.com")
        headers = _authed(token)
        pool_id = _create_pool(client, headers)

        # Entry A — picks NE for week 1
        entry_a_id = _create_entry(client, headers, pool_id, name="Entry A")
        client.post(
            "/picks/create",
            json={"entry_id": entry_a_id, "week": 1, "team": "NE"},
            headers=headers,
        )

        # Entry B — no pick
        token_b = _register_and_login(client, email="lock_member@example.com")
        entry_b_id = _create_entry(client, _authed(token_b), pool_id, name="Entry B")

        # Admin locks week 1
        resp = client.post(f"/admin/pools/{pool_id}/lock-week/1", headers=headers)
        assert resp.status_code == 200, f"Lock-week failed: {resp.json()}"
        data = resp.json()
        assert data["auto_picks_created"] == 1

        report = client.get(
            f"/admin/pools/{pool_id}/auto-picks?week=1", headers=headers
        )
        assert report.status_code == 200
        assert report.json() == [
            {
                "audit_id": report.json()[0]["audit_id"],
                "week": 1,
                "user_id": report.json()[0]["user_id"],
                "user_email": "lock_member@example.com",
                "entry_id": entry_b_id,
                "entry_name": "Entry B",
                "team": "NE",
                "created_at": report.json()[0]["created_at"],
            }
        ]
        assert (
            client.get(
                f"/admin/pools/{pool_id}/auto-picks?week=1",
                headers=_authed(token_b),
            ).status_code
            == 403
        )

        # Entry B should now have a pick for week 1 equal to "NE"
        pick_b = (
            db_session.query(m.Pick)
            .filter(m.Pick.entry_id == entry_b_id, m.Pick.week == 1)
            .first()
        )
        assert pick_b is not None, "Auto-pick was not created for entry B"
        assert pick_b.team == "NE"

    def test_lock_week_idempotent(self, client):
        """Locking the same week twice — second call returns auto_picks_created: 0."""
        token = _register_and_login(client, email="lock_idem@example.com")
        headers = _authed(token)
        pool_id = _create_pool(client, headers)
        entry_id = _create_entry(client, headers, pool_id)

        # Give entry a pick so no auto-pick is needed
        client.post(
            "/picks/create",
            json={"entry_id": entry_id, "week": 1, "team": "GB"},
            headers=headers,
        )

        resp1 = client.post(f"/admin/pools/{pool_id}/lock-week/1", headers=headers)
        assert resp1.status_code == 200
        assert resp1.json()["auto_picks_created"] == 0

        resp2 = client.post(f"/admin/pools/{pool_id}/lock-week/1", headers=headers)
        assert resp2.status_code == 200
        assert resp2.json()["auto_picks_created"] == 0

    def test_lock_week_non_admin_forbidden(self, client):
        """A user who does not own the pool gets 403 when calling lock-week."""
        token_a = _register_and_login(client, email="lock_owner2@example.com")
        pool_id = _create_pool(client, _authed(token_a))

        token_b = _register_and_login(client, email="lock_intruder@example.com")
        resp = client.post(
            f"/admin/pools/{pool_id}/lock-week/1", headers=_authed(token_b)
        )
        assert resp.status_code == 403

    def test_lock_week_skips_entry_that_already_picked(self, client, db_session):
        """An entry that already has a pick for the week is not overwritten."""
        import models as m

        token = _register_and_login(client, email="lock_skip@example.com")
        headers = _authed(token)
        pool_id = _create_pool(client, headers)
        entry_id = _create_entry(client, headers, pool_id)

        # Pre-existing pick for week 1
        client.post(
            "/picks/create",
            json={"entry_id": entry_id, "week": 1, "team": "DAL"},
            headers=headers,
        )

        resp = client.post(f"/admin/pools/{pool_id}/lock-week/1", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["auto_picks_created"] == 0

        # Original pick must be untouched
        pick = (
            db_session.query(m.Pick)
            .filter(m.Pick.entry_id == entry_id, m.Pick.week == 1)
            .first()
        )
        assert pick is not None
        assert pick.team == "DAL"


# ---------------------------------------------------------------------------
# Test class — admin pick edit endpoint
# ---------------------------------------------------------------------------


class TestAdminPickEdit:
    """Integration tests for PATCH /admin/pools/{pool_id}/picks/{pick_id}."""

    def test_admin_update_pick_success(self, client, db_session):
        """Admin can change the team on a locked pick."""
        token = _register_and_login(client, email="pickadmin@example.com")
        headers = _authed(token)
        pool_id = _create_pool(client, headers)
        entry_id = _create_entry(client, headers, pool_id)

        pick = _create_pick(db_session, entry_id, week=1, team="NE", locked=True)

        resp = client.patch(
            f"/admin/pools/{pool_id}/picks/{pick.id}",
            json={"team": "KC"},
            headers=headers,
        )
        assert resp.status_code == 200, f"Patch failed: {resp.json()}"
        assert resp.json()["team"] == "KC"

    def test_losers_correction_updates_scoring_identity_and_alive_state(
        self, client, db_session
    ):
        """A displayed correction cannot retain the previous team's scoring ID."""
        import models as m

        token = _register_and_login(client, email="loserpickadmin@example.com")
        headers = _authed(token)
        pool_id = _create_pool(client, headers)
        entry_id = _create_entry(client, headers, pool_id)
        pool = db_session.query(m.Pool).filter_by(id=pool_id).one()
        entry = db_session.query(m.Entry).filter_by(id=entry_id).one()
        pool.survivor_objective = "lose"
        entry.alive = False
        favorite = m.Team(id=9811, name="Correction Favorite", abbrv="FAV")
        underdog = m.Team(id=9812, name="Correction Underdog", abbrv="DOG")
        game = m.Schedule(
            game_id=98101,
            season=2026,
            week_num=1,
            home_team_id=favorite.id,
            away_team_id=underdog.id,
            start_time=datetime(2026, 9, 13, 17),
            status="final",
            home_score=24,
            away_score=17,
            winning_team_id=favorite.id,
        )
        db_session.add_all([favorite, underdog, game])
        db_session.flush()
        pick = _create_pick(
            db_session, entry_id, week=1, team="FAV", locked=True
        )
        pick.team_id = favorite.id
        pick.result = "loss"
        db_session.commit()

        resp = client.patch(
            f"/admin/pools/{pool_id}/picks/{pick.id}",
            json={"team": "dog"},
            headers=headers,
        )

        assert resp.status_code == 200, resp.text
        db_session.expire_all()
        corrected = db_session.query(m.Pick).filter_by(id=pick.id).one()
        corrected_entry = db_session.query(m.Entry).filter_by(id=entry_id).one()
        assert corrected.team == "DOG"
        assert corrected.team_id == underdog.id
        assert corrected.result == "win"
        assert corrected_entry.alive is True

    def test_admin_pick_correction_rejects_unscheduled_team(
        self, client, db_session
    ):
        import models as m

        token = _register_and_login(client, email="loserinvalidadmin@example.com")
        headers = _authed(token)
        pool_id = _create_pool(client, headers)
        entry_id = _create_entry(client, headers, pool_id)
        scheduled = m.Team(id=9821, name="Scheduled", abbrv="SCH")
        opponent = m.Team(id=9822, name="Opponent", abbrv="OPP")
        unscheduled = m.Team(id=9823, name="Unscheduled", abbrv="BAD")
        game = m.Schedule(
            game_id=98201,
            season=2026,
            week_num=1,
            home_team_id=scheduled.id,
            away_team_id=opponent.id,
            start_time=datetime(2026, 9, 13, 17),
        )
        db_session.add_all([scheduled, opponent, unscheduled, game])
        db_session.flush()
        pick = _create_pick(db_session, entry_id, week=1, team="SCH", locked=True)
        pick.team_id = scheduled.id
        db_session.commit()

        resp = client.patch(
            f"/admin/pools/{pool_id}/picks/{pick.id}",
            json={"team": "BAD"},
            headers=headers,
        )

        assert resp.status_code == 400
        assert "not scheduled" in resp.json()["detail"]

    def test_admin_update_pick_team_conflict(self, client, db_session):
        """Admin cannot change a pick's team to one already used by the entry in another week."""
        token = _register_and_login(client, email="pickconflict@example.com")
        headers = _authed(token)
        pool_id = _create_pool(client, headers)
        entry_id = _create_entry(client, headers, pool_id)

        pick_w1 = _create_pick(db_session, entry_id, week=1, team="NE", locked=True)
        _create_pick(db_session, entry_id, week=2, team="KC", locked=True)

        # Try to change week-1 pick to "KC" — already used in week 2
        resp = client.patch(
            f"/admin/pools/{pool_id}/picks/{pick_w1.id}",
            json={"team": "KC"},
            headers=headers,
        )
        assert resp.status_code == 400

    def test_admin_update_pick_non_admin_forbidden(self, client, db_session):
        """A regular user (non-admin) cannot PATCH a pick via the admin endpoint."""
        token_a = _register_and_login(client, email="pickowner_a@example.com")
        pool_id = _create_pool(client, _authed(token_a))
        entry_id = _create_entry(client, _authed(token_a), pool_id)
        pick = _create_pick(db_session, entry_id, week=1, team="SF")

        token_b = _register_and_login(client, email="pickintruder_b@example.com")
        resp = client.patch(
            f"/admin/pools/{pool_id}/picks/{pick.id}",
            json={"team": "SEA"},
            headers=_authed(token_b),
        )
        assert resp.status_code == 403

    def test_admin_update_pick_not_in_pool(self, client, db_session):
        """Admin of pool A cannot edit a pick that belongs to pool B — returns 404."""
        # Pool A owner
        token_a = _register_and_login(client, email="pool_a_admin@example.com")
        pool_a_id = _create_pool(client, _authed(token_a))

        # Pool B with a pick
        token_b = _register_and_login(client, email="pool_b_owner@example.com")
        pool_b_id = _create_pool(client, _authed(token_b))
        entry_b_id = _create_entry(client, _authed(token_b), pool_b_id)
        pick_b = _create_pick(db_session, entry_b_id, week=1, team="MIA")

        # Pool A admin tries to edit pool B's pick
        resp = client.patch(
            f"/admin/pools/{pool_a_id}/picks/{pick_b.id}",
            json={"team": "BUF"},
            headers=_authed(token_a),
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# TestCSVExport
# ---------------------------------------------------------------------------


class TestCSVExport:
    """Tests for GET /admin/pools/{pool_id}/export/entries.csv"""

    def test_admin_downloads_csv_200_and_correct_content_type(self, client, db_session):
        """Admin can download entries CSV with correct Content-Type."""
        token = _register_and_login(client, email="csv_admin@example.com")
        pool_id = _create_pool(client, _authed(token))
        _create_entry(client, _authed(token), pool_id, name="Entry A")

        resp = client.get(
            f"/admin/pools/{pool_id}/export/entries.csv",
            headers=_authed(token),
        )
        assert resp.status_code == 200, resp.text
        assert "text/csv" in resp.headers.get("content-type", "")

    def test_csv_contains_all_entries(self, client, db_session):
        """CSV includes every entry in the pool from all users."""
        import models as m

        token_a = _register_and_login(client, email="csv_a@example.com")
        token_b = _register_and_login(client, email="csv_b@example.com")
        pool_id = _create_pool(client, _authed(token_a))
        # Admin needs to allow token_b user to create entry — pool has no lock
        _create_entry(client, _authed(token_a), pool_id, name="A Entry")
        _create_entry(client, _authed(token_b), pool_id, name="B Entry")

        resp = client.get(
            f"/admin/pools/{pool_id}/export/entries.csv",
            headers=_authed(token_a),
        )
        assert resp.status_code == 200
        body = resp.text
        assert "csv_a@example.com" in body
        assert "csv_b@example.com" in body
        assert "A Entry" in body
        assert "B Entry" in body

    def test_csv_has_header_row(self, client, db_session):
        """CSV always has a header row even for an empty pool."""
        token = _register_and_login(client, email="csv_empty@example.com")
        pool_id = _create_pool(client, _authed(token))

        resp = client.get(
            f"/admin/pools/{pool_id}/export/entries.csv",
            headers=_authed(token),
        )
        assert resp.status_code == 200
        lines = resp.text.strip().splitlines()
        assert lines[0] == "email,entry_name"

    def test_csv_sorted_by_email_then_entry_name(self, client, db_session):
        """CSV rows are ordered by email then entry name."""
        token_a = _register_and_login(client, email="aaa_csv@example.com")
        token_b = _register_and_login(client, email="bbb_csv@example.com")
        pool_id = _create_pool(client, _authed(token_a))
        _create_entry(client, _authed(token_a), pool_id, name="Z Entry")
        _create_entry(client, _authed(token_a), pool_id, name="A Entry")
        _create_entry(client, _authed(token_b), pool_id, name="B Entry")

        resp = client.get(
            f"/admin/pools/{pool_id}/export/entries.csv",
            headers=_authed(token_a),
        )
        assert resp.status_code == 200
        lines = resp.text.strip().splitlines()
        data_lines = lines[1:]  # skip header
        emails = [ln.split(",")[0] for ln in data_lines]
        assert emails == sorted(emails), "Rows not sorted by email"

    def test_non_admin_csv_download_forbidden(self, client, db_session):
        """Non-admin user cannot download the CSV — returns 403."""
        token_owner = _register_and_login(client, email="csv_owner@example.com")
        token_other = _register_and_login(client, email="csv_other@example.com")
        pool_id = _create_pool(client, _authed(token_owner))

        resp = client.get(
            f"/admin/pools/{pool_id}/export/entries.csv",
            headers=_authed(token_other),
        )
        assert resp.status_code == 403

    def test_csv_neutralizes_spreadsheet_formulas(self, client, db_session):
        token = _register_and_login(client, email="csv_formula@example.com")
        pool_id = _create_pool(client, _authed(token))
        _create_entry(
            client, _authed(token), pool_id, name='=HYPERLINK("https://evil.invalid")'
        )

        resp = client.get(
            f"/admin/pools/{pool_id}/export/entries.csv",
            headers=_authed(token),
        )

        assert resp.status_code == 200
        assert "'=HYPERLINK" in resp.text


# ---------------------------------------------------------------------------
# TestUserLock
# ---------------------------------------------------------------------------


class TestUserLock:
    """Tests for POST/DELETE /admin/pools/{pool_id}/users/{user_id}/lock"""

    def _get_user_id(self, db_session, email):
        import models as m

        user = db_session.query(m.User).filter(m.User.email == email).first()
        assert user is not None
        return user.id

    def test_lock_creates_row_200(self, client, db_session):
        """Admin can lock a user in a pool — returns 200 with lock record."""
        token = _register_and_login(client, email="lock_admin@example.com")
        target_token = _register_and_login(client, email="lock_target@example.com")
        pool_id = _create_pool(client, _authed(token))
        target_id = self._get_user_id(db_session, "lock_target@example.com")
        _add_pool_member(db_session, pool_id, "lock_target@example.com")

        resp = client.post(
            f"/admin/pools/{pool_id}/users/{target_id}/lock",
            json={},
            headers=_authed(token),
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["pool_id"] == pool_id
        assert data["user_id"] == target_id

    def test_duplicate_lock_returns_409(self, client, db_session):
        """Locking an already-locked user returns 409."""
        token = _register_and_login(client, email="lock_dup_admin@example.com")
        _register_and_login(client, email="lock_dup_target@example.com")
        pool_id = _create_pool(client, _authed(token))
        target_id = self._get_user_id(db_session, "lock_dup_target@example.com")
        _add_pool_member(db_session, pool_id, "lock_dup_target@example.com")

        client.post(
            f"/admin/pools/{pool_id}/users/{target_id}/lock",
            json={},
            headers=_authed(token),
        )
        resp = client.post(
            f"/admin/pools/{pool_id}/users/{target_id}/lock",
            json={},
            headers=_authed(token),
        )
        assert resp.status_code == 409

    def test_unlock_removes_row_200(self, client, db_session):
        """Admin can unlock a user — returns 200."""
        token = _register_and_login(client, email="unlock_admin@example.com")
        _register_and_login(client, email="unlock_target@example.com")
        pool_id = _create_pool(client, _authed(token))
        target_id = self._get_user_id(db_session, "unlock_target@example.com")
        _add_pool_member(db_session, pool_id, "unlock_target@example.com")

        client.post(
            f"/admin/pools/{pool_id}/users/{target_id}/lock",
            json={},
            headers=_authed(token),
        )
        resp = client.delete(
            f"/admin/pools/{pool_id}/users/{target_id}/lock", headers=_authed(token)
        )
        assert resp.status_code == 200

    def test_unlock_when_not_locked_returns_404(self, client, db_session):
        """Unlocking a user who is not locked returns 404."""
        token = _register_and_login(client, email="unlock_noop_admin@example.com")
        _register_and_login(client, email="unlock_noop_target@example.com")
        pool_id = _create_pool(client, _authed(token))
        target_id = self._get_user_id(db_session, "unlock_noop_target@example.com")
        _add_pool_member(db_session, pool_id, "unlock_noop_target@example.com")

        resp = client.delete(
            f"/admin/pools/{pool_id}/users/{target_id}/lock", headers=_authed(token)
        )
        assert resp.status_code == 404

    def test_non_admin_cannot_lock_user(self, client, db_session):
        """Non-admin cannot call the lock endpoint — returns 403."""
        owner_token = _register_and_login(client, email="lock_ne_owner@example.com")
        other_token = _register_and_login(client, email="lock_ne_other@example.com")
        _register_and_login(client, email="lock_ne_target@example.com")
        pool_id = _create_pool(client, _authed(owner_token))
        target_id = self._get_user_id(db_session, "lock_ne_target@example.com")

        resp = client.post(
            f"/admin/pools/{pool_id}/users/{target_id}/lock",
            json={},
            headers=_authed(other_token),
        )
        assert resp.status_code == 403

    def test_admin_cannot_lock_user_from_another_league(self, client, db_session):
        owner_token = _register_and_login(client, "lock_scope_owner@example.com")
        _register_and_login(client, "lock_scope_outsider@example.com")
        pool_id = _create_pool(client, _authed(owner_token))
        target_id = self._get_user_id(db_session, "lock_scope_outsider@example.com")

        response = client.post(
            f"/admin/pools/{pool_id}/users/{target_id}/lock",
            json={},
            headers=_authed(owner_token),
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "User not found in this pool"


# ---------------------------------------------------------------------------
# TestUserLockEnforcement
# ---------------------------------------------------------------------------


class TestUserLockEnforcement:
    """Tests that locked users cannot create/modify entries or picks."""

    def _lock_user(self, client, admin_token, pool_id, user_id):
        resp = client.post(
            f"/admin/pools/{pool_id}/users/{user_id}/lock",
            json={},
            headers=_authed(admin_token),
        )
        assert resp.status_code == 200, f"Lock failed: {resp.text}"

    def _get_user_id(self, db_session, email):
        import models as m

        user = db_session.query(m.User).filter(m.User.email == email).first()
        return user.id

    def test_locked_user_cannot_create_entry(self, client, db_session):
        """Locked user gets 423 when trying to create an entry in the locked pool."""
        admin_token = _register_and_login(client, email="enf_admin@example.com")
        user_token = _register_and_login(client, email="enf_user@example.com")
        pool_id = _create_pool(client, _authed(admin_token))
        user_id = self._get_user_id(db_session, "enf_user@example.com")
        _add_pool_member(db_session, pool_id, "enf_user@example.com")

        self._lock_user(client, admin_token, pool_id, user_id)

        resp = client.post(
            "/entries/create",
            json={"pool_id": pool_id, "name": "Locked Entry"},
            headers=_authed(user_token),
        )
        assert resp.status_code == 423, resp.text
        assert "locked" in resp.json().get("detail", "").lower()

    def test_locked_user_cannot_delete_entry(self, client, db_session):
        """Locked user gets 423 when trying to delete an entry in the locked pool."""
        admin_token = _register_and_login(client, email="enf_del_admin@example.com")
        user_token = _register_and_login(client, email="enf_del_user@example.com")
        pool_id = _create_pool(client, _authed(admin_token))

        # Create entry before locking
        entry_resp = client.post(
            "/entries/create",
            json={"pool_id": pool_id, "name": "Pre-lock Entry"},
            headers=_authed(user_token),
        )
        assert entry_resp.status_code == 200
        entry_id = entry_resp.json()["id"]

        user_id = self._get_user_id(db_session, "enf_del_user@example.com")
        self._lock_user(client, admin_token, pool_id, user_id)

        resp = client.delete(f"/entries/{entry_id}", headers=_authed(user_token))
        assert resp.status_code == 423, resp.text

    def test_locked_user_cannot_create_pick(self, client, db_session):
        """Locked user gets 423 when submitting a pick in the locked pool."""
        admin_token = _register_and_login(client, email="enf_pick_admin@example.com")
        user_token = _register_and_login(client, email="enf_pick_user@example.com")
        pool_id = _create_pool(client, _authed(admin_token))

        # Create entry before locking
        entry_resp = client.post(
            "/entries/create",
            json={"pool_id": pool_id, "name": "Pick Entry"},
            headers=_authed(user_token),
        )
        assert entry_resp.status_code == 200
        entry_id = entry_resp.json()["id"]

        user_id = self._get_user_id(db_session, "enf_pick_user@example.com")
        self._lock_user(client, admin_token, pool_id, user_id)

        resp = client.post(
            "/picks/create",
            json={"entry_id": entry_id, "week": 1, "team": "NE"},
            headers=_authed(user_token),
        )
        assert resp.status_code == 423, resp.text

    def test_locked_user_cannot_clear_pick(self, client, db_session):
        """Locked users cannot clear a previously saved Survivor pick."""
        admin_token = _register_and_login(client, email="enf_clear_admin@example.com")
        user_token = _register_and_login(client, email="enf_clear_user@example.com")
        pool_id = _create_pool(client, _authed(admin_token))
        entry_resp = client.post(
            "/entries/create",
            json={"pool_id": pool_id, "name": "Clear Pick Entry"},
            headers=_authed(user_token),
        )
        assert entry_resp.status_code == 200
        pick_resp = client.post(
            "/picks/create",
            json={"entry_id": entry_resp.json()["id"], "week": 1, "team": "NE"},
            headers=_authed(user_token),
        )
        assert pick_resp.status_code == 200

        user_id = self._get_user_id(db_session, "enf_clear_user@example.com")
        self._lock_user(client, admin_token, pool_id, user_id)

        response = client.delete(
            f"/picks/{pick_resp.json()['id']}", headers=_authed(user_token)
        )
        assert response.status_code == 423
        assert "locked" in response.json()["detail"].lower()

    def test_locked_user_can_still_log_in(self, client, db_session):
        """Locking a user in a pool does not affect their ability to log in."""
        admin_token = _register_and_login(client, email="enf_login_admin@example.com")
        _register_and_login(client, email="enf_login_user@example.com")
        pool_id = _create_pool(client, _authed(admin_token))
        user_id = self._get_user_id(db_session, "enf_login_user@example.com")
        _add_pool_member(db_session, pool_id, "enf_login_user@example.com")
        self._lock_user(client, admin_token, pool_id, user_id)

        # Login should still succeed
        login_resp = client.post(
            "/auth/login",
            json={"email": "enf_login_user@example.com", "password": "Test1234!"},
        )
        assert login_resp.status_code == 200
        assert "access_token" in login_resp.json()

    def test_locked_user_can_create_entry_in_other_pool(self, client, db_session):
        """Lock in pool A does not affect pool B."""
        admin_token = _register_and_login(client, email="enf_other_admin@example.com")
        user_token = _register_and_login(client, email="enf_other_user@example.com")

        pool_a = _create_pool(client, _authed(admin_token))
        pool_b = _create_pool(client, _authed(admin_token))

        user_id = self._get_user_id(db_session, "enf_other_user@example.com")
        _add_pool_member(db_session, pool_a, "enf_other_user@example.com")
        self._lock_user(client, admin_token, pool_a, user_id)

        # Should succeed in pool B
        resp = client.post(
            "/entries/create",
            json={"pool_id": pool_b, "name": "Pool B Entry"},
            headers=_authed(user_token),
        )
        assert (
            resp.status_code == 200
        ), f"Expected 200 in unlocked pool, got {resp.status_code}: {resp.text}"

    def test_admin_can_transfer_locked_users_entry(self, client, db_session):
        """Admin transfer works even when the entry owner is locked in the pool."""
        admin_token = _register_and_login(client, email="enf_xfr_admin@example.com")
        user_token = _register_and_login(client, email="enf_xfr_user@example.com")
        new_owner_token = _register_and_login(
            client, email="enf_xfr_newowner@example.com"
        )
        pool_id = _create_pool(client, _authed(admin_token))

        entry_resp = client.post(
            "/entries/create",
            json={"pool_id": pool_id, "name": "Transfer Target"},
            headers=_authed(user_token),
        )
        assert entry_resp.status_code == 200
        entry_id = entry_resp.json()["id"]
        _add_pool_member(db_session, pool_id, "enf_xfr_newowner@example.com")

        user_id = self._get_user_id(db_session, "enf_xfr_user@example.com")
        self._lock_user(client, admin_token, pool_id, user_id)

        resp = client.post(
            f"/admin/pools/{pool_id}/transfer-entry",
            json={"entry_id": entry_id, "to_email": "enf_xfr_newowner@example.com"},
            headers=_authed(admin_token),
        )
        assert resp.status_code == 200, f"Transfer should succeed: {resp.text}"
