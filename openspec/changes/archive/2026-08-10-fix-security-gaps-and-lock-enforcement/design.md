# Design: fix-security-gaps-and-lock-enforcement

Six bugs and enforcement gaps confirmed against the live codebase: picks submittable after the lock window, Thursday games not enforcing early lock, dead entries accepting picks, user enumeration without auth, a broken admin password reset endpoint, and an unwired admin UI button.

## Context

The backend is FastAPI + SQLAlchemy against MySQL (SQLite in tests). The lock enforcement pattern already exists in `entries.py` — it compares `pool.lock_time` to `datetime.now(timezone.utc).replace(tzinfo=None)` (naive UTC). The picks router (`picks.py`) currently performs no time-based checks at all.

`Schedule.start_time` is stored as a naive UTC datetime. Per-game early lock requires looking up the game for the team being picked in the current week and comparing its `start_time` to `now`.

The `user_id` type bug in `users.py` (`int` vs UUID string) means `GET /users/{user_id}` currently never finds any user. Fixing the auth restriction is the right time to fix the type too.

The admin password reset flow exists and works in `auth.py`. The frontend already has `/forgot-password` and `/reset-password` pages fully built. The admin UI button just needs an `onClick` handler.

No `docs/dev/architecture.md` exists in this project.

## References

- `rmp/backend/picks.py` — pick creation/update logic; no lock checks today
- `rmp/backend/admin.py` — `lock_week()`: sets `pool.lock_time`, creates auto-picks; does not update existing picks
- `rmp/backend/entries.py` — working pattern for `pool.lock_time` comparison
- `rmp/backend/users.py` — broken endpoints: wrong type annotation, no auth, plaintext password
- `rmp/backend/auth.py` — working `forgot-password` / `reset-password` flow
- `rmp/backend/models.py` — `Schedule.start_time`: `DateTime`, naive UTC; `Entry.alive`: `Boolean`
- `rmp/frontend/pages/admin/league/[id].js` — admin UI with unhooked Reset Password button

## Goals / Non-Goals

**Goals:**

- `picks.py` rejects picks after `pool.lock_time` (HTTP 423)
- `picks.py` rejects picks for teams whose game kicked off before Sunday 1pm ET, after that game's `start_time` (HTTP 423)
- `picks.py` rejects picks on eliminated entries — `Entry.alive == False` (HTTP 403)
- `admin.py` `lock_week` bulk-sets `Pick.locked = True` on all existing week-N picks
- `users.py` `GET /` and `GET /{id}` require POOL_ADMIN or SUPER_ADMIN role; fix `user_id` type annotation to `str`
- `users.py` `PATCH /{id}/password` removed
- Admin UI Reset Password button calls `POST /auth/forgot-password` and shows result
- All gap/bug tests updated to assert correct behavior

**Non-Goals:**

- Email delivery for password reset (currently logs to stdout — separate change)
- Reset token blacklist (deferred until email is working)
- "Force change on next login" feature (no backend support; checkbox removed)
- Modifying the `auth.py` reset flow itself
- Any changes to entry lock enforcement (already in `entries.py`)

## Decisions

### D1: picks.py lock check order and lookup strategy

Lock checks are added to both `create_pick` and `update_pick` (but NOT the upsert path in `create_pick` when `existing_pick` is found — the upsert updates an existing pick for the same week, which should also be blocked after lock). The check order:

1. Ownership check (existing — entry belongs to current user)
2. **New:** Alive check — entry is not eliminated
3. **New:** Pick-level lock check — if `existing_pick.locked` is True (for upsert/update paths)
4. **New:** Pool lock_time check — pool.lock_time has not passed
5. **New:** Per-game start_time check — the team's game has not kicked off
6. Team uniqueness check (existing)

The per-game check requires one additional query: find the `Schedule` row for the picked team in the given week.

```python
# rmp/backend/picks.py  (additions to create_pick and update_pick)

from datetime import datetime, timezone

def _get_effective_lock_time(db, pool, team_abbrev: str, week: int):
    """
    Return the effective lock time for a pick: the earlier of pool.lock_time
    and the game start_time for the team being picked this week.

    Returns None if pool has no lock_time and no game is found (no restriction).
    """
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    # Find the Schedule row for this team this week
    team = db.query(Team).filter(Team.abbrv == team_abbrev).first()
    game = None
    if team:
        game = (
            db.query(Schedule)
            .filter(
                Schedule.week_num == week,
                (Schedule.home_team_id == team.id) | (Schedule.away_team_id == team.id),
            )
            .first()
        )

    candidates = []
    if pool.lock_time is not None:
        candidates.append(pool.lock_time)
    if game is not None and game.start_time is not None:
        candidates.append(game.start_time)

    return min(candidates) if candidates else None


def _check_pick_lock(db, pool, team_abbrev: str, week: int):
    """
    Raise HTTP 423 if the effective lock time has passed.
    """
    effective_lock = _get_effective_lock_time(db, pool, team_abbrev, week)
    if effective_lock is None:
        return  # no lock configured

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if effective_lock <= now:
        raise HTTPException(
            status_code=423,
            detail="This pick is locked. The game has started or the pool lock time has passed.",
        )
```

For the `update_pick` path, the lock check uses the **existing pick's team** (not the proposed new team) — because the pick was locked at the kickoff of the team already selected. If you picked a Thursday team and the Thursday game has started, you cannot change that pick to a Sunday team either.

**Alternative considered:** Check the new team's game start_time instead. Rejected — the intent is that once a Thursday pick is locked (game started), that slot is frozen regardless of what team you want to switch to.

---

### D2: lock_week bulk-updates existing picks

A single bulk UPDATE is added before the auto-pick loop:

```python
# rmp/backend/admin.py  (addition inside lock_week, after building alive_ids)

# Lock all existing picks for this week
db.query(models.Pick).filter(
    models.Pick.entry_id.in_(alive_ids),
    models.Pick.week == week,
).update({"locked": True}, synchronize_session="fetch")
db.flush()
```

This runs before the auto-pick loop. Auto-picks are created with `locked=True` already. Net result: after `lock_week`, every pick for week N in this pool has `locked=True`.

**Alternative considered:** Lock picks only for alive entries. Adopted as written — the filter already uses `alive_ids`.

---

### D3: users.py role check and type fix

Two changes: add `get_current_user` dependency and a role guard; fix `user_id: int` to `user_id: str`.

```python
# rmp/backend/users.py

from deps import get_db, get_current_user
import models

def _require_admin(current_user: models.User):
    """Raise 403 if the current user is not POOL_ADMIN or SUPER_ADMIN."""
    if current_user.role not in (models.UserRole.POOL_ADMIN, models.UserRole.SUPER_ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )


@router.get("/", response_model=List[schemas.UserOut])
def list_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(get_current_user),
):
    _require_admin(current_user)
    return db.query(models.User).offset(skip).limit(limit).all()


@router.get("/{user_id}", response_model=schemas.UserOut)
def get_user(
    user_id: str,           # was: int
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(get_current_user),
):
    _require_admin(current_user)
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
```

`PATCH /{user_id}/password` is removed entirely. `DELETE /{user_id}` and `PATCH /{user_id}/email` already have `get_current_user` but lack role checks — those are left for a separate hardening pass.

**Alternative considered:** `SUPER_ADMIN` only for user listing. Rejected — pool admins legitimately need to look up users to manage their pools.

---

### D4: picks.py alive check

Added immediately after the ownership check, before any other validation:

```python
# rmp/backend/picks.py — inside create_pick, after entry ownership check

if not entry.alive:
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Entry has been eliminated",
    )
```

Same check added to `update_pick` after the ownership join.

**Alternative considered:** HTTP 404 to obscure the entry's state. Rejected — the user already knows their entry is eliminated; a clear 403 is more useful and honest.

---

### D5: Admin UI Reset Password button

The existing button in `renderUserManagement()` gets an `onClick` handler that calls `POST /auth/forgot-password`. The input field already captures the user's email (`resetPasswordData.username`). The "Force change" checkbox is removed — no backend support exists.

```javascript
// rmp/frontend/pages/admin/league/[id].js

const handleResetPassword = async () => {
  if (!resetPasswordData.username.trim()) return;
  try {
    const res = await fetch(
      process.env.NEXT_PUBLIC_API_URL + '/auth/forgot-password',
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: resetPasswordData.username }),
      }
    );
    if (!res.ok) throw new Error('Failed');
    setResetPasswordMessage('Password reset link sent (check server logs until email is configured).');
  } catch {
    setResetPasswordMessage('Failed to send reset link.');
  }
};
```

The button receives `onClick={handleResetPassword}`. A `resetPasswordMessage` state variable displays the result below the button. The "Force user to change password on next login" checkbox and its state are removed.

**Alternative considered:** Call `GET /users/` to validate the email exists first. Rejected — `POST /auth/forgot-password` intentionally never confirms whether an email is registered (security best practice). The admin doesn't need confirmation of existence.

## Data Storage

No schema changes. No new tables or columns.

## Data Structures

No new Pydantic schemas. The `ResetPasswordRequest` and `ForgotPasswordRequest` schemas in `auth.py` are used as-is.

## Implementation Detail

### picks.py changes summary

- Import `Schedule`, `Team` (already imported in some cases — verify)
- Add `_get_effective_lock_time(db, pool, team_abbrev, week)` helper
- Add `_check_pick_lock(db, pool, team_abbrev, week)` helper  
- In `create_pick`: add alive check; fetch pool; call `_check_pick_lock` before upsert and before new pick creation
- In `update_pick`: add alive check; fetch pool (via `pick.entry.pool`); call `_check_pick_lock` with the **existing** team (not the new team)

### admin.py changes summary

- In `lock_week`: after building `alive_ids`, add `db.query(Pick).filter(...).update({"locked": True})` before the auto-pick loop

### users.py changes summary

- Add `from deps import get_current_user` import
- Add `_require_admin(current_user)` helper
- Add `current_user` dependency to `list_users` and `get_user`; call `_require_admin`
- Fix `user_id: int` → `user_id: str` on `get_user`
- Remove `reset_password` route handler entirely

### admin/league/[id].js changes summary

- Add `resetPasswordMessage` state: `const [resetPasswordMessage, setResetPasswordMessage] = useState('')`
- Add `handleResetPassword` async function
- Wire `onClick={handleResetPassword}` to the Reset Password button
- Remove `forceChange` field from `resetPasswordData` initial state
- Remove "Force user to change password" checkbox JSX
- Add message display element below the button

## Migrations

No database migrations required.

## Testing Philosophy

### Gap and bug tests converted to correctness tests

`test_lock_time.py` contains `@pytest.mark.gap` tests that currently assert broken behavior. After this change, `test_lock_week_sets_existing_picks_to_locked` must be updated to remove the gap mark and assert `Pick.locked == True`. `test_thursday_pick_not_blocked_gap` must be updated to assert HTTP 423.

`test_security.py` contains `@pytest.mark.known_bug` tests for the unauthenticated user list and plaintext password. After this change, `test_get_users_accessible_without_auth_BUG` must assert HTTP 403. The plaintext password test must be removed (endpoint no longer exists).

`test_elimination.py` contains `test_dead_entry_cannot_pick` which currently asserts HTTP 200 (gap). After this change it must assert HTTP 403.

### New lock enforcement tests

`test_lock_time.py` needs new tests covering:
- `POST /picks/create` after `pool.lock_time` → 423
- `PUT /picks/{id}` after `pool.lock_time` → 423
- `POST /picks/create` for a team whose game has already started → 423
- `PUT /picks/{id}` (changing team) after existing pick's game started → 423
- `POST /picks/create` for a Sunday 4pm team before `pool.lock_time` → 200

### Admin pick lock test

`test_lock_time.py` gap test for lock-week becomes a passing correctness test asserting `Pick.locked == True` on pre-existing picks after `lock_week` is called.

## Documentation Plan

### `TESTING.md` updates

**Audience:** Developers

Update the gap/known_bug section to remove the resolved items. Update test counts. Note that `@pytest.mark.gap` and `@pytest.mark.known_bug` tests that were converted to correctness tests no longer carry those marks.

## Risks / Trade-offs

### Per-game lock adds a DB query per pick submission

**Risk:** Each pick creation and update now requires an additional query to `Schedule` to find the team's game and compare `start_time`. For most users this is one extra indexed lookup per pick submission — negligible. At scale (many concurrent submissions around lock time) this could become visible.

**Mitigation:** The query is indexed on `week_num` and `home_team_id`/`away_team_id`. No caching needed at current scale. If performance becomes an issue, the game lookup can be memoized per request.

### lock_week bulk UPDATE changes behavior for existing locked picks

**Risk:** Calling `lock_week` twice for the same week will set `locked=True` on picks that were already `locked=True` — a no-op in practice but wastes a DB write.

**Mitigation:** Add `Pick.locked == False` filter to the bulk UPDATE. Not strictly necessary but cleaner.

### Removing PATCH /users/{id}/password may break undiscovered callers

**Risk:** No frontend caller is known, but the endpoint is publicly listed in the OpenAPI docs. An external script or integration could be calling it.

**Mitigation:** The endpoint currently returns 422 for all real user IDs due to the `int` type annotation bug, so no real callers exist. The removal is safe.
