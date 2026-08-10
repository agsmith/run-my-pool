## 1. Schema and Migration

- [x] 1.1 Add `PoolUserLock` model to `models.py` — columns: `pool_id` (String(36), FK pools.id, PK), `user_id` (String(36), FK users.id, PK), `locked_at` (DateTime, nullable=False), `reason` (String(255), nullable=True); relationships to Pool and User
- [x] 1.2 Add `PoolUserLockCreate` and `PoolUserLockOut` schemas to `schemas.py`
- [x] 1.3 Create Alembic migration `add_pool_user_locks_table` — creates `pool_user_locks` with composite PK and both FKs

## 2. Backend — admin.py

- [x] 2.1 Extract `_parse_lock_time(time_str)` helper in `pools.py` — same logic as existing `create_pool` parsing; used by both `create_pool` and `update_pool`
- [x] 2.2 Fix `update_pool` (`PATCH /pools/{pool_id}`) to call `_parse_lock_time` instead of direct assignment when `lock_time` is provided
- [x] 2.3 Add `is_user_locked_in_pool(db, pool_id, user_id)` helper in `admin.py`
- [x] 2.4 Add `POST /admin/pools/{pool_id}/users/{user_id}/lock` endpoint — admin-only; creates `PoolUserLock` row; returns 409 if already locked
- [x] 2.5 Add `DELETE /admin/pools/{pool_id}/users/{user_id}/lock` endpoint — admin-only; deletes lock row; returns 404 if not locked
- [x] 2.6 Add `GET /admin/pools/{pool_id}/export/entries.csv` endpoint — admin-only; queries `Entry JOIN User` ordered by `email, entry.name`; returns `StreamingResponse` with CSV content

## 3. Backend — entries.py and picks.py

- [x] 3.1 In `entries.py` `create_entry`: after ownership/lock_time checks, call `is_user_locked_in_pool` and raise HTTP 423 if locked
- [x] 3.2 In `entries.py` `delete_entry`: same lock check after ownership check
- [x] 3.3 In `picks.py` `create_pick`: after entry ownership and alive checks, call `is_user_locked_in_pool` using `entry.pool_id` and raise HTTP 423 if locked
- [x] 3.4 In `picks.py` `update_pick`: same lock check after entry alive check

## 4. Frontend — admin console

- [x] 4.1 Add `TIMEZONES` constant array with ET, CT, MT, PT, UTC entries including IANA timezone names
- [x] 4.2 Add `toUtcIso(dateStr, timeStr, ianaTimezone)` utility function using `Intl.DateTimeFormat` for DST-aware UTC conversion
- [x] 4.3 Add `lockTimeData` state: `{ date: '', time: '', timezone: 'America/New_York' }`; add `lockTimeMessage` state for feedback
- [x] 4.4 Add `handleSetLockTime` async function that calls `toUtcIso`, then calls `PATCH /pools/{leagueId}` with `{ lock_time: utcString }`; sets `lockTimeMessage`
- [x] 4.5 Add lock time picker UI in League Management section: date input, time select (30-min increments, 12-hour), timezone select; Set Lock Time button wired to `handleSetLockTime`; message display
- [x] 4.6 Add `lockUserData` state: `{ userId: '', locked: false }` and `lockMessage` state
- [x] 4.7 Add `handleToggleUserLock(userId, currentlyLocked)` async function — calls `POST` or `DELETE` on `/admin/pools/{leagueId}/users/{userId}/lock`; updates lock state
- [x] 4.8 Add CSV export button in Entry Management section — anchor tag with `href` pointing to the CSV export endpoint; includes auth token via `fetch`+Blob or a signed URL approach
- [x] 4.9 In the entry lookup results display, add a lock toggle (checkbox) per user row showing current lock status; wired to `handleToggleUserLock`

## 5. Tests

- [x] 5.1 In `test_admin.py`, add `TestCSVExport` class: test admin can download CSV (200, correct content-type, correct rows); test non-admin gets 403; test empty pool returns header row only; test sort order is email then entry_name
- [x] 5.2 Add `TestUserLock` class in `test_admin.py`: test lock creates row (200); test duplicate lock returns 409; test unlock removes row (200); test unlock when not locked returns 404
- [x] 5.3 Add `TestUserLockEnforcement` class: test locked user cannot create entry (423); test locked user cannot delete entry (423); test locked user cannot create pick (423); test locked user CAN log in (200); test locked user CAN create entry in different pool (200); test admin can transfer locked user's entry (200)
- [x] 5.4 In `test_pools.py`, add tests for `_parse_lock_time`: valid ISO format, valid space-separated format, ISO with T separator, format missing seconds; add test that `PATCH /pools/{id}` with lock_time string parses correctly
- [x] 5.5 In `test_entries.py` and `test_picks.py`, verify existing tests still pass after adding the lock check (no regression — lock only fires when a pool_user_locks row exists)

## 6. Verification

- [x] 6.1 Run `cd rmp/backend && venv/bin/python -m pytest tests/ -q` — confirm 0 failures
- [x] 6.2 Run `cd rmp/frontend && npm test` — confirm frontend tests pass
