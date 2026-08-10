## Why

The existing test suite (138 tests, 80% coverage) validates basic CRUD mechanics but does not cover the full survivor pool season lifecycle, pick locking semantics, Lambda-driven elimination, audit correctness, or the documented security gaps. A comprehensive suite is needed to establish a correctness baseline before any future refactoring or performance testing against production data.

## What Changes

- **New**: Full 17-week season simulation test covering 750 users and 2000 entries against the actual 2025 NFL schedule
- **New**: Lock time tests covering all three locking layers (pool lock_time, pick.locked boolean, per-game start_time) including documented gaps in enforcement
- **New**: Team eligibility tests asserting that any picked team (win or loss) is consumed forever for that entry, and that the constraint is per-entry not per-user
- **New**: Entry elimination tests simulating Lambda game result propagation (set winning_team_id → set pick results → eliminate losing entries)
- **New**: Auto-pick tests verifying that entries with no pick after lock-week receive an assigned pick
- **New**: Message board tests covering pool membership access, eliminated entry access, deleted entry access, rate limiting, character limits, and deletion authorization
- **New**: Audit trail tests verifying every action produces a correctly structured audit log entry
- **New**: Security tests covering horizontal privilege escalation, admin boundary enforcement, input validation, JWT handling, and known documented bugs
- **New**: `conftest.py` extensions: schedule seeding from 2025 JSON, user/entry factories, `simulate_game_result()`, `advance_time()` context manager

## Capabilities

### New Capabilities

- `full-season-simulation`: 17-week deterministic season run with 750 users and 2000 entries; picks, results, and elimination verified at each week; final invariants asserted across the full season
- `lock-time-testing`: All three lock enforcement layers tested with boundary conditions and documented gaps explicitly asserted
- `team-eligibility-testing`: Per-entry team uniqueness invariants tested across season; win/loss both consume team; per-entry vs per-user distinction verified
- `elimination-testing`: Lambda simulation helpers; elimination on loss; auto-pick on missed deadline; admin edge cases (transfer, delete, override)
- `message-board-testing`: Full coverage of access rules, alive vs eliminated entry access, deleted entry access, rate limit window, character limits, deletion authorization
- `audit-testing`: Every user and admin action verified to produce a correctly structured audit log entry; failure isolation verified
- `security-testing`: Privilege escalation, JWT validation, input sanitization, known documented bugs asserted and labeled

### Modified Capabilities

- `scenario-test-suite`: Extended with season simulation fixtures and week-by-week helper infrastructure
- `security-test-suite`: Extended with new horizontal escalation, JWT, and input validation cases

## Impact

- `rmp/backend/tests/conftest.py` — extended with new fixtures and helpers
- `rmp/backend/tests/test_full_season.py` — new file
- `rmp/backend/tests/test_lock_time.py` — new file
- `rmp/backend/tests/test_eligibility.py` — new file
- `rmp/backend/tests/test_elimination.py` — new file
- `rmp/backend/tests/test_message_board.py` — new file
- `rmp/backend/tests/test_audit.py` — new file
- `rmp/backend/tests/test_security.py` — new file (expands existing security tests)
- No production code changes — test-only
- No new dependencies expected; uses existing pytest, SQLite in-memory, FastAPI TestClient
- Lambda simulation handled by calling internal functions directly, not via HTTP
