# Design: comprehensive-season-test-suite

## Context

RunMyPool is a FastAPI + SQLAlchemy + MySQL application for managing NFL survivor pools. The backend exposes RESTful endpoints for auth, pools, entries, picks, schedule, and message boards. Tests currently cover individual endpoints in isolation (unit/integration style). No tests simulate a multi-user, multi-week season under realistic conditions, and several features required for realistic season operation are missing or broken.

This design covers four implementation areas:
1. **Bug fix** — `admin.py` crashes when accessing `User.username` (field doesn't exist; use `User.email`)
2. **Auto-pick** — assign a team at lock time for entries with no pick
3. **Admin pick edit** — allow pool admins to override the team on any pick
4. **Message board rate limiting** — 5 messages per user per 10-minute rolling window
5. **Test suites** — scenario (season simulation) and security (OWASP Top 10)

No `docs/dev/architecture.md` exists in the project.

## References

- Existing `admin.py` — source of the `User.username` crash; documents current admin endpoint patterns
- Existing `picks.py` — lock enforcement logic to be partially bypassed by admin edit
- Existing `message_board.py` — insertion logic that will gain rate limit check
- Existing `entries.py` — lock time comparison pattern reused for auto-pick trigger
- Existing `conftest.py` — SQLite test DB setup, fixture patterns to extend

## Goals / Non-Goals

**Goals:**

- Fix `User.username` AttributeError in `admin.py`
- Implement auto-pick at lock time using most-popular-team strategy
- Implement `PATCH /admin/pools/{pool_id}/picks/{pick_id}` for admin pick override
- Implement 5-per-10-minute rate limit on message board posts
- Write `test_scenario_season.py` — multi-user, multi-week season simulation
- Write `test_security.py` — OWASP Top 10 coverage with `@pytest.mark.security`
- All new tests run in CI on every push

**Non-Goals:**

- Email notifications for auto-pick events
- Frontend changes
- Rate limiting on endpoints other than message board
- Automated lock triggering (lock time is still enforced per-request; auto-pick is triggered by a new endpoint or Lambda step, not a background scheduler)
- Tie-game handling (not yet defined; tests will document the gap)

## Decisions

### D1: Fix User.username → User.email in admin.py

**Decision:** Replace all references to `User.username` with `User.email` throughout `admin.py`. The `User` model has no `username` field — it uses `email` as the sole string identifier. Both `transfer_entry` and `delete_entry_admin` crash at runtime because of this.

```python
# rmp/backend/admin.py (affected lines — before)
new_owner = db.query(models.User).filter(models.User.username == transfer_data.to_username).first()
...
old_username = current_owner.username
...
owner_username = entry_owner.username if entry_owner else "unknown"

# rmp/backend/admin.py (after)
new_owner = db.query(models.User).filter(models.User.email == transfer_data.to_email).first()
...
old_email = current_owner.email
...
owner_email = entry_owner.email if entry_owner else "unknown"
```

The `EntryTransfer` schema field `to_username` is renamed to `to_email` and its type remains `str`. All audit log references updated accordingly.

**Alternative considered:** Add a `username` column to `User`. Rejected — the application uses email as the identifier everywhere else; adding username just to satisfy admin.py would be inconsistent.

---

### D2: Auto-pick at lock time — trigger and strategy

**Decision:** Auto-pick is triggered by a new endpoint `POST /admin/pools/{pool_id}/lock-week/{week}`. When called, it:
1. Verifies caller is pool admin
2. Sets `pool.lock_time` to now (if not already past)
3. For every alive entry in the pool that has no pick for `week`, selects the most popular team among alive entries that *do* have a pick, excluding teams already used by that entry
4. Creates a pick with `locked=True` for each entry that was missing one
5. Logs each auto-pick to audit

The "most popular team" is: the team abbreviation with the highest count of `Pick.week == week AND Pick.entry_id IN (alive entry ids for this pool)`, excluding teams already used by the target entry across all weeks.

```python
# rmp/backend/admin.py

@router.post("/pools/{pool_id}/lock-week/{week}")
def lock_week(
    pool_id: str,
    week: int,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
):
    """Lock the week for a pool and auto-pick for entries with no pick."""
    if not verify_admin_access(pool_id, current_user, db):
        raise HTTPException(status_code=403, detail="Admin access required")

    pool = db.query(models.Pool).filter(models.Pool.id == pool_id).first()
    if not pool:
        raise HTTPException(status_code=404, detail="Pool not found")

    # Lock the pool if not already locked
    now = datetime.utcnow()
    if pool.lock_time is None or pool.lock_time > now:
        pool.lock_time = now

    # Find alive entries
    alive_entries = (
        db.query(models.Entry)
        .filter(models.Entry.pool_id == pool_id, models.Entry.alive == True)
        .all()
    )
    alive_ids = {e.id for e in alive_entries}

    # Entries missing a pick for this week
    entries_with_pick = {
        p.entry_id
        for p in db.query(models.Pick)
        .filter(models.Pick.entry_id.in_(alive_ids), models.Pick.week == week)
        .all()
    }
    entries_needing_pick = [e for e in alive_entries if e.id not in entries_with_pick]

    # Popularity map: team → count of alive picks this week
    popularity = {}
    for p in db.query(models.Pick).filter(
        models.Pick.entry_id.in_(alive_ids), models.Pick.week == week
    ).all():
        popularity[p.team] = popularity.get(p.team, 0) + 1

    auto_picks_created = 0
    for entry in entries_needing_pick:
        # Teams already used by this entry across all weeks
        used = {
            p.team
            for p in db.query(models.Pick)
            .filter(models.Pick.entry_id == entry.id)
            .all()
        }
        # Best available team by popularity, excluding used teams
        candidate = next(
            (
                team
                for team, _ in sorted(popularity.items(), key=lambda x: -x[1])
                if team not in used
            ),
            None,
        )
        if candidate is None:
            # No valid team available — skip (edge case: all teams used)
            continue

        db_pick = models.Pick(
            id=str(uuid.uuid4()),
            entry_id=entry.id,
            week=week,
            team=candidate,
            locked=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(db_pick)
        log_admin_action(
            db=db,
            action="AUTO_PICK",
            admin_user_id=current_user.id,
            details=f"Auto-picked {candidate} for entry {entry.id} in week {week}",
            target_entity_type="pick",
            target_entity_id=db_pick.id,
            additional_data={
                "pool_id": pool_id,
                "entry_id": entry.id,
                "week": week,
                "team": candidate,
                "reason": "no_pick_at_lock",
            },
        )
        auto_picks_created += 1

    db.commit()
    return {
        "message": f"Week {week} locked",
        "pool_id": pool_id,
        "auto_picks_created": auto_picks_created,
    }
```

**Alternative considered:** Triggering auto-pick inside the Lambda game updater when results are processed. Rejected — the Lambda runs after games complete, which may be hours after lock. Auto-pick must fire at lock time so the pick is in place before any game starts.

---

### D3: Admin pick edit endpoint

**Decision:** New endpoint `PATCH /admin/pools/{pool_id}/picks/{pick_id}`. Pool admin can change the `team` field on any pick regardless of `locked` status. The pick is re-locked after the change. The old team and new team are written to audit.

```python
# rmp/backend/admin.py

class AdminPickUpdate(BaseModel):
    team: str

@router.patch("/pools/{pool_id}/picks/{pick_id}", response_model=schemas.PickOut)
def admin_update_pick(
    pool_id: str,
    pick_id: str,
    pick_update: AdminPickUpdate,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
):
    """Admin override: change the team on any pick, locked or not."""
    if not verify_admin_access(pool_id, current_user, db):
        raise HTTPException(status_code=403, detail="Admin access required")

    pick = (
        db.query(models.Pick)
        .join(models.Entry)
        .filter(models.Pick.id == pick_id, models.Entry.pool_id == pool_id)
        .first()
    )
    if not pick:
        raise HTTPException(status_code=404, detail="Pick not found in this pool")

    # Verify the new team hasn't been used by this entry in another week
    team_conflict = (
        db.query(models.Pick)
        .filter(
            models.Pick.entry_id == pick.entry_id,
            models.Pick.team == pick_update.team,
            models.Pick.id != pick_id,
        )
        .first()
    )
    if team_conflict:
        raise HTTPException(
            status_code=400,
            detail=f"Team {pick_update.team} already used by this entry in week {team_conflict.week}",
        )

    old_team = pick.team
    pick.team = pick_update.team
    pick.locked = True
    pick.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(pick)

    log_admin_action(
        db=db,
        action="ADMIN_PICK_EDIT",
        admin_user_id=current_user.id,
        details=f"Changed pick from {old_team} to {pick_update.team}",
        target_entity_type="pick",
        target_entity_id=pick_id,
        additional_data={
            "pool_id": pool_id,
            "entry_id": pick.entry_id,
            "week": pick.week,
            "old_team": old_team,
            "new_team": pick_update.team,
            "admin_email": current_user.email,
        },
    )
    return pick
```

**Alternative considered:** Admin unlocks the pick, user changes it, re-locks. Rejected — creates race condition (game could start between unlock and re-lock) and requires two endpoints. Direct override is simpler and fully audited.

---

### D4: Message board rate limiting — DB query approach

**Decision:** Before inserting a new message, count how many messages the current user has posted to this pool in the last 10 minutes. If ≥ 5, return HTTP 429. No Redis or external state required.

```python
# rmp/backend/message_board.py

RATE_LIMIT_COUNT = 5
RATE_LIMIT_WINDOW_MINUTES = 10

@router.post("/pool/{pool_id}", response_model=schemas.MessageBoardOut)
def post_message(pool_id: str, message: schemas.MessageBoardCreate,
                 current_user: models.User = Depends(deps.get_current_user),
                 db: Session = Depends(deps.get_db)):
    # ... existing membership check ...

    # Rate limit check
    window_start = datetime.utcnow() - timedelta(minutes=RATE_LIMIT_WINDOW_MINUTES)
    recent_count = (
        db.query(models.MessageBoard)
        .filter(
            models.MessageBoard.pool_id == pool_id,
            models.MessageBoard.user_id == current_user.id,
            models.MessageBoard.created_at >= window_start,
        )
        .count()
    )
    if recent_count >= RATE_LIMIT_COUNT:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded: maximum {RATE_LIMIT_COUNT} messages per {RATE_LIMIT_WINDOW_MINUTES} minutes per pool.",
        )

    # ... existing insert logic ...
```

**Alternative considered:** Redis with sliding window counter. Rejected — adds an infrastructure dependency for a low-traffic feature. DB query on `created_at` is sufficient at this scale and requires no new services.

---

### D5: Test suite architecture — marks and fixtures

**Decision:** Two new test files alongside existing tests:

- `tests/test_scenario_season.py` — marked `@pytest.mark.scenario`
- `tests/test_security.py` — marked `@pytest.mark.security`

Both use the existing SQLite conftest fixture. A new `season_fixture` helper in conftest builds a complete pool state (10 users, 10 entries, schedule seeded for weeks 1–3) reusable across scenario tests.

```python
# rmp/backend/tests/conftest.py (additions)

import pytest

def pytest_configure(config):
    config.addinivalue_line("markers", "scenario: multi-week season simulation tests")
    config.addinivalue_line("markers", "security: OWASP Top 10 security tests")


@pytest.fixture
def season_setup(client, db_session):
    """
    Build a realistic pool state:
    - 1 pool admin + 9 regular users (10 total)
    - 10 entries (one per user)
    - 2 weeks of NFL schedule seeded in the DB
    Returns: dict with tokens, pool_id, entry_ids
    """
    import models
    from datetime import datetime, timedelta

    users = []
    tokens = []
    for i in range(10):
        email = f"player{i}@season.test"
        client.post("/auth/register", json={"email": email, "password": "Pass1234!"})
        resp = client.post("/auth/login", json={"email": email, "password": "Pass1234!"})
        tokens.append(resp.json()["access_token"])
        user = db_session.query(models.User).filter(models.User.email == email).first()
        users.append(user)

    admin_token = tokens[0]
    headers = lambda t: {"Authorization": f"Bearer {t}"}

    pool_resp = client.post(
        "/pools/create",
        json={"name": "Season Test Pool", "is_private": False, "rule_values": []},
        headers=headers(admin_token),
    )
    pool_id = pool_resp.json()["id"]

    entry_ids = []
    for i, token in enumerate(tokens):
        e = client.post(
            "/entries/create",
            json={"pool_id": pool_id, "name": f"Entry {i}"},
            headers=headers(token),
        )
        entry_ids.append(e.json()["id"])

    # Seed two NFL teams and a week-1 game
    t1 = models.Team(id=1, name="Team A", abbrv="TA", logo="/nfl/ta.svg")
    t2 = models.Team(id=2, name="Team B", abbrv="TB", logo="/nfl/tb.svg")
    db_session.add_all([t1, t2])
    game = models.Schedule(
        game_id=9001,
        week_num=1,
        home_team_id=1,
        away_team_id=2,
        start_time=datetime.utcnow() + timedelta(hours=2),
        winning_team_id=99,
    )
    db_session.add(game)
    db_session.commit()

    return {
        "pool_id": pool_id,
        "tokens": tokens,
        "entry_ids": entry_ids,
        "users": users,
        "admin_token": admin_token,
    }
```

**Alternative considered:** Parametrized test data via JSON fixtures. Rejected — the scenario tests need live HTTP calls through the actual API stack to be meaningful; static JSON can't exercise lock enforcement or audit logging.

## Data Storage

No new tables. Existing schema is sufficient:
- `picks.locked` (Boolean) — already present; set to `True` by auto-pick and admin edit
- `audit_logs.details` (Text JSON blob) — captures all new admin actions
- `message_board.created_at` (DateTime) — used for rate limit window query

## Data Structures

```python
# rmp/backend/admin.py

class AdminPickUpdate(BaseModel):
    team: str  # Team abbreviation (e.g., "NE", "KC")

# EntryTransfer schema change:
class EntryTransfer(BaseModel):
    entry_id: str
    to_email: str  # was: to_username
```

```python
# Lock-week response (inline dict, no new schema needed)
{
    "message": "Week 1 locked",
    "pool_id": "uuid",
    "auto_picks_created": 3
}
```

## Interfaces

### REST API — Admin additions

| Method | Path | Request | Response | Description |
|---|---|---|---|---|
| `POST` | `/admin/pools/{pool_id}/lock-week/{week}` | — | `{"message", "auto_picks_created"}` | Lock week and auto-pick for missing entries |
| `PATCH` | `/admin/pools/{pool_id}/picks/{pick_id}` | `AdminPickUpdate` | `PickOut` | Override any pick's team |

### REST API — Message board change

| Method | Path | New behavior |
|---|---|---|
| `POST` | `/messages/pool/{pool_id}` | Returns `429` if user has posted ≥ 5 times in last 10 min |

### Admin endpoint change

`POST /admin/pools/{pool_id}/transfer-entry` body field `to_username` → `to_email`.

## Implementation Detail

All implementation lives in `rmp/backend/admin.py` and `rmp/backend/message_board.py`. No new files required for the feature code. The test files are new.

See Decisions D1–D4 for complete implementation code.

## Testing Philosophy

### Season scenario tests

`test_scenario_season.py` tells the story of a complete survivor pool season. Tests are ordered and build on each other using the `season_setup` fixture: users register, create entries, submit picks, the pool admin locks the week (triggering auto-pick for entries without a pick), game results are simulated by directly writing to the DB, and the Lambda elimination logic is invoked via the existing `eliminate_losing_entries` function imported directly. Subsequent weeks repeat the pattern with a shrinking survivor pool. The final test in the file verifies that the last surviving entry is identifiable and audit logs are complete for every action taken.

### Security tests

`test_security.py` takes an adversarial stance. Each test class maps to an OWASP Top 10 category. Tests for broken access control (A01) verify that User A cannot read, modify, or delete User B's picks or entries — using valid tokens for both users and confirming 403/404 responses. Injection tests (A03) submit SQL metacharacters and script tags in pool names, pick team fields, and message body content, then verify the stored value is sanitized or the request rejected. Authentication failure tests (A07) replay expired JWTs, submit tokens with tampered signatures, and attempt to use a password reset token twice. Security misconfiguration tests (A05) confirm that the `/users/` endpoint (currently unauthenticated) is documented as a known gap, and that the `/pools/` list endpoint behaves correctly for unauthenticated callers.

### Rate limit tests

Rate limit tests live in `test_message_board.py` alongside existing message board tests. They post 5 messages rapidly in a loop, verify all 5 succeed, then confirm the 6th returns 429 with the expected error message. A second test verifies that after the 10-minute window passes (simulated by directly setting `created_at` on the old messages to >10 minutes ago in `db_session`), a new post succeeds.

### Admin feature tests

Admin endpoint tests in `test_admin.py` are extended with: lock-week triggering auto-pick for entries missing a pick, admin pick edit changing the team on a locked pick, and the fixed entry transfer using `to_email`. The `User.username` crash tests are updated to assert the endpoints now work correctly rather than crash.

## Risks / Trade-offs

### Auto-pick favors the same team when popularity is tied

**Risk:** If multiple teams are equally popular, the sorting is non-deterministic (Python dict ordering). Two entries with no pick may receive different or the same team based on iteration order.

**Mitigation:** Add a secondary sort key (e.g., team abbreviation alphabetically) to make the selection deterministic. Document this as the defined tie-breaking behavior.

### Rate limit window uses server UTC, not user's timezone

**Risk:** A user who posts at 11:58 PM and 12:03 AM may have their window reset unexpectedly because the window is a rolling 10 minutes from the earliest recent message, not calendar-time.

**Mitigation:** Rolling window is the correct semantics for spam prevention. This is intentional behavior, not a bug. Document it clearly in the 429 error message.

### Season scenario tests are slow

**Risk:** A full 18-week simulation with 10 users and picks for each week could take 30–60 seconds or more in CI, adding meaningful time to the test suite.

**Mitigation:** The scenario tests are marked `@pytest.mark.scenario` and can be excluded from the fast pre-commit check with `pytest -m "not scenario"`. CI runs the full suite including scenarios on every push, but the marks allow local development to skip them.

### Admin pick edit allows bypassing team-uniqueness for the entry

**Risk:** An admin could theoretically change a pick to a team already used in a different week, violating the survivor pool rules.

**Mitigation:** The endpoint explicitly checks for team reuse across other weeks before accepting the change, returning 400 if a conflict is detected. This is enforced in D3.
