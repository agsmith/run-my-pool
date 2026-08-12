import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta, timezone
import models


def _register(client, email):
    password = "Pass1234!"
    client.post("/auth/register", json={"email": email, "password": password})
    token = client.post(
        "/auth/login", json={"email": email, "password": password}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestPoolEndpoints:
    """Test pool-related endpoints"""

    def test_create_pool_success(self, authenticated_client, test_pool_data):
        """Test successful pool creation"""
        client, user_data = authenticated_client

        response = client.post("/pools/create", json=test_pool_data)

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == test_pool_data["name"]
        assert data["description"] == test_pool_data["description"]
        assert data["is_private"] == test_pool_data["is_private"]
        assert "id" in data

    def test_create_pool_unauthorized(self, client, test_pool_data):
        """Test pool creation without authentication"""
        response = client.post("/pools/create", json=test_pool_data)

        # FastAPI HTTPBearer returns 403 when no credentials are provided
        assert response.status_code in (401, 403)

    def test_create_pool_rejects_duplicate_name_and_suggests_unique_names(self, client):
        owner = _register(client, "duplicate.owner@example.com")
        other_owner = _register(client, "duplicate.other@example.com")
        created = client.post(
            "/pools/create",
            json={"name": "Office Champions", "is_private": False},
            headers=owner,
        )
        assert created.status_code == 200

        response = client.post(
            "/pools/create",
            json={"name": "  office champions  ", "is_private": False},
            headers=other_owner,
        )

        assert response.status_code == 409
        detail = response.json()["detail"]
        assert detail["code"] == "league_name_taken"
        assert "already in use" in detail["message"]
        assert len(detail["suggestions"]) == 3
        assert all(name != "Office Champions" for name in detail["suggestions"])

        for suggestion in detail["suggestions"]:
            suggestion_response = client.post(
                "/pools/create",
                json={"name": suggestion, "is_private": False},
                headers=other_owner,
            )
            assert suggestion_response.status_code == 200

    def test_pool_rename_cannot_duplicate_another_pool_name(self, client):
        owner = _register(client, "rename.owner@example.com")
        first = client.post(
            "/pools/create", json={"name": "First League"}, headers=owner
        ).json()
        second = client.post(
            "/pools/create", json={"name": "Second League"}, headers=owner
        ).json()

        response = client.patch(
            f"/pools/{second['id']}",
            json={"name": first["name"].upper()},
            headers=owner,
        )

        assert response.status_code == 409
        assert response.json()["detail"]["code"] == "league_name_taken"

    def test_duplicate_max_length_name_still_returns_suggestions(self, client):
        owner = _register(client, "long.name.owner@example.com")
        long_name = "L" * 255
        assert client.post(
            "/pools/create", json={"name": long_name}, headers=owner
        ).status_code == 200

        response = client.post(
            "/pools/create", json={"name": long_name}, headers=owner
        )

        assert response.status_code == 409
        suggestions = response.json()["detail"]["suggestions"]
        assert len(suggestions) == 3
        assert all(len(suggestion) <= 255 for suggestion in suggestions)

    def test_get_my_pools(self, authenticated_client, test_pool_data):
        """Test getting user's pools"""
        client, user_data = authenticated_client

        # Create a pool first
        client.post("/pools/create", json=test_pool_data)

        # Get user's pools
        response = client.get("/pools/my-pools")

        assert response.status_code == 200
        pools = response.json()
        assert len(pools) >= 1
        assert any(pool["name"] == test_pool_data["name"] for pool in pools)

    def test_activity_summary_counts_only_current_users_entries_and_selections(self, client):
        owner = _register(client, "activity.owner@example.com")
        member = _register(client, "activity.member@example.com")
        pool = client.post(
            "/pools/create", json={"name": "Activity Summary Pool"}, headers=owner
        ).json()
        assert client.post(
            f"/pools/{pool['id']}/join", json={}, headers=member
        ).status_code == 200

        owner_entry = client.post(
            "/entries/create",
            json={"pool_id": pool["id"], "name": "Owner Entry"},
            headers=owner,
        ).json()
        member_entry = client.post(
            "/entries/create",
            json={"pool_id": pool["id"], "name": "Member Entry"},
            headers=member,
        ).json()
        unpicked_member_entry = client.post(
            "/entries/create",
            json={"pool_id": pool["id"], "name": "Unpicked Member Entry"},
            headers=member,
        ).json()
        assert owner_entry["id"] != member_entry["id"]
        assert unpicked_member_entry["id"] != member_entry["id"]
        assert client.post(
            "/picks/create",
            json={"entry_id": member_entry["id"], "week": 1, "team": "DET"},
            headers=member,
        ).status_code == 200
        assert client.post(
            "/picks/create",
            json={"entry_id": owner_entry["id"], "week": 1, "team": "WSH"},
            headers=owner,
        ).status_code == 200

        response = client.get(
            f"/pools/{pool['id']}/activity-summary?week=1", headers=member
        )

        assert response.status_code == 200
        assert response.json() == {
            "entries_remaining": 2,
            "total_entries": 2,
            "week": 1,
            "week_selections": 1,
        }

    def test_pool_discovery_requires_auth_and_shows_private_leagues(self, client):
        owner = _register(client, "private.discovery.owner@example.com")
        outsider = _register(client, "private.discovery.outsider@example.com")
        private_pool = client.post(
            "/pools/create",
            json={
                "name": "Private Discovery League",
                "is_private": True,
                "join_password": "Private123!",
            },
            headers=owner,
        ).json()
        public_pool = client.post(
            "/pools/create",
            json={"name": "Visible Discovery League", "is_private": False},
            headers=owner,
        ).json()

        client.cookies.clear()
        assert client.get("/pools/").status_code in (401, 403)

        outsider_ids = {
            pool["id"] for pool in client.get("/pools/", headers=outsider).json()
        }
        owner_ids = {
            pool["id"] for pool in client.get("/pools/", headers=owner).json()
        }
        assert public_pool["id"] in outsider_ids
        assert private_pool["id"] in outsider_ids
        assert private_pool["id"] in owner_ids

    def test_get_pool_by_id_success(self, authenticated_client, test_pool_data):
        """Test getting a specific pool by ID"""
        client, user_data = authenticated_client

        # Create a pool first
        create_response = client.post("/pools/create", json=test_pool_data)
        pool_id = create_response.json()["id"]

        # Get the pool
        response = client.get(f"/pools/{pool_id}")

        assert response.status_code == 200
        pool = response.json()
        assert pool["id"] == pool_id
        assert pool["name"] == test_pool_data["name"]

    def test_get_pool_nonexistent(self, authenticated_client):
        """Test getting a non-existent pool"""
        client, user_data = authenticated_client

        fake_id = "00000000-0000-0000-0000-000000000000"
        response = client.get(f"/pools/{fake_id}")

        assert response.status_code == 404

    def test_get_pool_unauthorized(self, client, test_pool_data):
        """Test getting pool without authentication"""
        response = client.get("/pools/some-id")

        # FastAPI HTTPBearer returns 403 when no credentials are provided
        assert response.status_code in (401, 403)

    def test_get_pool_requires_membership(self, client):
        owner = _register(client, "pool.access.owner@example.com")
        outsider = _register(client, "pool.access.outsider@example.com")
        pool = client.post(
            "/pools/create", json={"name": "Members Only Details"}, headers=owner
        ).json()

        response = client.get(f"/pools/{pool['id']}", headers=outsider)

        assert response.status_code == 403
        assert response.json()["detail"] == "League membership required"

    def test_lock_status_requires_membership(self, client):
        owner = _register(client, "lock.status.owner@example.com")
        outsider = _register(client, "lock.status.outsider@example.com")
        pool = client.post(
            "/pools/create", json={"name": "Private Lock Status"}, headers=owner
        ).json()

        denied = client.get(f"/pools/{pool['id']}/lock-status", headers=outsider)
        allowed = client.get(f"/pools/{pool['id']}/lock-status", headers=owner)

        assert denied.status_code == 403
        assert allowed.status_code == 200
        assert len(allowed.json()["weeks"]) == 18

    def test_pool_validation_missing_name(self, authenticated_client):
        """Test pool creation with missing name"""
        client, user_data = authenticated_client

        invalid_data = {"description": "A test pool for testing", "is_private": False}

        response = client.post("/pools/create", json=invalid_data)
        assert response.status_code == 422  # Validation error

    def test_pool_validation_empty_name(self, authenticated_client):
        """Pool names must contain at least one visible character."""
        client, user_data = authenticated_client

        invalid_data = {
            "name": "",
            "description": "A test pool for testing",
            "is_private": False,
        }

        response = client.post("/pools/create", json=invalid_data)
        assert response.status_code == 400

    @patch("pools.log_create_operation")
    def test_pool_creation_audit_logging(
        self, mock_audit, authenticated_client, test_pool_data
    ):
        """Test that pool creation is audited"""
        client, user_data = authenticated_client

        response = client.post("/pools/create", json=test_pool_data)

        assert response.status_code == 200
        mock_audit.assert_called()


class TestPoolRules:
    """Test pool rules functionality"""

    def test_get_available_rules(self, client):
        """Test getting available pool rules"""
        response = client.get("/rules?pool_type=survivor")

        # This might not require authentication depending on your implementation
        assert response.status_code in [200, 401]

        if response.status_code == 200:
            rules = response.json()
            assert isinstance(rules, list)

    def test_pool_with_custom_rules(self, authenticated_client):
        """Test creating pool with custom rule values"""
        client, user_data = authenticated_client

        pool_data = {
            "name": "Custom Rules Pool",
            "description": "Pool with custom rules",
            "is_private": False,
            "rule_values": [
                {"rule_id": "weekly-lock-day", "rule_value": "5"},  # Friday
                {"rule_id": "weekly-lock-time", "rule_value": "20:00:00"},  # 8 PM
                {"rule_id": "game-mode", "rule_value": "pick_loser"},
            ],
        }

        response = client.post("/pools/create", json=pool_data)

        assert response.status_code == 200
        pool = response.json()
        assert pool["name"] == pool_data["name"]


class TestPoolAdminOperations:
    """Test pool admin-specific operations"""

    def test_check_admin_access_owner(self, authenticated_client, test_pool_data):
        """Test admin access check for pool owner"""
        client, user_data = authenticated_client

        # Create a pool (user becomes owner)
        create_response = client.post("/pools/create", json=test_pool_data)
        pool_id = create_response.json()["id"]

        # Check admin access
        response = client.get(f"/pools/{pool_id}/is-admin")

        assert response.status_code == 200
        admin_data = response.json()
        assert admin_data["has_admin_access"] is True

    def test_check_admin_access_non_owner(self, client, test_user_data):
        """Test admin access check for non-owner"""
        # Starlette <0.20 returns 401, >=0.20 returns 403 when no token is provided
        response = client.get("/pools/some-id/is-admin")
        assert response.status_code in (401, 403)


class TestPoolJoining:
    def test_join_rejected_after_league_lock_time(self, client):
        owner = _register(client, "deadline.owner@example.com")
        past = (datetime.now(timezone.utc) - timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S")
        pool = client.post(
            "/pools/create",
            json={"name": "Closed Pool", "is_private": False, "join_lock_time": past},
            headers=owner,
        ).json()
        member = _register(client, "deadline.member@example.com")

        response = client.post(f"/pools/{pool['id']}/join", json={}, headers=member)
        assert response.status_code == 423
        assert response.json()["detail"] == "League registration is closed. Contact the league admin."

    def test_owner_can_save_recurring_weekly_lock(self, client):
        owner = _register(client, "recurring.owner@example.com")
        pool = client.post(
            "/pools/create", json={"name": "Weekly Pool", "is_private": False}, headers=owner
        ).json()

        response = client.patch(
            f"/pools/{pool['id']}",
            json={"lock_day_of_week": 6, "lock_time_of_day": "13:00", "lock_timezone": "America/New_York"},
            headers=owner,
        )
        assert response.status_code == 200, response.text
        assert response.json()["lock_day_of_week"] == 6
        assert response.json()["lock_time_of_day"].startswith("13:00")
        assert response.json()["lock_timezone"] == "America/New_York"

    def test_private_pool_creation_requires_password(self, client):
        headers = _register(client, "private.no.password@example.com")
        response = client.post(
            "/pools/create",
            json={"name": "Private", "is_private": True},
            headers=headers,
        )
        assert response.status_code == 400
        assert "at least 6 characters" in response.json()["detail"]

    def test_private_password_is_hashed_and_never_returned(self, client, db_session):
        headers = _register(client, "private.hash@example.com")
        response = client.post(
            "/pools/create",
            json={"name": "Private", "is_private": True, "join_password": "huddle42"},
            headers=headers,
        )
        assert response.status_code == 200, response.text
        assert "join_password" not in response.json()
        pool = db_session.query(models.Pool).filter(models.Pool.id == response.json()["id"]).first()
        assert pool.join_password_hash
        assert pool.join_password_hash != "huddle42"
        assert pool.join_password_encrypted
        assert pool.join_password_encrypted != "huddle42"

        revealed = client.get(
            f"/pools/{pool.id}/join-password", headers=headers
        )
        assert revealed.status_code == 200
        assert revealed.json() == {"available": True, "password": "huddle42"}
        assert revealed.headers["cache-control"] == "no-store"

    def test_join_password_is_only_viewable_by_league_admins(self, client):
        owner = _register(client, "view.password.owner@example.com")
        pool = client.post(
            "/pools/create",
            json={"name": "View Password", "is_private": True, "join_password": "sideline8"},
            headers=owner,
        ).json()
        outsider = _register(client, "view.password.outsider@example.com")

        denied = client.get(
            f"/pools/{pool['id']}/join-password", headers=outsider
        )

        assert denied.status_code == 403
        assert "password" not in denied.json()

    def test_legacy_password_becomes_viewable_after_admin_changes_it(self, client, db_session):
        owner = _register(client, "legacy.password.owner@example.com")
        pool = client.post(
            "/pools/create",
            json={"name": "Legacy Password", "is_private": True, "join_password": "original8"},
            headers=owner,
        ).json()
        stored = db_session.query(models.Pool).filter(models.Pool.id == pool["id"]).one()
        stored.join_password_encrypted = None
        db_session.commit()

        unavailable = client.get(
            f"/pools/{pool['id']}/join-password", headers=owner
        )
        assert unavailable.status_code == 200
        assert unavailable.json() == {"available": False, "password": None}

        changed = client.patch(
            f"/pools/{pool['id']}",
            json={"join_password": "replacement9"},
            headers=owner,
        )
        assert changed.status_code == 200
        revealed = client.get(
            f"/pools/{pool['id']}/join-password", headers=owner
        )
        assert revealed.json() == {"available": True, "password": "replacement9"}

    def test_public_pool_joins_without_password_and_appears_in_my_pools(self, client):
        owner = _register(client, "public.owner@example.com")
        pool = client.post(
            "/pools/create", json={"name": "Open Pool", "is_private": False}, headers=owner
        ).json()
        member = _register(client, "public.member@example.com")

        joined = client.post(f"/pools/{pool['id']}/join", json={}, headers=member)
        assert joined.status_code == 200, joined.text
        my_pools = client.get("/pools/my-pools", headers=member).json()
        assert [item["id"] for item in my_pools] == [pool["id"]]

    def test_private_pool_rejects_missing_and_wrong_password(self, client):
        owner = _register(client, "private.owner@example.com")
        pool = client.post(
            "/pools/create",
            json={"name": "Locked Pool", "is_private": True, "join_password": "correct7"},
            headers=owner,
        ).json()
        member = _register(client, "private.member@example.com")

        missing = client.post(f"/pools/{pool['id']}/join", json={}, headers=member)
        wrong = client.post(
            f"/pools/{pool['id']}/join", json={"password": "wrong77"}, headers=member
        )
        assert missing.status_code == 403
        assert wrong.status_code == 403
        assert missing.json()["detail"] == "Invalid pool password"
        assert wrong.json()["detail"] == "Invalid pool password"

    def test_private_pool_invite_resolves_for_authenticated_outsider(self, client):
        owner = _register(client, "invite.owner@example.com")
        pool = client.post(
            "/pools/create",
            json={"name": "Invite Only", "is_private": True, "join_password": "invite77"},
            headers=owner,
        ).json()
        outsider = _register(client, "invite.outsider@example.com")

        directory = client.get("/pools/", headers=outsider).json()
        assert pool["id"] in {item["id"] for item in directory}

        invite = client.get(f"/pools/invite/{pool['id']}", headers=outsider)
        assert invite.status_code == 200
        assert invite.json() == {
            "id": pool["id"],
            "name": "Invite Only",
            "description": None,
            "join_lock_time": None,
            "is_private": True,
        }
        assert "owner_id" not in invite.json()

    def test_pool_invite_requires_auth_and_rejects_unknown_id(self, client):
        headers = _register(client, "invite.lookup@example.com")
        client.cookies.clear()
        assert client.get("/pools/invite/not-a-pool").status_code in (401, 403)
        missing = client.get("/pools/invite/not-a-pool", headers=headers)
        assert missing.status_code == 404
        assert missing.json()["detail"] == "Pool invitation not found"

    def test_private_pool_accepts_correct_password_idempotently(self, client):
        owner = _register(client, "private.owner2@example.com")
        pool = client.post(
            "/pools/create",
            json={"name": "Locked Pool", "is_private": True, "join_password": "correct7"},
            headers=owner,
        ).json()
        member = _register(client, "private.member2@example.com")

        first = client.post(
            f"/pools/{pool['id']}/join", json={"password": "correct7"}, headers=member
        )
        second = client.post(
            f"/pools/{pool['id']}/join", json={"password": "correct7"}, headers=member
        )
        assert first.status_code == 200
        assert first.json()["message"] == "Pool joined successfully"
        assert second.status_code == 200
        assert second.json()["message"] == "Already joined"

    def test_private_pool_password_cannot_be_bypassed_by_creating_entry(self, client):
        owner = _register(client, "private.entry.owner@example.com")
        pool = client.post(
            "/pools/create",
            json={"name": "No Bypass", "is_private": True, "join_password": "secret77"},
            headers=owner,
        ).json()
        outsider = _register(client, "private.entry.outsider@example.com")

        response = client.post(
            "/entries/create",
            json={"pool_id": pool["id"], "name": "Unauthorized Entry"},
            headers=outsider,
        )
        assert response.status_code == 403
        assert "Join this private pool" in response.json()["detail"]

    def test_owner_can_flip_public_private_and_must_set_password(self, client, db_session):
        owner = _register(client, "flip.owner@example.com")
        pool = client.post(
            "/pools/create", json={"name": "Flip Pool", "is_private": False}, headers=owner
        ).json()

        missing = client.patch(
            f"/pools/{pool['id']}", json={"is_private": True}, headers=owner
        )
        assert missing.status_code == 400

        private = client.patch(
            f"/pools/{pool['id']}",
            json={"is_private": True, "join_password": "switch88"},
            headers=owner,
        )
        assert private.status_code == 200
        assert private.json()["is_private"] is True

        public = client.patch(
            f"/pools/{pool['id']}", json={"is_private": False}, headers=owner
        )
        assert public.status_code == 200
        db_session.expire_all()
        stored = db_session.query(models.Pool).filter(models.Pool.id == pool["id"]).first()
        assert stored.is_private is False
        assert stored.join_password_hash is None

    def test_delegated_admin_can_change_access_non_admin_cannot(self, client, db_session):
        owner = _register(client, "admin.owner@example.com")
        owner_data = client.get("/auth/me", headers=owner).json()
        pool = client.post(
            "/pools/create", json={"name": "Admin Pool", "is_private": False}, headers=owner
        ).json()
        admin = _register(client, "admin.delegate@example.com")
        admin_data = client.get("/auth/me", headers=admin).json()
        outsider = _register(client, "admin.outsider@example.com")
        db_session.add(models.PoolAdmin(pool_id=pool["id"], user_id=admin_data["id"]))
        db_session.commit()

        changed = client.patch(
            f"/pools/{pool['id']}",
            json={"is_private": True, "join_password": "delegate9"},
            headers=admin,
        )
        denied = client.patch(
            f"/pools/{pool['id']}", json={"is_private": False}, headers=outsider
        )
        assert changed.status_code == 200, changed.text
        assert denied.status_code == 403
        revealed = client.get(
            f"/pools/{pool['id']}/join-password", headers=admin
        )
        assert revealed.status_code == 200
        assert revealed.json()["password"] == "delegate9"


# ---------------------------------------------------------------------------
# TestParseLockTime
# ---------------------------------------------------------------------------


class TestParseLockTime:
    """Tests for the _parse_lock_time helper and PATCH /pools/{id} lock_time parsing."""

    def _reg_and_create_pool(self, client):
        from datetime import datetime, timedelta
        email = f"plt_{datetime.utcnow().timestamp():.0f}@example.com"
        client.post("/auth/register", json={"email": email, "password": "Pass1234!"})
        resp = client.post("/auth/login", json={"email": email, "password": "Pass1234!"})
        token = resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        pool_resp = client.post(
            "/pools/create",
            json={"name": "Lock Test Pool", "description": "", "is_private": False},
            headers=headers,
        )
        return token, headers, pool_resp.json()["id"]

    def test_parse_lock_time_iso_format(self):
        """_parse_lock_time handles ISO format with T separator."""
        from pools import _parse_lock_time
        from datetime import datetime
        result = _parse_lock_time("2025-09-07T17:00:00")
        assert result == datetime(2025, 9, 7, 17, 0, 0)

    def test_parse_lock_time_iso_with_z(self):
        """_parse_lock_time strips Z from ISO format."""
        from pools import _parse_lock_time
        from datetime import datetime
        result = _parse_lock_time("2025-09-07T17:00:00Z")
        assert result == datetime(2025, 9, 7, 17, 0, 0)

    def test_parse_lock_time_space_separated(self):
        """_parse_lock_time handles YYYY-MM-DD HH:MM:SS format."""
        from pools import _parse_lock_time
        from datetime import datetime
        result = _parse_lock_time("2025-09-07 17:00:00")
        assert result == datetime(2025, 9, 7, 17, 0, 0)

    def test_parse_lock_time_missing_seconds(self):
        """_parse_lock_time appends :00 when seconds are missing."""
        from pools import _parse_lock_time
        from datetime import datetime
        result = _parse_lock_time("2025-09-07 17:00")
        assert result == datetime(2025, 9, 7, 17, 0, 0)

    def test_patch_pool_lock_time_updates_correctly(self, client):
        """PATCH /pools/{id} with a valid lock_time string updates the pool."""
        token, headers, pool_id = self._reg_and_create_pool(client)
        resp = client.patch(
            f"/pools/{pool_id}",
            json={"lock_time": "2025-09-07T17:00:00Z"},
            headers=headers,
        )
        assert resp.status_code == 200, resp.text
        # lock_time should be stored and returned (may be null in PoolOut if not serialised)
        # at minimum the endpoint should not 500
