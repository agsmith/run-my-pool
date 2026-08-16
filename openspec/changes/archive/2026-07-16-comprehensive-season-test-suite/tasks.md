## 1. Bug Fixes

- [x] 1.1 Replace `User.username` with `User.email` in `admin.py` — `transfer_entry`, `delete_entry_admin`, and all audit log details
- [x] 1.2 Rename `EntryTransfer.to_username` → `to_email` in `schemas.py` and update all references
- [x] 1.3 Update `test_admin.py` — remove `pytest.raises(AttributeError)` crash assertions; replace with positive assertions that the endpoints work correctly

## 2. Auto-Pick at Lock Time

- [x] 2.1 Add `POST /admin/pools/{pool_id}/lock-week/{week}` endpoint to `admin.py` — sets `pool.lock_time = now` and creates locked picks for alive entries with no pick that week
- [x] 2.2 Implement most-popular-team strategy with used-team exclusion logic
- [x] 2.3 Write `AUTO_PICK` audit log entries for every auto-pick created
- [x] 2.4 Wire new route in `routers.py`
- [x] 2.5 Add tests in `test_admin.py`: lock-week creates auto-picks, idempotent second call, used-team excluded, no candidate available (skip)

## 3. Admin Pick Edit Endpoint

- [x] 3.1 Add `AdminPickUpdate` schema to `schemas.py`
- [x] 3.2 Add `PATCH /admin/pools/{pool_id}/picks/{pick_id}` endpoint to `admin.py` — updates team, keeps `locked=True`, writes `ADMIN_PICK_EDIT` audit entry
- [x] 3.3 Enforce team-uniqueness check (reject if new team used in another week by same entry)
- [x] 3.4 Wire new route in `routers.py`
- [x] 3.5 Add tests in `test_admin.py`: happy path, team conflict rejected (400), non-admin rejected (403), pick not in pool (404), audit log contents verified

## 4. Message Board Rate Limiting

- [x] 4.1 Add rate limit check to `POST /messages/pool/{pool_id}` in `message_board.py` — count messages by user in pool in last 10 min; return 429 if ≥ 5
- [x] 4.2 Add tests in `test_message_board.py`: 5 succeed, 6th returns 429, window reset (manipulate `created_at` in db_session), limit is per-user-per-pool

## 5. Test Infrastructure

- [x] 5.1 Add `pytest_configure` to `conftest.py` registering `scenario` and `security` marks
- [x] 5.2 Add `season_setup` fixture to `conftest.py` — 10 users, 10 entries, seeded schedule for 2 weeks
- [x] 5.3 Create `tests/test_scenario_season.py` with `@pytest.mark.scenario` — week 1 picks, lock, auto-pick, results, eliminations, week 2 team reuse rejection, admin pick correction, audit trail verification
- [x] 5.4 Create `tests/test_security.py` with `@pytest.mark.security` — IDOR on picks/entries, SQL injection in pool name, XSS in message body, oversized payload, expired JWT, tampered JWT, reset token replay, cross-pool message access, unauthenticated user enumeration (documented gap)
- [x] 5.5 Update `pytest.ini` to include `scenario` and `security` marks in the default run; add `--timeout=60` for scenario tests

## 6. CI Verification

- [x] 6.1 Run full test suite locally and confirm all tests pass including `scenario` and `security`
- [x] 6.2 Push to main and confirm CI backend test job is green
