# Design: frontend-entry-cleanup

Three targeted fixes: backend lock enforcement, dead route removal, and committing validated frontend changes.

## Context

The RunMyPool backend exposes entry management endpoints (`POST /entries/create`, `DELETE /entries/{entry_id}`) with no enforcement of the pool's `lock_time`. The frontend has new client-side guards (`isPoolLocked()`) in uncommitted changes, but these are bypassable. The pool lock is a core game rule — entries must not be created or deleted after the season's lock time.

Separately, `pages/league/[leagueId]/entries/[entryId].js` exists as an unreachable 225-line stub. It has no JSX return statement, no navigation pointing to it, and has never rendered anything. It is dead code.

The uncommitted frontend changes in three files contain the client-side lock enforcement, visual refinements (smaller circles, outlined style, removed legend), and a genuine bug fix (`renderPickCircle` previously returned `null`). These are blocked from commit until the backend gap is resolved.

No `docs/dev/architecture.md` exists in the project.

## References

- [HTTP 423 Locked](https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/423) — Appropriate status code for a resource that is locked and cannot be modified.
- `rmp/backend/entries.py` — Current entry endpoints, no lock enforcement present.
- `rmp/backend/models.py` — `Pool.lock_time` is a `DateTime` column, nullable.

## Goals / Non-Goals

**Goals:**

- Enforce `pool.lock_time` server-side on entry create and delete
- Return `HTTP 423` with a clear message when lock is active
- Delete the dead `[entryId].js` route
- Commit the validated uncommitted frontend changes as-is

**Non-Goals:**

- Visual redesign beyond what's already in the uncommitted changes
- Building out the `[entryId].js` page as a functional feature
- Enforcing lock on pick creation/updates (separate concern, separate endpoint)
- Admin override of lock (admins can already correct picks — separate flow)

## Decisions

### D1: Use HTTP 423 Locked for post-lock entry operations

**Decision:** When a pool is past its `lock_time`, `POST /entries/create` and `DELETE /entries/{entry_id}` return `HTTP 423 Locked` with a descriptive detail message. The check is added immediately after pool existence is confirmed, before any write operations.

```python
# rmp/backend/entries.py

from datetime import datetime, timezone

@router.post("/create", response_model=schemas.EntryOut)
def create_entry(
    entry: schemas.EntryCreate,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    pool = db.query(models.Pool).filter(models.Pool.id == entry.pool_id).first()
    if not pool:
        raise HTTPException(status_code=404, detail="Pool not found")

    # Enforce pool lock time
    if pool.lock_time and pool.lock_time < datetime.utcnow():
        raise HTTPException(
            status_code=423,
            detail="Pool is locked. Entry creation is not allowed after the lock time."
        )
    # ... rest of existing logic unchanged

@router.delete("/{entry_id}")
def delete_entry(
    entry_id: str,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    entry = db.query(models.Entry).filter(
        models.Entry.id == entry_id,
        models.Entry.user_id == current_user.id
    ).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")

    # Enforce pool lock time
    pool = db.query(models.Pool).filter(models.Pool.id == entry.pool_id).first()
    if pool and pool.lock_time and pool.lock_time < datetime.utcnow():
        raise HTTPException(
            status_code=423,
            detail="Pool is locked. Entry deletion is not allowed after the lock time."
        )
    # ... rest of existing logic unchanged
```

**Alternative considered:** HTTP 403 Forbidden. Rejected — 403 implies the user lacks permission. 423 is semantically correct: the resource is temporarily locked, not permanently forbidden.

---

### D2: Delete `[entryId].js` outright, do not stub or redirect

**Decision:** Delete `rmp/frontend/pages/league/[leagueId]/entries/[entryId].js`. No redirect is added because no existing navigation points to this route. No stub page is left because it would be worse than nothing — a blank page that silently fails is more confusing than a 404.

**Alternative considered:** Add a redirect from the route to the entries list page. Rejected — nothing navigates to this route, so no user will ever encounter it. A redirect adds complexity for zero benefit.

---

### D3: Commit uncommitted frontend changes as-is, with one clarification

**Decision:** The three modified frontend files are committed as-is. The `league/[leagueId]/entries.js` page does not have the `isPoolLocked()` check on its Create/Delete buttons yet (it's in the diff but still shows both buttons always). Confirm the diff's lock guard is also applied to this view consistently.

The visual changes (circle size, outlined style, removed legend, button repositioning) are accepted as the intended design direction.

## Interfaces

### Modified REST Endpoints

| Method | Path | When locked response |
|---|---|---|
| `POST` | `/entries/create` | `423 Locked` — "Pool is locked. Entry creation is not allowed after the lock time." |
| `DELETE` | `/entries/{entry_id}` | `423 Locked` — "Pool is locked. Entry deletion is not allowed after the lock time." |

### Deleted Route

| Route | Action |
|---|---|
| `/league/[leagueId]/entries/[entryId]` | Deleted — file removed, route returns Next.js 404 |

## Migrations

No schema changes. No Alembic revision needed. `Pool.lock_time` already exists.

## Testing Philosophy

### Backend lock enforcement

Test `POST /entries/create` with a pool whose `lock_time` is in the past — expect `423`. Test with `lock_time` in the future — expect normal `200` creation. Test with `lock_time = null` — expect normal `200` (no lock). Same three cases for `DELETE /entries/{entry_id}`.

### Frontend lock guard

With a locked pool, verify Create Entry and Delete Entry buttons are not rendered. With an unlocked pool, verify they are rendered. Verify the error message from a `423` response surfaces to the user (the existing `setError` path handles this automatically since the frontend checks `res.ok`).

## Risks / Trade-offs

### `datetime.utcnow()` vs timezone-aware comparison

**Risk:** `pool.lock_time` is stored as a naive datetime in MySQL. `datetime.utcnow()` is also naive. If the comparison is ever changed to use timezone-aware datetimes, a mismatch will raise a TypeError at runtime.

**Mitigation:** Both sides of the comparison use naive UTC datetimes consistently, matching the existing pattern in `entries.py` (`datetime.utcnow()` is already used for `created_at`/`updated_at`). Document the convention — don't mix naive and aware datetimes in this codebase without a broader migration.

### Admin bypass not implemented

**Risk:** League admins cannot override the lock to add entries for a participant who missed the window (e.g., a late joiner the admin approved).

**Mitigation:** This is an explicit non-goal. Admins already have a separate entry transfer flow. If an admin needs to add an entry post-lock, it can be done directly in the DB or via a future admin override endpoint.
