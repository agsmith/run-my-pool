## Why

Two unrelated but similarly-scoped issues need fixing before they cause problems in production or obscure real test failures:

1. The NFL score updater Lambda loops all 17 weeks on every invocation and has its game-time guard commented out — likely from a debugging session that was never cleaned up. This makes every run 17× more expensive than necessary and fires ESPN API calls at all hours regardless of whether games are being played.

2. Five backend auth tests have been failing since the test suite was written. The tests send login requests as form-encoded data (`data=`) but the login endpoint expects a JSON body (`json=`). Additionally, a `SECRET_KEY` mismatch causes the JWT decode test to fail. These aren't flaky tests — they have never passed. Broken tests provide no value and mask real failures.

## What Changes

- **Lambda**: Uncomment `get_current_nfl_week()` call and remove the `for current_week in range(1, 18)` loop — process only the current week per invocation
- **Lambda**: Uncomment the `is_nfl_game_time()` guard block — skip processing when no games are being played
- **Lambda**: Remove the duplicate `get_current_nfl_week()` function definition (lines 190–206)
- **Tests**: Fix `test_auth.py` login tests — change `data=` to `json=`, change `"username"` key to `"email"` key
- **Tests**: Fix `test_create_access_token` — align the `SECRET_KEY` used for decoding with the key the module was loaded with

## Capabilities

### New Capabilities

_(none)_

### Modified Capabilities

_(none — these are bug fixes, not behavior changes)_

## Impact

- **Lambda**: `lambda/src/nfl_game_updater.py` — 3 targeted edits
- **Tests**: `rmp/backend/tests/test_auth.py` — login test fixes
- **No API changes, no schema changes, no frontend changes**
- **Production behavior**: Lambda runs will skip non-game-time invocations (correct behavior, previously bypassed) and process only the current week (correct behavior, previously over-broad)
