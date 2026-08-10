## 1. Backend — picks.py lock enforcement

- [x] 1.1 Add imports for `Schedule` and `Team` to `picks.py` if not already present
- [x] 1.2 Add `_get_effective_lock_time(db, pool, team_abbrev, week)` helper — returns `min(pool.lock_time, game.start_time)` or `None`
- [x] 1.3 Add `_check_pick_lock(db, pool, team_abbrev, week)` helper — raises HTTP 423 if effective lock time has passed
- [x] 1.4 In `create_pick`: after ownership check, add alive check — raise HTTP 403 "Entry has been eliminated" if `entry.alive == False`
- [x] 1.5 In `create_pick`: fetch the pool via `entry.pool_id`; call `_check_pick_lock` before the upsert branch and before the new-pick branch
- [x] 1.6 In `create_pick` upsert path: apply lock check using the **existing** pick's team (the slot is locked at the existing pick's game kickoff)
- [x] 1.7 In `update_pick`: after ownership check, add alive check — raise HTTP 403 if `entry.alive == False`
- [x] 1.8 In `update_pick`: fetch the pool via `pick.entry.pool_id`; call `_check_pick_lock` using the **existing** team (not the new proposed team)

## 2. Backend — admin.py lock_week bulk update

- [x] 2.1 In `lock_week`, after building `alive_ids` and before the auto-pick loop, add `db.query(Pick).filter(Pick.entry_id.in_(alive_ids), Pick.week == week, Pick.locked == False).update({"locked": True}, synchronize_session="fetch")` followed by `db.flush()`

## 3. Backend — users.py auth restriction and cleanup

- [x] 3.1 Add `from deps import get_current_user` import to `users.py`
- [x] 3.2 Add `_require_admin(current_user)` helper that raises HTTP 403 for non-POOL_ADMIN/SUPER_ADMIN roles
- [x] 3.3 Add `current_user: models.User = Depends(get_current_user)` to `list_users`; call `_require_admin(current_user)`
- [x] 3.4 Add `current_user` dependency to `get_user`; call `_require_admin(current_user)`; fix `user_id: int` → `user_id: str`; fix query to use `models.User.id == user_id`
- [x] 3.5 Remove the `reset_password` route handler (`PATCH /{user_id}/password`) from `users.py`

## 4. Frontend — admin UI Reset Password button

- [x] 4.1 In `pages/admin/league/[id].js`, add `const [resetPasswordMessage, setResetPasswordMessage] = useState('')` state
- [x] 4.2 Remove `forceChange` field from the `resetPasswordData` initial state object
- [x] 4.3 Add `handleResetPassword` async function that calls `POST /auth/forgot-password` with the entered email and sets `resetPasswordMessage` with success/error text
- [x] 4.4 Wire `onClick={handleResetPassword}` to the Reset Password button
- [x] 4.5 Remove the "Force user to change password on next login" checkbox JSX and its `onChange` handler
- [x] 4.6 Add a message display element below the button that renders `resetPasswordMessage` when non-empty

## 5. Tests — convert gap/bug tests to correctness tests

- [x] 5.1 In `test_lock_time.py`: update `test_lock_week_sets_existing_picks_to_locked` — remove `@pytest.mark.gap`, change assertion from `False` to `True`, remove gap documentation comment
- [x] 5.2 In `test_lock_time.py`: update `test_thursday_pick_not_blocked_gap` — remove `@pytest.mark.gap`, change assertion from HTTP 200 to HTTP 423, remove gap documentation comment; rename to `test_thursday_pick_blocked_after_kickoff`
- [x] 5.3 In `test_security.py`: update `test_get_users_accessible_without_auth_BUG` — remove `@pytest.mark.known_bug`, change assertion from HTTP 200 to HTTP 403, rename to `test_get_users_requires_auth`
- [x] 5.4 In `test_security.py`: remove `test_patch_password_stores_plaintext_BUG` entirely (endpoint removed)
- [x] 5.5 In `test_elimination.py`: update `test_dead_entry_cannot_pick` — remove gap comment, change assertion from HTTP 200 to HTTP 403 with "eliminated" in detail

## 6. Tests — new lock enforcement tests

- [x] 6.1 In `test_lock_time.py`, add `TestPickLockTimeEnforcement` class with test: pick creation after `pool.lock_time` returns HTTP 423
- [x] 6.2 Add test: pick update (`PUT`) after `pool.lock_time` returns HTTP 423
- [x] 6.3 Add test: pick creation for a team whose game `start_time` has passed returns HTTP 423 (seed a Schedule row with `start_time` in the past)
- [x] 6.4 Add test: pick update (changing team) after existing pick's game `start_time` has passed returns HTTP 423 — lock is on the existing slot, not the new team's game
- [x] 6.5 Add test: pick creation for a Sunday 4pm team (start_time in the future) before `pool.lock_time` returns HTTP 200
- [x] 6.6 In `test_security.py`, add test: `GET /users/` with regular USER token returns HTTP 403
- [x] 6.7 Add test: `GET /users/` with POOL_ADMIN token returns HTTP 200

## 7. Verification

- [x] 7.1 Run `cd rmp/backend && venv/bin/python -m pytest tests/ -q` — confirm 0 failures and no regressions
- [x] 7.2 Run `cd rmp/backend && venv/bin/python -m pytest tests/ -m "gap or known_bug"` — confirm 0 tests found (all converted or removed)
- [x] 7.3 Run `cd rmp/frontend && npm test` — confirm frontend tests still pass
