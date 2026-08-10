"""
Tests for team eligibility / uniqueness rules in NFL Survivor Pool picks.

Rule: A team is consumed forever for a given entry the moment a pick is created
for that team, regardless of result (win, loss, or unresolved). Uniqueness is
scoped to the entry — not the user or the pool.
"""

import pytest
import models

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

NFL_TEAMS_17 = [
    "NE",
    "KC",
    "GB",
    "DAL",
    "PHI",
    "ATL",
    "SF",
    "SEA",
    "DEN",
    "MIA",
    "BUF",
    "PIT",
    "BAL",
    "HOU",
    "MIN",
    "TEN",
    "LAC",
]


def _reg(client, email, password="Pass1234!"):
    """Register and log in a user; return the access token."""
    client.post("/auth/register", json={"email": email, "password": password})
    resp = client.post("/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    return resp.json()["access_token"]


def _h(token):
    """Return an Authorization header dict for the given bearer token."""
    return {"Authorization": f"Bearer {token}"}


def _create_pool(client, token, name="Test Pool"):
    """Create a pool and return its id."""
    resp = client.post(
        "/pools/create",
        json={"name": name, "description": "test", "is_private": False},
        headers=_h(token),
    )
    assert resp.status_code == 200, f"Pool creation failed: {resp.text}"
    return resp.json()["id"]


def _create_entry(client, token, pool_id, name="My Entry"):
    """Create an entry in the given pool and return its id."""
    resp = client.post(
        "/entries/create",
        json={"pool_id": pool_id, "name": name},
        headers=_h(token),
    )
    assert resp.status_code == 200, f"Entry creation failed: {resp.text}"
    return resp.json()["id"]


def _create_pick(client, token, entry_id, week, team):
    """POST /picks/create and return the full response."""
    return client.post(
        "/picks/create",
        json={"entry_id": entry_id, "week": week, "team": team},
        headers=_h(token),
    )


def _update_pick(client, token, pick_id, team):
    """PUT /picks/{pick_id} with a new team and return the full response."""
    return client.put(
        f"/picks/{pick_id}",
        json={"team": team},
        headers=_h(token),
    )


def _set_result(db_session, pick_id, result):
    """Directly set Pick.result via the db_session (simulates score ingestion)."""
    pick = db_session.query(models.Pick).filter(models.Pick.id == pick_id).one()
    pick.result = result
    db_session.commit()
    db_session.refresh(pick)


# ---------------------------------------------------------------------------
# Test class
# ---------------------------------------------------------------------------


class TestTeamEligibility:
    """
    Integration tests for the per-entry team uniqueness rule.

    A team abbreviation may only appear once in an entry's pick history.
    The result of the pick (win, loss, or None) does not affect eligibility —
    the team is consumed the moment the pick is recorded.
    """

    def test_duplicate_team_after_win(self, client, db_session):
        """
        Picking a team in week 1 with result='win' and then attempting to pick
        the same team in week 2 for the same entry must return HTTP 400 with
        the expected error message.

        Verifies that a winning pick still consumes the team permanently.
        """
        token = _reg(client, "elig_win@example.com")
        pool_id = _create_pool(client, token)
        entry_id = _create_entry(client, token, pool_id)

        # Week 1: pick NE
        resp = _create_pick(client, token, entry_id, week=1, team="NE")
        assert resp.status_code == 200, f"Initial pick failed: {resp.text}"
        pick_id = resp.json()["id"]

        # Simulate score ingestion: NE wins week 1
        _set_result(db_session, pick_id, "win")

        # Week 2: attempt to pick NE again — must be rejected
        resp2 = _create_pick(client, token, entry_id, week=2, team="NE")
        assert resp2.status_code == 400, (
            f"Expected 400, got {resp2.status_code}: {resp2.text}"
        )
        assert "already been selected" in resp2.json()["detail"], resp2.json()

    def test_duplicate_team_after_loss(self, client, db_session):
        """
        Picking a team in week 1 with result='loss' and then attempting to pick
        the same team in week 2 for the same entry must return HTTP 400.

        A losing pick still consumes the team — the entry may be eliminated, but
        the rule is enforced regardless of alive status.
        """
        token = _reg(client, "elig_loss@example.com")
        pool_id = _create_pool(client, token)
        entry_id = _create_entry(client, token, pool_id)

        resp = _create_pick(client, token, entry_id, week=1, team="KC")
        assert resp.status_code == 200, f"Initial pick failed: {resp.text}"
        pick_id = resp.json()["id"]

        _set_result(db_session, pick_id, "loss")

        resp2 = _create_pick(client, token, entry_id, week=2, team="KC")
        assert resp2.status_code == 400, (
            f"Expected 400, got {resp2.status_code}: {resp2.text}"
        )
        assert "already been selected" in resp2.json()["detail"], resp2.json()

    def test_duplicate_team_unresolved(self, client, db_session):
        """
        Picking a team in week 1 with result=None (game not yet played) and
        then attempting to pick the same team in week 2 must return HTTP 400.

        The uniqueness check applies even before the game outcome is known.
        """
        token = _reg(client, "elig_unresolved@example.com")
        pool_id = _create_pool(client, token)
        entry_id = _create_entry(client, token, pool_id)

        resp = _create_pick(client, token, entry_id, week=1, team="GB")
        assert resp.status_code == 200, f"Initial pick failed: {resp.text}"
        # result stays None — no _set_result call

        resp2 = _create_pick(client, token, entry_id, week=2, team="GB")
        assert resp2.status_code == 400, (
            f"Expected 400, got {resp2.status_code}: {resp2.text}"
        )
        assert "already been selected" in resp2.json()["detail"], resp2.json()

    def test_uniqueness_is_per_entry_not_per_user_same_week(self, client, db_session):
        """
        One user with two entries in the same pool may pick the same team in the
        same week across those entries — uniqueness is per-entry, not per-user.

        Entry A picks 'NE' in week 1 → HTTP 200.
        Entry B picks 'NE' in week 1 → HTTP 200 (different entry, team not consumed).
        """
        token = _reg(client, "elig_two_entries_same_week@example.com")
        pool_id = _create_pool(client, token)
        entry_a = _create_entry(client, token, pool_id, name="Entry A")
        entry_b = _create_entry(client, token, pool_id, name="Entry B")

        resp_a = _create_pick(client, token, entry_a, week=1, team="NE")
        assert resp_a.status_code == 200, f"Entry A pick failed: {resp_a.text}"

        resp_b = _create_pick(client, token, entry_b, week=1, team="NE")
        assert resp_b.status_code == 200, (
            f"Entry B pick should succeed (different entry); got {resp_b.status_code}: {resp_b.text}"
        )

    def test_uniqueness_is_per_entry_not_per_user_different_weeks(
        self, client, db_session
    ):
        """
        One user with two entries may pick the same team in different weeks
        across those entries — the uniqueness scope is strictly per entry.

        Entry A picks 'NE' in week 1 → HTTP 200.
        Entry B picks 'NE' in week 2 → HTTP 200 (different entry).
        """
        token = _reg(client, "elig_two_entries_diff_weeks@example.com")
        pool_id = _create_pool(client, token)
        entry_a = _create_entry(client, token, pool_id, name="Entry A")
        entry_b = _create_entry(client, token, pool_id, name="Entry B")

        resp_a = _create_pick(client, token, entry_a, week=1, team="NE")
        assert resp_a.status_code == 200, f"Entry A pick failed: {resp_a.text}"

        resp_b = _create_pick(client, token, entry_b, week=2, team="NE")
        assert resp_b.status_code == 200, (
            f"Entry B pick should succeed (different entry); got {resp_b.status_code}: {resp_b.text}"
        )

    def test_update_pick_to_already_used_team(self, client, db_session):
        """
        Updating an existing pick (week 2) via PUT /picks/{id} to a team that
        has already been used in week 1 by the same entry must return HTTP 400
        with the expected error message.

        This ensures the uniqueness check also applies to edits.
        """
        token = _reg(client, "elig_put_duplicate@example.com")
        pool_id = _create_pool(client, token)
        entry_id = _create_entry(client, token, pool_id)

        # Week 1: pick NE
        resp1 = _create_pick(client, token, entry_id, week=1, team="NE")
        assert resp1.status_code == 200, f"Week 1 pick failed: {resp1.text}"

        # Week 2: pick KC (valid)
        resp2 = _create_pick(client, token, entry_id, week=2, team="KC")
        assert resp2.status_code == 200, f"Week 2 pick failed: {resp2.text}"
        week2_pick_id = resp2.json()["id"]

        # Attempt to update week 2 pick to NE (already used in week 1)
        resp3 = _update_pick(client, token, week2_pick_id, team="NE")
        assert resp3.status_code == 400, (
            f"Expected 400, got {resp3.status_code}: {resp3.text}"
        )
        assert "already been selected" in resp3.json()["detail"], resp3.json()

    def test_update_pick_to_unused_team_succeeds(self, client, db_session):
        """
        Updating a pick via PUT /picks/{id} to a team that has NOT been used
        elsewhere in the entry must return HTTP 200.

        This verifies that valid edits are not incorrectly blocked.
        """
        token = _reg(client, "elig_put_valid@example.com")
        pool_id = _create_pool(client, token)
        entry_id = _create_entry(client, token, pool_id)

        # Week 1: pick NE
        resp1 = _create_pick(client, token, entry_id, week=1, team="NE")
        assert resp1.status_code == 200, f"Week 1 pick failed: {resp1.text}"
        week1_pick_id = resp1.json()["id"]

        # Update week 1 pick to GB (unused)
        resp2 = _update_pick(client, token, week1_pick_id, team="GB")
        assert resp2.status_code == 200, (
            f"Updating to unused team should succeed; got {resp2.status_code}: {resp2.text}"
        )

    def test_no_repeated_teams_in_db_after_multiple_picks(self, client, db_session):
        """
        After creating K picks for a single entry (all different teams), verify
        that the Pick rows in the database contain K distinct team values with no
        repeats.

        Uses 5 picks as a representative sample.
        """
        token = _reg(client, "elig_distinct_5@example.com")
        pool_id = _create_pool(client, token)
        entry_id = _create_entry(client, token, pool_id)

        teams_used = NFL_TEAMS_17[:5]
        created_ids = []
        for week, team in enumerate(teams_used, start=1):
            resp = _create_pick(client, token, entry_id, week=week, team=team)
            assert resp.status_code == 200, f"Pick week {week} failed: {resp.text}"
            created_ids.append(resp.json()["id"])

        # Query the DB directly and verify no duplicate teams
        picks = (
            db_session.query(models.Pick).filter(models.Pick.id.in_(created_ids)).all()
        )
        recorded_teams = [p.team for p in picks]
        assert len(recorded_teams) == len(set(recorded_teams)), (
            f"Duplicate teams found in DB: {recorded_teams}"
        )

    def test_17_picks_all_different_teams_succeed(self, client, db_session):
        """
        Creating 17 picks for a single entry — one per NFL week — each with a
        distinct team abbreviation must all return HTTP 200, and the database
        must contain exactly 17 picks with 17 distinct team values.

        This exercises the full regular-season survivor pool scenario for one
        entry that never repeats a team.
        """
        token = _reg(client, "elig_17_picks@example.com")
        pool_id = _create_pool(client, token)
        entry_id = _create_entry(client, token, pool_id)

        assert len(NFL_TEAMS_17) == 17, "Test setup error: expected exactly 17 teams"

        created_ids = []
        for week, team in enumerate(NFL_TEAMS_17, start=1):
            resp = _create_pick(client, token, entry_id, week=week, team=team)
            assert resp.status_code == 200, (
                f"Pick week {week} team {team} failed: {resp.status_code} {resp.text}"
            )
            created_ids.append(resp.json()["id"])

        assert len(created_ids) == 17, (
            f"Expected 17 picks created, got {len(created_ids)}"
        )

        picks = (
            db_session.query(models.Pick).filter(models.Pick.id.in_(created_ids)).all()
        )
        assert len(picks) == 17, f"Expected 17 Pick rows, found {len(picks)}"

        recorded_teams = [p.team for p in picks]
        assert len(set(recorded_teams)) == 17, (
            f"Expected 17 distinct teams, got duplicates: {recorded_teams}"
        )
