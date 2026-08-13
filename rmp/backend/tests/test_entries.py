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
        first_entry = self._create_entry(client, headers, pool_id, name="Entry 1").json()
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

    def test_automatic_entry_names_are_football_themed_and_unique(
        self, client, mocker
    ):
        token = _register_and_login(client, email="entry-names@example.com")
        headers = _authed(client, token)
        pool_id = self._create_pool(client, headers)
        generated = iter([
            ["Red Zone", "Raptors"],
            ["Red Zone", "Raptors"],
            ["Blitzing", "Badgers"],
        ])
        mocker.patch("entry_names._GENERATOR.generate", side_effect=lambda: next(generated))

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
        assert first.json()["name"] == "Red Zone Raptors"
        assert second.json()["name"] == "Blitzing Badgers"

    def test_manual_entry_name_is_preserved(self, client):
        token = _register_and_login(client, email="manual-entry-name@example.com")
        headers = _authed(client, token)
        pool_id = self._create_pool(client, headers)

        response = self._create_entry(
            client, headers, pool_id, name="The Smith Family"
        )

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
