# Design: comprehensive-test-suite

A full correctness test suite for the RunMyPool NFL survivor pool platform covering a 17-week season simulation with 750 users and 2000 entries, lock time enforcement, team eligibility, Lambda-driven elimination, message board access rules, audit trail coverage, and security edge cases.

## Context

The existing test suite has 138 tests at 80% coverage using pytest with SQLite in-memory. It validates basic CRUD but does not cover the full survivor season lifecycle, per-game lock time semantics, Lambda elimination flow, or the known security gaps documented in TESTING.md.

The backend is FastAPI + SQLAlchemy (declarative ORM) running against SQLite in tests. The Lambda function (`lambda/src/nfl_game_updater.py`) is a separate AWS process that polls ESPN and writes game results and elimination state. It is not accessible via HTTP in tests — its internal functions must be called directly or replicated in test helpers.

All existing tests use `TestClient` from `starlette.testclient` and a shared `conftest.py` that creates an in-memory SQLite DB per test. The new suite extends this infrastructure, adds session-scoped fixtures for the large-scale season simulation, and introduces time-mocking via `unittest.mock.patch`.

No `docs/dev/architecture.md` exists in the project.

## References

- `rmp/backend/tests/conftest.py` — Existing fixture structure: `client`, `db_session`, `authenticated_client`, `setup_test_env`.
- `rmp/backend/picks.py` — Pick upsert, team uniqueness enforcement, lock enforcement (Pick.locked only).
- `rmp/backend/entries.py` — Entry lock_time enforcement (pool.lock_time vs now).
- `rmp/backend/admin.py` — Auto-pick algorithm (popularity-ranked, alpha tie-break), lock-week logic.
- `rmp/backend/audit_utils.py` — `create_audit_log`, `log_create_operation`, `log_admin_action` etc.
- `rmp/backend/message_board.py` — Rate limit window, pool membership gate, content constraints.
- `lambda/src/nfl_game_updater.py` — Game result update logic and `eliminate_losing_entries()`.
- `rmp/backend/nfl-schedule-2025.json` — 2025 regular season: 17 weeks, 256 games, 32 teams.

## Goals / Non-Goals

**Goals:**

- Session-scoped fixture seeding 750 users, 2000 entries, and the full 2025 regular season schedule
- `simulate_game_result()` helper replicating Lambda logic without AWS or HTTP
- `advance_time()` context manager for deterministic lock-time boundary testing
- 17-week season simulation with deterministic pick strategies and game results
- Season-end global invariant assertions
- Full lock time layer coverage: pool.lock_time, Pick.locked, per-game start_time gap documentation
- Team eligibility invariant tests: any pick (win or loss) consumes a team forever, per-entry scope
- Elimination tests: loss → alive=False, auto-pick on missed deadline, admin edge cases
- Message board: eliminated entry access (allowed), deleted entry access (blocked), rate limit, char limits
- Audit trail: every action → correct log entry, admin prefix, immutability
- Security: horizontal escalation, JWT validation, input validation, known bug documentation
- No production code changes

**Non-Goals:**

- Performance or load testing (deferred to a future change against the production database)
- Frontend JavaScript test expansion
- Lambda infrastructure or deployment testing
- Multi-season or playoff simulation
- Real ESPN API calls in any test

## Decisions

### D1: Session-scoped fixture for the season simulation

The season simulation fixture (750 users, 2000 entries, 17-week schedule) is expensive to create. It is session-scoped so it runs once per pytest session and is reused across all `test_full_season.py` tests. All season tests that mutate state (e.g. pick creation, elimination) do so in a deterministic order and do not depend on fixture isolation between individual tests — the week-by-week progression is the shared state.

All other test files use the existing function-scoped `client` and `db_session` fixtures, which create and drop tables per test. This prevents contamination between the season sim and isolated unit tests.

```python
# rmp/backend/tests/conftest.py (additions)

import json
import pytest
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from ..models import User, Pool, Entry, Pick, Schedule, Team
from ..database import Base, engine, SessionLocal


@pytest.fixture(scope="session")
def nfl_schedule_2025() -> list[dict]:
    """Load the 2025 NFL regular season game data from the bundled JSON."""
    schedule_path = Path(__file__).parent.parent / "nfl-schedule-2025.json"
    with open(schedule_path) as f:
        data = json.load(f)
    return [
        e for e in data["events"]
        if e["season"].get("year") == 2025
        and e["season"].get("slug") == "regular-season"
    ]


@pytest.fixture(scope="session")
def season_db():
    """Session-scoped DB for the full-season simulation. Created once, torn down after all tests."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    yield db
    db.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="session")
def season_client(season_db):
    """TestClient sharing the same session-scoped DB as the season simulation."""
    from ..main import app
    from ..database import get_db

    def override_get_db():
        yield season_db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
```

**Alternative considered:** Function-scoped fixture with DB rollback between tests. Rejected — rollback semantics don't map cleanly to a 17-week progression where each week's state depends on the prior week's results.

---

### D2: User and entry distribution formula

To hit exactly 2000 entries across 750 users without complex allocation logic, the first 500 users get 3 entries each (1500 total) and the remaining 250 users get 2 entries each (500 total), for exactly 2000.

```python
# rmp/backend/tests/conftest.py (additions)

def create_season_users_and_entries(db: Session, pool_id: str) -> tuple[list[User], list[Entry]]:
    """Create 750 users and 2000 entries (first 500 users: 3 entries, last 250: 2 entries)."""
    users = []
    entries = []
    for i in range(750):
        user = User(
            id=str(uuid4()),
            email=f"survivor_user_{i:04d}@test.runmypool.net",
            hashed_password=bcrypt_hash("TestPass123!"),
            is_active=True,
            role="USER",
        )
        db.add(user)
        users.append(user)

        entry_count = 3 if i < 500 else 2
        for j in range(entry_count):
            entry = Entry(
                id=str(uuid4()),
                user_id=user.id,
                pool_id=pool_id,
                name=f"Entry-{i:04d}-{j}",
                alive=True,
            )
            db.add(entry)
            entries.append(entry)

    db.commit()
    return users, entries
```

**Alternative considered:** Random distribution via `random.choices`. Rejected — non-deterministic counts make assertions fragile and test output unpredictable.

---

### D3: simulate_game_result replicates Lambda logic directly

Rather than importing from `lambda/src/nfl_game_updater.py` (which has AWS SSM and boto3 dependencies), the test helper replicates only the core DB-writing logic: setting `Schedule.winning_team_id`, updating `Pick.result`, and calling a local copy of `eliminate_losing_entries`.

```python
# rmp/backend/tests/helpers.py

from sqlalchemy.orm import Session
from ..models import Schedule, Pick, Entry


def simulate_game_result(db: Session, game_id: int, winner_team_id: int) -> None:
    """
    Simulate the Lambda's game result update for a single game.
    Sets Schedule.winning_team_id, updates Pick.result for all affected picks,
    and eliminates entries with losing picks.
    """
    game = db.query(Schedule).filter(Schedule.game_id == game_id).one()
    loser_team_id = (
        game.away_team_id if game.home_team_id == winner_team_id else game.home_team_id
    )

    game.winning_team_id = winner_team_id
    db.flush()

    # Update pick results for this week
    db.query(Pick).filter(
        Pick.week == game.week_num,
        Pick.team_id == winner_team_id,
    ).update({"result": "win"})

    db.query(Pick).filter(
        Pick.week == game.week_num,
        Pick.team_id == loser_team_id,
    ).update({"result": "loss"})

    db.flush()
    _eliminate_losing_entries(db)
    db.commit()


def _eliminate_losing_entries(db: Session) -> None:
    """Set alive=False for any entry with a loss pick."""
    loss_entry_ids = (
        db.query(Pick.entry_id)
        .filter(Pick.result == "loss")
        .subquery()
    )
    db.query(Entry).filter(
        Entry.id.in_(loss_entry_ids),
        Entry.alive == True,
    ).update({"alive": False}, synchronize_session="fetch")


def simulate_week_results(db: Session, week: int, winners: dict[str, str]) -> None:
    """
    Simulate all games for a week.
    winners: {winner_team_abbrev: loser_team_abbrev}
    """
    games = db.query(Schedule).filter(Schedule.week_num == week).all()
    team_map = {t.abbrv: t.id for t in db.query(Team).all()}

    for game in games:
        home_abbrv = db.query(Team).get(game.home_team_id).abbrv
        away_abbrv = db.query(Team).get(game.away_team_id).abbrv
        if home_abbrv in winners:
            simulate_game_result(db, game.game_id, game.home_team_id)
        elif away_abbrv in winners:
            simulate_game_result(db, game.game_id, game.away_team_id)
```

**Alternative considered:** Import Lambda handler directly. Rejected — `nfl_game_updater.py` imports boto3 and SSM clients at module level, causing import failures in the test environment without AWS credentials.

---

### D4: advance_time via unittest.mock.patch

Lock time boundary tests need to control `datetime.now()` without modifying the pool's `lock_time` row on every test. `unittest.mock.patch` on `rmp.backend.entries.datetime` and `rmp.backend.picks.datetime` is the standard approach for this codebase's import style.

```python
# rmp/backend/tests/test_lock_time.py (excerpt)

from contextlib import contextmanager
from unittest.mock import patch
from datetime import datetime, timezone


@contextmanager
def advance_time(target: datetime):
    """
    Patch datetime.now() in entries.py and picks.py to return target.
    target must be a naive UTC datetime (matching the codebase's timezone.utc.replace(tzinfo=None) pattern).
    """
    naive = target.replace(tzinfo=None) if target.tzinfo else target
    with patch("rmp.backend.entries.datetime") as mock_entries_dt, \
         patch("rmp.backend.picks.datetime") as mock_picks_dt:
        mock_entries_dt.now.return_value = naive
        mock_picks_dt.now.return_value = naive
        yield
```

**Alternative considered:** `freezegun` library. Rejected — introduces a new test dependency. `unittest.mock.patch` is already in stdlib and sufficient for targeted patching.

---

### D5: Deterministic pick strategy for season simulation

Season tests use a controlled pick strategy to guarantee deterministic state at each week. Each entry is assigned to one of three cohorts based on `entry_index % 3`:

- **Cohort 0 ("survivors")**: Always picks the home team. Game results set home team as winner → cohort 0 never loses.
- **Cohort 1 ("early exits")**: Picks the away team in weeks 1 and 2, home team thereafter. Away team is set as loser → cohort 1 is eliminated by end of week 2.
- **Cohort 2 ("mid-season exits")**: Picks the home team until week 8, then picks the away team in week 8. Eliminated in week 8.

This gives exact known counts of alive entries at each week boundary, enabling precise assertions.

```python
# rmp/backend/tests/test_full_season.py (excerpt)

def pick_strategy(entry_index: int, week: int, game: Schedule) -> int:
    """
    Returns team_id to pick based on cohort assignment.
    Cohort 0: always home. Cohort 1: away in weeks 1-2. Cohort 2: away in week 8.
    """
    cohort = entry_index % 3
    if cohort == 0:
        return game.home_team_id
    elif cohort == 1:
        return game.away_team_id if week <= 2 else game.home_team_id
    else:
        return game.away_team_id if week == 8 else game.home_team_id
```

**Alternative considered:** Random picks with seeded `random`. Rejected — random strategies make expected alive counts probabilistic and harder to assert precisely.

---

### D6: Known gaps are documented in tests, not worked around

The pick endpoint does not enforce `pool.lock_time` — only `Pick.locked` (set by admin action). The per-game start_time early lock is also not enforced. Rather than skipping these cases, tests explicitly assert the current (gap) behavior and mark them with a comment and `pytest.mark.gap`:

```python
# rmp/backend/tests/test_lock_time.py (excerpt)

@pytest.mark.gap
def test_pick_not_blocked_by_pool_lock_time_gap(client, db_session, ...):
    """
    KNOWN GAP: picks.py does not check pool.lock_time.
    Picks can be submitted after lock_time passes as long as Pick.locked is False.
    This test documents the current behavior. Expected behavior: 423 Locked.
    """
    # set pool.lock_time to past
    pool.lock_time = datetime(2020, 1, 1)
    db_session.commit()

    response = client.post("/picks/create", json={...}, headers=auth)
    # Current behavior: 200 (gap — should be 423)
    assert response.status_code == 200, (
        "GAP: picks.py does not enforce pool.lock_time. "
        "Picks should be blocked after lock_time passes."
    )
```

**Alternative considered:** Xfail marks. Rejected — `xfail` implies the test is expected to fail and will pass once fixed. `pytest.mark.gap` with an assertion of the broken behavior is a cleaner contract: the test passes today and will need to be updated when the gap is closed.

## Data Storage

No new tables or schema changes. The test suite reads and writes the existing tables using the existing models. The `simulate_game_result` helper writes to `Schedule.winning_team_id`, `Pick.result`, and `Entry.alive` directly via SQLAlchemy.

## Data Structures

No new Pydantic schemas. Tests use existing request/response schemas from the live API.

The following data constants are defined in `tests/constants.py` for reuse across test files:

```python
# rmp/backend/tests/constants.py

NFL_2025_WEEK_COUNT = 17
NFL_2025_GAME_COUNT = 256
NFL_2025_TEAM_COUNT = 32

# Kickoff times UTC for Week 1 (representative of every week's pattern)
WEEK1_THURSDAY_KICKOFF_UTC = "2025-09-05T00:20:00Z"   # DAL @ PHI
WEEK1_SUNDAY_LOCK_UTC = "2025-09-07T17:00:00Z"         # Pool lock_time (1pm ET)
WEEK1_SUNDAY_SNF_UTC = "2025-09-08T00:20:00Z"          # Sunday night
WEEK1_MONDAY_MNF_UTC = "2025-09-09T00:15:00Z"          # Monday night

SEASON_USER_COUNT = 750
SEASON_ENTRY_COUNT = 2000

# Cohort elimination schedule (based on pick_strategy above)
COHORT_1_ELIMINATED_AFTER_WEEK = 2
COHORT_2_ELIMINATED_AFTER_WEEK = 8
```

## Implementation Detail

### conftest.py extensions

The existing `conftest.py` is extended with:

1. `nfl_schedule_2025` — session-scoped, loads JSON, filters to 2025 regular season
2. `season_db` — session-scoped SQLAlchemy `Session` over a persistent SQLite file (`test_season.db`)
3. `season_client` — `TestClient` wired to `season_db` via dependency override
4. `season_pool` — session-scoped pool record with `lock_time=None` initially
5. `season_fixture` — session-scoped, calls `create_season_users_and_entries` and seeds all Schedule rows

### tests/helpers.py (new file)

Contains: `simulate_game_result`, `_eliminate_losing_entries`, `simulate_week_results`, `advance_time` context manager, `get_alive_entries`, `get_entry_used_teams`.

### test_full_season.py

```text
TestFullSeason
├── test_season_fixture_counts          — 750 users, 2000 entries, 256 games
├── test_week_1_picks_before_lock       — all alive entries pick
├── test_week_1_lock_and_autopick       — lock-week, verify autopick
├── test_week_1_picks_blocked_after_lock— locked picks reject update/delete
├── test_week_1_results_and_elimination — game results, alive counts
├── test_week_2_through_17              — parameterized over weeks 2-17
├── test_season_no_duplicate_teams      — global: no entry picks same team twice
├── test_season_dead_entries_have_losses— global: eliminated = has loss pick
├── test_season_survivors_all_wins      — global: survivors = all wins
└── test_season_eligible_team_count     — global: survivors used 17 of 32 teams
```

### test_lock_time.py

```text
TestPoolLockTime
├── test_entry_create_after_lock        — 423
├── test_entry_delete_after_lock        — 423
├── test_entry_create_before_lock       — 200
├── test_entry_create_null_lock         — 200
└── test_lock_time_boundary             — exactly at lock_time

TestPickLocked
├── test_locked_pick_update_blocked     — 400
├── test_locked_pick_delete_blocked     — 400
└── test_admin_overrides_locked_pick    — 200

TestPerGameStartTimeGap (mark: gap)
├── test_thursday_pick_not_blocked_gap  — documents missing enforcement
└── test_all_picks_locked_after_lock_week — lock-week makes all locked

TestLockWeek
├── test_lock_week_sets_all_picks_locked
├── test_lock_week_autopick_for_missing
└── test_lock_week_autopick_skip_no_eligible_teams
```

### test_eligibility.py

```text
TestTeamEligibility
├── test_winning_team_cannot_be_repicked
├── test_losing_team_cannot_be_repicked
├── test_unresolved_pick_team_cannot_be_repicked
├── test_same_user_two_entries_same_team_allowed
├── test_put_pick_to_used_team_rejected
├── test_put_pick_to_unused_team_succeeds
├── test_eligible_team_count_decreases_per_pick
└── test_full_season_17_picks_leaves_15_eligible
```

### test_elimination.py

```text
TestSimulateGameResult
├── test_win_pick_gets_win_result
├── test_loss_pick_gets_loss_result
├── test_entry_eliminated_after_loss
├── test_entry_alive_after_win
└── test_dead_entry_cannot_pick

TestAutoPick
├── test_autopick_assigned_when_no_pick
├── test_autopick_respects_team_uniqueness
└── test_autopick_skipped_no_eligible_teams

TestAdminOps
├── test_admin_transfer_entry
├── test_admin_delete_entry
└── test_non_admin_cannot_use_admin_routes
```

### test_message_board.py

```text
TestMessageBoardAccess
├── test_alive_entry_user_can_post
├── test_eliminated_entry_user_can_post
├── test_no_entry_user_cannot_post
├── test_deleted_entry_user_cannot_post
└── test_no_entry_user_cannot_read

TestRateLimit
├── test_fifth_message_succeeds
├── test_sixth_message_rejected_429
└── test_rate_limit_resets_after_window (mock time)

TestContentConstraints
├── test_empty_message_rejected
├── test_whitespace_message_rejected
├── test_250_char_message_accepted
└── test_251_char_message_rejected

TestDeletion
├── test_user_deletes_own_message
└── test_user_cannot_delete_others_message
```

### test_audit.py

```text
TestAuditOnUserActions
├── test_register_creates_audit
├── test_failed_login_creates_audit
├── test_create_pool_creates_audit
├── test_create_entry_creates_audit
├── test_create_pick_creates_audit
├── test_update_pick_creates_audit_with_diff
├── test_delete_pick_creates_audit
└── test_create_message_creates_audit

TestAuditOnAdminActions
├── test_lock_week_creates_admin_audit
├── test_pick_override_creates_admin_audit
└── test_transfer_entry_creates_admin_audit

TestAuditProperties
├── test_audit_failure_does_not_break_operation
└── test_no_audit_delete_endpoint
```

### test_security.py

```text
TestJWT
├── test_no_token_returns_401_or_403
├── test_expired_jwt_returns_401
└── test_tampered_jwt_returns_401

TestHorizontalEscalation
├── test_user_cannot_pick_for_others_entry
├── test_user_cannot_update_others_pick
├── test_user_cannot_delete_others_pick
└── test_user_cannot_delete_others_entry

TestAdminBoundary
├── test_admin_a_cannot_lock_pool_b
└── test_admin_a_cannot_override_pick_in_pool_b

TestKnownBugs (mark: known_bug)
├── test_get_users_accessible_without_auth_BUG
└── test_patch_password_stores_plaintext_BUG

TestInputValidation
├── test_pick_week_zero_rejected
├── test_pick_week_18_rejected
├── test_pick_week_negative_rejected
└── test_sql_injection_in_pool_name_no_500

TestPasswordReset
└── test_reset_token_cannot_be_reused
```

## Migrations

No schema migrations required. The test suite runs against the existing schema using the existing Alembic baseline. The `season_db` fixture uses a named SQLite file (`test_season.db`) that is created fresh on each session and deleted on teardown.

## Testing Philosophy

### Season simulation correctness

The season simulation is not a statistical exercise — it is a deterministic scenario. Picks are assigned by cohort formula, game results are set to match the pick strategy, and alive counts are known precisely at each week boundary. Tests assert exact counts: after week 2, cohort 1 entries are eliminated; after week 8, cohort 2 entries are eliminated. The global invariants (no duplicate teams, survivors have all wins) are asserted once after all 17 weeks complete.

### Lock time boundary testing

Lock time tests use `advance_time()` to place `datetime.now()` at specific points relative to `pool.lock_time`: well before, exactly at (boundary), and well after. Each combination of lock layer (pool lock_time, Pick.locked, game start_time) is tested independently so failures are localized. Gap tests assert current broken behavior with clear comments indicating the expected behavior when the gap is closed.

### Elimination and Lambda simulation

The `simulate_game_result` helper is the test suite's contract with the Lambda. Its behavior (win/loss assignment, elimination) is verified in isolation in `test_elimination.py` before being relied upon in `test_full_season.py`. This two-layer testing gives confidence that season simulation failures are pick/eligibility issues, not helper bugs.

### Message board edge cases

The eliminated-entry-can-post rule is explicitly tested because it is a non-obvious business rule (the access check is Entry existence, not Entry.alive). Rate limit window reset is tested using mocked time rather than sleeping, keeping the test suite fast.

### Audit trail completeness

Every action that calls an `audit_utils` function is tested for the presence of an AuditLog row with the correct `action` string. Tests do not assert the full JSON structure of `details` — only the top-level `entity_type` and `entity_id` fields. Deep `details` assertion is out of scope for this suite.

### Security gap documentation

Known bugs (GET /users/ unauthenticated, plaintext password storage) are tested with `pytest.mark.known_bug` and assertion messages that explicitly describe the bug. This makes them discoverable in the test report and ensures they are not silently fixed without updating the test.

## Documentation Plan

### `TESTING.md` updates

**Audience:** Developers and pool administrators

Update the existing `TESTING.md` to document the new test marks (`season`, `gap`, `known_bug`), how to run only the season simulation (`pytest -m season`), and how to run only the gap/bug documentation tests (`pytest -m "gap or known_bug"`). Note the session-scoped `test_season.db` file and that it is cleaned up automatically.

## Risks / Trade-offs

### Session-scoped fixture state pollution

**Risk:** Because the season simulation uses a session-scoped DB, test ordering within `test_full_season.py` matters. If a test mutates state in an unexpected way (e.g. deletes an entry mid-season), subsequent week tests will fail with confusing errors.

**Mitigation:** Season tests are numbered and run in strict order (week 1 through 17, then invariants). Tests do not delete entries — only the Lambda simulation sets `alive=False`. Admin delete tests live in `test_elimination.py` with their own function-scoped fixtures, isolated from the season DB.

### SQLite vs MySQL behavioral differences

**Risk:** SQLite lacks strict type enforcement and some constraint behaviors that MySQL enforces (e.g. FK cascade, enum validation). A bug that passes in SQLite may fail in production MySQL.

**Mitigation:** The test suite is explicitly scoped to correctness verification in SQLite. A follow-on performance testing change against production MySQL is the correct venue for MySQL-specific behavior.

### advance_time patching scope

**Risk:** `datetime` is imported differently across modules (`from datetime import datetime` vs `import datetime`). Patching `rmp.backend.entries.datetime` only works if `entries.py` imports `datetime` the class directly. If the import style varies, the patch silently does nothing.

**Mitigation:** Read each target module's import style before writing the patch target string. If a module uses `import datetime` and calls `datetime.datetime.now()`, the patch target must be `rmp.backend.entries.datetime.datetime` instead.

### Cohort-based pick strategy exhausting teams

**Risk:** If the pick strategy assigns the same team to an entry twice across weeks (e.g., home team in week 1 and week 3 is the same team due to schedule structure), the pick will fail with a 400 and the simulation will break.

**Mitigation:** The pick strategy is validated in a preflight check before the season simulation runs. If any entry would be assigned a duplicate team, the strategy is adjusted to use the next eligible team. This is implemented in the `pick_strategy` function via a fallback loop over eligible teams.
