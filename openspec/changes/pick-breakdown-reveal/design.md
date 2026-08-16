# Design: pick-breakdown-reveal

Add a pool-wide pick breakdown panel to the entries page, revealing team pick counts progressively as games kick off throughout the week.

## Context

The backend is FastAPI with synchronous SQLAlchemy (non-async). Routes follow the pattern in `picks.py` and `schedule.py` — plain `Session` dependency injection, Pydantic response schemas, router registered in `routers.py`.

The frontend is Next.js (Pages Router). The entries page (`pages/pool/[id]/entries.js`) already fetches schedule data per week on demand, maintains `selectedWeek` state, has an `isPoolLocked()` helper, and renders the entries grid. The new breakdown panel sits above that grid.

`Pick.team` stores the team abbreviation string (e.g. `"KC"`). `Pick.team_id` is a FK to the `teams` table which has `id`, `name`, `abbrv`, and `logo`. `Schedule` has `home_team_id`, `away_team_id`, and `start_time`. The join path for reveal logic is:

```
Pick.team_id → Team.id
Schedule: (home_team_id = Pick.team_id OR away_team_id = Pick.team_id) AND week_num = pick.week
```

No `docs/dev/architecture.md` exists in the project.

## Goals / Non-Goals

**Goals:**

- New backend endpoint `GET /picks/pool/{pool_id}/week/{week}/breakdown` returning per-team pick counts for alive entries, only for teams whose game has already started
- Frontend breakdown panel above the entries grid showing a bar chart of revealed pick counts
- Panel is hidden when no games in the selected week have started
- Panel updates to reflect whichever week the user is currently viewing
- Breakdown always reflects current pick state (admin overrides included automatically)

**Non-Goals:**

- Revealing picks for games that have not yet kicked off
- Showing eliminated entries in the breakdown
- Real-time polling / websocket updates (static on page load, user can refresh)
- Breakdown for non-current weeks that have no games started yet
- Historical breakdown for prior seasons

## Decisions

### D1: Reveal condition based on `Schedule.start_time < NOW()`

**Decision:** A team's picks are included in the breakdown only when `Schedule.start_time < datetime.now(utc)` for the game containing that team in the given week. This is evaluated at query time — no pre-computation or caching needed.

```python
# rmp/backend/picks.py  (new endpoint)
from datetime import datetime, timezone
from sqlalchemy import func, and_, or_

@router.get("/pool/{pool_id}/week/{week}/breakdown", response_model=List[PickBreakdownItem])
def get_pick_breakdown(
    pool_id: str,
    week: int,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
):
    """
    Return per-team pick counts for alive entries in a pool/week,
    only for teams whose game has already kicked off.
    """
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    # Subquery: team_ids with a started game this week
    started_team_ids = (
        db.query(models.Schedule.home_team_id)
        .filter(
            models.Schedule.week_num == week,
            models.Schedule.start_time < now,
        )
        .union(
            db.query(models.Schedule.away_team_id)
            .filter(
                models.Schedule.week_num == week,
                models.Schedule.start_time < now,
            )
        )
        .subquery()
    )

    rows = (
        db.query(
            models.Pick.team,
            models.Pick.team_id,
            models.Team.name.label("team_name"),
            models.Team.abbrv.label("team_abbrv"),
            models.Team.logo.label("team_logo"),
            func.count(models.Pick.id).label("count"),
        )
        .join(models.Entry, models.Pick.entry_id == models.Entry.id)
        .join(models.Team, models.Pick.team_id == models.Team.id)
        .filter(
            models.Entry.pool_id == pool_id,
            models.Entry.alive == True,
            models.Pick.week == week,
            models.Pick.team_id.in_(started_team_ids),
        )
        .group_by(
            models.Pick.team,
            models.Pick.team_id,
            models.Team.name,
            models.Team.abbrv,
            models.Team.logo,
        )
        .order_by(func.count(models.Pick.id).desc())
        .all()
    )

    return [
        PickBreakdownItem(
            team=row.team,
            team_id=row.team_id,
            team_name=row.team_name,
            team_abbrv=row.team_abbrv,
            team_logo=row.team_logo,
            count=row.count,
        )
        for row in rows
    ]
```

**Alternative considered:** Pre-computing breakdown on a schedule or caching in Redis. Rejected — this pool is small-scale, the query is a simple aggregation with indexes on `entry.pool_id`, `pick.week`, `pick.team_id`, and `schedule.week_num`. No caching needed.

---

### D2: Response schema — `PickBreakdownItem`

**Decision:** Return a flat list of items with team identity and count. No total is included in the response — the frontend sums counts itself. This keeps the API simple and lets the frontend decide how to display percentages.

```python
# rmp/backend/schemas.py  (additions)
from pydantic import BaseModel, Field
from typing import Optional

class PickBreakdownItem(BaseModel):
    team: str = Field(description="Team abbreviation string as stored on the pick.")
    team_id: int = Field(description="Team ID from the teams table.")
    team_name: str = Field(description="Full team name.")
    team_abbrv: str = Field(description="Team abbreviation (e.g. KC, PHI).")
    team_logo: Optional[str] = Field(default=None, description="Team logo filename.")
    count: int = Field(description="Number of alive entries that picked this team this week.")
```

**Alternative considered:** Including `total` and `percentage` in the response. Rejected — the frontend computes these anyway for display, and the total is just `sum(item.count)`.

---

### D3: Frontend panel placement and trigger

**Decision:** Render the breakdown panel inside the entries page, above the entries grid, conditioned on `breakdownData.length > 0`. The panel fetches from the new endpoint whenever `selectedWeek` changes (or on initial load). An empty array means no games have started yet — panel is hidden.

```jsx
// rmp/frontend/pages/pool/[id]/entries.js  (additions)

// State
const [breakdownData, setBreakdownData] = useState([]);
const [breakdownLoading, setBreakdownLoading] = useState(false);

// Fetch on selectedWeek change
const fetchBreakdown = async (week) => {
  if (!week || !id) return;
  setBreakdownLoading(true);
  try {
    const token = localStorage.getItem('access_token');
    const res = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL}/picks/pool/${id}/week/${week}/breakdown`,
      { headers: { Authorization: `Bearer ${token}` } }
    );
    if (res.ok) {
      setBreakdownData(await res.json());
    } else {
      setBreakdownData([]);
    }
  } catch {
    setBreakdownData([]);
  } finally {
    setBreakdownLoading(false);
  }
};

useEffect(() => {
  if (selectedWeek) fetchBreakdown(selectedWeek);
}, [selectedWeek]);
```

**Alternative considered:** Always showing the panel with "no data yet" messaging. Rejected — empty state adds noise. The panel should only appear when there is something to show.

---

### D4: Bar chart rendering — inline CSS bars, no library

**Decision:** Render the breakdown as a simple percentage bar chart using inline `div` widths. No charting library needed — the data is a ranked list of 1–32 items with counts. Each bar's width is `(count / total) * 100%`.

```jsx
// rmp/frontend/pages/pool/[id]/entries.js  (PickBreakdownPanel component)

function PickBreakdownPanel({ data, week }) {
  const total = data.reduce((sum, item) => sum + item.count, 0);
  if (total === 0) return null;

  return (
    <div style={{
      backgroundColor: '#f8f9fa',
      border: '1px solid #dee2e6',
      borderRadius: '8px',
      padding: '1rem 1.25rem',
      marginBottom: '1.5rem',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', marginBottom: '0.75rem', gap: '0.5rem' }}>
        <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: '600' }}>
          Week {week} Pick Breakdown
        </h3>
        <span style={{
          fontSize: '0.75rem',
          backgroundColor: '#dc3545',
          color: '#fff',
          padding: '2px 8px',
          borderRadius: '10px',
          fontWeight: '500',
        }}>
          🔒 Locked
        </span>
        <span style={{ fontSize: '0.8rem', color: '#666', marginLeft: 'auto' }}>
          {total} alive {total === 1 ? 'entry' : 'entries'}
        </span>
      </div>

      {data.map((item) => {
        const pct = Math.round((item.count / total) * 100);
        return (
          <div key={item.team_id} style={{ marginBottom: '0.4rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            {item.team_logo && (
              <img
                src={`/nfl/${item.team_abbrv.toLowerCase()}.svg`}
                alt={item.team_abbrv}
                style={{ width: '20px', height: '20px', objectFit: 'contain', flexShrink: 0 }}
              />
            )}
            <span style={{ width: '36px', fontSize: '0.8rem', fontWeight: '500', flexShrink: 0 }}>
              {item.team_abbrv}
            </span>
            <div style={{ flex: 1, backgroundColor: '#e9ecef', borderRadius: '4px', height: '18px', overflow: 'hidden' }}>
              <div style={{
                width: `${pct}%`,
                minWidth: pct > 0 ? '4px' : '0',
                height: '100%',
                backgroundColor: '#667eea',
                borderRadius: '4px',
                transition: 'width 0.3s ease',
              }} />
            </div>
            <span style={{ width: '48px', fontSize: '0.8rem', color: '#555', textAlign: 'right', flexShrink: 0 }}>
              {item.count} ({pct}%)
            </span>
          </div>
        );
      })}
    </div>
  );
}
```

**Alternative considered:** A third-party chart library (recharts, chart.js). Rejected — adds bundle weight for a simple bar display that CSS handles cleanly.

---

## Data Structures

```python
# rmp/backend/schemas.py  (additions)

class PickBreakdownItem(BaseModel):
    team: str = Field(description="Team abbreviation string as stored on the pick.")
    team_id: int = Field(description="Team ID from the teams table.")
    team_name: str = Field(description="Full team name.")
    team_abbrv: str = Field(description="Team abbreviation (e.g. KC, PHI).")
    team_logo: Optional[str] = Field(default=None, description="Team logo filename.")
    count: int = Field(description="Number of alive entries that picked this team this week.")
```

## Interfaces

### REST API — Pick Breakdown

| Method | Path | Request | Response | Description |
|---|---|---|---|---|
| `GET` | `/picks/pool/{pool_id}/week/{week}/breakdown` | — | `PickBreakdownItem[]` | Returns per-team pick counts for alive entries in a pool/week, only for teams whose game has started. Empty array if no games started yet. |

**Error responses:**

| Status | Condition |
|---|---|
| `401` | Missing or invalid auth token |
| `404` | Pool not found (implicitly — no explicit check, returns empty array) |

### Frontend Panel

The `PickBreakdownPanel` component renders above the entries grid when `breakdownData.length > 0`. It shows:

- Panel header: "Week N Pick Breakdown" + 🔒 Locked badge + alive entry count
- One bar row per revealed team: logo, abbreviation, filled bar, count + percentage
- Sorted by count descending (highest pick share first)
- Hidden entirely when no games have started yet for the selected week

## Accessibility

### Visual Design

- Bar fill color (`#667eea`) is not the only indicator — count and percentage are shown as text alongside each bar.
- "Locked" badge uses red background with white text. Text label "🔒 Locked" provides a non-color indicator.
- All text meets WCAG 2.1 AA contrast minimums.

### Screen Reader Support

- Team logo `<img>` elements have `alt` set to the team abbreviation.
- Bar `<div>` elements are presentational and carry no semantic meaning — the count and percentage text alongside each bar conveys all information to screen readers.

### Keyboard Navigation

- The panel is purely informational — no interactive elements. No keyboard navigation concerns.

## Migrations

No schema changes. No migrations required.

**Deployment order:**

1. Deploy backend with new endpoint
2. Deploy frontend with new panel

Both are additive — either can deploy first without breaking the other. Frontend gracefully handles a missing endpoint (falls back to empty array, panel hidden).

## Testing Philosophy

### Reveal logic

Verify that picks for teams whose game has not yet started are excluded from the breakdown response. Test with a week containing multiple games at different start times — only the subset with `start_time < now` should appear. Test the boundary condition where `start_time == now` (should be excluded — strictly less than).

### Alive entries only

Verify that picks from eliminated entries (where `Entry.alive = False`) are not counted. Create test data with a mix of alive and eliminated entries picking the same team and confirm the count reflects alive entries only.

### Admin override reflection

Verify that after an admin changes a pick, the breakdown reflects the new team rather than the old one. No special handling needed — the query reads current `Pick.team`/`Pick.team_id` values.

### Empty response

Verify the endpoint returns an empty array (not an error) when no games have started for the week, when no entries exist, or when no picks have been made.

### Frontend panel visibility

Verify the panel renders when `breakdownData` is non-empty and is absent from the DOM when `breakdownData` is empty. Verify it updates when `selectedWeek` changes.

## Risks / Trade-offs

### Stale breakdown on page load

**Risk:** A user loads the entries page at 12:58pm Sunday. The breakdown shows Thursday's revealed picks. At 1:00pm, games kick off but the user's browser doesn't know — they see stale data until they navigate away and back, or manually refresh.

**Mitigation:** The breakdown is accurate at page load time and on week change. Users who want updated reveals can refresh the page. A polling mechanism or "Refresh" button can be added in a future iteration if needed.

### Pool not validated in breakdown endpoint

**Risk:** The endpoint joins `Entry.pool_id = pool_id` but does not verify the caller is a member of or authorized to view that pool. Any authenticated user could query breakdown data for any pool.

**Mitigation:** The breakdown data is post-lock (picks are immutable at this point) and intended for transparency within the pool. For the current single-tenant use case this is acceptable. Enforce pool membership checks if RunMyPool adds private pools with sensitive membership.
