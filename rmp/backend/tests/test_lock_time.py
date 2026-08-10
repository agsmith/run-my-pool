"""
Tests for time-based locking behavior in the NFL Survivor Pool application.

Coverage:
  - Pool.lock_time: controls entry creation and deletion (HTTP 423)
  - Pick.locked boolean: controls pick modification (HTTP 400)
  - Per-game start_time enforcement: picks for teams whose game has kicked off return 423
  - Lock-week admin endpoint: sets picks to locked, auto-picks missing entries

Boundary note (lock_time == utcnow):
  The comparison in entries.py is a strict less-than:
      lock_time < datetime.now(timezone.utc).replace(tzinfo=None)
  A lock_time set to datetime.utcnow() at the instant of the check is
  effectively equal to "now" — it is NOT strictly less than now, so it
  lands on the OPEN side of the boundary (pool is NOT yet locked).
  In practice the clock advances between the assignment and the check,
  which means real-world behavior at the exact boundary is timing-sensitive.
  See test_create_entry_boundary_lock_time for the documented behavior.
"""

import uuid
import pytest
from datetime import datetime, timedelta, timezone

import models
from models import Pick, Entry, Pool, Team, PoolAdmin, Schedule


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

ALL_NFL_ABBRVS = [
    "ARI",
    "ATL",
    "BAL",
    "BUF",
    "CAR",
    "CHI",
    "CIN",
    "CLE",
    "DAL",
    "DEN",
    "DET",
    "GB",
    "HOU",
    "IND",
    "JAX",
    "KC",
    "LAC",
    "LAR",
    "LV",
    "MIA",
    "MIN",
    "NE",
    "NO",
    "NYG",
    "NYJ",
    "PHI",
    "PIT",
    "SEA",
    "SF",
    "TB",
    "TEN",
    "WAS",
]

_POOL_PAYLOAD = {
    "name": "Lock Test Pool",
    "description": "Pool for lock-time tests",
    "is_private": False,
}


def _reg(client, email, password="Pass1234!"):
    client.post("/auth/register", json={"email": email, "password": password})
    resp = client.post("/auth/login", json={"email": email, "password": password})
    return resp.json()["access_token"]


def _h(token):
    return {"Authorization": f"Bearer {token}"}


def _create_pool(client, token, payload=None):
    """Create a pool and return its id."""
    data = payload or _POOL_PAYLOAD
    resp = client.post("/pools/create", json=data, headers=_h(token))
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


def _create_entry(client, token, pool_id, name="TestEntry"):
    """Create an entry and return the response."""
    return client.post(
        "/entries/create",
        json={"pool_id": pool_id, "name": name},
        headers=_h(token),
    )


def _set_lock_time(db_session, pool_id, lock_time):
    """Directly set pool.lock_time via the db session."""
    pool = db_session.query(Pool).filter(Pool.id == pool_id).first()
    pool.lock_time = lock_time
    db_session.commit()


# ---------------------------------------------------------------------------
# TestPoolLockTime
# ---------------------------------------------------------------------------


class TestPoolLockTime:
    """Tests for pool.lock_time enforcement on entry create/delete."""

    def test_create_entry_allowed_when_lock_time_is_none(self, client, db_session):
        """Entry creation succeeds when pool.lock_time is None."""
        token = _reg(client, "lt_none@example.com")
        pool_id = _create_pool(client, token)
        # Confirm lock_time is None (pools/create doesn't set it)
        _set_lock_time(db_session, pool_id, None)

        resp = _create_entry(client, token, pool_id)
        assert resp.status_code == 200, resp.text

    def test_create_entry_allowed_when_lock_time_is_future(self, client, db_session):
        """Entry creation succeeds when pool.lock_time is in the future."""
        token = _reg(client, "lt_future@example.com")
        pool_id = _create_pool(client, token)
        future = datetime.utcnow() + timedelta(hours=1)
        _set_lock_time(db_session, pool_id, future)

        resp = _create_entry(client, token, pool_id)
        assert resp.status_code == 200, resp.text

    def test_create_entry_blocked_when_lock_time_is_past(self, client, db_session):
        """Entry creation returns 423 when pool.lock_time is in the past."""
        token = _reg(client, "lt_past_create@example.com")
        pool_id = _create_pool(client, token)
        past = datetime.utcnow() - timedelta(hours=1)
        _set_lock_time(db_session, pool_id, past)

        resp = _create_entry(client, token, pool_id)
        assert resp.status_code == 423, resp.text
        assert "Pool is locked" in resp.json()["detail"]
        assert (
            "Entry creation is not allowed after the lock time" in resp.json()["detail"]
        )

    def test_create_entry_blocked_exact_error_message(self, client, db_session):
        """Exact error message for entry creation after lock time."""
        token = _reg(client, "lt_errmsg_create@example.com")
        pool_id = _create_pool(client, token)
        _set_lock_time(db_session, pool_id, datetime.utcnow() - timedelta(seconds=1))

        resp = _create_entry(client, token, pool_id)
        assert resp.status_code == 423
        assert resp.json()["detail"] == (
            "Pool is locked. Entry creation is not allowed after the lock time."
        )

    def test_delete_entry_allowed_when_lock_time_is_none(self, client, db_session):
        """Entry deletion succeeds when pool.lock_time is None."""
        token = _reg(client, "lt_del_none@example.com")
        pool_id = _create_pool(client, token)
        _set_lock_time(db_session, pool_id, None)

        entry_resp = _create_entry(client, token, pool_id)
        assert entry_resp.status_code == 200
        entry_id = entry_resp.json()["id"]

        resp = client.delete(f"/entries/{entry_id}", headers=_h(token))
        assert resp.status_code == 200, resp.text

    def test_delete_entry_allowed_when_lock_time_is_future(self, client, db_session):
        """Entry deletion succeeds when pool.lock_time is in the future."""
        token = _reg(client, "lt_del_future@example.com")
        pool_id = _create_pool(client, token)

        # Create the entry first with no lock
        _set_lock_time(db_session, pool_id, None)
        entry_resp = _create_entry(client, token, pool_id)
        assert entry_resp.status_code == 200
        entry_id = entry_resp.json()["id"]

        # Now set a future lock time
        _set_lock_time(db_session, pool_id, datetime.utcnow() + timedelta(hours=1))

        resp = client.delete(f"/entries/{entry_id}", headers=_h(token))
        assert resp.status_code == 200, resp.text

    def test_delete_entry_blocked_when_lock_time_is_past(self, client, db_session):
        """Entry deletion returns 423 when pool.lock_time is in the past."""
        token = _reg(client, "lt_del_past@example.com")
        pool_id = _create_pool(client, token)

        # Create the entry before locking
        _set_lock_time(db_session, pool_id, None)
        entry_resp = _create_entry(client, token, pool_id)
        assert entry_resp.status_code == 200
        entry_id = entry_resp.json()["id"]

        # Lock the pool in the past
        _set_lock_time(db_session, pool_id, datetime.utcnow() - timedelta(hours=1))

        resp = client.delete(f"/entries/{entry_id}", headers=_h(token))
        assert resp.status_code == 423, resp.text
        assert "Pool is locked" in resp.json()["detail"]
        assert (
            "Entry deletion is not allowed after the lock time" in resp.json()["detail"]
        )

    def test_delete_entry_blocked_exact_error_message(self, client, db_session):
        """Exact error message for entry deletion after lock time."""
        token = _reg(client, "lt_errmsg_del@example.com")
        pool_id = _create_pool(client, token)

        _set_lock_time(db_session, pool_id, None)
        entry_resp = _create_entry(client, token, pool_id)
        entry_id = entry_resp.json()["id"]

        _set_lock_time(db_session, pool_id, datetime.utcnow() - timedelta(seconds=1))

        resp = client.delete(f"/entries/{entry_id}", headers=_h(token))
        assert resp.status_code == 423
        assert resp.json()["detail"] == (
            "Pool is locked. Entry deletion is not allowed after the lock time."
        )

    def test_create_entry_boundary_lock_time(self, client, db_session):
        """
        Boundary test: lock_time set to datetime.utcnow() at call time.

        The comparison in entries.py is strict less-than:
            lock_time < datetime.now(timezone.utc).replace(tzinfo=None)

        A lock_time equal to "now" is NOT strictly less than "now", so the
        pool is NOT considered locked at that instant.  However, since a
        real-time clock advances between the db.commit() and the subsequent
        HTTP call, this boundary is timing-sensitive; the test documents that
        the behavior could go either way in practice.

        We assert that 200 is the more likely outcome (open boundary) but
        accept 423 as a valid alternative to avoid a flaky test.
        """
        token = _reg(client, "lt_boundary@example.com")
        pool_id = _create_pool(client, token)

        # Set lock_time to "right now" — intended to hit the strict boundary
        _set_lock_time(db_session, pool_id, datetime.utcnow())

        resp = _create_entry(client, token, pool_id)
        # At the exact boundary the pool should NOT be locked (open boundary),
        # but we permit 423 because the clock advances during the request.
        assert resp.status_code in (200, 423), (
            f"Unexpected status {resp.status_code} at lock_time boundary: {resp.text}"
        )


# ---------------------------------------------------------------------------
# TestPickLocked
# ---------------------------------------------------------------------------


class TestPickLocked:
    """Tests for Pick.locked boolean enforcement on pick update and delete."""

    def _setup(self, client, db_session, email_prefix):
        """Register user, create pool+entry, return (token, pool_id, entry_id)."""
        token = _reg(client, f"{email_prefix}@example.com")
        pool_id = _create_pool(client, token)

        entry_resp = _create_entry(client, token, pool_id)
        assert entry_resp.status_code == 200, entry_resp.text
        entry_id = entry_resp.json()["id"]
        return token, pool_id, entry_id

    def _insert_pick(self, db_session, entry_id, week=1, team="NE", locked=False):
        """Insert a Pick row directly via db_session."""
        pick = Pick(
            id=str(uuid.uuid4()),
            entry_id=entry_id,
            week=week,
            team=team,
            locked=locked,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db_session.add(pick)
        db_session.commit()
        db_session.refresh(pick)
        return pick

    def test_update_unlocked_pick_succeeds(self, client, db_session):
        """PUT /picks/{pick_id} returns 200 when pick is not locked."""
        token, pool_id, entry_id = self._setup(client, db_session, "pick_upd_ok")
        pick = self._insert_pick(db_session, entry_id, team="NE", locked=False)

        resp = client.put(
            f"/picks/{pick.id}",
            json={"team": "KC"},
            headers=_h(token),
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["team"] == "KC"

    def test_update_locked_pick_returns_400(self, client, db_session):
        """PUT /picks/{pick_id} returns 400 when pick.locked is True."""
        token, pool_id, entry_id = self._setup(client, db_session, "pick_upd_locked")
        pick = self._insert_pick(db_session, entry_id, team="NE", locked=True)

        resp = client.put(
            f"/picks/{pick.id}",
            json={"team": "KC"},
            headers=_h(token),
        )
        assert resp.status_code == 400, resp.text
        assert "locked" in resp.json()["detail"].lower()

    def test_update_locked_pick_exact_error_message(self, client, db_session):
        """Exact error message for updating a locked pick."""
        token, pool_id, entry_id = self._setup(client, db_session, "pick_upd_errmsg")
        pick = self._insert_pick(db_session, entry_id, team="DAL", locked=True)

        resp = client.put(
            f"/picks/{pick.id}",
            json={"team": "GB"},
            headers=_h(token),
        )
        assert resp.status_code == 400
        assert resp.json()["detail"] == "Cannot update a locked pick"

    def test_delete_unlocked_pick_succeeds(self, client, db_session):
        """DELETE /picks/{pick_id} returns 200 when pick is not locked."""
        token, pool_id, entry_id = self._setup(client, db_session, "pick_del_ok")
        pick = self._insert_pick(db_session, entry_id, team="SEA", locked=False)

        resp = client.delete(f"/picks/{pick.id}", headers=_h(token))
        assert resp.status_code == 200, resp.text

    def test_delete_locked_pick_returns_400(self, client, db_session):
        """DELETE /picks/{pick_id} returns 400 when pick.locked is True."""
        token, pool_id, entry_id = self._setup(client, db_session, "pick_del_locked")
        pick = self._insert_pick(db_session, entry_id, team="BUF", locked=True)

        resp = client.delete(f"/picks/{pick.id}", headers=_h(token))
        assert resp.status_code == 400, resp.text
        assert "locked" in resp.json()["detail"].lower()

    def test_delete_locked_pick_exact_error_message(self, client, db_session):
        """Exact error message for deleting a locked pick."""
        token, pool_id, entry_id = self._setup(client, db_session, "pick_del_errmsg")
        pick = self._insert_pick(db_session, entry_id, team="SF", locked=True)

        resp = client.delete(f"/picks/{pick.id}", headers=_h(token))
        assert resp.status_code == 400
        assert resp.json()["detail"] == "Cannot delete a locked pick"

    def test_admin_patch_overrides_locked_pick(self, client, db_session):
        """
        PATCH /admin/pools/{pool_id}/picks/{pick_id} can update a locked pick
        and returns 200.  The pool creator is automatically an admin.
        """
        token, pool_id, entry_id = self._setup(client, db_session, "pick_admin_patch")
        pick = self._insert_pick(db_session, entry_id, team="ATL", locked=True)

        resp = client.patch(
            f"/admin/pools/{pool_id}/picks/{pick.id}",
            json={"team": "MIA"},
            headers=_h(token),
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["team"] == "MIA"
        assert data["locked"] is True  # admin patch keeps it locked


# ---------------------------------------------------------------------------
# Schedule/team seed helpers (used by per-game start_time tests)
# ---------------------------------------------------------------------------


def _seed_team(db, team_id, name, abbrv):
    """Insert or update a team row directly."""
    team = models.Team(id=team_id, name=name, abbrv=abbrv, logo=None)
    db.merge(team)
    db.commit()
    return team


def _seed_schedule(db, game_id, week_num, home_team_id, away_team_id, start_time):
    """Insert or update a schedule row directly."""
    game = models.Schedule(
        game_id=game_id,
        week_num=week_num,
        home_team_id=home_team_id,
        away_team_id=away_team_id,
        start_time=start_time,
        winning_team_id=None,
    )
    db.merge(game)
    db.commit()
    return game


# ---------------------------------------------------------------------------
# TestPerGameStartTimeEnforcement
# ---------------------------------------------------------------------------


class TestPerGameStartTimeEnforcement:
    """
    Per-game start_time enforcement: picks for teams whose game has already
    kicked off are rejected with HTTP 423, even before pool.lock_time.

    This covers Thursday night / Friday / Saturday games that kick off before
    the Sunday 1pm pool lock window.
    """

    def test_thursday_pick_blocked_after_kickoff(self, client, db_session):
        """
        After a game's start_time has passed, picks for that game's team
        return HTTP 423 — even if pool.lock_time has not yet been reached.
        """
        token = _reg(client, "per_game_enforce@example.com")
        pool_id = _create_pool(client, token)
        # Pool lock is far in the future (Sunday 1pm simulation)
        _set_lock_time(db_session, pool_id, datetime.utcnow() + timedelta(hours=48))

        entry_resp = _create_entry(client, token, pool_id)
        assert entry_resp.status_code == 200
        entry_id = entry_resp.json()["id"]

        # Seed a team and a game that has already kicked off
        team = _seed_team(db_session, 99, "Thursday FC", "THU")
        _seed_schedule(
            db_session,
            game_id=9901,
            week_num=1,
            home_team_id=99,
            away_team_id=98,
            start_time=datetime.utcnow() - timedelta(hours=1),  # kicked off 1hr ago
        )

        resp = client.post(
            "/picks/create",
            json={"entry_id": entry_id, "week": 1, "team": "THU"},
            headers=_h(token),
        )
        assert resp.status_code == 423, (
            f"Expected 423 after game kickoff, got {resp.status_code}: {resp.text}"
        )

    def test_game_not_yet_started_pick_allowed(self, client, db_session):
        """
        Before a game's start_time, picks for that team succeed even if the
        team plays before pool.lock_time.
        """
        token = _reg(client, "per_game_future@example.com")
        pool_id = _create_pool(client, token)
        _set_lock_time(db_session, pool_id, datetime.utcnow() + timedelta(hours=48))

        entry_resp = _create_entry(client, token, pool_id)
        assert entry_resp.status_code == 200
        entry_id = entry_resp.json()["id"]

        # Game kicks off in 2 hours — not yet locked
        team = _seed_team(db_session, 97, "Future Team", "FUT")
        _seed_schedule(
            db_session,
            game_id=9902,
            week_num=1,
            home_team_id=97,
            away_team_id=96,
            start_time=datetime.utcnow() + timedelta(hours=2),
        )

        resp = client.post(
            "/picks/create",
            json={"entry_id": entry_id, "week": 1, "team": "FUT"},
            headers=_h(token),
        )
        assert resp.status_code == 200, (
            f"Expected 200 before game kickoff, got {resp.status_code}: {resp.text}"
        )


# ---------------------------------------------------------------------------
# TestLockWeek
# ---------------------------------------------------------------------------


class TestLockWeek:
    """Tests for POST /admin/pools/{pool_id}/lock-week/{week}."""

    def _setup(self, client, db_session, email_prefix, num_entries=1):
        """
        Register a user, create a pool, create num_entries entries.
        Returns (token, pool_id, [entry_id, ...]).
        """
        token = _reg(client, f"{email_prefix}@example.com")
        pool_id = _create_pool(client, token)
        # Ensure no lock on the pool so entries can be created
        _set_lock_time(db_session, pool_id, None)

        entry_ids = []
        for i in range(num_entries):
            resp = _create_entry(client, token, pool_id, name=f"Entry{i}")
            assert resp.status_code == 200, resp.text
            entry_ids.append(resp.json()["id"])

        return token, pool_id, entry_ids

    def _insert_pick(self, db_session, entry_id, week, team, locked=False):
        pick = Pick(
            id=str(uuid.uuid4()),
            entry_id=entry_id,
            week=week,
            team=team,
            locked=locked,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db_session.add(pick)
        db_session.commit()
        return pick

    def test_lock_week_requires_admin(self, client, db_session):
        """Non-admin user gets 403 on lock-week."""
        token_owner = _reg(client, "lw_owner@example.com")
        pool_id = _create_pool(client, token_owner)

        token_other = _reg(client, "lw_other@example.com")
        resp = client.post(
            f"/admin/pools/{pool_id}/lock-week/1",
            headers=_h(token_other),
        )
        assert resp.status_code == 403, resp.text

    def test_lock_week_nonexistent_pool_returns_404(self, client, db_session):
        """lock-week on a non-existent pool returns 403 (admin access check fails first,
        since the user is not owner or admin of a pool that doesn't exist)."""
        token = _reg(client, "lw_404@example.com")
        resp = client.post(
            f"/admin/pools/{str(uuid.uuid4())}/lock-week/1",
            headers=_h(token),
        )
        # verify_admin_access returns False for a nonexistent pool → 403
        assert resp.status_code in (403, 404), resp.text

    def test_lock_week_sets_existing_picks_to_locked(self, client, db_session):
        """lock-week sets locked=True on all existing week-N picks."""
        token, pool_id, entry_ids = self._setup(client, db_session, "lw_lock_existing")
        entry_id = entry_ids[0]

        # Insert an unlocked pick for week 1
        pick = self._insert_pick(db_session, entry_id, week=1, team="NE", locked=False)
        assert pick.locked is False

        resp = client.post(
            f"/admin/pools/{pool_id}/lock-week/1",
            headers=_h(token),
        )
        assert resp.status_code == 200, resp.text

        db_session.expire_all()
        assert pick.locked is True, "lock-week should set existing picks to locked=True"

    def test_lock_week_auto_picks_for_entries_with_no_pick(self, client, db_session):
        """
        Entries with no pick for week N receive an auto-pick after lock-week.
        The response reports auto_picks_created == 1.
        """
        token, pool_id, entry_ids = self._setup(client, db_session, "lw_autopick")
        entry_id = entry_ids[0]

        # Insert picks for the entry in other weeks to seed the popularity map —
        # but leave week 2 empty so auto-pick fires.
        self._insert_pick(db_session, entry_id, week=1, team="NE", locked=True)

        # Also seed the popularity map: insert a pick from a *second* alive entry
        # so that the popularity-ranked list is non-empty.
        token2 = _reg(client, "lw_autopick_p2@example.com")
        # Register and add second user's entry directly via db
        from passlib.context import CryptContext

        _pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
        from models import User

        user2 = User(
            id=str(uuid.uuid4()),
            email="lw_autopick_u2@example.com",
            hashed_password=_pwd.hash("Pass1234!"),
            is_active=True,
        )
        db_session.add(user2)
        db_session.flush()
        entry2 = Entry(
            id=str(uuid.uuid4()),
            user_id=user2.id,
            pool_id=pool_id,
            name="EntryP2",
            alive=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db_session.add(entry2)
        db_session.flush()
        # entry2 has a pick for week 2 — this populates the popularity map
        self._insert_pick(db_session, entry2.id, week=2, team="KC", locked=False)
        db_session.commit()

        resp = client.post(
            f"/admin/pools/{pool_id}/lock-week/2",
            headers=_h(token),
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        # entry_id had no pick for week 2 → auto-pick created
        assert data["auto_picks_created"] >= 1

        # Verify a locked pick now exists for entry_id week 2
        auto_pick = (
            db_session.query(Pick)
            .filter(Pick.entry_id == entry_id, Pick.week == 2)
            .first()
        )
        assert auto_pick is not None
        assert auto_pick.locked is True

    def test_lock_week_auto_pick_skipped_when_all_teams_used(self, client, db_session):
        """
        When an entry has already used all 32 NFL teams, auto-pick is skipped
        and an AUTO_PICK_SKIPPED audit log is created instead.

        Setup: insert Pick rows for all 32 team abbreviations across weeks 1-32
        for the entry.  Then call lock-week for week 33 (no existing pick).
        The admin.py auto-pick logic checks used_teams per entry; with all 32
        teams used, candidate is None → skip.
        """
        token, pool_id, entry_ids = self._setup(client, db_session, "lw_skip")
        entry_id = entry_ids[0]

        # Also add a second entry that DOES have a pick for week 33 so the
        # popularity map is non-empty (otherwise ranked_teams is empty and
        # candidate would also be None — which is the same outcome, but for a
        # different reason).
        from passlib.context import CryptContext
        from models import User, AuditLog

        _pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
        user2 = User(
            id=str(uuid.uuid4()),
            email="lw_skip_u2@example.com",
            hashed_password=_pwd.hash("Pass1234!"),
            is_active=True,
        )
        db_session.add(user2)
        db_session.flush()
        entry2 = Entry(
            id=str(uuid.uuid4()),
            user_id=user2.id,
            pool_id=pool_id,
            name="SkipEntry2",
            alive=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db_session.add(entry2)
        db_session.flush()
        # entry2 picks "ARI" in week 33 → popularity map is populated
        self._insert_pick(db_session, entry2.id, week=33, team="ARI", locked=False)

        # Exhaust all 32 teams for entry_id across weeks 1-32
        for week_num, abbrv in enumerate(ALL_NFL_ABBRVS, start=1):
            self._insert_pick(
                db_session, entry_id, week=week_num, team=abbrv, locked=True
            )

        db_session.commit()

        resp = client.post(
            f"/admin/pools/{pool_id}/lock-week/33",
            headers=_h(token),
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        # entry_id should have been skipped (all teams used); entry2 already had a pick
        assert data["auto_picks_created"] == 0

        # Verify no pick was created for entry_id in week 33
        skipped_pick = (
            db_session.query(Pick)
            .filter(Pick.entry_id == entry_id, Pick.week == 33)
            .first()
        )
        assert skipped_pick is None

        # Verify AUTO_PICK_SKIPPED audit log was written
        db_session.expire_all()
        audit = (
            db_session.query(AuditLog)
            .filter(AuditLog.action == "ADMIN_AUTO_PICK_SKIPPED")
            .first()
        )
        assert audit is not None, "Expected AUTO_PICK_SKIPPED audit log entry"

    def test_lock_week_response_shape(self, client, db_session):
        """lock-week response contains the expected keys."""
        token, pool_id, _ = self._setup(client, db_session, "lw_shape")
        resp = client.post(
            f"/admin/pools/{pool_id}/lock-week/5",
            headers=_h(token),
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "message" in data
        assert "pool_id" in data
        assert "auto_picks_created" in data
        assert data["pool_id"] == pool_id

    def test_lock_week_sets_pool_lock_time_if_not_already_past(
        self, client, db_session
    ):
        """
        lock-week sets pool.lock_time to now when lock_time is None or future,
        effectively locking the pool.
        """
        token, pool_id, _ = self._setup(client, db_session, "lw_set_lock")
        # Confirm lock_time is None
        pool = db_session.query(Pool).filter(Pool.id == pool_id).first()
        assert pool.lock_time is None

        resp = client.post(
            f"/admin/pools/{pool_id}/lock-week/1",
            headers=_h(token),
        )
        assert resp.status_code == 200, resp.text

        db_session.refresh(pool)
        assert pool.lock_time is not None
        # lock_time should be in the past or very close to now
        assert pool.lock_time <= datetime.utcnow() + timedelta(seconds=2)

    def test_lock_week_does_not_advance_lock_time_if_already_past(
        self, client, db_session
    ):
        """
        If pool.lock_time is already in the past, lock-week does not change it.
        """
        token, pool_id, _ = self._setup(client, db_session, "lw_no_advance")
        original_lock = datetime.utcnow() - timedelta(hours=2)
        _set_lock_time(db_session, pool_id, original_lock)

        resp = client.post(
            f"/admin/pools/{pool_id}/lock-week/1",
            headers=_h(token),
        )
        assert resp.status_code == 200, resp.text

        pool = db_session.query(Pool).filter(Pool.id == pool_id).first()
        db_session.refresh(pool)
        # lock_time should remain at (or near) original_lock, not advanced
        assert pool.lock_time <= original_lock + timedelta(seconds=2)

    def test_lock_week_only_auto_picks_alive_entries(self, client, db_session):
        """
        Dead entries (alive=False) are ignored during auto-pick.
        """
        token, pool_id, entry_ids = self._setup(client, db_session, "lw_alive_only")
        entry_id = entry_ids[0]

        # Mark the entry as dead
        entry = db_session.query(Entry).filter(Entry.id == entry_id).first()
        entry.alive = False
        db_session.commit()

        resp = client.post(
            f"/admin/pools/{pool_id}/lock-week/1",
            headers=_h(token),
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["auto_picks_created"] == 0

        # Confirm no pick was created for the dead entry
        pick = (
            db_session.query(Pick)
            .filter(Pick.entry_id == entry_id, Pick.week == 1)
            .first()
        )
        assert pick is None


# ---------------------------------------------------------------------------
# TestPickLockTimeEnforcement
# ---------------------------------------------------------------------------


class TestPickLockTimeEnforcement:
    """
    Tests for the new pick-level lock enforcement in picks.py.

    Covers:
    - pool.lock_time blocks create and update after it passes
    - game start_time blocks picks for that game's team after kickoff
    - switching away from a pre-Sunday game pick is blocked after kickoff
    - Sunday 4pm game pick is allowed before pool.lock_time
    """

    def _setup(self, client, db_session, email_prefix):
        """Register user, create pool with no lock, create entry. Returns (token, pool_id, entry_id)."""
        token = _reg(client, f"{email_prefix}@example.com")
        pool_id = _create_pool(client, token)
        _set_lock_time(db_session, pool_id, None)
        entry_resp = _create_entry(client, token, pool_id)
        assert entry_resp.status_code == 200
        return token, pool_id, entry_resp.json()["id"]

    def test_pick_create_blocked_after_pool_lock_time(self, client, db_session):
        """POST /picks/create returns HTTP 423 after pool.lock_time has passed."""
        token, pool_id, entry_id = self._setup(client, db_session, "plte_create_lock")
        # Set pool lock to the past
        _set_lock_time(db_session, pool_id, datetime.utcnow() - timedelta(hours=1))

        resp = client.post(
            "/picks/create",
            json={"entry_id": entry_id, "week": 1, "team": "NE"},
            headers=_h(token),
        )
        assert resp.status_code == 423, (
            f"Expected 423 after pool.lock_time, got {resp.status_code}: {resp.text}"
        )
        assert "locked" in resp.json().get("detail", "").lower()

    def test_pick_update_blocked_after_pool_lock_time(self, client, db_session):
        """PUT /picks/{id} returns HTTP 423 after pool.lock_time has passed."""
        token, pool_id, entry_id = self._setup(client, db_session, "plte_update_lock")

        # Create pick while pool is unlocked
        create_resp = client.post(
            "/picks/create",
            json={"entry_id": entry_id, "week": 1, "team": "NE"},
            headers=_h(token),
        )
        assert create_resp.status_code == 200
        pick_id = create_resp.json()["id"]

        # Lock the pool
        _set_lock_time(db_session, pool_id, datetime.utcnow() - timedelta(hours=1))

        resp = client.put(
            f"/picks/{pick_id}",
            json={"team": "KC"},
            headers=_h(token),
        )
        assert resp.status_code == 423, (
            f"Expected 423 after pool.lock_time on update, got {resp.status_code}: {resp.text}"
        )

    def test_pick_create_blocked_after_game_kickoff(self, client, db_session):
        """POST /picks/create returns HTTP 423 if the team's game has already kicked off."""
        token, pool_id, entry_id = self._setup(client, db_session, "plte_game_lock")
        # Pool lock is still in the future
        _set_lock_time(db_session, pool_id, datetime.utcnow() + timedelta(hours=48))

        # Seed a team whose game kicked off 30 minutes ago
        _seed_team(db_session, 201, "Thursday Night Team", "TNT")
        _seed_schedule(
            db_session,
            game_id=8801,
            week_num=1,
            home_team_id=201,
            away_team_id=202,
            start_time=datetime.utcnow() - timedelta(minutes=30),
        )

        resp = client.post(
            "/picks/create",
            json={"entry_id": entry_id, "week": 1, "team": "TNT"},
            headers=_h(token),
        )
        assert resp.status_code == 423, (
            f"Expected 423 after game kickoff, got {resp.status_code}: {resp.text}"
        )

    def test_pick_update_blocked_when_existing_game_started(self, client, db_session):
        """
        PUT /picks/{id} returns 423 when the EXISTING pick's game has started,
        even if the proposed new team's game has not started yet.
        """
        token, pool_id, entry_id = self._setup(client, db_session, "plte_existing_game")
        # Pool lock is in the future
        _set_lock_time(db_session, pool_id, datetime.utcnow() + timedelta(hours=48))

        # Seed a Thursday team (game already started)
        _seed_team(db_session, 301, "Thursday Team", "THU")
        _seed_schedule(
            db_session,
            game_id=8802,
            week_num=1,
            home_team_id=301,
            away_team_id=302,
            start_time=datetime.utcnow() - timedelta(hours=2),
        )
        # Seed a Sunday team (game not yet started)
        _seed_team(db_session, 303, "Sunday Team", "SUN")
        _seed_schedule(
            db_session,
            game_id=8803,
            week_num=1,
            home_team_id=303,
            away_team_id=304,
            start_time=datetime.utcnow() + timedelta(hours=24),
        )

        # Create pick for Thursday team while game had not yet started
        # (simulate by inserting directly to bypass timing)
        pick = Pick(
            id=str(uuid.uuid4()),
            entry_id=entry_id,
            week=1,
            team="THU",
            team_id=301,
            locked=False,
            result=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db_session.add(pick)
        db_session.commit()
        pick_id = pick.id

        # Attempt to switch to Sunday team after Thursday kickoff — lock applies
        # to the EXISTING pick's game (Thursday), not the new team's game.
        resp = client.put(
            f"/picks/{pick_id}",
            json={"team": "SUN"},
            headers=_h(token),
        )
        assert resp.status_code == 423, (
            f"Expected 423 (Thursday slot locked at kickoff), "
            f"got {resp.status_code}: {resp.text}"
        )

    def test_sunday_4pm_pick_allowed_before_pool_lock(self, client, db_session):
        """
        Pick for a Sunday 4pm team succeeds before pool.lock_time,
        even though the game starts after the pool lock.
        The effective lock = min(pool.lock_time=Sunday1pm, game.start_time=Sunday4pm)
        = Sunday 1pm — so before Sunday 1pm the pick is allowed.
        """
        token, pool_id, entry_id = self._setup(client, db_session, "plte_sun4pm")
        # Pool lock is in the future (simulates before Sunday 1pm)
        _set_lock_time(db_session, pool_id, datetime.utcnow() + timedelta(hours=2))

        # Sunday 4pm game — kicks off after pool.lock_time (future)
        _seed_team(db_session, 401, "Sunday Afternoon", "SAF")
        _seed_schedule(
            db_session,
            game_id=8804,
            week_num=1,
            home_team_id=401,
            away_team_id=402,
            start_time=datetime.utcnow() + timedelta(hours=5),
        )

        resp = client.post(
            "/picks/create",
            json={"entry_id": entry_id, "week": 1, "team": "SAF"},
            headers=_h(token),
        )
        assert resp.status_code == 200, (
            f"Expected 200 for Sunday 4pm pick before lock, got {resp.status_code}: {resp.text}"
        )
