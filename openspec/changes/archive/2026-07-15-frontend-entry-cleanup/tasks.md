## 1. Backend — Pool Lock Enforcement

- [x] 1.1 Add lock time check to `POST /entries/create` in `rmp/backend/entries.py` — after pool existence check, raise `HTTP 423` if `pool.lock_time` is set and `pool.lock_time < datetime.utcnow()`
- [x] 1.2 Add lock time check to `DELETE /entries/{entry_id}` in `rmp/backend/entries.py` — load the entry's pool, raise `HTTP 423` if locked
- [x] 1.3 Write pytest tests covering: create on locked pool (expect 423), create on unlocked pool (expect 200), create on pool with null lock_time (expect 200) — repeat same three cases for delete

## 2. Frontend — Delete Dead Route

- [x] 2.1 Delete `rmp/frontend/pages/league/[leagueId]/entries/[entryId].js`

## 3. Frontend — Commit Validated Changes

- [x] 3.1 Verify `pool/[id]/entries.js` uncommitted diff is correct — `isPoolLocked()` guard hides Create/Delete buttons, visual circle changes, removed legend
- [x] 3.2 Verify `league/[leagueId]/entries.js` uncommitted diff is correct — same visual changes, button positioning, removed legend; confirm lock guard is also applied to this view's Create/Delete buttons consistently
- [x] 3.3 Stage and verify all three changed files are clean (no unintended changes)

## 4. Verification

- [x] 4.1 Run backend tests: `pytest tests/ -v` — all pass
- [x] 4.2 Start local backend and manually test `POST /entries/create` against a pool with a past `lock_time` — confirm 423 response
- [x] 4.3 Start local backend and manually test `DELETE /entries/{entry_id}` against a locked pool — confirm 423 response
- [x] 4.4 Confirm Next.js route `/league/[leagueId]/entries/[entryId]` returns 404 after deletion
