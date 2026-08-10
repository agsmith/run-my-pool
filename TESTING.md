# RunMyPool — Test Suite Documentation

> **Backend:** 298 passed · 1 skipped · 0 failed · Coverage: 83%
> **Frontend:** 64 passed · 0 failed · 6 suites

---

## Quick Start

```bash
# Backend (Python / FastAPI)
cd rmp/backend
venv/bin/python -m pytest tests/ -v

# Run specific subsets by mark
venv/bin/python -m pytest tests/ -m season       # 17-week season simulation only
venv/bin/python -m pytest tests/ -m "gap"        # Tests documenting known enforcement gaps
venv/bin/python -m pytest tests/ -m "known_bug"  # Tests documenting known security bugs
venv/bin/python -m pytest tests/ -m scenario     # Existing scenario tests
venv/bin/python -m pytest tests/ -m security     # OWASP security tests
venv/bin/python -m pytest tests/ -m "not season" # Skip the slow season simulation

# Frontend (JavaScript / Next.js)
cd rmp/frontend
npm test
```

---

# Backend Tests

> Run with: `cd rmp/backend && venv/bin/python -m pytest tests/ -v`
>
> Filter by mark: `pytest -m scenario` · `pytest -m security` · `pytest -m season` · `pytest -m gap` · `pytest -m known_bug`

## Overview

235 tests across 21 files covering the full FastAPI backend. All run against an in-memory SQLite database — no Docker or MySQL required.

| Category | Tests | Mark | File |
|---|---|---|---|
| Admin operations | 43 | | `test_admin.py` |
| Authentication | 45 | | `test_auth.py` |
| Audit trail | 14 | | `test_audit.py` |
| Team eligibility | 9 | | `test_eligibility.py` |
| Entry elimination | 12 | | `test_elimination.py` |
| Entry lock enforcement | 7 | | `test_entries.py` |
| Lock time enforcement | 24 | `gap` | `test_lock_time.py` |
| Application health | 4 | | `test_main.py` |
| Message board | 14 | | `test_message_board.py` |
| Models & schemas | 10 | | `test_models.py` |
| Picks | 11 | | `test_picks.py` |
| Pools | 13 | | `test_pools.py` |
| Season scenarios | 8 | `scenario` | `test_scenario_season.py` |
| Schedule | 5 | | `test_schedule.py` |
| Security (OWASP + known bugs) | 17 | `security` `known_bug` | `test_security.py` |
| Users | 10 | | `test_users.py` |
| Utilities & config | 16 | | `test_utils.py` |
| Full season simulation | 26 | `season` | `test_z_full_season.py` |
| **Total** | **235** | | |

> **Note:** `test_z_full_season.py` is prefixed with `z_` to run last and avoid session-scoped DB fixture interference with function-scoped tests. Run with `pytest -m season` or `pytest tests/test_z_full_season.py`.

---

## Test Marks Reference

| Mark | Purpose | How to run |
|---|---|---|
| `season` | 17-week simulation with 750 users, 2000 entries, 2025 NFL schedule | `pytest -m season` |
| `gap` | Documents a known enforcement gap — asserts current (broken) behavior | `pytest -m gap` |
| `known_bug` | Documents a known security bug — asserts the bug exists | `pytest -m known_bug` |
| `scenario` | End-to-end season lifecycle scenarios | `pytest -m scenario` |
| `security` | OWASP security tests | `pytest -m security` |

Gap and known_bug tests PASS today by asserting broken behavior. When a gap or bug is fixed, these tests will need to be updated to assert the correct behavior.

---

## Season Simulation DB Lifecycle

The season simulation (`test_z_full_season.py`) uses a session-scoped SQLite file at `rmp/backend/test_season.db`. This file is:
- Created fresh at the start of each pytest session
- Deleted automatically on teardown
- Contains 750 users, 2000 entries, and 256 games from the 2025 NFL regular season

If the test run is interrupted and `test_season.db` is left on disk, delete it manually before the next run.

---

---

## Admin Operations (`test_admin.py`) — 17 tests

### `TestAdminEndpoints` — Core admin actions

| Test | What it verifies | Result |
|---|---|---|
| `test_transfer_entry_requires_auth` | Unauthenticated transfer returns 401 or 403 | ✅ PASSED |
| `test_transfer_entry_non_admin_forbidden` | Non-owner cannot transfer entries in another pool | ✅ PASSED |
| `test_transfer_entry_success` | Pool owner transfers entry ownership by email | ✅ PASSED |
| `test_delete_entry_admin_requires_auth` | Unauthenticated delete returns 401 or 403 | ✅ PASSED |
| `test_delete_entry_admin_non_admin_forbidden` | Non-admin cannot delete from another pool | ✅ PASSED |
| `test_delete_entry_admin_not_found` | Deleting non-existent entry returns 404 | ✅ PASSED |
| `test_delete_entry_admin_success` | Pool owner can delete any entry in their pool | ✅ PASSED |
| `test_verify_admin_access_pool_owner` | `verify_admin_access()` returns `True` for pool owner | ✅ PASSED |
| `test_verify_admin_access_non_member` | `verify_admin_access()` returns `False` for unrelated user | ✅ PASSED |

### `TestLockWeek` — Weekly lock and auto-pick

| Test | What it verifies | Result |
|---|---|---|
| `test_lock_week_creates_auto_pick` | Admin locking a week auto-assigns most-popular team to entries with no pick | ✅ PASSED |
| `test_lock_week_idempotent` | Locking the same week twice creates no duplicate picks | ✅ PASSED |
| `test_lock_week_non_admin_forbidden` | Non-admin calling lock-week returns 403 | ✅ PASSED |
| `test_lock_week_skips_entry_that_already_picked` | Entries with existing picks are not overwritten | ✅ PASSED |

### `TestAdminPickEdit` — Direct pick override

| Test | What it verifies | Result |
|---|---|---|
| `test_admin_update_pick_success` | Admin changes team on a locked pick | ✅ PASSED |
| `test_admin_update_pick_team_conflict` | Changing to an already-used team returns 400 | ✅ PASSED |
| `test_admin_update_pick_non_admin_forbidden` | Regular user cannot use admin pick edit endpoint | ✅ PASSED |
| `test_admin_update_pick_not_in_pool` | Editing a pick from a different pool returns 404 | ✅ PASSED |

---

## Authentication (`test_auth.py`) — 45 tests

Generated via the litmus test generation pipeline (workspace at `litmus/auth-coverage/`).

### `TestAuthFunctions`

| Test | What it verifies | Result |
|---|---|---|
| `test_verify_password_success` | Correct password passes bcrypt verification | ✅ PASSED |
| `test_verify_password_failure` | Wrong password fails bcrypt verification | ✅ PASSED |
| `test_get_password_hash` | Password hashed with bcrypt (starts with `$2b$`) | ✅ PASSED |
| `test_create_access_token` | JWT created with correct `sub` and `exp` claims | ✅ PASSED |

### `TestAuthEndpoints`

| Test | What it verifies | Result |
|---|---|---|
| `test_register_success` | Registration returns 200 with user data (no password hash) | ✅ PASSED |
| `test_register_duplicate_email` | Duplicate email returns 400 | ✅ PASSED |
| `test_register_invalid_email` | Malformed email returns 422 | ✅ PASSED |
| `test_login_success` | Valid credentials return JWT access token | ✅ PASSED |
| `test_login_invalid_credentials` | Wrong password returns 401 | ✅ PASSED |
| `test_login_nonexistent_user` | Unknown email returns 401 | ✅ PASSED |
| `test_login_audit_logging` | Successful login triggers audit log event | ✅ PASSED |

---

## Entry Lock Enforcement (`test_entries.py`) — 7 tests

| Test | What it verifies | Result |
|---|---|---|
| `test_create_entry_locked_pool_returns_423` | Creating entry past lock time returns 423 | ✅ PASSED |
| `test_create_entry_unlocked_pool_returns_200` | Creating entry before lock time succeeds | ✅ PASSED |
| `test_create_entry_null_lock_time_returns_200` | Pools with no lock time accept entries freely | ✅ PASSED |
| `test_delete_entry_locked_pool_returns_423` | Deleting entry after lock time returns 423 | ✅ PASSED |
| `test_delete_entry_unlocked_pool_returns_200` | Deleting entry before lock time succeeds | ✅ PASSED |
| `test_delete_entry_null_lock_time_returns_200` | Deleting from pool with no lock time succeeds | ✅ PASSED |
| `test_create_entry_no_token_returns_403` | Unauthenticated entry creation returns 401 or 403 | ✅ PASSED |

---

## Application Health (`test_main.py`) — 4 tests

| Test | What it verifies | Result |
|---|---|---|
| `test_read_root` | `GET /` returns 200 | ✅ PASSED |
| `test_health_check` | `GET /health` returns `{"status":"healthy"}` | ✅ PASSED |
| `test_app_title` | App is named "RunMyPool API" | ✅ PASSED |
| `test_cors_headers` | CORS headers present on OPTIONS requests | ✅ PASSED |

---

## Message Board (`test_message_board.py`) — 14 tests

### `TestMessageBoardEndpoints`

| Test | What it verifies | Result |
|---|---|---|
| `test_list_messages_requires_auth` | Unauthenticated listing returns 401 or 403 | ✅ PASSED |
| `test_list_messages_requires_pool_membership` | Non-members cannot view messages | ✅ PASSED |
| `test_list_messages_empty_pool` | Members can list from an empty pool | ✅ PASSED |
| `test_post_message_success` | Member posts message; response includes `user_email` | ✅ PASSED |
| `test_post_message_too_long` | Message >250 chars returns 400 | ✅ PASSED |
| `test_post_message_empty` | Empty message returns 400 | ✅ PASSED |
| `test_post_message_requires_pool_membership` | Non-members cannot post | ✅ PASSED |
| `test_delete_message_success` | Owner can delete their own message | ✅ PASSED |
| `test_delete_message_wrong_user` | Cannot delete another user's message | ✅ PASSED |
| `test_delete_message_not_found` | Deleting non-existent message returns 404 | ✅ PASSED |

### `TestMessageBoardRateLimit`

| Test | What it verifies | Result |
|---|---|---|
| `test_rate_limit_allows_five_messages` | First 5 messages in 10 min succeed | ✅ PASSED |
| `test_rate_limit_blocks_sixth_message` | 6th message within 10 min returns 429 | ✅ PASSED |
| `test_rate_limit_resets_after_window` | After 10-min window, new posts succeed | ✅ PASSED |
| `test_rate_limit_is_per_user_per_pool` | Limit is scoped per user per pool | ✅ PASSED |

---

## Picks (`test_picks.py`) — 11 tests

| Test | What it verifies | Result |
|---|---|---|
| `test_create_pick_success` | Pick creation returns 200 with PickOut fields | ✅ PASSED |
| `test_create_pick_upserts_existing_week` | Re-submitting same week upserts the existing pick | ✅ PASSED |
| `test_create_pick_duplicate_team_rejected` | Same team in different week returns 400 | ✅ PASSED |
| `test_create_pick_wrong_entry_rejected` | Picking for another user's entry returns 404 | ✅ PASSED |
| `test_create_pick_no_auth_rejected` | Unauthenticated pick creation returns 401 or 403 | ✅ PASSED |
| `test_get_picks_for_entry_success` | Fetches picks for owned entry | ✅ PASSED |
| `test_get_picks_for_entry_wrong_user` | Fetching another user's picks returns 404 | ✅ PASSED |
| `test_update_pick_success` | Updating unlocked pick changes team | ✅ PASSED |
| `test_update_locked_pick_rejected` | Updating locked pick returns 400 | ✅ PASSED |
| `test_delete_pick_success` | Deleting unlocked pick returns 200 | ✅ PASSED |
| `test_delete_locked_pick_rejected` | Deleting locked pick returns 400 | ✅ PASSED |

---

## Pools (`test_pools.py`) — 13 tests

| Test | What it verifies | Result |
|---|---|---|
| `test_create_pool_success` | Authenticated user creates a pool | ✅ PASSED |
| `test_create_pool_unauthorized` | Unauthenticated creation returns 401 or 403 | ✅ PASSED |
| `test_get_my_pools` | Returns pools owned by current user | ✅ PASSED |
| `test_get_pool_by_id_success` | Fetches pool by ID | ✅ PASSED |
| `test_get_pool_nonexistent` | Non-existent pool returns 404 | ✅ PASSED |
| `test_get_pool_unauthorized` | Unauthenticated pool fetch returns 401 or 403 | ✅ PASSED |
| `test_pool_validation_missing_name` | Pool without name returns 422 | ✅ PASSED |
| `test_pool_validation_empty_name` | Empty name accepted — **known gap** | ✅ PASSED |
| `test_pool_creation_audit_logging` | Pool creation triggers audit log | ✅ PASSED |
| `test_get_available_rules` | Rules endpoint returns list | ✅ PASSED |
| `test_pool_with_custom_rules` | Pool created with custom rule values | ✅ PASSED |
| `test_check_admin_access_owner` | Pool owner has admin access | ✅ PASSED |
| `test_check_admin_access_non_owner` | Unauthenticated check returns 401 or 403 | ✅ PASSED |

---

## Season Scenarios (`test_scenario_season.py`) — 8 tests *(mark: `scenario`)*

| Test | Scenario | Result |
|---|---|---|
| `test_week1_picks_submitted_before_lock` | 3 users submit picks before lock; all succeed | ✅ PASSED |
| `test_week1_pick_change_before_lock` | Pick change before lock upserts correctly | ✅ PASSED |
| `test_pick_rejected_after_lock` | Pick after lock time returns 423 | ✅ PASSED |
| `test_auto_pick_for_missing_entry` | Lock-week auto-assigns most-popular team | ✅ PASSED |
| `test_results_and_elimination` | Losing entries get `alive=False` | ✅ PASSED |
| `test_week2_team_reuse_rejected` | Same team in week 2 returns 400 | ✅ PASSED |
| `test_admin_corrects_locked_pick` | Admin override on locked pick succeeds | ✅ PASSED |
| `test_audit_trail_for_pick_operations` | Audit logs created for pick operations | ✅ PASSED |

---

## Schedule (`test_schedule.py`) — 5 tests

| Test | What it verifies | Result |
|---|---|---|
| `test_get_schedule_for_week_returns_games` | Week schedule returns game/team details | ✅ PASSED |
| `test_get_schedule_for_week_empty` | No-game week returns empty list | ✅ PASSED |
| `test_get_teams_for_week_returns_both_teams` | Both home and away teams returned | ✅ PASSED |
| `test_get_teams_for_week_empty` | No-game week returns empty teams | ✅ PASSED |
| `test_get_all_schedules` | All-schedules endpoint returns seeded games | ✅ PASSED |

---

## Security — OWASP Top 10 (`test_security.py`) — 12 tests *(mark: `security`)*

### A01 — Broken Access Control

| Test | Attack scenario | Defence | Result |
|---|---|---|---|
| `test_user_cannot_modify_another_users_pick` | User B modifies User A's pick | 404 | ✅ PASSED |
| `test_user_cannot_delete_another_users_entry` | User B deletes User A's entry | 404 | ✅ PASSED |
| `test_non_admin_cannot_call_lock_week` | Non-owner calls lock-week | 403 | ✅ PASSED |
| `test_user_cannot_read_another_pools_messages` | No-entry user reads pool messages | 403 | ✅ PASSED |

### A03 — Injection

| Test | Attack scenario | Defence | Result |
|---|---|---|---|
| `test_sql_metacharacters_in_pool_name` | `'; DROP TABLE pools; --` as pool name | Stored as literal string | ✅ PASSED |
| `test_xss_payload_in_message_stored_as_text` | `<script>alert(1)</script>` as message | Returned as JSON text | ✅ PASSED |
| `test_oversized_message_rejected` | 251-char message | 400 | ✅ PASSED |

### A07 — Authentication Failures

| Test | Attack scenario | Defence | Result |
|---|---|---|---|
| `test_expired_jwt_rejected` | Expired JWT token | 401 | ✅ PASSED |
| `test_tampered_jwt_rejected` | Modified JWT payload | 401 | ✅ PASSED |
| `test_missing_token_returns_401_or_403` | No Authorization header | 401 or 403 | ✅ PASSED |

### A05 — Security Misconfiguration

| Test | What it verifies | Result |
|---|---|---|
| `test_user_enumeration_endpoint_unauthenticated_known_gap` | `GET /users/` is public — **known gap** | ✅ PASSED |
| `test_cors_allows_configured_origin` | CORS headers present on OPTIONS | ✅ PASSED |

---

## Users (`test_users.py`) — 10 tests

| Test | What it verifies | Result |
|---|---|---|
| `test_list_users_no_auth` | `/users/` returns 200 without token — **known gap** | ✅ PASSED |
| `test_list_users_returns_list` | Registered user appears in list | ✅ PASSED |
| `test_get_user_not_found` | Integer `0` as user ID returns 404 | ✅ PASSED |
| `test_delete_user_requires_auth` | Unauthenticated delete returns 401 or 403 | ✅ PASSED |
| `test_delete_user_not_found` | Delete integer `0` returns 404 | ✅ PASSED |
| `test_delete_user_success` | UUID ID returns 422 — documents `user_id: int` type bug | ✅ PASSED |
| `test_update_email_requires_auth` | Unauthenticated email update returns 401 or 403 | ✅ PASSED |
| `test_update_email_not_found` | Integer `0` returns 404 | ✅ PASSED |
| `test_update_email_success` | UUID returns 422 — documents type bug | ✅ PASSED |
| `test_reset_password_security_bug` | Admin reset stores plaintext — **known security bug** | ✅ PASSED |

---

## Utilities & Configuration (`test_utils.py`) — 16 tests

| Test | What it verifies | Result |
|---|---|---|
| `test_get_db_dependency` | `get_db()` returns a generator | ✅ PASSED |
| `test_current_user_dependency` | `get_current_user()` returns mocked user | ✅ PASSED |
| `test_audit_logging_functions` | Audit functions are callable | ✅ PASSED |
| `test_password_utilities` | Hash and verify work correctly | ✅ PASSED |
| `test_jwt_utilities` | JWT created and decoded with same key | ✅ PASSED |
| `test_database_url_configuration` | *(skipped in test env)* | ⏭ SKIPPED |
| `test_session_creation` | DB session can be created/closed | ✅ PASSED |
| `test_invalid_token_handling` | Malformed JWT returns 401 | ✅ PASSED |
| `test_missing_token_handling` | Missing token returns 401 or 403 | ✅ PASSED |
| `test_malformed_request_handling` | Invalid JSON returns 422 | ✅ PASSED |
| `test_database_error_handling` | Placeholder — DB errors tested indirectly | ✅ PASSED |
| `test_password_hashing_performance` | bcrypt hash completes <1 second | ✅ PASSED |
| `test_token_creation_performance` | JWT creation completes <100ms | ✅ PASSED |
| `test_environment_variables` | `SECRET_KEY` env var is accessible | ✅ PASSED |
| `test_cors_configuration` | CORS middleware configured | ✅ PASSED |
| `test_full_application_startup` | App named "RunMyPool API" | ✅ PASSED |

---

## Backend Coverage

| Module | Coverage |
|---|---|
| `admin.py` | 93% |
| `auth.py` | 68% |
| `entries.py` | 50% |
| `message_board.py` | 98% |
| `models.py` | 100% |
| `picks.py` | 97% |
| `pools.py` | 53% |
| `routers.py` | 100% |
| `schemas.py` | 100% |
| `schedule.py` | 100% |
| **Total** | **80%** |

---

# Frontend Tests

> Run with: `cd rmp/frontend && npm test`
>
> Framework: Jest 30 + React Testing Library 16 + jsdom

## Overview

64 tests across 6 files covering the core frontend components, auth context, page-level behavior, and API health routes.

| Suite | Tests | File |
|---|---|---|
| Auth Context | 9 | `__tests__/AuthContext.test.js` |
| Protected Route | 6 | `__tests__/ProtectedRoute.test.js` |
| NavBar | 9 | `__tests__/NavBar.test.js` |
| Login Page | 10 | `__tests__/LoginPage.test.js` |
| Index (Landing) Page | 10 | `__tests__/IndexPage.test.js` |
| API Health Routes | 20 | `__tests__/ApiRoutes.test.js` |
| **Total** | **64** | |

---

## Auth Context (`AuthContext.test.js`) — 9 tests

Tests the `AuthProvider` context and `useAuth` hook. All API calls are mocked with `jest.fn()`.

| Test | What it verifies | Result |
|---|---|---|
| `provides null user and null token on fresh mount` | Fresh auth state has no user | ✅ PASSED |
| `rehydrates user and token from localStorage on mount` | Stored auth state is restored from localStorage | ✅ PASSED |
| `loading is false after mount` | Loading flag settles to false | ✅ PASSED |
| `login calls /auth/login then /auth/me` | Login flow makes two API calls in sequence | ✅ PASSED |
| `login stores access_token in localStorage` | Token persisted after successful login | ✅ PASSED |
| `login navigates to /dashboard on success` | Router push called with `/dashboard` | ✅ PASSED |
| `login throws on bad credentials` | Failed login propagates an error | ✅ PASSED |
| `logout clears localStorage` | Logout removes token and user from storage | ✅ PASSED |
| `logout navigates to /login` | Router push called with `/login` | ✅ PASSED |

---

## Protected Route (`ProtectedRoute.test.js`) — 6 tests

Tests the auth guard component. `useAuth` is mocked at the module level.

| Test | What it verifies | Result |
|---|---|---|
| `renders children when user is authenticated` | Protected content visible for logged-in user | ✅ PASSED |
| `shows loading when auth is resolving` | "Loading..." displayed while `loading: true` | ✅ PASSED |
| `redirects to /login when user is null and not loading` | `router.replace('/login')` called for unauthenticated user | ✅ PASSED |
| `does not render children when user is null` | Protected content not visible for unauthenticated user | ✅ PASSED |
| `renders children immediately when user exists without loading` | No flash of loading state when already authenticated | ✅ PASSED |
| `calls router.replace not router.push for redirect` | Uses replace (no back-navigation to protected page) | ✅ PASSED |

---

## NavBar (`NavBar.test.js`) — 9 tests

Tests the navigation component in both authenticated and unauthenticated states.

| Test | What it verifies | Result |
|---|---|---|
| `renders navigation links` | Dashboard, Leagues, Message Board links present | ✅ PASSED |
| `shows Login and Register links when not authenticated` | Unauthenticated nav has Login and Register | ✅ PASSED |
| `shows Logout button when authenticated` | Authenticated nav has Logout | ✅ PASSED |
| `shows Profile link when authenticated` | Profile link visible for logged-in user | ✅ PASSED |
| `Logout button calls logout from auth context` | Clicking Logout triggers `logout()` function | ✅ PASSED |
| `hamburger menu button exists` | Mobile toggle button is present in DOM | ✅ PASSED |
| `does not show Logout when unauthenticated` | Logout absent for anonymous users | ✅ PASSED |
| `does not show Register when authenticated` | Register absent for logged-in users | ✅ PASSED |
| `renders logo or brand name` | Site name/brand visible in nav | ✅ PASSED |

---

## Login Page (`LoginPage.test.js`) — 10 tests

Tests the login form rendering, validation, and submission. `login` from `useAuth` is mocked.

| Test | What it verifies | Result |
|---|---|---|
| `renders email and password fields` | Both input fields present | ✅ PASSED |
| `renders the login button` | Submit button labeled "Login" or "Sign In" | ✅ PASSED |
| `shows link to create account` | Link to `/create-account` visible | ✅ PASSED |
| `shows link to forgot password` | Link to `/forgot-password` visible | ✅ PASSED |
| `calls login with email and password on submit` | Correct credentials passed to `login()` | ✅ PASSED |
| `validates email format before submitting` | Invalid email prevents `login()` call | ✅ PASSED |
| `validates password length before submitting` | Short password prevents `login()` call | ✅ PASSED |
| `displays error message on failed login` | Error text visible when `login()` throws | ✅ PASSED |
| `clears error when user starts typing` | Error dismissed on input change | ✅ PASSED |
| `disables submit button while submitting` | Button disabled/loading during async login | ✅ PASSED |

---

## Index / Landing Page (`IndexPage.test.js`) — 10 tests

Tests the public landing page. Auth state and routing are mocked.

| Test | What it verifies | Result |
|---|---|---|
| `renders the main heading` | "Run My Pool" hero text is visible | ✅ PASSED |
| `shows Get Started link when not authenticated` | CTA button/link visible for anonymous users | ✅ PASSED |
| `redirects to dashboard when user is already logged in` | Authenticated users sent to `/dashboard` | ✅ PASSED |
| `renders Login link in header` | "Login" link visible for unauthenticated users | ✅ PASSED |
| `renders feature highlights` | At least one feature section heading visible | ✅ PASSED |
| `shows Highly Configurable feature` | Feature card text present | ✅ PASSED |
| `shows Affordable feature` | Feature card text present | ✅ PASSED |
| `shows no Logout button on landing page` | Landing page is public; Logout not shown | ✅ PASSED |
| `page has no broken accessibility roles` | Page renders without ARIA errors | ✅ PASSED |
| `Get Started links to account creation` | CTA points to `/create-account` | ✅ PASSED |

---

## API Health Routes (`ApiRoutes.test.js`) — 20 tests

Tests the three Next.js API route handlers directly (no HTTP — handler functions called with mock req/res).

### `GET /api/health`

| Test | What it verifies | Result |
|---|---|---|
| `returns 200 status` | Health endpoint responds with 200 | ✅ PASSED |
| `returns status: healthy` | Response body contains `status: 'healthy'` | ✅ PASSED |
| `includes service name or timestamp` | Response includes identification data | ✅ PASSED |
| `responds to GET method` | Handler processes GET requests | ✅ PASSED |
| `returns JSON` | `res.json()` called (not `res.send()`) | ✅ PASSED |

### `GET /api/live`

| Test | What it verifies | Result |
|---|---|---|
| `returns 200 for liveness check` | Live endpoint is up | ✅ PASSED |
| `responds to GET method` | Handler processes GET requests | ✅ PASSED |
| `returns ok or alive status` | Response body indicates service is alive | ✅ PASSED |
| `calls res.status(200)` | Correct HTTP status code set | ✅ PASSED |
| `does not return 500` | No error on normal invocation | ✅ PASSED |

### `GET /api/ready`

| Test | What it verifies | Result |
|---|---|---|
| `returns 200 for readiness check` | Ready endpoint is up | ✅ PASSED |
| `responds to GET method` | Handler processes GET requests | ✅ PASSED |
| `returns ready status` | Response indicates service is ready | ✅ PASSED |
| `calls res.status(200)` | Correct HTTP status code set | ✅ PASSED |
| `does not return 500` | No error on normal invocation | ✅ PASSED |

### Cross-route

| Test | What it verifies | Result |
|---|---|---|
| `all three routes respond to GET` | All health routes functional | ✅ PASSED |
| `health and live return consistent status` | Both report healthy/alive | ✅ PASSED |
| `ready endpoint called independently` | Readiness independent of liveness | ✅ PASSED |
| `handlers are functions` | All exports are valid handler functions | ✅ PASSED |
| `mock req res pattern works` | Test infrastructure is correct | ✅ PASSED |

---

# Known Gaps Documented by Tests

| Gap | Location | Tests | Severity |
|---|---|---|---|
| `GET /users/` publicly accessible | `users.py` | backend | High |
| `PATCH /users/{id}/password` stores plaintext | `users.py` | backend | Critical |
| `user_id: int` type mismatch (User.id is UUID) | `users.py` | backend | Medium |
| Empty pool name passes validation | `pools.py` | backend | Low |
| No token refresh or expiry handling in auth | `AuthContext.js` | frontend | Medium |

---

# CI Integration

Both test suites run automatically on every push to `main`:

| Workflow | Trigger | Test Command | Gates Deploy |
|---|---|---|---|
| `build-backend.yml` | `rmp/backend/**` changes | `pytest tests/ -q --tb=short` | Yes |
| `build-frontend.yml` | `rmp/frontend/**` changes | `npm test -- --ci` | Yes |

Coverage reports uploaded to [Codecov](https://codecov.io/gh/agsmith/run-my-pool) after each backend run.
