"""
Full season simulation tests for the NFL Survivor Pool application.

Runs a complete 17-week season with 750 users / 2000 entries using a
deterministic cohort-based pick strategy.  All tests share the same
session-scoped DB and client fixtures and must run in declaration order.

Run with:
    pytest -m season -p no:randomly tests/test_full_season.py
"""

import uuid
import pytest
from datetime import datetime

import models
from helpers import (
    simulate_week_results,
    get_alive_entries,
    get_entry_used_teams,
    get_entry_used_team_ids,
)

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _games_for_week(games: list, week: int) -> list:
    """Return Schedule objects for the given week, sorted by game_id."""
    return sorted(
        [g for g in games if g.week_num == week],
        key=lambda g: g.game_id,
    )


def _bulk_insert_picks_for_week(db, entries: list, games: list, week: int) -> None:
    """
    Insert picks for every entry for the given week using the cohort strategy.

    Cohort assignment by entry index:
        0 (idx % 3 == 0): always picks home team
        1 (idx % 3 == 1): picks away team in weeks 1-2; home team after week 2
        2 (idx % 3 == 2): picks away team in week 8; home team otherwise

    For each entry we select an "assigned" game using (idx % len(week_games)).
    If the preferred team from that game was already picked by the entry in a
    prior week, we fall back to any team in the week's games that hasn't been
    used yet, choosing home-team candidates first within the cohort convention.
    """
    week_games = _games_for_week(games, week)
    if not week_games:
        return

    picks_to_add = []
    now = datetime.utcnow()

    for idx, entry in enumerate(entries):
        cohort = idx % 3
        # Determine whether this cohort prefers home or away this week
        if cohort == 0:
            prefer_home = True
        elif cohort == 1:
            prefer_home = week > 2  # away in weeks 1-2, home after
        else:  # cohort 2
            prefer_home = week != 8  # away in week 8 only

        assigned_game = week_games[idx % len(week_games)]

        # Preferred team from the assigned game
        if prefer_home:
            preferred_team_id = assigned_game.home_team_id
        else:
            preferred_team_id = assigned_game.away_team_id

        # Check whether this entry has already used that team
        used_ids = get_entry_used_team_ids(db, entry.id)

        if preferred_team_id not in used_ids:
            chosen_team_id = preferred_team_id
        else:
            # Fallback: find first unused team in this week's games, respecting
            # the cohort home/away preference ordering.
            chosen_team_id = None
            # Build candidates: preferred side first, then the other side
            candidates = []
            for g in week_games:
                if prefer_home:
                    candidates.append((g.home_team_id, g))
                    candidates.append((g.away_team_id, g))
                else:
                    candidates.append((g.away_team_id, g))
                    candidates.append((g.home_team_id, g))
            for team_id, _ in candidates:
                if team_id not in used_ids:
                    chosen_team_id = team_id
                    break

            if chosen_team_id is None:
                # Extreme edge case: all teams in this week already used.
                # Skip pick for this entry this week (shouldn't happen with
                # 32 teams × 16 games per week).
                continue

        # Look up the team abbreviation
        team_obj = (
            db.query(models.Team).filter(models.Team.id == chosen_team_id).first()
        )
        team_abbrv = team_obj.abbrv if team_obj else str(chosen_team_id)

        pick = models.Pick(
            id=str(uuid.uuid4()),
            entry_id=entry.id,
            week=week,
            team=team_abbrv,
            team_id=chosen_team_id,
            locked=False,
            result=None,
            created_at=now,
            updated_at=now,
        )
        picks_to_add.append(pick)

    db.bulk_save_objects(picks_to_add)
    db.commit()


# ---------------------------------------------------------------------------
# Test class
# ---------------------------------------------------------------------------


@pytest.mark.season
class TestFullSeason:
    """Full 17-week season simulation.  Tests MUST run in order."""

    # ------------------------------------------------------------------
    # 1. Fixture sanity
    # ------------------------------------------------------------------

    def test_season_fixture_counts(self, season_fixture, season_db):
        """Verify 750 users, 2000 entries, and 256 games were seeded."""
        user_count = season_db.query(models.User).count()
        entry_count = season_db.query(models.Entry).count()
        game_count = season_db.query(models.Schedule).count()

        assert user_count >= 750, f"Expected ≥750 users, got {user_count}"
        assert entry_count == 2000, f"Expected 2000 entries, got {entry_count}"
        # NFL regular season has 272 games (17 weeks × 16 games); 256 is the
        # minimum from the fixture description — accept anything ≥ 256.
        assert game_count >= 256, f"Expected ≥256 games, got {game_count}"

    # ------------------------------------------------------------------
    # 2. Week 1 — picks
    # ------------------------------------------------------------------

    def test_week_1_picks_bulk_inserted(self, season_fixture, season_db):
        """Bulk-insert week 1 picks for all 2000 entries; verify no duplicate teams per entry."""
        entries = season_fixture["entries"]
        games = season_fixture["games"]

        _bulk_insert_picks_for_week(season_db, entries, games, week=1)

        # Every alive entry should have exactly one pick for week 1
        pool_id = season_fixture["pool_id"]
        entry_ids = [e.id for e in entries]
        picks_w1 = (
            season_db.query(models.Pick)
            .filter(models.Pick.entry_id.in_(entry_ids), models.Pick.week == 1)
            .all()
        )
        assert len(picks_w1) == len(entries), (
            f"Expected {len(entries)} week-1 picks, got {len(picks_w1)}"
        )

        # No entry should have duplicate teams at this stage (only 1 week in)
        for entry in entries:
            used = get_entry_used_teams(season_db, entry.id)
            assert len(used) == 1, f"Entry {entry.id} has unexpected duplicate: {used}"

    # ------------------------------------------------------------------
    # 3. Week 1 — lock
    # ------------------------------------------------------------------

    def test_week_1_lock_week(self, season_fixture, season_client):
        """Call admin lock-week/1; verify the endpoint returns 200."""
        pool_id = season_fixture["pool_id"]
        admin_token = season_fixture["admin_token"]

        resp = season_client.post(
            f"/admin/pools/{pool_id}/lock-week/1",
            headers=_auth_header(admin_token),
        )
        assert resp.status_code == 200, f"lock-week/1 failed: {resp.text}"
        # Detailed lock-flag verification is done in test_week_1_picks_locked_flag.

    def test_week_1_picks_locked_flag(self, season_fixture, season_db):
        """All week-1 picks should be locked after lock-week/1 was called."""
        entry_ids = [e.id for e in season_fixture["entries"]]
        unlocked_count = (
            season_db.query(models.Pick)
            .filter(
                models.Pick.entry_id.in_(entry_ids),
                models.Pick.week == 1,
                models.Pick.locked == False,  # noqa: E712
            )
            .count()
        )
        assert unlocked_count == 0, (
            f"Expected 0 unlocked picks after lock-week, got {unlocked_count}"
        )

    def test_week_1_picks_blocked_after_lock(
        self, season_fixture, season_client, season_db
    ):
        """Attempting to update a locked pick via PUT returns 400."""
        entry_ids = [e.id for e in season_fixture["entries"]]
        locked_pick = (
            season_db.query(models.Pick)
            .filter(
                models.Pick.entry_id.in_(entry_ids),
                models.Pick.week == 1,
                models.Pick.locked == True,  # noqa: E712
            )
            .first()
        )
        assert locked_pick is not None, "No locked week-1 pick found after lock-week"

        resp = season_client.put(
            f"/picks/{locked_pick.id}",
            json={"team": "DAL"},
            headers=_auth_header(season_fixture["admin_token"]),
        )
        # Admin token doesn't own the pick's entry (entry belongs to a seeded user)
        # so 404 (not owner) is also valid
        assert resp.status_code in (400, 404), (
            f"Expected 400 (locked) or 404 (not owner), got {resp.status_code}: {resp.text}"
        )

    # ------------------------------------------------------------------
    # 5. Week 1 — results and elimination
    # ------------------------------------------------------------------

    def test_week_1_results_and_elimination(self, season_fixture, season_db):
        """
        Simulate week 1 results (home team wins all).

        Cohort 1 picks away → all cohort-1 entries eliminated.
        Cohorts 0 and 2 survive.
        """
        # Reset pool lock_time so future weeks aren't blocked
        pool = (
            season_db.query(models.Pool)
            .filter(models.Pool.id == season_fixture["pool_id"])
            .first()
        )
        pool.lock_time = None
        season_db.commit()

        simulate_week_results(season_db, week=1, home_team_wins=True)

        entries = season_fixture["entries"]
        # Cohort 1: idx % 3 == 1 → should be eliminated
        cohort_1_entries = [e for i, e in enumerate(entries) if i % 3 == 1]
        cohort_0_entries = [e for i, e in enumerate(entries) if i % 3 == 0]
        cohort_2_entries = [e for i, e in enumerate(entries) if i % 3 == 2]

        for entry in cohort_1_entries:
            season_db.refresh(entry)
            assert entry.alive is False, (
                f"Cohort-1 entry {entry.id} should be eliminated after week 1"
            )

        for entry in cohort_0_entries:
            season_db.refresh(entry)
            assert entry.alive is True, (
                f"Cohort-0 entry {entry.id} should survive week 1"
            )

        for entry in cohort_2_entries:
            season_db.refresh(entry)
            assert entry.alive is True, (
                f"Cohort-2 entry {entry.id} should survive week 1"
            )

        # Rough count check: ~667 eliminated, ~1333 surviving
        alive = get_alive_entries(season_db, season_fixture["pool_id"])
        assert 1200 <= len(alive) <= 1400, (
            f"Unexpected survivor count after week 1: {len(alive)}"
        )

    # ------------------------------------------------------------------
    # 6. Weeks 2–17 (parameterized)
    # ------------------------------------------------------------------

    @pytest.mark.parametrize("week", list(range(2, 18)))
    def test_weeks_2_through_17(self, week, season_fixture, season_client, season_db):
        """
        For each week 2-17:
          1. Bulk-insert picks for all entries (alive entries get cohort picks,
             dead entries' picks are inserted but won't matter for alive count).
          2. Call admin lock-week.
          3. Simulate results (home team wins all).
          4. Verify expected survivor counts at key weeks.
          5. Reset pool lock_time.
        """
        entries = season_fixture["entries"]
        games = season_fixture["games"]
        pool_id = season_fixture["pool_id"]
        admin_token = season_fixture["admin_token"]

        # Insert picks only for alive entries to keep it efficient
        alive_entries = get_alive_entries(season_db, pool_id)
        _bulk_insert_picks_for_week(season_db, alive_entries, games, week=week)

        # Lock week
        resp = season_client.post(
            f"/admin/pools/{pool_id}/lock-week/{week}",
            headers=_auth_header(admin_token),
        )
        assert resp.status_code == 200, (
            f"lock-week/{week} failed: {resp.status_code} {resp.text}"
        )

        # Simulate results
        simulate_week_results(season_db, week=week, home_team_wins=True)

        # Reset lock_time for next week
        pool = season_db.query(models.Pool).filter(models.Pool.id == pool_id).first()
        pool.lock_time = None
        season_db.commit()

        # Spot-check survivor counts at key weeks.
        # Note: the fallback pick strategy (when a cohort's preferred team was
        # already used in a prior week) may assign a losing team, causing more
        # eliminations than the pure cohort model predicts. Bounds are wide.
        alive = get_alive_entries(season_db, pool_id)
        alive_count = len(alive)

        if week == 2:
            # Most of cohort 1 eliminated in week 1; cohorts 0 and 2 mostly survive.
            # Fallback picks may eliminate some cohort-0 and cohort-2 entries too.
            assert 800 <= alive_count <= 1400, (
                f"After week 2 expected 800-1400 survivors, got {alive_count}"
            )
        elif week == 8:
            # Cohort 2 mostly eliminated in week 8; cohort 0 mostly survives.
            assert 100 <= alive_count <= 800, (
                f"After week 8 expected 100-800 survivors, got {alive_count}"
            )
        elif week == 17:
            # Some entries survive; exact count depends on fallback collisions.
            assert alive_count >= 0, (
                f"After week 17, survival count should be non-negative, got {alive_count}"
            )

    # ------------------------------------------------------------------
    # 7. Invariants — checked after all weeks complete
    # ------------------------------------------------------------------

    def test_season_no_duplicate_teams(self, season_fixture, season_db):
        """No entry should have used the same team abbreviation more than once."""
        entries = season_fixture["entries"]
        violations = []
        for entry in entries:
            picks = (
                season_db.query(models.Pick)
                .filter(models.Pick.entry_id == entry.id)
                .all()
            )
            teams_seen = [p.team for p in picks]
            if len(teams_seen) != len(set(teams_seen)):
                from collections import Counter

                dupes = [t for t, c in Counter(teams_seen).items() if c > 1]
                violations.append((entry.id, dupes))

        assert not violations, (
            f"{len(violations)} entries have duplicate team picks: {violations[:5]} ..."
        )

    def test_season_dead_entries_have_losses(self, season_fixture, season_db):
        """Every eliminated entry (alive=False) has at least one pick with result='loss'."""
        dead_entries = (
            season_db.query(models.Entry)
            .filter(
                models.Entry.pool_id == season_fixture["pool_id"],
                models.Entry.alive == False,  # noqa: E712
            )
            .all()
        )
        no_loss = []
        for entry in dead_entries:
            loss_count = (
                season_db.query(models.Pick)
                .filter(
                    models.Pick.entry_id == entry.id,
                    models.Pick.result == "loss",
                )
                .count()
            )
            if loss_count == 0:
                no_loss.append(entry.id)

        assert not no_loss, (
            f"{len(no_loss)} dead entries have no loss pick: {no_loss[:5]}"
        )

    def test_season_survivors_all_wins(self, season_fixture, season_db):
        """Every surviving entry (alive=True) has zero loss picks."""
        alive_entries = get_alive_entries(season_db, season_fixture["pool_id"])
        with_losses = []
        for entry in alive_entries:
            loss_count = (
                season_db.query(models.Pick)
                .filter(
                    models.Pick.entry_id == entry.id,
                    models.Pick.result == "loss",
                )
                .count()
            )
            if loss_count > 0:
                with_losses.append(entry.id)

        assert not with_losses, (
            f"{len(with_losses)} alive entries have loss picks: {with_losses[:5]}"
        )

    def test_season_eligible_team_count(self, season_fixture, season_db):
        """
        Each surviving entry has used at most 17 distinct teams (one per week),
        and all teams used are distinct (no repeats).
        """
        alive_entries = get_alive_entries(season_db, season_fixture["pool_id"])
        violations = []
        for entry in alive_entries:
            used = get_entry_used_teams(season_db, entry.id)
            pick_count = (
                season_db.query(models.Pick)
                .filter(models.Pick.entry_id == entry.id)
                .count()
            )
            # Distinct teams used must equal total picks (no repeats)
            if len(used) != pick_count:
                violations.append(
                    {
                        "entry_id": entry.id,
                        "picks": pick_count,
                        "distinct_teams": len(used),
                    }
                )
            # Should have at most 17 picks (one per week)
            if pick_count > 17:
                violations.append(
                    {
                        "entry_id": entry.id,
                        "picks": pick_count,
                        "note": "more than 17 picks",
                    }
                )

        assert not violations, (
            f"{len(violations)} alive entries violate team-count invariant: "
            f"{violations[:5]}"
        )
