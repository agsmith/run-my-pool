"""
Tests for rmp/backend/weekly_locks.py

Covers:
  - pool_week_lock_time()         (UC-1.1 through UC-1.7)
  - lock_pool_week()              (UC-2a, UC-2b, UC-2c, UC-2d, UC-2e)
  - process_due_weekly_locks()    (UC-3.1 through UC-3.11)
"""

import uuid
from datetime import datetime, time, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import models
import weekly_locks


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _pool(
    db,
    *,
    pool_id=None,
    pool_type="survivor",
    owner_id=None,
    lock_day_of_week=None,
    lock_time_of_day=None,
    lock_timezone=None,
    lock_time=None,
):
    owner_id = owner_id or str(uuid.uuid4())
    pool_id = pool_id or str(uuid.uuid4())
    p = models.Pool(
        id=pool_id,
        name=f"Test Pool {pool_id[:8]}",
        owner_id=owner_id,
        pool_type=pool_type,
        lock_day_of_week=lock_day_of_week,
        lock_time_of_day=lock_time_of_day,
        lock_timezone=lock_timezone,
        lock_time=lock_time,
    )
    return p


def _user(db, *, user_id=None, email=None):
    user_id = user_id or str(uuid.uuid4())
    email = email or f"user-{user_id[:8]}@example.com"
    u = models.User(id=user_id, email=email, hashed_password="unused", is_active=True)
    db.add(u)
    return u


def _entry(db, *, entry_id=None, pool_id, user_id, alive=True):
    entry_id = entry_id or str(uuid.uuid4())
    e = models.Entry(
        id=entry_id, pool_id=pool_id, user_id=user_id, name="E", alive=alive
    )
    db.add(e)
    return e


def _pick(db, *, pick_id=None, entry_id, week, team="NE", locked=False):
    pick_id = pick_id or str(uuid.uuid4())
    p = models.Pick(id=pick_id, entry_id=entry_id, week=week, team=team, locked=locked)
    db.add(p)
    return p


def _game(start_time):
    """Minimal game-like object with a start_time attribute."""
    g = SimpleNamespace(start_time=start_time)
    return g


def _line(team_abbrv, spread):
    team = SimpleNamespace(abbrv=team_abbrv, id=team_abbrv)
    return SimpleNamespace(
        favorite_team=team, favorite_team_id=team_abbrv, spread=spread
    )


# ---------------------------------------------------------------------------
# UC-1: pool_week_lock_time
# ---------------------------------------------------------------------------


class TestPoolWeekLockTime:
    def test_uc1_1_no_games_returns_none(self, db_session):
        """UC-1.1: empty games list -> None."""
        pool = _pool(
            db_session,
            lock_day_of_week=6,
            lock_time_of_day=time(13, 0),
            lock_timezone="America/New_York",
        )
        assert weekly_locks.pool_week_lock_time(pool, []) is None

    def test_uc1_2_missing_lock_day_falls_back(self, db_session):
        """UC-1.2: pool.lock_day_of_week is None -> falls back to pool.lock_time."""
        fallback = datetime(2025, 9, 10, 18, 0)
        pool = _pool(
            db_session,
            lock_day_of_week=None,
            lock_time_of_day=time(13, 0),
            lock_timezone="America/New_York",
            lock_time=fallback,
        )
        game = _game(datetime(2025, 9, 7, 13, 0))
        result = weekly_locks.pool_week_lock_time(pool, [game])
        assert result == fallback

    def test_uc1_2_missing_lock_time_of_day_falls_back(self, db_session):
        """UC-1.2: pool.lock_time_of_day is None -> falls back to pool.lock_time."""
        fallback = datetime(2025, 9, 10, 18, 0)
        pool = _pool(
            db_session,
            lock_day_of_week=6,
            lock_time_of_day=None,
            lock_timezone="America/New_York",
            lock_time=fallback,
        )
        game = _game(datetime(2025, 9, 7, 13, 0))
        result = weekly_locks.pool_week_lock_time(pool, [game])
        assert result == fallback

    def test_uc1_2_empty_timezone_falls_back(self, db_session):
        """UC-1.2: pool.lock_timezone is empty string -> falls back to pool.lock_time."""
        fallback = datetime(2025, 9, 10, 18, 0)
        pool = _pool(
            db_session,
            lock_day_of_week=6,
            lock_time_of_day=time(13, 0),
            lock_timezone="",
            lock_time=fallback,
        )
        game = _game(datetime(2025, 9, 7, 13, 0))
        result = weekly_locks.pool_week_lock_time(pool, [game])
        assert result == fallback

    def test_uc1_2_none_timezone_falls_back(self, db_session):
        """UC-1.2: pool.lock_timezone is None -> falls back to pool.lock_time."""
        fallback = datetime(2025, 9, 10, 18, 0)
        pool = _pool(
            db_session,
            lock_day_of_week=6,
            lock_time_of_day=time(13, 0),
            lock_timezone=None,
            lock_time=fallback,
        )
        game = _game(datetime(2025, 9, 7, 13, 0))
        result = weekly_locks.pool_week_lock_time(pool, [game])
        assert result == fallback

    def test_uc1_4_invalid_timezone_falls_back(self, db_session):
        """UC-1.4: invalid timezone string -> ZoneInfoNotFoundError caught, fallback returned."""
        fallback = datetime(2025, 9, 10, 18, 0)
        pool = _pool(
            db_session,
            lock_day_of_week=6,
            lock_time_of_day=time(13, 0),
            lock_timezone="Bad/Zone",
            lock_time=fallback,
        )
        game = _game(datetime(2025, 9, 7, 13, 0))
        result = weekly_locks.pool_week_lock_time(pool, [game])
        assert result == fallback

    def test_uc1_3_fully_configured_returns_utc_deadline(self, db_session):
        """UC-1.3: fully configured recurring lock -> returns naive UTC datetime."""
        # Week 1 2025: first game Sunday 2025-09-07 13:00 UTC
        # lock_day_of_week=6 (Saturday), lock_time_of_day=13:00, tz=America/New_York (UTC-4 in Sep)
        pool = _pool(
            db_session,
            lock_day_of_week=6,
            lock_time_of_day=time(13, 0),
            lock_timezone="America/New_York",
        )
        game = _game(datetime(2025, 9, 7, 13, 0))  # Sunday UTC
        result = weekly_locks.pool_week_lock_time(pool, [game])
        assert isinstance(result, datetime)
        assert result.tzinfo is None  # naive UTC

    def test_uc1_5_lock_day_before_kickoff_deadline_in_prior_week(self, db_session):
        """UC-1.5: lock day (Thursday=4) before Sunday kickoff -> deadline before kickoff."""
        # lock_day_of_week=4 (Thursday), first game is Sunday
        pool = _pool(
            db_session,
            lock_day_of_week=4,
            lock_time_of_day=time(20, 0),
            lock_timezone="America/New_York",
        )
        game = _game(datetime(2025, 9, 7, 17, 0))  # Sunday
        result = weekly_locks.pool_week_lock_time(pool, [game])
        assert result is not None
        assert result < game.start_time  # deadline is before kickoff

    def test_uc1_6_lock_day_equals_kickoff_day(self, db_session):
        """UC-1.6: lock day equals kickoff day -> deadline is same calendar day as kickoff."""
        # lock_day_of_week=6 maps to Sunday (weekday=6). Game is also Sunday 2025-09-07.
        pool = _pool(
            db_session,
            lock_day_of_week=6,
            lock_time_of_day=time(12, 0),
            lock_timezone="America/New_York",
        )
        game = _game(datetime(2025, 9, 7, 17, 0))  # Sunday UTC = Sunday local in ET
        result = weekly_locks.pool_week_lock_time(pool, [game])
        assert result is not None
        # Result should land on Sunday. Result is naive UTC; ET offset is -4h in Sep.
        local_result = result + timedelta(hours=4)
        assert local_result.weekday() == 6  # Sunday (Python weekday: 0=Mon, 6=Sun)

    def test_uc1_7_lock_day_after_kickoff_deadline_following_week(self, db_session):
        """UC-1.7: lock day after Sunday kickoff -> deadline is after kickoff."""
        # lock_day_of_week=7 maps to Monday (day after Sunday kickoff)
        pool = _pool(
            db_session,
            lock_day_of_week=7,
            lock_time_of_day=time(20, 0),
            lock_timezone="America/New_York",
        )
        game = _game(datetime(2025, 9, 7, 17, 0))  # Sunday
        result = weekly_locks.pool_week_lock_time(pool, [game])
        assert result is not None
        # deadline should be after the Sunday kickoff
        assert result > game.start_time

    def test_fallback_returns_none_when_lock_time_is_none(self, db_session):
        """Pool.lock_time is None and config incomplete -> returns None."""
        pool = _pool(
            db_session,
            lock_day_of_week=None,
            lock_time_of_day=None,
            lock_timezone=None,
            lock_time=None,
        )
        game = _game(datetime(2025, 9, 7, 13, 0))
        result = weekly_locks.pool_week_lock_time(pool, [game])
        assert result is None


# ---------------------------------------------------------------------------
# UC-2a: lock_pool_week — pick'em path
# ---------------------------------------------------------------------------


class TestLockPoolWeekPickem:
    def test_uc2a_1_unlocked_picks_flipped(self, db_session):
        """UC-2a.1: pick'em pool with unlocked picks -> all flipped locked=True; returns 0."""
        owner = _user(db_session)
        db_session.flush()
        pool = _pool(db_session, pool_type="pickem", owner_id=owner.id)
        db_session.add(pool)
        db_session.flush()
        entry = _entry(db_session, pool_id=pool.id, user_id=owner.id)
        db_session.flush()
        p1 = _pick(db_session, entry_id=entry.id, week=3, team="BUF", locked=False)
        p2 = _pick(db_session, entry_id=entry.id, week=3, team="KC", locked=False)
        db_session.commit()

        result = weekly_locks.lock_pool_week(
            db_session,
            pool,
            3,
            owner.id,
            games_provider=lambda db, week: [],
            line_freezer=lambda *a, **kw: (_ for _ in ()).throw(
                AssertionError("must not call")
            ),
        )

        assert result == 0
        picks = db_session.query(models.Pick).filter(models.Pick.week == 3).all()
        assert all(p.locked is True for p in picks)

    def test_uc2a_2_no_picks_returns_zero(self, db_session):
        """UC-2a.2: pick'em pool with no picks -> nothing created; returns 0."""
        owner = _user(db_session)
        db_session.flush()
        pool = _pool(db_session, pool_type="pickem", owner_id=owner.id)
        db_session.add(pool)
        db_session.flush()
        _entry(db_session, pool_id=pool.id, user_id=owner.id)
        db_session.commit()

        result = weekly_locks.lock_pool_week(
            db_session,
            pool,
            3,
            owner.id,
            games_provider=lambda db, week: [],
            line_freezer=lambda *a, **kw: (_ for _ in ()).throw(
                AssertionError("must not call")
            ),
        )

        assert result == 0
        assert db_session.query(models.Pick).count() == 0

    def test_uc2a_3_pickem_never_calls_line_freezer(self, db_session):
        """UC-2a.3: pick'em must never invoke line_freezer."""
        owner = _user(db_session)
        db_session.flush()
        pool = _pool(db_session, pool_type="pickem", owner_id=owner.id)
        db_session.add(pool)
        db_session.flush()
        entry = _entry(db_session, pool_id=pool.id, user_id=owner.id)
        _pick(db_session, entry_id=entry.id, week=5, team="DAL", locked=False)
        db_session.commit()

        called = []

        def asserting_freezer(*a, **kw):
            called.append(True)
            raise AssertionError("line_freezer must not be called for pick'em")

        weekly_locks.lock_pool_week(
            db_session,
            pool,
            5,
            owner.id,
            games_provider=lambda db, week: [],
            line_freezer=asserting_freezer,
        )

        assert called == [], "line_freezer was called unexpectedly"

    def test_uc2a_already_locked_idempotent(self, db_session):
        """UC-2a: re-locking already-locked picks is idempotent; pick count unchanged."""
        owner = _user(db_session)
        db_session.flush()
        pool = _pool(db_session, pool_type="pickem", owner_id=owner.id)
        db_session.add(pool)
        db_session.flush()
        entry = _entry(db_session, pool_id=pool.id, user_id=owner.id)
        _pick(db_session, entry_id=entry.id, week=3, team="BUF", locked=True)
        db_session.commit()

        result = weekly_locks.lock_pool_week(
            db_session,
            pool,
            3,
            owner.id,
            games_provider=lambda db, week: [],
            line_freezer=lambda *a, **kw: [],
        )

        assert result == 0
        assert db_session.query(models.Pick).count() == 1
        assert db_session.query(models.Pick).first().locked is True

    def test_uc2a_multiple_entries_all_locked(self, db_session):
        """UC-2a: multiple entries with picks — all picks across all entries locked."""
        owner = _user(db_session)
        db_session.flush()
        pool = _pool(db_session, pool_type="pickem", owner_id=owner.id)
        db_session.add(pool)
        db_session.flush()
        entry1 = _entry(db_session, pool_id=pool.id, user_id=owner.id)
        entry2 = _entry(db_session, pool_id=pool.id, user_id=owner.id)
        _pick(db_session, entry_id=entry1.id, week=4, team="NE", locked=False)
        _pick(db_session, entry_id=entry2.id, week=4, team="SF", locked=False)
        db_session.commit()

        weekly_locks.lock_pool_week(
            db_session,
            pool,
            4,
            owner.id,
            games_provider=lambda db, week: [],
            line_freezer=lambda *a, **kw: [],
        )

        picks = db_session.query(models.Pick).filter(models.Pick.week == 4).all()
        assert len(picks) == 2
        assert all(p.locked is True for p in picks)


# ---------------------------------------------------------------------------
# UC-2b / 2c / 2d / 2e: lock_pool_week — survivor path
# ---------------------------------------------------------------------------


class TestLockPoolWeekSurvivor:
    def _survivor_pool(self, db_session):
        owner = _user(db_session)
        db_session.flush()
        pool = _pool(db_session, pool_type="survivor", owner_id=owner.id)
        db_session.add(pool)
        db_session.flush()
        return owner, pool

    def test_uc2b_1_alive_entry_with_pick_locked(self, db_session):
        """UC-2b.1: alive entry already has a pick -> flipped to locked=True; returns 0."""
        owner, pool = self._survivor_pool(db_session)
        entry = _entry(db_session, pool_id=pool.id, user_id=owner.id, alive=True)
        _pick(db_session, entry_id=entry.id, week=1, team="NE", locked=False)
        db_session.commit()

        result = weekly_locks.lock_pool_week(
            db_session,
            pool,
            1,
            owner.id,
            games_provider=lambda db, week: [_game(datetime(2025, 9, 7, 17, 0))],
            line_freezer=lambda *a, **kw: [],
        )

        assert result == 0
        pick = db_session.query(models.Pick).filter(models.Pick.week == 1).one()
        assert pick.locked is True

    def test_uc2b_2_eliminated_entry_ignored(self, db_session):
        """UC-2b.2: eliminated entry (alive=False) is ignored."""
        owner, pool = self._survivor_pool(db_session)
        entry = _entry(db_session, pool_id=pool.id, user_id=owner.id, alive=False)
        _pick(db_session, entry_id=entry.id, week=1, team="NE", locked=False)
        db_session.commit()

        result = weekly_locks.lock_pool_week(
            db_session,
            pool,
            1,
            owner.id,
            games_provider=lambda db, week: [_game(datetime(2025, 9, 7, 17, 0))],
            line_freezer=lambda *a, **kw: [],
        )

        assert result == 0
        # eliminated entry's pick should NOT be locked
        pick = db_session.query(models.Pick).filter(models.Pick.week == 1).one()
        assert pick.locked is False

    def test_uc2b_3_already_locked_idempotent(self, db_session):
        """UC-2b.3: week already locked -> idempotent; returns 0; no duplicates."""
        owner, pool = self._survivor_pool(db_session)
        entry = _entry(db_session, pool_id=pool.id, user_id=owner.id, alive=True)
        _pick(db_session, entry_id=entry.id, week=2, team="KC", locked=True)
        db_session.commit()

        result = weekly_locks.lock_pool_week(
            db_session,
            pool,
            2,
            owner.id,
            games_provider=lambda db, week: [_game(datetime(2025, 9, 14, 17, 0))],
            line_freezer=lambda *a, **kw: [],
        )

        assert result == 0
        assert db_session.query(models.Pick).filter(models.Pick.week == 2).count() == 1

    def test_uc2c_1_auto_pick_line_ranked_team(self, db_session, monkeypatch):
        """UC-2c.1: alive entry without pick -> auto-pick from line-ranked team."""
        owner, pool = self._survivor_pool(db_session)
        entry = _entry(db_session, pool_id=pool.id, user_id=owner.id, alive=True)
        db_session.commit()

        audit_calls = []
        monkeypatch.setattr(
            weekly_locks, "log_admin_action", lambda **kw: audit_calls.append(kw)
        )

        lines = [_line("KC", 7.5), _line("BUF", 3.0)]
        result = weekly_locks.lock_pool_week(
            db_session,
            pool,
            1,
            owner.id,
            games_provider=lambda db, week: [_game(datetime(2025, 9, 7, 17, 0))],
            line_freezer=lambda *a, **kw: lines,
        )

        assert result == 1
        pick = db_session.query(models.Pick).filter(models.Pick.week == 1).one()
        assert pick.locked is True
        assert pick.team == "KC"  # highest spread
        assert any(c["action"] == "AUTO_PICK" for c in audit_calls)

    def test_uc2c_2_falls_back_to_popularity_ranked(self, db_session, monkeypatch):
        """UC-2c.2: no line-ranked team available -> falls back to popularity-ranked team."""
        owner, pool = self._survivor_pool(db_session)
        # entry has used KC in a prior week
        entry = _entry(db_session, pool_id=pool.id, user_id=owner.id, alive=True)
        _pick(db_session, entry_id=entry.id, week=0, team="KC", locked=True)
        # another entry picked BUF this week (to populate popularity)
        other_entry = _entry(db_session, pool_id=pool.id, user_id=owner.id, alive=True)
        _pick(db_session, entry_id=other_entry.id, week=1, team="BUF", locked=True)
        db_session.commit()

        audit_calls = []
        monkeypatch.setattr(
            weekly_locks, "log_admin_action", lambda **kw: audit_calls.append(kw)
        )

        # line_freezer returns only KC, which is already used by our entry
        lines = [_line("KC", 10.0)]
        result = weekly_locks.lock_pool_week(
            db_session,
            pool,
            1,
            owner.id,
            games_provider=lambda db, week: [_game(datetime(2025, 9, 7, 17, 0))],
            line_freezer=lambda *a, **kw: lines,
        )

        assert result == 1
        # Should have fallen back to BUF (from popularity, since KC was used)
        new_pick = (
            db_session.query(models.Pick)
            .filter(models.Pick.entry_id == entry.id, models.Pick.week == 1)
            .one()
        )
        assert new_pick.team == "BUF"

    def test_uc2c_3_no_candidate_skip_audit_written(self, db_session, monkeypatch):
        """UC-2c.3: no candidate team -> no pick created; AUTO_PICK_SKIPPED audit written."""
        owner, pool = self._survivor_pool(db_session)
        entry = _entry(db_session, pool_id=pool.id, user_id=owner.id, alive=True)
        # entry already used KC, no other lines or popularity choices
        _pick(db_session, entry_id=entry.id, week=0, team="KC", locked=True)
        db_session.commit()

        audit_calls = []
        monkeypatch.setattr(
            weekly_locks, "log_admin_action", lambda **kw: audit_calls.append(kw)
        )

        lines = [_line("KC", 10.0)]
        result = weekly_locks.lock_pool_week(
            db_session,
            pool,
            1,
            owner.id,
            games_provider=lambda db, week: [_game(datetime(2025, 9, 7, 17, 0))],
            line_freezer=lambda *a, **kw: lines,
            log_skipped_defaults=True,
        )

        assert result == 0
        assert db_session.query(models.Pick).filter(models.Pick.week == 1).count() == 0
        assert any(c["action"] == "AUTO_PICK_SKIPPED" for c in audit_calls)

    def test_uc2c_4_log_skipped_false_suppresses_audit(self, db_session, monkeypatch):
        """UC-2c.4: log_skipped_defaults=False -> AUTO_PICK_SKIPPED audit suppressed."""
        owner, pool = self._survivor_pool(db_session)
        entry = _entry(db_session, pool_id=pool.id, user_id=owner.id, alive=True)
        _pick(db_session, entry_id=entry.id, week=0, team="KC", locked=True)
        db_session.commit()

        audit_calls = []
        monkeypatch.setattr(
            weekly_locks, "log_admin_action", lambda **kw: audit_calls.append(kw)
        )

        lines = [_line("KC", 10.0)]
        result = weekly_locks.lock_pool_week(
            db_session,
            pool,
            1,
            owner.id,
            games_provider=lambda db, week: [_game(datetime(2025, 9, 7, 17, 0))],
            line_freezer=lambda *a, **kw: lines,
            log_skipped_defaults=False,
        )

        assert result == 0
        assert not any(c["action"] == "AUTO_PICK_SKIPPED" for c in audit_calls)

    def test_uc2c_5_multiple_entries_each_auto_picked(self, db_session, monkeypatch):
        """UC-2c.5: multiple entries without picks -> each gets independent auto-pick."""
        owner, pool = self._survivor_pool(db_session)
        entry1 = _entry(db_session, pool_id=pool.id, user_id=owner.id, alive=True)
        entry2 = _entry(db_session, pool_id=pool.id, user_id=owner.id, alive=True)
        db_session.commit()

        monkeypatch.setattr(weekly_locks, "log_admin_action", lambda **kw: None)

        lines = [_line("KC", 7.0), _line("BUF", 3.0)]
        result = weekly_locks.lock_pool_week(
            db_session,
            pool,
            1,
            owner.id,
            games_provider=lambda db, week: [_game(datetime(2025, 9, 7, 17, 0))],
            line_freezer=lambda *a, **kw: lines,
        )

        assert result == 2
        picks = db_session.query(models.Pick).filter(models.Pick.week == 1).all()
        assert len(picks) == 2
        assert all(p.locked is True for p in picks)

    def test_uc2c_6_auto_pick_audit_records_owner_email(self, db_session, monkeypatch):
        """UC-2c.6: auto-pick audit records owner email."""
        owner, pool = self._survivor_pool(db_session)
        entry = _entry(db_session, pool_id=pool.id, user_id=owner.id, alive=True)
        db_session.commit()

        audit_calls = []
        monkeypatch.setattr(
            weekly_locks, "log_admin_action", lambda **kw: audit_calls.append(kw)
        )

        lines = [_line("KC", 5.0)]
        weekly_locks.lock_pool_week(
            db_session,
            pool,
            1,
            owner.id,
            games_provider=lambda db, week: [_game(datetime(2025, 9, 7, 17, 0))],
            line_freezer=lambda *a, **kw: lines,
        )

        auto_pick_calls = [c for c in audit_calls if c["action"] == "AUTO_PICK"]
        assert len(auto_pick_calls) == 1
        assert auto_pick_calls[0]["additional_data"]["user_email"] == owner.email

    def test_uc2c_7_auto_pick_audit_user_not_found_no_crash(
        self, db_session, monkeypatch
    ):
        """UC-2c.7: auto-pick when owner not found -> user_email=None; no crash."""
        owner, pool = self._survivor_pool(db_session)
        # entry references a user_id that doesn't exist in DB
        entry = models.Entry(
            id=str(uuid.uuid4()),
            pool_id=pool.id,
            user_id="nonexistent-user-id",
            name="Ghost",
            alive=True,
        )
        db_session.add(entry)
        db_session.commit()

        audit_calls = []
        monkeypatch.setattr(
            weekly_locks, "log_admin_action", lambda **kw: audit_calls.append(kw)
        )

        lines = [_line("KC", 5.0)]
        result = weekly_locks.lock_pool_week(
            db_session,
            pool,
            1,
            owner.id,
            games_provider=lambda db, week: [_game(datetime(2025, 9, 7, 17, 0))],
            line_freezer=lambda *a, **kw: lines,
        )

        assert result == 1
        auto_pick_calls = [c for c in audit_calls if c["action"] == "AUTO_PICK"]
        assert len(auto_pick_calls) == 1
        assert auto_pick_calls[0]["additional_data"]["user_email"] is None

    def test_uc2d_1_line_freezer_called_once_correct_args(
        self, db_session, monkeypatch
    ):
        """UC-2d.1: line_freezer called exactly once with correct args."""
        owner, pool = self._survivor_pool(db_session)
        _entry(db_session, pool_id=pool.id, user_id=owner.id, alive=True)
        db_session.commit()

        monkeypatch.setattr(weekly_locks, "log_admin_action", lambda **kw: None)
        now = datetime(2025, 9, 12, 18, 0)
        games = [_game(datetime(2025, 9, 7, 17, 0))]
        freezer_calls = []

        def capturing_freezer(db, pool_id, week, g, captured_at=None):
            freezer_calls.append(
                {
                    "db": db,
                    "pool_id": pool_id,
                    "week": week,
                    "games": g,
                    "captured_at": captured_at,
                }
            )
            return [_line("NE", 3.0)]

        weekly_locks.lock_pool_week(
            db_session,
            pool,
            1,
            owner.id,
            now=now,
            games_provider=lambda db, week: games,
            line_freezer=capturing_freezer,
        )

        assert len(freezer_calls) == 1
        call = freezer_calls[0]
        assert call["pool_id"] == pool.id
        assert call["week"] == 1
        assert call["games"] is games
        assert call["captured_at"] == now

    def test_uc2d_2_line_ranked_teams_ordered_by_spread_desc(
        self, db_session, monkeypatch
    ):
        """UC-2d.2: line-ranked teams ordered by spread descending -> highest spread chosen."""
        owner, pool = self._survivor_pool(db_session)
        _entry(db_session, pool_id=pool.id, user_id=owner.id, alive=True)
        db_session.commit()

        monkeypatch.setattr(weekly_locks, "log_admin_action", lambda **kw: None)
        # BUF has lower spread, KC has higher; KC should be auto-picked
        lines = [_line("BUF", 1.5), _line("KC", 9.5)]
        weekly_locks.lock_pool_week(
            db_session,
            pool,
            1,
            owner.id,
            games_provider=lambda db, week: [_game(datetime(2025, 9, 7, 17, 0))],
            line_freezer=lambda *a, **kw: lines,
        )

        pick = db_session.query(models.Pick).filter(models.Pick.week == 1).one()
        assert pick.team == "KC"

    def test_uc2e_1_returns_count_of_auto_picks(self, db_session, monkeypatch):
        """UC-2e.1: returns count of auto-picks created."""
        owner, pool = self._survivor_pool(db_session)
        _entry(db_session, pool_id=pool.id, user_id=owner.id, alive=True)
        _entry(db_session, pool_id=pool.id, user_id=owner.id, alive=True)
        db_session.commit()

        monkeypatch.setattr(weekly_locks, "log_admin_action", lambda **kw: None)
        lines = [_line("KC", 7.0), _line("BUF", 3.0)]
        result = weekly_locks.lock_pool_week(
            db_session,
            pool,
            1,
            owner.id,
            games_provider=lambda db, week: [_game(datetime(2025, 9, 7, 17, 0))],
            line_freezer=lambda *a, **kw: lines,
        )
        assert result == 2

    def test_uc2e_2_returns_zero_when_no_auto_picks_needed(
        self, db_session, monkeypatch
    ):
        """UC-2e.2: returns 0 when no auto-picks needed (all alive entries have picks)."""
        owner, pool = self._survivor_pool(db_session)
        entry = _entry(db_session, pool_id=pool.id, user_id=owner.id, alive=True)
        _pick(db_session, entry_id=entry.id, week=1, team="KC", locked=False)
        db_session.commit()

        monkeypatch.setattr(weekly_locks, "log_admin_action", lambda **kw: None)
        result = weekly_locks.lock_pool_week(
            db_session,
            pool,
            1,
            owner.id,
            games_provider=lambda db, week: [_game(datetime(2025, 9, 7, 17, 0))],
            line_freezer=lambda *a, **kw: [],
        )
        assert result == 0


# ---------------------------------------------------------------------------
# UC-2 idempotency (integration)
# ---------------------------------------------------------------------------


class TestLockPoolWeekIdempotency:
    def test_survivor_all_locked_no_changes(self, db_session, monkeypatch):
        """Survivor: all alive entries already locked -> no DB changes; returns 0."""
        owner = _user(db_session)
        db_session.flush()
        pool = _pool(db_session, pool_type="survivor", owner_id=owner.id)
        db_session.add(pool)
        db_session.flush()
        entry = _entry(db_session, pool_id=pool.id, user_id=owner.id, alive=True)
        _pick(db_session, entry_id=entry.id, week=3, team="NE", locked=True)
        db_session.commit()

        monkeypatch.setattr(weekly_locks, "log_admin_action", lambda **kw: None)
        result = weekly_locks.lock_pool_week(
            db_session,
            pool,
            3,
            owner.id,
            games_provider=lambda db, week: [_game(datetime(2025, 9, 21, 17, 0))],
            line_freezer=lambda *a, **kw: [],
        )

        assert result == 0
        assert db_session.query(models.Pick).count() == 1

    def test_pickem_all_locked_no_changes(self, db_session):
        """Pick'em: all picks already locked -> re-lock is a no-op; returns 0."""
        owner = _user(db_session)
        db_session.flush()
        pool = _pool(db_session, pool_type="pickem", owner_id=owner.id)
        db_session.add(pool)
        db_session.flush()
        entry = _entry(db_session, pool_id=pool.id, user_id=owner.id)
        _pick(db_session, entry_id=entry.id, week=3, team="BUF", locked=True)
        db_session.commit()

        result = weekly_locks.lock_pool_week(
            db_session,
            pool,
            3,
            owner.id,
            games_provider=lambda db, week: [],
            line_freezer=lambda *a, **kw: [],
        )

        assert result == 0
        assert db_session.query(models.Pick).count() == 1

    def test_partial_lock_only_unlocked_flipped(self, db_session, monkeypatch):
        """Partially locked state -> only unlocked picks are flipped."""
        owner = _user(db_session)
        db_session.flush()
        pool = _pool(db_session, pool_type="survivor", owner_id=owner.id)
        db_session.add(pool)
        db_session.flush()
        entry1 = _entry(db_session, pool_id=pool.id, user_id=owner.id, alive=True)
        entry2 = _entry(db_session, pool_id=pool.id, user_id=owner.id, alive=True)
        _pick(db_session, entry_id=entry1.id, week=4, team="NE", locked=True)
        _pick(db_session, entry_id=entry2.id, week=4, team="BUF", locked=False)
        db_session.commit()

        monkeypatch.setattr(weekly_locks, "log_admin_action", lambda **kw: None)
        weekly_locks.lock_pool_week(
            db_session,
            pool,
            4,
            owner.id,
            games_provider=lambda db, week: [_game(datetime(2025, 9, 28, 17, 0))],
            line_freezer=lambda *a, **kw: [],
        )

        picks = db_session.query(models.Pick).filter(models.Pick.week == 4).all()
        assert all(p.locked is True for p in picks)

    def test_no_duplicate_picks_on_rerun(self, db_session, monkeypatch):
        """Re-running lock does not create duplicate pick rows."""
        owner = _user(db_session)
        db_session.flush()
        pool = _pool(db_session, pool_type="survivor", owner_id=owner.id)
        db_session.add(pool)
        db_session.flush()
        entry = _entry(db_session, pool_id=pool.id, user_id=owner.id, alive=True)
        _pick(db_session, entry_id=entry.id, week=5, team="KC", locked=True)
        db_session.commit()

        monkeypatch.setattr(weekly_locks, "log_admin_action", lambda **kw: None)
        for _ in range(3):
            weekly_locks.lock_pool_week(
                db_session,
                pool,
                5,
                owner.id,
                games_provider=lambda db, week: [_game(datetime(2025, 10, 5, 17, 0))],
                line_freezer=lambda *a, **kw: [],
            )

        assert db_session.query(models.Pick).filter(models.Pick.week == 5).count() == 1


# ---------------------------------------------------------------------------
# UC-2c team selection (integration)
# ---------------------------------------------------------------------------


class TestSurvivorAutoPickTeamSelection:
    def _setup(self, db_session):
        owner = _user(db_session)
        db_session.flush()
        pool = _pool(db_session, pool_type="survivor", owner_id=owner.id)
        db_session.add(pool)
        db_session.flush()
        return owner, pool

    def test_highest_spread_chosen(self, db_session, monkeypatch):
        """Line-ranked teams sorted by spread descending; highest chosen."""
        owner, pool = self._setup(db_session)
        _entry(db_session, pool_id=pool.id, user_id=owner.id, alive=True)
        db_session.commit()

        monkeypatch.setattr(weekly_locks, "log_admin_action", lambda **kw: None)
        lines = [_line("DEN", 2.0), _line("KC", 14.0), _line("BUF", 6.5)]
        weekly_locks.lock_pool_week(
            db_session,
            pool,
            1,
            owner.id,
            games_provider=lambda db, week: [_game(datetime(2025, 9, 7, 17, 0))],
            line_freezer=lambda *a, **kw: lines,
        )

        pick = db_session.query(models.Pick).filter(models.Pick.week == 1).one()
        assert pick.team == "KC"

    def test_popularity_fallback_when_line_used(self, db_session, monkeypatch):
        """Falls back to popularity when line-ranked team is already used."""
        owner, pool = self._setup(db_session)
        entry = _entry(db_session, pool_id=pool.id, user_id=owner.id, alive=True)
        _pick(db_session, entry_id=entry.id, week=0, team="KC", locked=True)
        # seed popularity: BUF picked by another entry this week
        other_entry = _entry(db_session, pool_id=pool.id, user_id=owner.id, alive=True)
        _pick(db_session, entry_id=other_entry.id, week=1, team="BUF", locked=True)
        db_session.commit()

        monkeypatch.setattr(weekly_locks, "log_admin_action", lambda **kw: None)
        lines = [_line("KC", 10.0)]
        weekly_locks.lock_pool_week(
            db_session,
            pool,
            1,
            owner.id,
            games_provider=lambda db, week: [_game(datetime(2025, 9, 7, 17, 0))],
            line_freezer=lambda *a, **kw: lines,
        )

        pick = (
            db_session.query(models.Pick)
            .filter(models.Pick.entry_id == entry.id, models.Pick.week == 1)
            .one()
        )
        assert pick.team == "BUF"

    def test_all_used_skip_with_audit(self, db_session, monkeypatch):
        """All teams used -> AUTO_PICK_SKIPPED written when log_skipped_defaults=True."""
        owner, pool = self._setup(db_session)
        entry = _entry(db_session, pool_id=pool.id, user_id=owner.id, alive=True)
        _pick(db_session, entry_id=entry.id, week=0, team="KC", locked=True)
        db_session.commit()

        audit_calls = []
        monkeypatch.setattr(
            weekly_locks, "log_admin_action", lambda **kw: audit_calls.append(kw)
        )
        lines = [_line("KC", 5.0)]
        result = weekly_locks.lock_pool_week(
            db_session,
            pool,
            1,
            owner.id,
            games_provider=lambda db, week: [_game(datetime(2025, 9, 7, 17, 0))],
            line_freezer=lambda *a, **kw: lines,
            log_skipped_defaults=True,
        )

        assert result == 0
        assert any(c["action"] == "AUTO_PICK_SKIPPED" for c in audit_calls)

    def test_all_used_no_skip_audit_when_suppressed(self, db_session, monkeypatch):
        """log_skipped_defaults=False suppresses AUTO_PICK_SKIPPED audit."""
        owner, pool = self._setup(db_session)
        entry = _entry(db_session, pool_id=pool.id, user_id=owner.id, alive=True)
        _pick(db_session, entry_id=entry.id, week=0, team="KC", locked=True)
        db_session.commit()

        audit_calls = []
        monkeypatch.setattr(
            weekly_locks, "log_admin_action", lambda **kw: audit_calls.append(kw)
        )
        lines = [_line("KC", 5.0)]
        weekly_locks.lock_pool_week(
            db_session,
            pool,
            1,
            owner.id,
            games_provider=lambda db, week: [_game(datetime(2025, 9, 7, 17, 0))],
            line_freezer=lambda *a, **kw: lines,
            log_skipped_defaults=False,
        )

        assert not any(c["action"] == "AUTO_PICK_SKIPPED" for c in audit_calls)

    def test_owner_not_found_user_email_none(self, db_session, monkeypatch):
        """Entry owner absent from DB -> user_email=None; no crash."""
        owner, pool = self._setup(db_session)
        entry = models.Entry(
            id=str(uuid.uuid4()),
            pool_id=pool.id,
            user_id="ghost-id",
            name="Ghost",
            alive=True,
        )
        db_session.add(entry)
        db_session.commit()

        audit_calls = []
        monkeypatch.setattr(
            weekly_locks, "log_admin_action", lambda **kw: audit_calls.append(kw)
        )
        lines = [_line("NE", 3.0)]
        result = weekly_locks.lock_pool_week(
            db_session,
            pool,
            1,
            owner.id,
            games_provider=lambda db, week: [_game(datetime(2025, 9, 7, 17, 0))],
            line_freezer=lambda *a, **kw: lines,
        )

        assert result == 1
        auto = [c for c in audit_calls if c["action"] == "AUTO_PICK"]
        assert len(auto) == 1
        assert auto[0]["additional_data"]["user_email"] is None


# ---------------------------------------------------------------------------
# UC-3: process_due_weekly_locks
# ---------------------------------------------------------------------------


class TestProcessDueWeeklyLocks:
    def _setup_recurring_pool(self, db_session):
        owner = _user(db_session)
        db_session.flush()
        pool = _pool(
            db_session,
            pool_type="survivor",
            owner_id=owner.id,
            lock_day_of_week=6,
            lock_time_of_day=time(13, 0),
            lock_timezone="America/New_York",
        )
        db_session.add(pool)
        db_session.flush()
        return owner, pool

    def test_uc3_1_due_pool_with_unlocked_picks_calls_lock(
        self, db_session, monkeypatch
    ):
        """UC-3.1: deadline passed, unlocked picks exist -> lock_pool_week called; returns 1."""
        owner, pool = self._setup_recurring_pool(db_session)
        entry = _entry(db_session, pool_id=pool.id, user_id=owner.id, alive=True)
        db_session.commit()

        now = datetime(2025, 9, 14, 20, 0)
        monkeypatch.setattr(weekly_locks, "current_season_week", lambda db, current: 1)
        monkeypatch.setattr(
            weekly_locks,
            "current_season_games",
            lambda db, week: [_game(datetime(2025, 9, 7, 17, 0))],
        )
        monkeypatch.setattr(
            weekly_locks, "pool_week_lock_time", lambda p, g: now - timedelta(hours=1)
        )

        called = []
        monkeypatch.setattr(
            weekly_locks,
            "lock_pool_week",
            lambda db, p, week, actor_id, current, **kw: called.append(
                (p.id, week, actor_id, kw)
            ),
        )

        result = weekly_locks.process_due_weekly_locks(db_session, now)

        assert result == 1
        assert len(called) == 1
        assert called[0][2] == owner.id

    def test_uc3_2_all_already_locked_skip(self, db_session, monkeypatch):
        """UC-3.2: deadline passed but all picks already locked -> lock_pool_week NOT called."""
        owner, pool = self._setup_recurring_pool(db_session)
        entry = _entry(db_session, pool_id=pool.id, user_id=owner.id, alive=True)
        _pick(db_session, entry_id=entry.id, week=1, team="KC", locked=True)
        db_session.commit()

        now = datetime(2025, 9, 14, 20, 0)
        monkeypatch.setattr(weekly_locks, "current_season_week", lambda db, current: 1)
        monkeypatch.setattr(
            weekly_locks,
            "current_season_games",
            lambda db, week: [_game(datetime(2025, 9, 7, 17, 0))],
        )
        monkeypatch.setattr(
            weekly_locks, "pool_week_lock_time", lambda p, g: now - timedelta(hours=1)
        )

        called = []
        monkeypatch.setattr(
            weekly_locks,
            "lock_pool_week",
            lambda db, p, week, actor_id, current, **kw: called.append(True),
        )

        result = weekly_locks.process_due_weekly_locks(db_session, now)

        assert result == 0
        assert called == []

    def test_uc3_3_deadline_not_reached_skipped(self, db_session, monkeypatch):
        """UC-3.3: deadline not yet reached -> pool skipped; returns 0."""
        owner, pool = self._setup_recurring_pool(db_session)
        _entry(db_session, pool_id=pool.id, user_id=owner.id, alive=True)
        db_session.commit()

        now = datetime(2025, 9, 7, 10, 0)
        monkeypatch.setattr(weekly_locks, "current_season_week", lambda db, current: 1)
        monkeypatch.setattr(
            weekly_locks,
            "current_season_games",
            lambda db, week: [_game(datetime(2025, 9, 7, 17, 0))],
        )
        monkeypatch.setattr(
            weekly_locks, "pool_week_lock_time", lambda p, g: now + timedelta(hours=6)
        )

        called = []
        monkeypatch.setattr(
            weekly_locks,
            "lock_pool_week",
            lambda db, p, week, actor_id, current, **kw: called.append(True),
        )

        result = weekly_locks.process_due_weekly_locks(db_session, now)

        assert result == 0
        assert called == []

    def test_uc3_4_pool_without_recurring_config_excluded(
        self, db_session, monkeypatch
    ):
        """UC-3.4: no recurring lock config -> pool excluded from query."""
        owner = _user(db_session)
        db_session.flush()
        # Pool with no lock fields
        pool = _pool(db_session, pool_type="survivor", owner_id=owner.id)
        db_session.add(pool)
        _entry(db_session, pool_id=pool.id, user_id=owner.id, alive=True)
        db_session.commit()

        now = datetime(2025, 9, 14, 20, 0)
        monkeypatch.setattr(weekly_locks, "current_season_week", lambda db, current: 1)
        monkeypatch.setattr(
            weekly_locks,
            "current_season_games",
            lambda db, week: [_game(datetime(2025, 9, 7, 17, 0))],
        )

        called = []
        monkeypatch.setattr(
            weekly_locks,
            "lock_pool_week",
            lambda db, p, week, actor_id, current, **kw: called.append(True),
        )

        result = weekly_locks.process_due_weekly_locks(db_session, now)

        assert result == 0
        assert called == []

    def test_uc3_5_lock_time_none_pool_skipped(self, db_session, monkeypatch):
        """UC-3.5: pool_week_lock_time returns None -> pool skipped; returns 0."""
        owner, pool = self._setup_recurring_pool(db_session)
        _entry(db_session, pool_id=pool.id, user_id=owner.id, alive=True)
        db_session.commit()

        now = datetime(2025, 9, 14, 20, 0)
        monkeypatch.setattr(weekly_locks, "current_season_week", lambda db, current: 1)
        monkeypatch.setattr(weekly_locks, "current_season_games", lambda db, week: [])
        monkeypatch.setattr(weekly_locks, "pool_week_lock_time", lambda p, g: None)

        called = []
        monkeypatch.setattr(
            weekly_locks,
            "lock_pool_week",
            lambda db, p, week, actor_id, current, **kw: called.append(True),
        )

        result = weekly_locks.process_due_weekly_locks(db_session, now)

        assert result == 0
        assert called == []

    def test_uc3_6_multiple_due_pools_all_processed(self, db_session, monkeypatch):
        """UC-3.6: multiple due pools -> all processed; returns total count."""
        owner1 = _user(db_session)
        owner2 = _user(db_session)
        db_session.flush()
        pool1 = _pool(
            db_session,
            pool_type="survivor",
            owner_id=owner1.id,
            lock_day_of_week=6,
            lock_time_of_day=time(13, 0),
            lock_timezone="America/New_York",
        )
        pool2 = _pool(
            db_session,
            pool_type="survivor",
            owner_id=owner2.id,
            lock_day_of_week=6,
            lock_time_of_day=time(13, 0),
            lock_timezone="America/New_York",
        )
        db_session.add_all([pool1, pool2])
        db_session.flush()
        _entry(db_session, pool_id=pool1.id, user_id=owner1.id, alive=True)
        _entry(db_session, pool_id=pool2.id, user_id=owner2.id, alive=True)
        db_session.commit()

        now = datetime(2025, 9, 14, 20, 0)
        monkeypatch.setattr(weekly_locks, "current_season_week", lambda db, current: 1)
        monkeypatch.setattr(
            weekly_locks,
            "current_season_games",
            lambda db, week: [_game(datetime(2025, 9, 7, 17, 0))],
        )
        monkeypatch.setattr(
            weekly_locks, "pool_week_lock_time", lambda p, g: now - timedelta(hours=1)
        )

        called = []
        monkeypatch.setattr(
            weekly_locks,
            "lock_pool_week",
            lambda db, p, week, actor_id, current, **kw: called.append(p.id),
        )

        result = weekly_locks.process_due_weekly_locks(db_session, now)

        assert result == 2
        assert len(called) == 2

    def test_uc3_7_no_due_pools_returns_zero(self, db_session, monkeypatch):
        """UC-3.7: no due pools -> returns 0."""
        now = datetime(2025, 9, 14, 20, 0)
        monkeypatch.setattr(weekly_locks, "current_season_week", lambda db, current: 1)
        monkeypatch.setattr(weekly_locks, "current_season_games", lambda db, week: [])

        result = weekly_locks.process_due_weekly_locks(db_session, now)

        assert result == 0

    def test_uc3_8_now_defaults_to_current_utc(self, db_session, monkeypatch):
        """UC-3.8: now not provided -> defaults to current UTC time without crash."""
        monkeypatch.setattr(weekly_locks, "current_season_week", lambda db, current: 1)
        monkeypatch.setattr(weekly_locks, "current_season_games", lambda db, week: [])

        # Should not raise
        result = weekly_locks.process_due_weekly_locks(db_session)
        assert result == 0

    def test_uc3_9_uses_owner_id_as_actor(self, db_session, monkeypatch):
        """UC-3.9: lock_pool_week called with actor_id=pool.owner_id."""
        owner, pool = self._setup_recurring_pool(db_session)
        _entry(db_session, pool_id=pool.id, user_id=owner.id, alive=True)
        db_session.commit()

        now = datetime(2025, 9, 14, 20, 0)
        monkeypatch.setattr(weekly_locks, "current_season_week", lambda db, current: 1)
        monkeypatch.setattr(
            weekly_locks,
            "current_season_games",
            lambda db, week: [_game(datetime(2025, 9, 7, 17, 0))],
        )
        monkeypatch.setattr(
            weekly_locks, "pool_week_lock_time", lambda p, g: now - timedelta(hours=1)
        )

        called = []
        monkeypatch.setattr(
            weekly_locks,
            "lock_pool_week",
            lambda db, p, week, actor_id, current, **kw: called.append(actor_id),
        )

        weekly_locks.process_due_weekly_locks(db_session, now)

        assert called == [owner.id]

    def test_uc3_10_log_skipped_defaults_false_passed_through(
        self, db_session, monkeypatch
    ):
        """UC-3.10: lock_pool_week called with log_skipped_defaults=False."""
        owner, pool = self._setup_recurring_pool(db_session)
        _entry(db_session, pool_id=pool.id, user_id=owner.id, alive=True)
        db_session.commit()

        now = datetime(2025, 9, 14, 20, 0)
        monkeypatch.setattr(weekly_locks, "current_season_week", lambda db, current: 1)
        monkeypatch.setattr(
            weekly_locks,
            "current_season_games",
            lambda db, week: [_game(datetime(2025, 9, 7, 17, 0))],
        )
        monkeypatch.setattr(
            weekly_locks, "pool_week_lock_time", lambda p, g: now - timedelta(hours=1)
        )

        called = []
        monkeypatch.setattr(
            weekly_locks,
            "lock_pool_week",
            lambda db, p, week, actor_id, current, **kw: called.append(
                kw.get("log_skipped_defaults")
            ),
        )

        weekly_locks.process_due_weekly_locks(db_session, now)

        assert called == [False]

    def test_uc3_11_no_alive_entries_skipped(self, db_session, monkeypatch):
        """UC-3.11: pool with no alive entries -> unlocked_or_missing=False; skipped."""
        owner, pool = self._setup_recurring_pool(db_session)
        # Only eliminated entries
        _entry(db_session, pool_id=pool.id, user_id=owner.id, alive=False)
        db_session.commit()

        now = datetime(2025, 9, 14, 20, 0)
        monkeypatch.setattr(weekly_locks, "current_season_week", lambda db, current: 1)
        monkeypatch.setattr(
            weekly_locks,
            "current_season_games",
            lambda db, week: [_game(datetime(2025, 9, 7, 17, 0))],
        )
        monkeypatch.setattr(
            weekly_locks, "pool_week_lock_time", lambda p, g: now - timedelta(hours=1)
        )

        called = []
        monkeypatch.setattr(
            weekly_locks,
            "lock_pool_week",
            lambda db, p, week, actor_id, current, **kw: called.append(True),
        )

        result = weekly_locks.process_due_weekly_locks(db_session, now)

        assert result == 0
        assert called == []


# ---------------------------------------------------------------------------
# Integration: process_due_weekly_locks background sweep
# ---------------------------------------------------------------------------


class TestProcessDueWeeklyLocksBackgroundSweep:
    def _pool_with_entry(self, db_session, alive=True):
        owner = _user(db_session)
        db_session.flush()
        pool = _pool(
            db_session,
            pool_type="survivor",
            owner_id=owner.id,
            lock_day_of_week=6,
            lock_time_of_day=time(13, 0),
            lock_timezone="America/New_York",
        )
        db_session.add(pool)
        db_session.flush()
        entry = _entry(db_session, pool_id=pool.id, user_id=owner.id, alive=alive)
        db_session.commit()
        return owner, pool, entry

    def test_one_due_pool_fires_lock(self, db_session, monkeypatch):
        """One recurring pool past deadline with alive entry -> lock fires; returns 1."""
        owner, pool, entry = self._pool_with_entry(db_session)
        now = datetime(2025, 9, 14, 20, 0)
        monkeypatch.setattr(weekly_locks, "current_season_week", lambda db, current: 1)
        monkeypatch.setattr(
            weekly_locks,
            "current_season_games",
            lambda db, week: [_game(datetime(2025, 9, 7, 17, 0))],
        )
        monkeypatch.setattr(
            weekly_locks, "pool_week_lock_time", lambda p, g: now - timedelta(minutes=5)
        )

        called = []
        monkeypatch.setattr(
            weekly_locks,
            "lock_pool_week",
            lambda db, p, week, actor_id, current, **kw: called.append(p.id),
        )

        result = weekly_locks.process_due_weekly_locks(db_session, now)
        assert result == 1
        assert pool.id in called

    def test_two_due_pools_both_processed(self, db_session, monkeypatch):
        """Two due pools in same sweep -> both processed; returns 2."""
        owner1, pool1, _ = self._pool_with_entry(db_session)
        owner2, pool2, _ = self._pool_with_entry(db_session)

        now = datetime(2025, 9, 14, 20, 0)
        monkeypatch.setattr(weekly_locks, "current_season_week", lambda db, current: 1)
        monkeypatch.setattr(
            weekly_locks,
            "current_season_games",
            lambda db, week: [_game(datetime(2025, 9, 7, 17, 0))],
        )
        monkeypatch.setattr(
            weekly_locks, "pool_week_lock_time", lambda p, g: now - timedelta(minutes=5)
        )

        called = []
        monkeypatch.setattr(
            weekly_locks,
            "lock_pool_week",
            lambda db, p, week, actor_id, current, **kw: called.append(p.id),
        )

        result = weekly_locks.process_due_weekly_locks(db_session, now)
        assert result == 2

    def test_pool_without_recurring_fields_excluded(self, db_session, monkeypatch):
        """Pool without recurring lock fields not processed."""
        owner = _user(db_session)
        db_session.flush()
        pool = _pool(db_session, pool_type="survivor", owner_id=owner.id)
        db_session.add(pool)
        db_session.flush()
        _entry(db_session, pool_id=pool.id, user_id=owner.id, alive=True)
        db_session.commit()

        now = datetime(2025, 9, 14, 20, 0)
        monkeypatch.setattr(weekly_locks, "current_season_week", lambda db, current: 1)
        monkeypatch.setattr(
            weekly_locks,
            "current_season_games",
            lambda db, week: [_game(datetime(2025, 9, 7, 17, 0))],
        )

        called = []
        monkeypatch.setattr(
            weekly_locks,
            "lock_pool_week",
            lambda db, p, week, actor_id, current, **kw: called.append(True),
        )

        result = weekly_locks.process_due_weekly_locks(db_session, now)
        assert result == 0
        assert called == []

    def test_lock_time_none_skipped(self, db_session, monkeypatch):
        """pool_week_lock_time returns None -> pool skipped; returns 0."""
        _, pool, _ = self._pool_with_entry(db_session)
        now = datetime(2025, 9, 14, 20, 0)
        monkeypatch.setattr(weekly_locks, "current_season_week", lambda db, current: 1)
        monkeypatch.setattr(weekly_locks, "current_season_games", lambda db, week: [])
        monkeypatch.setattr(weekly_locks, "pool_week_lock_time", lambda p, g: None)

        called = []
        monkeypatch.setattr(
            weekly_locks,
            "lock_pool_week",
            lambda db, p, week, actor_id, current, **kw: called.append(True),
        )

        result = weekly_locks.process_due_weekly_locks(db_session, now)
        assert result == 0
        assert called == []

    def test_deadline_in_future_skipped(self, db_session, monkeypatch):
        """Pool whose deadline is in the future -> skipped; returns 0."""
        _, pool, _ = self._pool_with_entry(db_session)
        now = datetime(2025, 9, 7, 10, 0)
        monkeypatch.setattr(weekly_locks, "current_season_week", lambda db, current: 1)
        monkeypatch.setattr(
            weekly_locks,
            "current_season_games",
            lambda db, week: [_game(datetime(2025, 9, 7, 17, 0))],
        )
        monkeypatch.setattr(
            weekly_locks, "pool_week_lock_time", lambda p, g: now + timedelta(hours=5)
        )

        called = []
        monkeypatch.setattr(
            weekly_locks,
            "lock_pool_week",
            lambda db, p, week, actor_id, current, **kw: called.append(True),
        )

        result = weekly_locks.process_due_weekly_locks(db_session, now)
        assert result == 0
        assert called == []

    def test_all_alive_already_locked_skipped(self, db_session, monkeypatch):
        """Past deadline but all alive entries locked -> lock_pool_week not called."""
        owner, pool, entry = self._pool_with_entry(db_session)
        _pick(db_session, entry_id=entry.id, week=1, team="KC", locked=True)
        db_session.commit()

        now = datetime(2025, 9, 14, 20, 0)
        monkeypatch.setattr(weekly_locks, "current_season_week", lambda db, current: 1)
        monkeypatch.setattr(
            weekly_locks,
            "current_season_games",
            lambda db, week: [_game(datetime(2025, 9, 7, 17, 0))],
        )
        monkeypatch.setattr(
            weekly_locks, "pool_week_lock_time", lambda p, g: now - timedelta(hours=1)
        )

        called = []
        monkeypatch.setattr(
            weekly_locks,
            "lock_pool_week",
            lambda db, p, week, actor_id, current, **kw: called.append(True),
        )

        result = weekly_locks.process_due_weekly_locks(db_session, now)
        assert result == 0
        assert called == []

    def test_no_alive_entries_skipped(self, db_session, monkeypatch):
        """Pool with no alive entries -> skipped; lock_pool_week not called."""
        _, pool, _ = self._pool_with_entry(db_session, alive=False)
        now = datetime(2025, 9, 14, 20, 0)
        monkeypatch.setattr(weekly_locks, "current_season_week", lambda db, current: 1)
        monkeypatch.setattr(
            weekly_locks,
            "current_season_games",
            lambda db, week: [_game(datetime(2025, 9, 7, 17, 0))],
        )
        monkeypatch.setattr(
            weekly_locks, "pool_week_lock_time", lambda p, g: now - timedelta(hours=1)
        )

        called = []
        monkeypatch.setattr(
            weekly_locks,
            "lock_pool_week",
            lambda db, p, week, actor_id, current, **kw: called.append(True),
        )

        result = weekly_locks.process_due_weekly_locks(db_session, now)
        assert result == 0
        assert called == []

    def test_lock_pool_week_receives_owner_id_and_false(self, db_session, monkeypatch):
        """lock_pool_week receives actor_id=pool.owner_id and log_skipped_defaults=False."""
        owner, pool, _ = self._pool_with_entry(db_session)
        now = datetime(2025, 9, 14, 20, 0)
        monkeypatch.setattr(weekly_locks, "current_season_week", lambda db, current: 1)
        monkeypatch.setattr(
            weekly_locks,
            "current_season_games",
            lambda db, week: [_game(datetime(2025, 9, 7, 17, 0))],
        )
        monkeypatch.setattr(
            weekly_locks, "pool_week_lock_time", lambda p, g: now - timedelta(hours=1)
        )

        calls = []
        monkeypatch.setattr(
            weekly_locks,
            "lock_pool_week",
            lambda db, p, week, actor_id, current, **kw: calls.append(
                {
                    "actor_id": actor_id,
                    "log_skipped_defaults": kw.get("log_skipped_defaults"),
                }
            ),
        )

        weekly_locks.process_due_weekly_locks(db_session, now)

        assert len(calls) == 1
        assert calls[0]["actor_id"] == owner.id
        assert calls[0]["log_skipped_defaults"] is False

    def test_now_not_provided_no_crash(self, db_session, monkeypatch):
        """now not provided -> defaults to current UTC; no crash."""
        monkeypatch.setattr(weekly_locks, "current_season_week", lambda db, current: 1)
        monkeypatch.setattr(weekly_locks, "current_season_games", lambda db, week: [])

        result = weekly_locks.process_due_weekly_locks(db_session)
        assert result == 0


# ---------------------------------------------------------------------------
# Existing tests (preserved verbatim)
# ---------------------------------------------------------------------------


def test_due_recurring_pool_is_processed(db_session, monkeypatch):
    owner = models.User(
        id="weekly-worker-owner",
        email="weekly.worker@example.com",
        hashed_password="unused",
        is_active=True,
    )
    pool = models.Pool(
        id="weekly-worker-pool",
        name="Weekly Worker Pool",
        owner_id=owner.id,
        lock_day_of_week=6,
        lock_time_of_day=time(13, 0),
        lock_timezone="America/New_York",
    )
    entry = models.Entry(
        id="weekly-worker-entry",
        pool_id=pool.id,
        user_id=owner.id,
        name="Entry 1",
        alive=True,
    )
    db_session.add_all([owner, pool, entry])
    db_session.commit()

    called = []
    now = datetime.utcnow()
    monkeypatch.setattr(weekly_locks, "current_season_week", lambda db, current: 4)
    monkeypatch.setattr(
        weekly_locks, "current_season_games", lambda db, week: [object()]
    )
    monkeypatch.setattr(
        weekly_locks,
        "pool_week_lock_time",
        lambda candidate, games: now - timedelta(minutes=1),
    )
    monkeypatch.setattr(
        weekly_locks,
        "lock_pool_week",
        lambda db, candidate, week, actor_id, current, **kwargs: called.append(
            (candidate.id, week, actor_id, kwargs["log_skipped_defaults"])
        ),
    )

    assert weekly_locks.process_due_weekly_locks(db_session, now) == 1
    assert called == [(pool.id, 4, owner.id, False)]


def test_pickem_lock_freezes_submitted_games_without_autopicks(db_session):
    owner = models.User(
        id="pickem-lock-owner",
        email="pickem.lock@example.com",
        hashed_password="unused",
        is_active=True,
    )
    pool = models.Pool(
        id="pickem-lock-pool",
        name="Pick Em Lock",
        owner_id=owner.id,
        pool_type="pickem",
    )
    entry = models.Entry(
        id="pickem-lock-entry", pool_id=pool.id, user_id=owner.id, name="Card"
    )
    pick = models.Pick(
        id="pickem-lock-pick",
        entry_id=entry.id,
        week=2,
        game_id=2001,
        team="BUF",
        locked=False,
    )
    db_session.add_all([owner, pool, entry, pick])
    db_session.commit()

    created = weekly_locks.lock_pool_week(
        db_session,
        pool,
        2,
        owner.id,
        games_provider=lambda db, week: [],
        line_freezer=lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("Pick 'Em must not freeze spreads")
        ),
    )

    assert created == 0
    assert db_session.query(models.Pick).one().locked is True
    assert db_session.query(models.Pick).count() == 1


# ---------------------------------------------------------------------------
# Additional tests for process_due_weekly_locks edge cases
# (rmp-backend-weekly-locks-process-due-weekly-locks stub)
# ---------------------------------------------------------------------------


class TestProcessDueWeeklyLocksEdgeCases:
    """Edge-case coverage for process_due_weekly_locks."""

    def _base_pool(self, owner_id, pool_id="pdwl-pool"):
        """Return a Pool with recurring lock configuration."""
        return models.Pool(
            id=pool_id,
            name="PDWL Pool",
            owner_id=owner_id,
            pool_type="survivor",
            lock_day_of_week=2,  # Tuesday
            lock_time_of_day=__import__("datetime").time(17, 0, 0),
            lock_timezone="America/New_York",
        )

    def test_no_pools_with_recurring_lock_returns_zero(self, db_session):
        """process_due_weekly_locks returns 0 when no pool has recurring lock config."""
        import weekly_locks

        owner = models.User(
            id="pdwl-owner-0", email="pdwl0@example.com", hashed_password="x"
        )
        pool = models.Pool(
            id="pdwl-no-config", name="NC", owner_id=owner.id, pool_type="survivor"
        )
        db_session.add_all([owner, pool])
        db_session.commit()

        result = weekly_locks.process_due_weekly_locks(
            db_session, now=__import__("datetime").datetime(2026, 9, 15, 20, 0, 0)
        )
        assert result == 0

    def test_future_deadline_not_processed(self, db_session):
        """Pool whose deadline is in the future is not processed."""
        import weekly_locks
        from datetime import datetime

        owner = models.User(
            id="pdwl-owner-1", email="pdwl1@example.com", hashed_password="x"
        )
        pool = self._base_pool(owner.id, "pdwl-future")
        db_session.add_all([owner, pool])
        db_session.commit()

        # Call with a time far in the past — before any Tuesday 17:00 ET deadline
        result = weekly_locks.process_due_weekly_locks(
            db_session, now=datetime(2026, 9, 1, 0, 0, 0)
        )
        assert result == 0

    def test_all_entries_already_locked_returns_zero(self, db_session):
        """If all entries already have locked picks, processed count is 0."""
        import weekly_locks
        from datetime import datetime

        owner = models.User(
            id="pdwl-owner-2", email="pdwl2@example.com", hashed_password="x"
        )
        pool = self._base_pool(owner.id, "pdwl-locked")
        home = models.Team(id=301, name="Home PDWL", abbrv="HPD")
        away = models.Team(id=302, name="Away PDWL", abbrv="APD")
        entry = models.Entry(
            id="pdwl-e1", pool_id=pool.id, user_id=owner.id, name="E1", alive=True
        )
        # Schedule a game for week 1, 2026-09-10 13:00 UTC
        game = models.Schedule(
            game_id=88001,
            season=2026,
            week_num=1,
            home_team_id=home.id,
            away_team_id=away.id,
            start_time=datetime(2026, 9, 10, 13),
        )
        pick = models.Pick(
            id="pdwl-pick-1", entry_id=entry.id, week=1, team="HPD", locked=True
        )
        db_session.add_all([owner, pool, home, away, entry, game, pick])
        db_session.commit()

        # Call after deadline — Tuesday 2026-09-08 22:00 UTC (17:00 ET + 5)
        result = weekly_locks.process_due_weekly_locks(
            db_session, now=datetime(2026, 9, 8, 22, 0, 0)
        )
        # Entry pick is already locked — no re-processing needed
        assert result == 0
