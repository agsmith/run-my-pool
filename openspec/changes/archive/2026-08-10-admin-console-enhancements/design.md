# Design: admin-console-enhancements

Three admin capabilities: CSV export of pool entries, pool-scoped user locking for non-paying participants, and a configurable lock time picker in the admin console. All three are admin-only operations.

## Context

The backend is FastAPI + SQLAlchemy (MySQL in prod, SQLite in tests). The admin console is a single Next.js page at `pages/admin/league/[id].js`. Admin access is determined by the `pool_admins` join table, not by `User.role`.

`User.is_active` exists in the model but is never checked at login or in `deps.get_current_user`. It cannot serve pool-scoped locking because it is a global flag. A new `pool_user_locks` join table (same pattern as `pool_admins`) provides pool-scoped locking without touching global auth.

The `PATCH /pools/{pool_id}` endpoint currently assigns `lock_time` directly from the request body without parsing, unlike `POST /pools/create` which has explicit datetime parsing. This is a bug that will be fixed as part of the lock time picker work.

No `docs/dev/architecture.md` exists in this project.

## References

- `rmp/backend/admin.py` — existing admin endpoints; `verify_admin_access()` helper
- `rmp/backend/models.py` — `PoolAdmin` join table pattern (reused for `PoolUserLock`)
- `rmp/backend/entries.py` — lock check pattern from `fix-security-gaps` change
- `rmp/backend/picks.py` — same lock check pattern
- `rmp/backend/pools.py` — `PATCH /{pool_id}` parsing bug
- `rmp/frontend/pages/admin/league/[id].js` — admin console state and render functions

## Goals / Non-Goals

**Goals:**

- `GET /admin/pools/{pool_id}/export/entries.csv` — CSV of all emails + entry names, admin-only, sorted
- `POST /admin/pools/{pool_id}/users/{user_id}/lock` and `DELETE` counterpart
- `pool_user_locks` table + Alembic migration
- Lock enforcement in `entries.py` (create, delete) and `picks.py` (create, update)
- Lock time datetime picker with timezone in admin console
- CSV Export button in admin console
- Lock toggle per user in admin console entry list
- Fix `PATCH /pools/{pool_id}` lock_time parsing

**Non-Goals:**

- Email delivery for password reset (separate change)
- Global account deactivation via `User.is_active`
- Lock enforcement on `GET` endpoints — locked users can still read their data
- Admin transfer blocked by user lock — admin operations always bypass user locks

## Decisions

### D1: pool_user_locks table mirrors pool_admins pattern

```python
# rmp/backend/models.py

class PoolUserLock(Base):
    __tablename__ = "pool_user_locks"
    pool_id = Column(String(36), ForeignKey("pools.id"), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id"), primary_key=True)
    locked_at = Column(DateTime, nullable=False)
    reason = Column(String(255), nullable=True)
    # relationships
    pool = relationship("Pool")
    user = relationship("User")
```

Composite primary key `(pool_id, user_id)` prevents duplicate locks. `locked_at` is set to `datetime.now(timezone.utc).replace(tzinfo=None)` at lock time. `reason` is optional — admins may note "unpaid fees" but it is not required.

**Alternative considered:** Add `locked_pool_ids` JSON column to `User`. Rejected — hard to query, harder to maintain referential integrity.

---

### D2: Lock check helper in admin.py reused in entries and picks

A single helper function checks if a user is locked in a pool:

```python
# rmp/backend/admin.py

def is_user_locked_in_pool(db: Session, pool_id: str, user_id: str) -> bool:
    """Return True if the user has an active lock record for this pool."""
    return (
        db.query(models.PoolUserLock)
        .filter(
            models.PoolUserLock.pool_id == pool_id,
            models.PoolUserLock.user_id == user_id,
        )
        .first()
    ) is not None
```

Called in `entries.py` create/delete and `picks.py` create/update after the ownership check. Raises HTTP 423:

```python
# rmp/backend/entries.py and picks.py (after ownership check)
from admin import is_user_locked_in_pool

if is_user_locked_in_pool(db, pool_id, current_user.id):
    raise HTTPException(
        status_code=423,
        detail="Your account is locked in this pool. Contact the pool admin.",
    )
```

**Alternative considered:** Inline the query in each endpoint. Rejected — duplication; a single helper is easier to test and maintain.

---

### D3: CSV endpoint uses Python csv module via StreamingResponse

```python
# rmp/backend/admin.py

import csv
import io
from fastapi.responses import StreamingResponse

@router.get("/pools/{pool_id}/export/entries.csv")
def export_entries_csv(
    pool_id: str,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
):
    if not verify_admin_access(pool_id, current_user, db):
        raise HTTPException(status_code=403, detail="Admin access required")

    rows = (
        db.query(models.User.email, models.Entry.name)
        .join(models.Entry, models.Entry.user_id == models.User.id)
        .filter(models.Entry.pool_id == pool_id)
        .order_by(models.User.email, models.Entry.name)
        .all()
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["email", "entry_name"])
    for email, entry_name in rows:
        writer.writerow([email, entry_name])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=entries.csv"},
    )
```

**Alternative considered:** Return JSON and let the frontend generate CSV. Rejected — a server-side CSV download is simpler for the admin (one click, no frontend logic) and works even without JavaScript.

---

### D4: Lock time picker uses a short timezone list + browser-side UTC conversion

The admin console supports a fixed list of US timezones relevant to NFL:

```javascript
// rmp/frontend/pages/admin/league/[id].js

const TIMEZONES = [
  { label: "Eastern Time (ET)",  offset_dst: -4, offset_std: -5, iana: "America/New_York" },
  { label: "Central Time (CT)",  offset_dst: -5, offset_std: -6, iana: "America/Chicago" },
  { label: "Mountain Time (MT)", offset_dst: -6, offset_std: -7, iana: "America/Denver" },
  { label: "Pacific Time (PT)",  offset_dst: -7, offset_std: -8, iana: "America/Los_Angeles" },
  { label: "UTC",                offset_dst:  0, offset_std:  0, iana: "UTC" },
];

// Conversion using Intl.DateTimeFormat to determine DST status
function toUtcIso(localDateStr, localTimeStr, ianaTimezone) {
  const localDt = new Date(`${localDateStr}T${localTimeStr}`);
  // Use Intl to get the UTC offset in the given timezone at that moment
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: ianaTimezone,
    year: "numeric", month: "2-digit", day: "2-digit",
    hour: "2-digit", minute: "2-digit", second: "2-digit",
    hour12: false,
  }).formatToParts(localDt);
  // reconstruct and diff to get offset
  // ... returns ISO string in UTC
}
```

The UI provides:
- A `<input type="date">` for the date
- A `<select>` for the time (30-minute increments, 12-hour display)
- A `<select>` for the timezone

On submit, `toUtcIso()` converts to UTC and sends to `PATCH /pools/{pool_id}` with `{ lock_time: "YYYY-MM-DD HH:MM:SS" }`.

**Alternative considered:** `<input type="datetime-local">` — gives local time with no TZ awareness, not appropriate for a scheduling feature that must lock at exactly 1pm ET.

---

### D5: PATCH /pools/{pool_id} lock_time parsing fix

The `PATCH` handler is updated to use the same parsing function extracted from `POST`:

```python
# rmp/backend/pools.py

def _parse_lock_time(time_str: str) -> datetime:
    """Parse a lock_time string in ISO or YYYY-MM-DD HH:MM:SS format."""
    time_str = time_str.strip()
    if 'T' in time_str:
        time_str = time_str.replace('Z', '')
        date_part, time_part = time_str.split('T')
        if '.' in time_part:
            time_part = time_part.split('.')[0]
        time_str = f"{date_part} {time_part}"
    if len(time_str.split(' ')[1].split(':')) == 2:
        time_str += ':00'
    return datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
```

Both `create_pool` and `update_pool` call `_parse_lock_time` instead of duplicating the logic.

## Data Storage

### New: PoolUserLock

```python
class PoolUserLock(Base):
    __tablename__ = "pool_user_locks"
    pool_id   = Column(String(36), ForeignKey("pools.id"), primary_key=True)
    user_id   = Column(String(36), ForeignKey("users.id"), primary_key=True)
    locked_at = Column(DateTime, nullable=False)
    reason    = Column(String(255), nullable=True)
    pool      = relationship("Pool")
    user      = relationship("User")
```

Alembic migration creates the table and both foreign keys.

## Data Structures

```python
# rmp/backend/schemas.py

class PoolUserLockCreate(BaseModel):
    reason: Optional[str] = None

class PoolUserLockOut(BaseModel):
    pool_id: str
    user_id: str
    locked_at: datetime
    reason: Optional[str] = None

    class Config:
        from_attributes = True
```

## Interfaces

### REST API — Admin Additions

| Method | Path | Request | Response | Description |
|--------|------|---------|----------|-------------|
| `GET` | `/admin/pools/{pool_id}/export/entries.csv` | — | CSV stream | Download all entries; admin-only |
| `POST` | `/admin/pools/{pool_id}/users/{user_id}/lock` | `PoolUserLockCreate` | `PoolUserLockOut` | Lock user in pool; admin-only |
| `DELETE` | `/admin/pools/{pool_id}/users/{user_id}/lock` | — | `{"message": "..."}` | Unlock user in pool; admin-only |

**Error responses:**
- `403` — not a pool admin
- `404` — pool or user not found
- `409` — user already locked (POST only)

## Migrations

One new Alembic migration: `add_pool_user_locks_table`. Creates `pool_user_locks` with composite PK `(pool_id, user_id)`, FK to `pools.id` and `users.id`. No changes to existing tables.

## Testing Philosophy

### CSV export tests
Verify content, headers, sort order, and auth. A multi-entry pool with two users ensures all entries appear. A non-admin caller verifies 403. An empty pool verifies the header row is still returned.

### User lock tests
Test the full lifecycle: lock → attempt entry create → 423; lock → attempt pick create → 423; unlock → attempt entry create → 200. Verify login succeeds for a locked user. Verify admin transfer still works on a locked user's entry. Verify lock in pool A does not affect pool B.

### Lock time picker tests
Backend: verify `_parse_lock_time` handles ISO, space-separated, and two-digit-second formats. Verify `PATCH /pools/{pool_id}` with a valid lock_time string updates correctly. Frontend: unit test the `toUtcIso` conversion function for ET→UTC, CT→UTC, DST boundary cases.

### Lock enforcement regression tests
After adding the pool user lock check, existing pick and entry tests must still pass — the lock only fires when a `pool_user_locks` row exists.

## Documentation Plan

### `TESTING.md` updates

**Audience:** Developers

Add the three new test areas (CSV export, user lock lifecycle, lock time picker) to the test overview table. Update test counts.

## Risks / Trade-offs

### Lock check adds one DB query per pick/entry creation

**Risk:** Every pick submission and entry creation now runs an additional `SELECT` on `pool_user_locks`. This table will typically be small (only locked users), so the query is fast. The performance impact is negligible at current scale.

**Mitigation:** The query is indexed by `(pool_id, user_id)` via the composite primary key. No additional index is needed.

### Timezone conversion relies on browser Intl API

**Risk:** `Intl.DateTimeFormat` behavior can differ across browsers, particularly for DST boundary handling. An incorrect conversion would set the wrong lock time.

**Mitigation:** The `toUtcIso` conversion function is unit-tested with known ET→UTC, CT→UTC, and DST-boundary inputs before ship. The UI also displays the converted UTC time for admin confirmation before saving.

### Admin console League Management section is largely stub UI

**Risk:** The existing Create/Modify/Delete League buttons in the admin console have no handlers. Adding the lock time picker alongside broken UI may cause confusion.

**Mitigation:** Only wire up what is in scope for this change. The lock time picker is added to the League Management section and clearly scoped. Existing stub buttons are left as-is (separate cleanup change).
