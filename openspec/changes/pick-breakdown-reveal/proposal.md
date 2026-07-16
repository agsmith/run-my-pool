## Why

In a Survivor Pool, strategy depends on knowing how the rest of the pool picked — but revealing picks before games lock would allow users to copy each other. Once a pick can no longer be changed (the game has kicked off), showing the pool-wide breakdown adds transparency and engagement without compromising game integrity.

## What Changes

- New backend endpoint: `GET /picks/pool/{pool_id}/week/{week}/breakdown` — returns a per-team pick count for alive entries, only for games that have already started
- New frontend panel on the entries page — displays above the entries grid showing a bar chart of team pick counts for the currently viewed week, visible only when at least one game in that week has started
- The breakdown rolls in progressively as games kick off throughout the week (Thursday → Sunday 1pm → Sunday afternoon → Sunday night → Monday night)
- Admin-corrected picks are reflected in the breakdown immediately (no special handling — breakdown always queries current pick state)

## Capabilities

### New Capabilities
- `pick-breakdown-reveal`: Pool-wide pick breakdown panel showing team pick counts after game kickoff, with progressive reveal as games start throughout the week

### Modified Capabilities
<!-- None — no existing spec-level behavior changes -->

## Impact

- **Backend**: New route in `picks.py` — joins `Pick`, `Entry`, `Schedule` tables; no schema changes
- **Frontend**: New UI panel in `pages/pool/[id]/entries.js` — appears above the entries grid
- **No breaking changes**
- **No new dependencies**
