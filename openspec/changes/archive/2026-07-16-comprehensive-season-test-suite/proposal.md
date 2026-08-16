## Why

The application has unit and integration tests for individual endpoints but no tests that simulate real usage across a full NFL season. Critical behaviors — auto-pick on missed deadline, admin pick correction, message board spam protection, security boundaries — are either untested or not yet implemented. This change closes that gap by first fixing the missing features and bugs, then building a comprehensive test suite that exercises them under realistic season conditions.

## What Changes

- Fix `admin.py` crash: replace `User.username` references with `User.email` throughout
- Add auto-pick at lock time: when a pool entry has no pick at lock, auto-assign the most popular team picked by alive entries in that pool for the current week
- Add admin pick edit endpoint: `PATCH /admin/pools/{pool_id}/picks/{pick_id}` — allows pool admin to directly change the team on any pick, locked or not
- Add message board rate limiting: enforce 5 messages per user per 10 minutes per pool at the API layer
- Add `pytest.mark.scenario` test suite: full season simulation across 18 weeks with multiple users, entries, picks, lock events, results, and eliminations
- Add `pytest.mark.security` test suite: OWASP Top 10 coverage — access control, injection, auth failures, broken object-level authorization

## Capabilities

### New Capabilities

- `auto-pick`: Auto-assign a team at lock time for entries that have not submitted a pick. Uses the most popular team picked by other alive entries in the pool that week. Fires as part of the lock mechanism.
- `admin-pick-edit`: Pool admin can directly update the team field on any pick (locked or not), bypassing normal lock enforcement. Audit logged.
- `message-board-rate-limit`: Enforce maximum 5 messages per user per 10-minute rolling window per pool. Return HTTP 429 with a clear error on violation.
- `scenario-test-suite`: Story-driven pytest scenarios that simulate a complete 18-week NFL survivor season: registration, pool creation, entry creation, weekly picks, lock enforcement, auto-pick, result processing, elimination, admin corrections, and message board interaction.
- `security-test-suite`: `pytest.mark.security` tests covering OWASP Top 10: broken access control (IDOR on picks/entries), injection (SQL, XSS in message content), auth failures (JWT tampering, expired tokens, brute force), and security misconfiguration (unauthenticated user enumeration endpoint).

### Modified Capabilities

- `pool-lock-enforcement`: Existing lock spec covers entry create/delete. This change extends lock enforcement to include auto-pick triggering at lock time.

## Impact

- `rmp/backend/admin.py`: Fix `User.username` → `User.email`; add new `PATCH /admin/pools/{pool_id}/picks/{pick_id}` endpoint
- `rmp/backend/message_board.py`: Add rate limit check before insert
- `rmp/backend/entries.py` or a new `lock_processor.py`: Add auto-pick logic triggered at lock time
- `rmp/backend/routers.py`: Wire new admin pick edit route
- `rmp/backend/tests/`: New `test_scenario_season.py`, `test_security.py`
- No schema changes required (existing `picks`, `entries`, `audit_logs` tables are sufficient)
- No new dependencies required (rate limiting via DB query on `message_board.created_at`)
