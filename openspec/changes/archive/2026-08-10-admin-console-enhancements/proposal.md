## Why

Pool admins currently have no way to export participant data, no way to configure the pool lock time from the admin console, and no way to lock a non-paying user out of their pool entries while keeping their account active elsewhere. These are operational gaps that prevent admins from managing real-money survivor pools effectively.

## What Changes

- **New**: `GET /admin/pools/{pool_id}/export/entries.csv` — returns a CSV of all participant email addresses and entry names for the pool; admin-only
- **New**: `pool_user_locks` table — tracks which users are locked in which pools; pool-scoped, does not affect the user globally or in other pools
- **New**: `POST /admin/pools/{pool_id}/users/{user_id}/lock` and `DELETE /admin/pools/{pool_id}/users/{user_id}/lock` — admin endpoints to lock/unlock a user within a pool
- **New**: Lock enforcement in `entries.py` and `picks.py` — locked users get HTTP 423 on any create/modify action within the locked pool; login is unaffected
- **New**: Pool lock time configuration in the admin console — datetime picker with timezone selector; calls existing `PATCH /pools/{pool_id}`
- **New**: CSV export button in admin console — triggers browser download of the entries CSV
- **New**: Lock user toggle in admin console — checkbox per user in the entry list; calls the lock/unlock endpoints
- **Fix**: `PATCH /pools/{pool_id}` lock_time parsing is inconsistent with `POST /pools/create`; both paths should use the same datetime parsing logic
- **Note**: `User.is_active` is not used for pool-scoped locking; the new `pool_user_locks` table handles this. `User.is_active` remains a global flag that is currently unenforced.
- **Note**: Username throughout the system is `User.email`. No separate username field is introduced.

## Capabilities

### New Capabilities

- `pool-csv-export`: admin can download a CSV of all user emails and entry names for a pool
- `pool-user-locking`: admin can lock a user within a specific pool; the user can still log in and access other pools; locked users cannot create entries, modify picks, or delete entries in the locked pool; locked entries can still be transferred by the admin

### Modified Capabilities

- `pool-lock-enforcement`: extended — the pool lock_time is now configurable via the admin console UI with a datetime picker and timezone selector; the backend parsing bug in `PATCH /pools/{pool_id}` is fixed

## Impact

- `rmp/backend/models.py` — new `PoolUserLock` model (pool_id, user_id, locked_at, reason)
- `rmp/backend/alembic/` — new migration for `pool_user_locks` table
- `rmp/backend/admin.py` — new lock/unlock endpoints; new CSV export endpoint
- `rmp/backend/entries.py` — lock check added to create and delete
- `rmp/backend/picks.py` — lock check added to create_pick and update_pick
- `rmp/backend/pools.py` — fix lock_time parsing in PATCH handler
- `rmp/backend/schemas.py` — new `PoolUserLockOut` schema
- `rmp/frontend/pages/admin/league/[id].js` — lock time picker with timezone; CSV export button; lock user toggle in entry list
- `rmp/backend/tests/` — new test coverage for all new endpoints and enforcement
