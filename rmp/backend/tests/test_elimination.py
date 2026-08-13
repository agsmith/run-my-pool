"""
Tests for elimination logic, auto-pick, and admin operations.

Covers:
  - simulate_game_result: win/loss pick results, entry alive/dead state
  - Dead entry pick gap (documented below)
  - Auto-pick: assignment, team uniqueness, skip-when-exhausted
  - Admin: transfer entry, delete entry, non-admin 403 guards
"""

import uuid
from datetime import datetime, timezone

import models
import pytest

from helpers import simulate_game_result, _eliminate_losing_entries, get_alive_entries

# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------


def _reg(client, email, password="Pass1234!"):
    """Register and log in; return JWT access token."""
    client.post("/auth/register", json={"email": email, "password": password})
    resp = client.post("/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, f"Login failed for {email}: {resp.json()}"
    return resp.json()["access_token"]


def _h(token):
    """Return Authorization header dict."""
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# DB seeding helpers
# ---------------------------------------------------------------------------


def _seed_team(db, team_id, abbrv, name):
    team = models.Team(id=team_id, name=name, abbrv=abbrv, logo=None)
    db.merge(team)
    db.flush()
    return team


def _seed_game(db, game_id, week_num, home_team_id, away_team_id):
    game = models.Schedule(
        game_id=game_id,
        week_num=week_num,
        home_team_id=home_team_id,
        away_team_id=away_team_id,
        start_time=datetime(2025, 9, 7, 17, 0, 0),
        winning_team_id=None,
    )
    db.merge(game)
    db.commit()
    return game


def _create_pool(client, headers):
    resp = client.post(
        "/pools/create",
        json={"name": "Elim Test Pool", "is_private": False, "rule_values": []},
        headers=headers,
    )
    assert resp.status_code == 200, f"Pool creation failed: {resp.json()}"
    return resp.json()["id"]


def _create_entry(client, headers, pool_id, name="Test Entry"):
    resp = client.post(
        "/entries/create",
        json={"pool_id": pool_id, "name": name},
        headers=headers,
    )
    assert resp.status_code == 200, f"Entry creation failed: {resp.json()}"
    return resp.json()["id"]


def _create_pick_direct(db, entry_id, week, team, team_id=None, locked=False):
    """Insert a Pick row directly into the DB (bypassing the API)."""
    pick = models.Pick(
        id=str(uuid.uuid4()),
        entry_id=entry_id,
        week=week,
        team=team,
        team_id=team_id,
        locked=locked,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(pick)
    db.commit()
    db.refresh(pick)
    return pick


# ---------------------------------------------------------------------------
# Shared fixture: two teams + one game seeded into the DB
# ---------------------------------------------------------------------------

NE_ID = 17
KC_ID = 12
GAME_ID = 9001
WEEK = 1


def _seed_ne_kc(db):
    """Seed NE (home) vs KC (away) for week 1, game 9001."""
    _seed_team(db, NE_ID, "NE", "New England Patriots")
    _seed_team(db, KC_ID, "KC", "Kansas City Chiefs")
    _seed_game(db, GAME_ID, WEEK, home_team_id=NE_ID, away_team_id=KC_ID)


# ---------------------------------------------------------------------------
# TestSimulateGameResult
# ---------------------------------------------------------------------------


class TestSimulateGameResult:
    """Tests for the simulate_game_result helper and _eliminate_losing_entries."""

    def _setup(self, client, db_session):
        """
        Create two users + entries, seed NE vs KC, and insert one pick per
        entry (NE picker and KC picker).  Returns a dict of useful IDs.
        """
        _seed_ne_kc(db_session)

        token_a = _reg(client, "elim_a@example.com")
        token_b = _reg(client, "elim_b@example.com")

        pool_id = _create_pool(client, _h(token_a))
        entry_a_id = _create_entry(client, _h(token_a), pool_id, name="Entry NE")
        entry_b_id = _create_entry(client, _h(token_b), pool_id, name="Entry KC")

        pick_a = _create_pick_direct(db_session, entry_a_id, WEEK, "NE", team_id=NE_ID)
        pick_b = _create_pick_direct(db_session, entry_b_id, WEEK, "KC", team_id=KC_ID)

        return {
            "pool_id": pool_id,
            "entry_a_id": entry_a_id,  # picked NE
            "entry_b_id": entry_b_id,  # picked KC
            "pick_a_id": pick_a.id,
            "pick_b_id": pick_b.id,
        }

    def test_win_pick_gets_win_result(self, client, db_session):
        """NE picker's pick result is 'win' after NE wins."""
        ids = self._setup(client, db_session)

        simulate_game_result(db_session, GAME_ID, NE_ID)

        pick = (
            db_session.query(models.Pick)
            .filter(models.Pick.id == ids["pick_a_id"])
            .first()
        )
        assert pick.result == "win"

    def test_loss_pick_gets_loss_result(self, client, db_session):
        """KC picker's pick result is 'loss' after NE wins."""
        ids = self._setup(client, db_session)

        simulate_game_result(db_session, GAME_ID, NE_ID)

        pick = (
            db_session.query(models.Pick)
            .filter(models.Pick.id == ids["pick_b_id"])
            .first()
        )
        assert pick.result == "loss"

    def test_entry_eliminated_after_loss(self, client, db_session):
        """Entry that picked KC (the loser) has alive=False after simulation."""
        ids = self._setup(client, db_session)

        simulate_game_result(db_session, GAME_ID, NE_ID)

        db_session.expire_all()
        entry = (
            db_session.query(models.Entry)
            .filter(models.Entry.id == ids["entry_b_id"])
            .first()
        )
        assert entry.alive is False

    def test_entry_alive_after_win(self, client, db_session):
        """Entry that picked NE (the winner) remains alive=True after simulation."""
        ids = self._setup(client, db_session)

        simulate_game_result(db_session, GAME_ID, NE_ID)

        db_session.expire_all()
        entry = (
            db_session.query(models.Entry)
            .filter(models.Entry.id == ids["entry_a_id"])
            .first()
        )
        assert entry.alive is True

    def test_pickem_entry_remains_active_after_incorrect_pick(self, client, db_session):
        """A Pick 'Em loss costs a point opportunity but never eliminates the entry."""
        ids = self._setup(client, db_session)
        pool = (
            db_session.query(models.Pool)
            .filter(models.Pool.id == ids["pool_id"])
            .first()
        )
        pool.pool_type = "pickem"
        # Pick 'Em scoring is intentionally game-specific. This test starts
        # from Survivor-style fixtures, so associate the converted picks with
        # the game just as the Pick 'Em creation endpoint does.
        db_session.query(models.Pick).filter(
            models.Pick.id.in_([ids["pick_a_id"], ids["pick_b_id"]])
        ).update({"game_id": GAME_ID}, synchronize_session="fetch")
        db_session.commit()

        simulate_game_result(db_session, GAME_ID, NE_ID)

        db_session.expire_all()
        entry = (
            db_session.query(models.Entry)
            .filter(models.Entry.id == ids["entry_b_id"])
            .first()
        )
        losing_pick = (
            db_session.query(models.Pick)
            .filter(models.Pick.id == ids["pick_b_id"])
            .first()
        )
        assert losing_pick.result == "loss"
        assert entry.alive is True


# ---------------------------------------------------------------------------
# Standalone elimination/pick gap tests
# ---------------------------------------------------------------------------


def test_dead_entry_cannot_pick(client, db_session):
    """
    POST /picks/create returns HTTP 403 when Entry.alive is False.
    Eliminated entries cannot submit picks.
    """
    token = _reg(client, "dead_pick@example.com")
    pool_id = _create_pool(client, _h(token))
    entry_id = _create_entry(client, _h(token), pool_id, name="Dead Entry")

    # Kill the entry directly in the DB
    entry = db_session.query(models.Entry).filter(models.Entry.id == entry_id).first()
    entry.alive = False
    db_session.commit()

    # Attempt to pick — the API now blocks this
    resp = client.post(
        "/picks/create",
        json={"entry_id": entry_id, "week": 1, "team": "NE"},
        headers=_h(token),
    )
    assert (
        resp.status_code == 403
    ), f"Expected 403 for dead entry pick, got {resp.status_code}: {resp.text}"
    assert "eliminated" in resp.json().get("detail", "").lower()


def test_dead_entry_has_no_picks_via_helper(client, db_session):
    """
    After _eliminate_losing_entries runs, dead entries are reflected in the DB.
    This is a data-integrity sanity check: get_alive_entries should not return
    entries that were killed by the elimination helper.
    """
    _seed_ne_kc(db_session)

    token = _reg(client, "dead_integrity@example.com")
    pool_id = _create_pool(client, _h(token))
    entry_id = _create_entry(client, _h(token), pool_id, name="KC Picker")

    _create_pick_direct(db_session, entry_id, WEEK, "KC", team_id=KC_ID)

    # Simulate KC losing
    simulate_game_result(db_session, GAME_ID, NE_ID)

    alive = get_alive_entries(db_session, pool_id)
    alive_ids = [e.id for e in alive]
    assert entry_id not in alive_ids, "Dead entry must not appear in alive entries list"


# ---------------------------------------------------------------------------
# TestAutoPick
# ---------------------------------------------------------------------------


class TestAutoPick:
    """Tests for the auto-pick logic in POST /admin/pools/{pool_id}/lock-week/{week}."""

    def test_autopick_assigned_when_no_pick(self, client, db_session):
        """
        Two entries in a pool; admin submits a pick for week 1, member does not.
        After lock-week/1 the member's entry receives an auto-pick with locked=True.
        """
        token_admin = _reg(client, "ap_admin@example.com")
        token_member = _reg(client, "ap_member@example.com")

        pool_id = _create_pool(client, _h(token_admin))
        entry_admin_id = _create_entry(
            client, _h(token_admin), pool_id, name="Admin Entry"
        )
        entry_member_id = _create_entry(
            client, _h(token_member), pool_id, name="Member Entry"
        )

        # Admin picks for week 1
        client.post(
            "/picks/create",
            json={"entry_id": entry_admin_id, "week": 1, "team": "SF"},
            headers=_h(token_admin),
        )

        # Member submits no pick — lock-week should auto-assign one
        resp = client.post(
            f"/admin/pools/{pool_id}/lock-week/1", headers=_h(token_admin)
        )
        assert resp.status_code == 200, f"lock-week failed: {resp.json()}"
        assert resp.json()["auto_picks_created"] == 1

        pick = (
            db_session.query(models.Pick)
            .filter(models.Pick.entry_id == entry_member_id, models.Pick.week == 1)
            .first()
        )
        assert pick is not None, "Auto-pick was not created for the member entry"
        assert pick.locked is True

    def test_autopick_respects_team_uniqueness(self, client, db_session):
        """
        An entry has picks for teams A, B, C in weeks 1–3.
        When lock-week/4 fires an auto-pick it must not reuse A, B, or C.
        """
        token = _reg(client, "ap_unique@example.com")
        pool_id = _create_pool(client, _h(token))
        entry_id = _create_entry(client, _h(token), pool_id, name="Used Teams Entry")

        # Seed picks for three teams — these are the only popular picks so the
        # popularity ranking will include them, but they must be skipped.
        used_teams = ["NE", "KC", "SF"]
        for week, team in enumerate(used_teams, start=1):
            _create_pick_direct(db_session, entry_id, week, team)

        # A second entry with a pick for week 4 — this drives the popularity map
        # so lock-week has something to rank.
        token_b = _reg(client, "ap_unique_b@example.com")
        entry_b_id = _create_entry(client, _h(token_b), pool_id, name="Entry B")
        _create_pick_direct(db_session, entry_b_id, 4, "DAL")

        resp = client.post(f"/admin/pools/{pool_id}/lock-week/4", headers=_h(token))
        assert resp.status_code == 200, f"lock-week failed: {resp.json()}"

        pick = (
            db_session.query(models.Pick)
            .filter(models.Pick.entry_id == entry_id, models.Pick.week == 4)
            .first()
        )
        assert pick is not None, "Auto-pick was not created"
        assert (
            pick.team not in used_teams
        ), f"Auto-pick reused a previously chosen team: {pick.team}"

    def test_autopick_skipped_no_eligible_teams(self, client, db_session):
        """
        An entry has already used every team in the popularity ranking.
        lock-week logs AUTO_PICK_SKIPPED and no pick is created.

        To keep the test fast we seed a small popularity map (4 teams) and
        give the entry prior picks for all 4 of those teams.
        """
        token = _reg(client, "ap_skip@example.com")
        pool_id = _create_pool(client, _h(token))
        entry_id = _create_entry(client, _h(token), pool_id, name="Exhausted Entry")

        teams = ["BUF", "MIA", "NYJ", "NE"]

        # Seed popularity for week 5 via a second entry
        token_b = _reg(client, "ap_skip_b@example.com")
        entry_b_id = _create_entry(
            client, _h(token_b), pool_id, name="Popularity Driver"
        )
        for week, team in enumerate(teams, start=1):
            _create_pick_direct(db_session, entry_b_id, week, team)
        # Week 5 pick for entry_b to drive the popularity map
        _create_pick_direct(db_session, entry_b_id, 5, "BUF")

        # The exhausted entry has already used every team in the popularity map
        for week, team in enumerate(teams, start=1):
            _create_pick_direct(db_session, entry_id, week, team)

        resp = client.post(f"/admin/pools/{pool_id}/lock-week/5", headers=_h(token))
        assert resp.status_code == 200, f"lock-week failed: {resp.json()}"
        assert resp.json()["auto_picks_created"] == 0

        # An AUTO_PICK_SKIPPED audit log must exist for our entry
        db_session.expire_all()
        log = (
            db_session.query(models.AuditLog)
            .filter(
                models.AuditLog.action == "ADMIN_AUTO_PICK_SKIPPED",
            )
            .first()
        )
        assert log is not None, "Expected AUTO_PICK_SKIPPED audit log was not created"


# ---------------------------------------------------------------------------
# TestAdminOps
# ---------------------------------------------------------------------------


class TestAdminOps:
    """Tests for admin transfer, delete, and access-control routes."""

    def test_admin_transfer_entry(self, client, db_session):
        """
        Admin transfers an entry from user A to user B.
        Entry.user_id changes; picks are preserved.
        """
        token_admin = _reg(client, "xfr_admin@example.com")
        token_a = _reg(client, "xfr_a@example.com")
        token_b = _reg(client, "xfr_b@example.com")

        pool_id = _create_pool(client, _h(token_admin))
        joined = client.post(f"/pools/{pool_id}/join", json={}, headers=_h(token_b))
        assert joined.status_code == 200, joined.text
        entry_id = _create_entry(client, _h(token_a), pool_id, name="Transfer Entry")

        # Give the entry a pick so we can assert it survives the transfer
        pick = _create_pick_direct(db_session, entry_id, 1, "GB")

        resp = client.post(
            f"/admin/pools/{pool_id}/transfer-entry",
            json={"entry_id": entry_id, "to_email": "xfr_b@example.com"},
            headers=_h(token_admin),
        )
        assert resp.status_code == 200, f"Transfer failed: {resp.json()}"

        db_session.expire_all()

        # Entry now belongs to user B
        entry = (
            db_session.query(models.Entry).filter(models.Entry.id == entry_id).first()
        )
        user_b = (
            db_session.query(models.User)
            .filter(models.User.email == "xfr_b@example.com")
            .first()
        )
        assert (
            entry.user_id == user_b.id
        ), "Entry user_id was not updated after transfer"

        # Pick is preserved
        surviving_pick = (
            db_session.query(models.Pick).filter(models.Pick.id == pick.id).first()
        )
        assert surviving_pick is not None, "Pick was lost after entry transfer"

    def test_admin_delete_entry(self, client, db_session):
        """Admin deletes an entry — returns 200 and entry no longer exists in DB."""
        token = _reg(client, "del_admin@example.com")
        pool_id = _create_pool(client, _h(token))
        entry_id = _create_entry(client, _h(token), pool_id, name="Doomed Entry")

        resp = client.delete(
            f"/admin/pools/{pool_id}/entries/{entry_id}",
            headers=_h(token),
        )
        assert resp.status_code == 200, f"Delete failed: {resp.json()}"

        entry = (
            db_session.query(models.Entry).filter(models.Entry.id == entry_id).first()
        )
        assert entry is None, "Entry still exists in DB after admin delete"

    def test_non_admin_cannot_use_admin_routes(self, client, db_session):
        """
        A plain user (non-admin, non-owner) receives 403 for:
          - POST /admin/pools/{pool_id}/lock-week/1
          - PATCH /admin/pools/{pool_id}/picks/{pick_id}
        """
        token_owner = _reg(client, "nacp_owner@example.com")
        token_plain = _reg(client, "nacp_plain@example.com")

        pool_id = _create_pool(client, _h(token_owner))
        entry_id = _create_entry(client, _h(token_owner), pool_id, name="Owner Entry")
        pick = _create_pick_direct(db_session, entry_id, 1, "LAR")

        # lock-week — non-admin must get 403
        lock_resp = client.post(
            f"/admin/pools/{pool_id}/lock-week/1",
            headers=_h(token_plain),
        )
        assert (
            lock_resp.status_code == 403
        ), f"Expected 403 from lock-week for non-admin, got {lock_resp.status_code}"

        # admin pick edit — non-admin must get 403
        patch_resp = client.patch(
            f"/admin/pools/{pool_id}/picks/{pick.id}",
            json={"team": "SEA"},
            headers=_h(token_plain),
        )
        assert (
            patch_resp.status_code == 403
        ), f"Expected 403 from admin pick edit for non-admin, got {patch_resp.status_code}"
