## 1. Backend — Schema

- [x] 1.1 Add `PickBreakdownItem` Pydantic schema to `rmp/backend/schemas.py` (fields: `team`, `team_id`, `team_name`, `team_abbrv`, `team_logo`, `count`)

## 2. Backend — Endpoint

- [x] 2.1 Add `GET /picks/pool/{pool_id}/week/{week}/breakdown` route to `rmp/backend/picks.py` per design D1
- [x] 2.2 Verify route is accessible via the existing router registration in `routers.py` (no additional registration needed — picks router is already included)

## 3. Backend — Tests

- [x] 3.1 Add tests for the breakdown endpoint in `rmp/backend/tests/test_picks.py`:
  - No games started → empty array
  - Some games started → only started-game teams returned
  - Eliminated entries excluded from counts
  - Admin-overridden pick reflected correctly
  - Results sorted by count descending

## 4. Frontend — State and Fetch

- [x] 4.1 Add `breakdownData` and `breakdownLoading` state to `pages/pool/[id]/entries.js`
- [x] 4.2 Add `fetchBreakdown(week)` function per design D3
- [x] 4.3 Add `useEffect` to call `fetchBreakdown` whenever `selectedWeek` changes

## 5. Frontend — Panel Component

- [x] 5.1 Add `PickBreakdownPanel` component to `pages/pool/[id]/entries.js` per design D4
- [x] 5.2 Render `<PickBreakdownPanel>` above the entries grid, passing `breakdownData` and `selectedWeek`

## 6. Verification

- [x] 6.1 Run backend test suite (`pytest tests/ -q`) and confirm all tests pass
- [x] 6.2 Run frontend test suite (`npm test`) and confirm all tests pass
- [ ] 6.3 Manual test: view entries page for a week with no started games — confirm panel is hidden
- [ ] 6.4 Manual test: view entries page for a week with started games — confirm panel shows correct counts and bars
- [ ] 6.5 Manual test: switch between weeks — confirm panel updates correctly
