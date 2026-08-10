## Why

The auth flows — registration, login, forgot password, and reset password — had significant test gaps. `GET /auth/me` had zero tests. The entire forgot-password and reset-password flows were untested. Several known behavioral gaps (no `is_active` enforcement, token reuse, reset token usable as access token) were undocumented in tests. The litmus pipeline was used to systematically discover, plan, and generate comprehensive coverage.

## What Changes

- **New**: 34 new tests added to `rmp/backend/tests/test_auth.py` covering `GET /auth/me`, `POST /auth/forgot-password`, `POST /auth/reset-password`, extended registration edge cases, and extended login edge cases
- **New**: `TestKnownBehaviorGaps` class (6 tests) documenting current broken/missing behaviors with `# KNOWN GAP` comments: `is_active` not enforced at login or `GET /auth/me`, deleted-user token not invalidated, no password complexity, audit events
- **Litmus workspace** at `litmus/auth-coverage/` — discover, plan, gaps, generate, and execute artifacts preserved for reference

## Capabilities

### Modified Capabilities

- `security-test-suite`: extended with comprehensive auth flow coverage; known behavior gaps documented in `TestKnownBehaviorGaps`

## Impact

- `rmp/backend/tests/test_auth.py` — 34 new tests appended; 5 new test classes
- `litmus/auth-coverage/` — litmus workspace artifacts (architecture, API surface, existing tests, use cases, plan, gaps, generate output)
- No production code changes
