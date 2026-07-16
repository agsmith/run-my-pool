# Design: lambda-and-test-fixes

Targeted bug fixes for the NFL score updater Lambda and pre-existing auth test failures.

## Context

**Lambda**: `lambda/src/nfl_game_updater.py` has two debugging artifacts left in place: (1) the `is_nfl_game_time()` guard was commented out, causing the function to run full processing on every EventBridge trigger regardless of time or day; (2) `get_current_nfl_week()` was commented out and replaced with a `for current_week in range(1, 18)` loop, causing 17 ESPN API calls and 17 DB write passes per invocation. Additionally, `get_current_nfl_week()` is defined twice — a duplicate at line 190 that was introduced alongside the loop workaround.

**Tests**: `rmp/backend/tests/test_auth.py` login tests use `data=` (form-encoded) and `"username"` as the key, but the `/auth/login` endpoint takes a JSON body with `"email"` as the field name (`def login(user: schemas.UserCreate, ...)`). This has caused 4 login-related tests to return 422 since the tests were written. A fifth test (`test_create_access_token`) fails because it reads `SECRET_KEY` from the environment after the `auth` module has already loaded with the default value — the env override in `setup_test_env` happens too late.

No `docs/dev/architecture.md` exists in the project.

## References

- `lambda/src/nfl_game_updater.py` — the functions `is_nfl_game_time()`, `get_current_nfl_week()`, and `lambda_handler()` are all well-implemented; only the call sites need fixing.
- `rmp/backend/auth.py:81` — `def login(user: schemas.UserCreate, ...)` — JSON body, `email` field.
- `rmp/backend/auth.py:13` — `SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey")` — module-level constant, loaded at import time.

## Goals / Non-Goals

**Goals:**

- Lambda processes only the current NFL week per invocation
- Lambda skips invocations outside NFL game hours
- Duplicate `get_current_nfl_week()` removed
- All 5 failing auth tests pass
- No currently-passing tests broken

**Non-Goals:**

- Rewriting the week calculation logic (it's correct)
- Improving the `is_nfl_game_time()` heuristic (it's reasonable)
- Fixing the broader pre-existing conftest login bug (affects `authenticated_client` fixture — separate scope)
- Any Lambda infrastructure changes

## Decisions

### D1: Uncomment `is_nfl_game_time()` guard as-is

**Decision:** Restore the guard block by uncommenting it. The function is correctly implemented — it checks day of week and hour in ET, covering Sunday/Monday/Thursday nights and late-season Saturdays. It was commented out, not deleted, indicating it was intentionally bypassed temporarily.

```python
# lambda/src/nfl_game_updater.py — lambda_handler(), restored guard

# Check if it's actually game time
if not is_nfl_game_time():
    logger.info("Not during NFL game time, skipping update")
    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': 'Skipped - not during NFL game time',
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
    }
```

**Alternative considered:** Leave it commented and rely on EventBridge schedule alone. Rejected — EventBridge triggers on a fixed schedule; without the guard, every trigger hits the ESPN API and writes to RDS even at 3am on a Tuesday.

---

### D2: Replace week loop with `get_current_nfl_week()` call

**Decision:** Replace `for current_week in range(1, 18):` with `current_week = get_current_nfl_week()` and move the body out of the loop. The function is already defined and correct.

```python
# lambda/src/nfl_game_updater.py — lambda_handler(), restored single-week processing

# Get current week
current_week = get_current_nfl_week()
logger.info(f"Processing games for week {current_week}")

# Fetch game results from ESPN API
game_results = fetch_nfl_game_results(current_week)
logger.info(f"Fetched {len(game_results)} game results for week {current_week}")

# Update database with results
updates_made = update_game_results(db, game_results)

# Update picks based on game results
picks_updated = update_picks_results(db, game_results)

# Eliminate losing entries
entries_eliminated = eliminate_losing_entries(db)

# Commit all changes
db.commit()

response = {
    'statusCode': 200,
    'body': json.dumps({
        'message': 'Successfully updated NFL game results',
        'week': current_week,
        'games_updated': updates_made,
        'picks_updated': picks_updated,
        'entries_eliminated': entries_eliminated,
        'timestamp': datetime.now(timezone.utc).isoformat()
    })
}
logger.info(f"Process completed successfully: {response['body']}")
return response
```

**Alternative considered:** Keep the loop but add `break` after the first iteration. Rejected — masking the bug rather than fixing it.

---

### D3: Remove duplicate `get_current_nfl_week()` at line 190

**Decision:** Delete the second definition (lines 190–206). The first definition at line 19 is identical in logic. Python uses the last definition when a name is defined twice — removing the duplicate makes the code unambiguous and reduces confusion.

**Alternative considered:** Keep both, add a comment. Rejected — duplicates are dead code, full stop.

---

### D4: Fix auth tests — `data=` → `json=`, `"username"` → `"email"`

**Decision:** Update all four login test cases in `TestAuthEndpoints` to send JSON bodies with the `"email"` key, matching the actual endpoint signature.

```python
# Before (broken):
login_data = {"username": test_user_data["email"], "password": test_user_data["password"]}
response = client.post("/auth/login", data=login_data)

# After (correct):
response = client.post("/auth/login", json={
    "email": test_user_data["email"],
    "password": test_user_data["password"]
})
```

**Alternative considered:** Change the login endpoint to accept form data. Rejected — the endpoint is working correctly in production; the tests are wrong, not the endpoint.

---

### D5: Fix `test_create_access_token` — use default key for decoding

**Decision:** The `SECRET_KEY` is read at module load time (`SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey")`). The `setup_test_env` fixture sets the env var after the module is imported. The test should decode using the actual constant value the module used — `"supersecretkey"` — or import `SECRET_KEY` directly from `auth`.

```python
# After (correct):
from auth import create_access_token, SECRET_KEY

def test_create_access_token(self):
    test_data = {"sub": "test@example.com"}
    token = create_access_token(test_data)

    assert isinstance(token, str)
    assert len(token) > 0

    decoded = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    assert decoded["sub"] == "test@example.com"
    assert "exp" in decoded
```

**Alternative considered:** Patch `auth.SECRET_KEY` in the test. Rejected — more indirection, less clear. Importing the actual constant directly is the right approach.

## Testing Philosophy

### Auth test fixes

Run `pytest tests/test_auth.py -v` and verify all tests pass. Pay attention that the previously-failing 5 tests now pass and that the previously-passing tests (`test_verify_password_*`, `test_get_password_hash`, `test_register_*`) remain green.

### Lambda changes

The Lambda cannot be unit-tested easily (requires AWS credentials + RDS). The changes are mechanical uncomments/removals — visual review of the `lambda_handler` function body is the primary verification. The `dev_nfl_game_updater.py` file in the lambda directory may provide a local test harness.

## Risks / Trade-offs

### Game-time guard re-enabled in off-season

**Risk:** `is_nfl_game_time()` returns `False` in July (month not in `[9,10,11,12,1,2]`). Re-enabling it means the Lambda will skip all invocations during off-season — which is correct, but means no score updates will happen if triggered manually during development.

**Mitigation:** Comment clearly in the code that the guard can be temporarily commented out for local testing. This is the same state it was in before — the guard was clearly known and intentional.

### Single-week processing misses completed past weeks

**Risk:** If a game result was missed (ESPN API was down, Lambda failed), `get_current_nfl_week()` returns the current week and past weeks are never re-checked.

**Mitigation:** This is an acceptable tradeoff — the Lambda is designed for real-time updates, not historical backfill. The admin `correct_pick` endpoint exists for manual corrections. The previous loop-all-weeks approach was a debug workaround that had its own problems (redundant writes, stale result overwriting).
