## Why

Six bugs and enforcement gaps were discovered during test suite development. They range from picks being modifiable after the lock window closes to unauthenticated user enumeration. None of these are hypothetical — each was confirmed against the live code. They need to be closed before the pool goes to more users.

## What Changes

- **Fix**: `lock-week` endpoint bulk-locks all existing week-N picks to `Pick.locked=True` (currently only auto-created picks are locked)
- **Fix**: `POST /picks/create` and `PUT /picks/{pick_id}` enforce `pool.lock_time` — picks submitted after the lock window are rejected with HTTP 423
- **Fix**: `POST /picks/create` and `PUT /picks/{pick_id}` enforce per-game `Schedule.start_time` — picks for teams whose game kicks off before Sunday 1pm ET lock at that game's kickoff, not at the Sunday pool lock_time
- **Fix**: `POST /picks/create` and `PUT /picks/{pick_id}` reject picks on eliminated entries (`Entry.alive == False`) with HTTP 403
- **Fix**: `GET /users/` and `GET /users/{user_id}` restricted to authenticated users with `POOL_ADMIN` or `SUPER_ADMIN` role
- **Remove**: `PATCH /users/{user_id}/password` endpoint — broken in three ways (wrong type annotation, plaintext storage, no role check); the working password reset flow in `auth.py` covers this use case
- **Fix**: Admin "Reset Password" button in `pages/admin/league/[id].js` wired to `POST /auth/forgot-password` using the target user's email
- **Remove**: "Force user to change password on next login" checkbox — no backend support exists

## Capabilities

### New Capabilities

- `pick-lock-enforcement`: picks.py enforces pool.lock_time and per-game start_time; lock-week bulk-locks existing picks; dead entries cannot pick

### Modified Capabilities

- `pool-lock-enforcement`: extended — existing spec covers entry creation/deletion lock; now also covers pick submission lock and per-game early lock
- `security-test-suite`: test coverage for the newly enforced rules and the removed/restricted endpoints

## Impact

- `rmp/backend/picks.py` — add lock time and alive checks to `create_pick` and `update_pick`
- `rmp/backend/admin.py` — add bulk `UPDATE` of existing picks in `lock_week`
- `rmp/backend/users.py` — add role-based auth to `GET /` and `GET /{id}`; remove `PATCH /{id}/password`
- `rmp/frontend/pages/admin/league/[id].js` — wire Reset Password button to `POST /auth/forgot-password`; remove "Force change" checkbox
- No schema migrations required
- Tests in `tests/test_lock_time.py`, `tests/test_security.py`, `tests/test_elimination.py` will need updates to assert the newly-enforced behavior (gap tests become passing correctness tests)
