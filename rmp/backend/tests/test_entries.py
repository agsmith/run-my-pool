import pytest
from datetime import datetime, timedelta, timezone


def _register_and_login(client, email="locktest@example.com", password="Test1234!"):
    """Register a user and return an auth token."""
    client.post("/auth/register", json={"email": email, "password": password})
    resp = client.post("/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, f"Login failed: {resp.json()}"
    return resp.json()["access_token"]


def _authed(client, token):
    """Return headers dict with bearer token."""
    return {"Authorization": f"Bearer {token}"}


class TestEntryLockEnforcement:
    """Tests for pool lock time enforcement on entry create and delete."""

    def _create_pool(self, client, headers, lock_time=None):
        """Helper: create a pool, optionally with a lock_time."""
        pool_data = {
            "name": "Lock Test Pool",
            "description": "Pool for lock enforcement tests",
            "is_private": False,
            "rule_values": [
                {"rule_id": "weekly-lock-day", "rule_value": "0"},
                {"rule_id": "weekly-lock-time", "rule_value": "13:00:00"},
                {"rule_id": "game-mode", "rule_value": "pick_winner"},
            ],
        }
        if lock_time is not None:
            pool_data["lock_time"] = lock_time

        response = client.post("/pools/create", json=pool_data, headers=headers)
        assert response.status_code == 200, f"Pool creation failed: {response.json()}"
        return response.json()["id"]

    def _create_entry(self, client, headers, pool_id, name="Test Entry"):
        """Helper: attempt to create an entry in a pool."""
        return client.post(
            "/entries/create",
            json={"pool_id": pool_id, "name": name},
            headers=headers,
        )

    # ---------------------------------------------------------------
    # POST /entries/create
    # ---------------------------------------------------------------

    def test_create_entry_locked_pool_returns_423(self, client):
        """Entry creation on a locked pool returns HTTP 423."""
        token = _register_and_login(client, email="lock1@example.com")
        headers = _authed(client, token)
        past_lock = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        pool_id = self._create_pool(client, headers, lock_time=past_lock)

        response = self._create_entry(client, headers, pool_id)

        assert response.status_code == 423
        assert "locked" in response.json()["detail"].lower()

    def test_create_entry_unlocked_pool_returns_200(self, client):
        """Entry creation on an unlocked pool succeeds."""
        token = _register_and_login(client, email="lock2@example.com")
        headers = _authed(client, token)
        future_lock = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
        pool_id = self._create_pool(client, headers, lock_time=future_lock)

        response = self._create_entry(client, headers, pool_id)

        assert response.status_code == 200
        assert "id" in response.json()

    def test_create_entry_null_lock_time_returns_200(self, client):
        """Entry creation on a pool with no lock_time succeeds."""
        token = _register_and_login(client, email="lock3@example.com")
        headers = _authed(client, token)
        pool_id = self._create_pool(client, headers, lock_time=None)

        response = self._create_entry(client, headers, pool_id)

        assert response.status_code == 200
        assert "id" in response.json()

    def test_create_additional_entry_preserves_existing_week_one_pick(self, client):
        """Adding an entry must never update or delete another entry's pick."""
        token = _register_and_login(client, email="entry_pick_preserved@example.com")
        headers = _authed(client, token)
        pool_id = self._create_pool(client, headers)
        first_entry = self._create_entry(
            client, headers, pool_id, name="Entry 1"
        ).json()
        pick = client.post(
            "/picks/create",
            json={"entry_id": first_entry["id"], "week": 1, "team": "DET"},
            headers=headers,
        )
        assert pick.status_code == 200

        second_entry = self._create_entry(client, headers, pool_id, name="Entry 2")

        assert second_entry.status_code == 200
        picks = client.get(f"/picks/entry/{first_entry['id']}", headers=headers)
        assert picks.status_code == 200
        assert [(item["week"], item["team"]) for item in picks.json()] == [(1, "DET")]

    def test_automatic_entry_names_use_two_word_display_names_and_are_unique(
        self, client, mocker
    ):
        token = _register_and_login(client, email="entry-names@example.com")
        headers = _authed(client, token)
        pool_id = self._create_pool(client, headers)
        generated = iter(["adaptable-lion", "adaptable-lion", "capable-heron"])
        mocker.patch("entry_names.generate_slug", side_effect=lambda _: next(generated))

        first = client.post(
            "/entries/create",
            json={"pool_id": pool_id, "generate_name": True},
            headers=headers,
        )
        second = client.post(
            "/entries/create",
            json={"pool_id": pool_id, "generate_name": True},
            headers=headers,
        )

        assert first.status_code == 200
        assert second.status_code == 200
        assert first.json()["name"] == "Adaptable Lion"
        assert second.json()["name"] == "Capable Heron"

    def test_manual_entry_name_is_preserved(self, client):
        token = _register_and_login(client, email="manual-entry-name@example.com")
        headers = _authed(client, token)
        pool_id = self._create_pool(client, headers)

        response = self._create_entry(client, headers, pool_id, name="The Smith Family")

        assert response.status_code == 200
        assert response.json()["name"] == "The Smith Family"

    def test_automatic_name_uses_numbered_fallback_after_repeated_collisions(
        self, client, mocker
    ):
        token = _register_and_login(client, email="entry-name-fallback@example.com")
        headers = _authed(client, token)
        pool_id = self._create_pool(client, headers)
        mocker.patch("entry_names._candidate", return_value="Red Zone Raptors")

        first = client.post(
            "/entries/create",
            json={"pool_id": pool_id, "generate_name": True},
            headers=headers,
        )
        second = client.post(
            "/entries/create",
            json={"pool_id": pool_id, "generate_name": True},
            headers=headers,
        )

        assert first.json()["name"] == "Red Zone Raptors"
        assert second.json()["name"] == "Red Zone Raptors 2"

    def test_missing_manual_entry_name_is_rejected(self, client):
        token = _register_and_login(client, email="missing-entry-name@example.com")
        headers = _authed(client, token)
        pool_id = self._create_pool(client, headers)

        response = client.post(
            "/entries/create", json={"pool_id": pool_id}, headers=headers
        )

        assert response.status_code == 422
        assert response.json()["detail"] == "Entry name is required"

    # ---------------------------------------------------------------
    # DELETE /entries/{entry_id}
    # ---------------------------------------------------------------

    def test_delete_entry_locked_pool_returns_423(self, client, db_session):
        """Entry deletion on a locked pool returns HTTP 423."""
        token = _register_and_login(client, email="lock4@example.com")
        headers = _authed(client, token)

        # Create entry while pool is unlocked
        future_lock = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
        pool_id = self._create_pool(client, headers, lock_time=future_lock)
        create_response = self._create_entry(client, headers, pool_id)
        entry_id = create_response.json()["id"]

        # Push pool lock_time into the past directly via DB
        import models

        pool = db_session.query(models.Pool).filter(models.Pool.id == pool_id).first()
        pool.lock_time = datetime.now(timezone.utc) - timedelta(hours=1)
        db_session.commit()

        response = client.delete(f"/entries/{entry_id}", headers=headers)

        assert response.status_code == 423
        assert "locked" in response.json()["detail"].lower()

    def test_delete_entry_unlocked_pool_returns_200(self, client):
        """Entry deletion on an unlocked pool succeeds."""
        token = _register_and_login(client, email="lock5@example.com")
        headers = _authed(client, token)
        future_lock = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
        pool_id = self._create_pool(client, headers, lock_time=future_lock)
        create_response = self._create_entry(client, headers, pool_id)
        entry_id = create_response.json()["id"]

        response = client.delete(f"/entries/{entry_id}", headers=headers)

        assert response.status_code == 200

    def test_delete_entry_null_lock_time_returns_200(self, client):
        """Entry deletion on a pool with no lock_time succeeds."""
        token = _register_and_login(client, email="lock6@example.com")
        headers = _authed(client, token)
        pool_id = self._create_pool(client, headers, lock_time=None)
        create_response = self._create_entry(client, headers, pool_id)
        entry_id = create_response.json()["id"]

        response = client.delete(f"/entries/{entry_id}", headers=headers)

        assert response.status_code == 200

    def test_delete_entry_after_week_one_lock_returns_423(self, client, mocker):
        """The server rejects deletion once the computed Week 1 lock passes."""
        token = _register_and_login(client, email="week1-delete-lock@example.com")
        headers = _authed(client, token)
        pool_id = self._create_pool(client, headers, lock_time=None)
        entry_id = self._create_entry(client, headers, pool_id).json()["id"]
        past = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=1)
        mocker.patch("entries.current_season_games", return_value=[object()])
        mocker.patch("entries.pool_week_lock_time", return_value=past)

        response = client.delete(f"/entries/{entry_id}", headers=headers)

        assert response.status_code == 423
        assert "week 1" in response.json()["detail"].lower()

    def test_create_entry_no_token_returns_403(self, client):
        """Entry creation without auth token returns 403."""
        response = client.post(
            "/entries/create",
            json={"pool_id": "some-id", "name": "Entry"},
        )
        assert response.status_code in (401, 403)


# ---------------------------------------------------------------------------
# TestPrivatePoolNonMember
# ---------------------------------------------------------------------------


class TestPrivatePoolNonMember:
    """Tests for private pool membership enforcement on entry creation."""

    def _create_private_pool(self, client, headers, password="secret123"):
        """Create a private pool and return its id."""
        resp = client.post(
            "/pools/create",
            json={
                "name": "Private Pool",
                "is_private": True,
                "join_password": password,
                "rule_values": [],
            },
            headers=headers,
        )
        assert resp.status_code == 200, f"Pool creation failed: {resp.json()}"
        return resp.json()["id"]

    def test_non_member_cannot_create_entry_in_private_pool(self, client):
        """Non-member of a private pool receives 403 on entry creation."""
        owner_token = _register_and_login(client, email="priv_owner@example.com")
        nonmember_token = _register_and_login(
            client, email="priv_nonmember@example.com"
        )

        pool_id = self._create_private_pool(client, _authed(client, owner_token))

        response = client.post(
            "/entries/create",
            json={"pool_id": pool_id, "name": "Sneaky Entry"},
            headers=_authed(client, nonmember_token),
        )

        assert response.status_code == 403
        assert "private pool" in response.json()["detail"].lower()

    def test_member_can_create_entry_in_private_pool(self, client):
        """A user who joined the private pool can create an entry."""
        owner_token = _register_and_login(client, email="priv_owner2@example.com")
        member_token = _register_and_login(client, email="priv_member2@example.com")
        password = "joinme99"

        pool_id = self._create_private_pool(
            client, _authed(client, owner_token), password=password
        )

        # Join the private pool first
        joined = client.post(
            f"/pools/{pool_id}/join",
            json={"password": password},
            headers=_authed(client, member_token),
        )
        assert joined.status_code == 200, f"Join failed: {joined.json()}"

        response = client.post(
            "/entries/create",
            json={"pool_id": pool_id, "name": "Legit Entry"},
            headers=_authed(client, member_token),
        )

        assert response.status_code == 200
        assert "id" in response.json()

    def test_pool_owner_can_create_entry_in_private_pool(self, client):
        """Pool owner can create an entry even without a separate PoolMember row."""
        owner_token = _register_and_login(client, email="priv_owner3@example.com")
        pool_id = self._create_private_pool(client, _authed(client, owner_token))

        response = client.post(
            "/entries/create",
            json={"pool_id": pool_id, "name": "Owner Entry"},
            headers=_authed(client, owner_token),
        )

        assert response.status_code == 200
        assert "id" in response.json()


# ---------------------------------------------------------------------------
# TestUserLockedEntry
# ---------------------------------------------------------------------------


class TestUserLockedEntry:
    """Tests for pool-level user lock enforcement on entry create and delete."""

    def _setup_pool_and_lock(self, client, db_session):
        """
        Create a pool, register two users (owner + victim), lock victim in the pool,
        and return (owner_token, victim_token, pool_id).
        """
        import models as m
        from datetime import timezone

        owner_token = _register_and_login(client, email="lock_owner@example.com")
        victim_token = _register_and_login(client, email="lock_victim@example.com")

        # Create pool
        resp = client.post(
            "/pools/create",
            json={"name": "Lock Pool", "is_private": False, "rule_values": []},
            headers=_authed(client, owner_token),
        )
        assert resp.status_code == 200
        pool_id = resp.json()["id"]

        # Resolve victim's user id from the DB
        victim_user = (
            db_session.query(m.User)
            .filter(m.User.email == "lock_victim@example.com")
            .first()
        )
        assert victim_user is not None

        # Insert a PoolUserLock row directly so the check fires
        lock = m.PoolUserLock(
            pool_id=pool_id,
            user_id=victim_user.id,
            locked_at=datetime.now(timezone.utc).replace(tzinfo=None),
            reason="test lock",
        )
        db_session.add(lock)
        db_session.commit()

        return owner_token, victim_token, pool_id

    def test_user_locked_create_entry_returns_423(self, client, db_session):
        """Locked user cannot create an entry — expects 423."""
        _, victim_token, pool_id = self._setup_pool_and_lock(client, db_session)

        response = client.post(
            "/entries/create",
            json={"pool_id": pool_id, "name": "Locked Entry"},
            headers=_authed(client, victim_token),
        )

        assert response.status_code == 423
        assert "locked" in response.json()["detail"].lower()

    def test_user_locked_delete_entry_returns_423(self, client, db_session):
        """Locked user cannot delete an entry — expects 423."""
        import models as m

        owner_token, victim_token, pool_id = self._setup_pool_and_lock(
            client, db_session
        )

        # Owner creates an entry on behalf of the victim directly via DB
        victim_user = (
            db_session.query(m.User)
            .filter(m.User.email == "lock_victim@example.com")
            .first()
        )
        import uuid as _uuid

        entry = m.Entry(
            id=str(_uuid.uuid4()),
            name="Victim Entry",
            user_id=victim_user.id,
            pool_id=pool_id,
            alive=True,
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
            updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        db_session.add(entry)
        db_session.commit()

        response = client.delete(
            f"/entries/{entry.id}",
            headers=_authed(client, victim_token),
        )

        assert response.status_code == 423
        assert "locked" in response.json()["detail"].lower()

    def test_unlocked_user_can_create_entry(self, client):
        """Sanity check: a user with no lock row can create an entry normally."""
        token = _register_and_login(client, email="lock_clean@example.com")
        resp = client.post(
            "/pools/create",
            json={"name": "Clean Pool", "is_private": False, "rule_values": []},
            headers=_authed(client, token),
        )
        assert resp.status_code == 200
        pool_id = resp.json()["id"]

        response = client.post(
            "/entries/create",
            json={"pool_id": pool_id, "name": "Clean Entry"},
            headers=_authed(client, token),
        )

        assert response.status_code == 200
        assert "id" in response.json()


# ---------------------------------------------------------------------------
# TestDuplicateEntryName
# ---------------------------------------------------------------------------


class TestDuplicateEntryName:
    """Tests for duplicate entry name validation within a pool."""

    def _setup(self, client):
        token = _register_and_login(client, email="dup_name@example.com")
        headers = _authed(client, token)
        resp = client.post(
            "/pools/create",
            json={"name": "Dup Pool", "is_private": False, "rule_values": []},
            headers=headers,
        )
        assert resp.status_code == 200
        return token, resp.json()["id"]

    def test_duplicate_entry_name_returns_400(self, client):
        """Creating a second entry with the same name in the same pool returns 400."""
        token, pool_id = self._setup(client)
        headers = _authed(client, token)

        first = client.post(
            "/entries/create",
            json={"pool_id": pool_id, "name": "My Entry"},
            headers=headers,
        )
        assert first.status_code == 200

        second = client.post(
            "/entries/create",
            json={"pool_id": pool_id, "name": "My Entry"},
            headers=headers,
        )

        assert second.status_code == 400
        assert "already have an entry" in second.json()["detail"].lower()

    def test_same_name_different_pool_is_allowed(self, client):
        """The same entry name is permitted across different pools."""
        token, pool_id_1 = self._setup(client)
        headers = _authed(client, token)

        # Create a second pool
        resp2 = client.post(
            "/pools/create",
            json={"name": "Dup Pool 2", "is_private": False, "rule_values": []},
            headers=headers,
        )
        assert resp2.status_code == 200
        pool_id_2 = resp2.json()["id"]

        client.post(
            "/entries/create",
            json={"pool_id": pool_id_1, "name": "Shared Name"},
            headers=headers,
        )
        response = client.post(
            "/entries/create",
            json={"pool_id": pool_id_2, "name": "Shared Name"},
            headers=headers,
        )

        assert response.status_code == 200

    def test_different_name_same_pool_is_allowed(self, client):
        """A second entry with a different name in the same pool is permitted."""
        token, pool_id = self._setup(client)
        headers = _authed(client, token)

        client.post(
            "/entries/create",
            json={"pool_id": pool_id, "name": "Alpha"},
            headers=headers,
        )
        response = client.post(
            "/entries/create",
            json={"pool_id": pool_id, "name": "Beta"},
            headers=headers,
        )

        assert response.status_code == 200


# ---------------------------------------------------------------------------
# TestGetEntry
# ---------------------------------------------------------------------------


class TestGetEntry:
    """Tests for GET /entries/{entry_id} access control."""

    def _setup(self, client):
        """Create owner + a second user, one pool, and one entry owned by owner."""
        owner_token = _register_and_login(client, email="get_owner@example.com")
        other_token = _register_and_login(client, email="get_other@example.com")

        pool_resp = client.post(
            "/pools/create",
            json={"name": "Get Entry Pool", "is_private": False, "rule_values": []},
            headers=_authed(client, owner_token),
        )
        pool_id = pool_resp.json()["id"]

        entry_resp = client.post(
            "/entries/create",
            json={"pool_id": pool_id, "name": "Owned Entry"},
            headers=_authed(client, owner_token),
        )
        entry_id = entry_resp.json()["id"]

        return owner_token, other_token, entry_id

    def test_owner_can_get_own_entry(self, client):
        """Owner retrieves their own entry — expects 200 and correct id."""
        owner_token, _, entry_id = self._setup(client)

        response = client.get(
            f"/entries/{entry_id}",
            headers=_authed(client, owner_token),
        )

        assert response.status_code == 200
        assert response.json()["id"] == entry_id

    def test_other_user_cannot_see_entry(self, client):
        """A different user cannot access another user's entry — expects 404."""
        _, other_token, entry_id = self._setup(client)

        response = client.get(
            f"/entries/{entry_id}",
            headers=_authed(client, other_token),
        )

        assert response.status_code == 404

    def test_nonexistent_entry_returns_404(self, client):
        """GET on a random UUID that doesn't exist returns 404."""
        owner_token, _, _ = self._setup(client)

        response = client.get(
            "/entries/00000000-0000-0000-0000-000000000000",
            headers=_authed(client, owner_token),
        )

        assert response.status_code == 404

    def test_unauthenticated_get_entry_returns_403(self, client):
        """GET /entries/{id} without a token returns 401, 403, or 404 (entry invisible without auth)."""
        owner_token, _, entry_id = self._setup(client)

        response = client.get(f"/entries/{entry_id}")

        assert response.status_code in (401, 403, 404)
