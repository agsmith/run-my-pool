## Why

Three related issues were discovered in the frontend entry management pages, two of which have security or correctness implications:

1. The backend does not enforce pool lock time on entry creation or deletion — the frontend check is purely cosmetic and trivially bypassed via direct API calls.
2. The entry detail page (`/league/[leagueId]/entries/[entryId]`) is an unreachable, non-rendering stub that has never been functional. It creates dead code and routing confusion.
3. Uncommitted frontend changes contain good work (pool lock UI enforcement, visual refinements, a real pick circle fix) that is blocked from being committed until the backend gap is closed.

## What Changes

- **Backend**: Add pool lock enforcement to `POST /entries/create` and `DELETE /entries/{entry_id}` — return HTTP 423 if the pool's `lock_time` is in the past
- **Frontend**: Delete `rmp/frontend/pages/league/[leagueId]/entries/[entryId].js` — dead route, no JSX return, no navigation pointing to it
- **Frontend**: Commit the three modified entry pages (`pool/[id]/entries.js`, `league/[leagueId]/entries.js`, `league/[leagueId]/entries/[entryId].js` → deleted) which contain pool lock UI guards, visual cleanup, and the `renderPickCircle` fix

## Capabilities

### New Capabilities

- `pool-lock-enforcement`: The system enforces pool lock time server-side — entry creation and deletion are rejected after `lock_time` with a clear error

### Modified Capabilities

_(none — no existing spec-level behavior changes; visual changes are implementation detail)_

## Impact

- **Backend**: `rmp/backend/entries.py` — two endpoints modified
- **Frontend**: `rmp/frontend/pages/league/[leagueId]/entries/[entryId].js` — deleted; `pool/[id]/entries.js` and `league/[leagueId]/entries.js` — committed with uncommitted changes applied
- **APIs**: `POST /entries/create` and `DELETE /entries/{entry_id}` now return `423 Locked` when pool is past lock time
- **No breaking changes** for normal usage — lock enforcement only activates after `pool.lock_time`
