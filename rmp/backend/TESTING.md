# RunMyPool — Test Suite Documentation

> **Last run:** 137 passed · 1 skipped · 0 failed · Coverage: 80.22%
>
> Run with: `cd rmp/backend && venv/bin/python -m pytest tests/ -v`

---

## Overview

The test suite covers the full RunMyPool backend: authentication, pool management, entries, picks, schedule, message board, admin operations, a multi-week season simulation, and OWASP security scenarios. All tests run against an in-memory SQLite database — no Docker or MySQL required.

| Category | Tests | File |
|---|---|---|
| Admin operations | 17 | `test_admin.py` |
| Authentication | 11 | `test_auth.py` |
| Entry lock enforcement | 7 | `test_entries.py` |
| Application health | 4 | `test_main.py` |
| Message board | 14 | `test_message_board.py` |
| Models & schemas | 10 | `test_models.py` |
| Picks | 11 | `test_picks.py` |
| Pools | 13 | `test_pools.py` |
| Season scenarios | 8 | `test_scenario_season.py` |
| Schedule | 5 | `test_schedule.py` |
| Security (OWASP) | 12 | `test_security.py` |
| Users | 10 | `test_users.py` |
| Utilities & config | 16 | `test_utils.py` |
| **Total** | **138** | |

---

## Running Tests

```bash
cd rmp/backend

# Full suite
venv/bin/python -m pytest tests/ -v

# By category
venv/bin/python -m pytest tests/ -m scenario -v    # Season simulation
venv/bin/python -m pytest tests/ -m security -v    # OWASP security
venv/bin/python -m pytest tests/ -m "not scenario" -q  # Skip slow tests

# Single file
venv/bin/python -m pytest tests/test_security.py -v
```

---

## Admin Operations (`test_admin.py`) — 17 tests

Tests for pool administration: entry transfer, entry deletion, weekly lock with auto-pick, and direct pick overrides.

### `TestAdminEndpoints` — Core admin actions

| Test | What it verifies | Result |
|---|---|---|
| `test_transfer_entry_requires_auth` | Unauthenticated transfer request returns 401 or 403 | ✅ PASSED |
| `test_transfer_entry_non_admin_forbidden` | Non-owner user cannot transfer an entry in another user's pool | ✅ PASSED |
| `test_transfer_entry_success` | Pool owner can transfer entry ownership to another user by email | ✅ PASSED |
| `test_delete_entry_admin_requires_auth` | Unauthenticated delete request returns 401 or 403 | ✅ PASSED |
| `test_delete_entry_admin_non_admin_forbidden` | Non-admin cannot delete entries from another pool | ✅ PASSED |
| `test_delete_entry_admin_not_found` | Deleting a non-existent entry returns 404 | ✅ PASSED |
| `test_delete_entry_admin_success` | Pool owner can delete any entry in their pool | ✅ PASSED |
| `test_verify_admin_access_pool_owner` | `verify_admin_access()` returns `True` for the pool owner | ✅ PASSED |
| `test_verify_admin_access_non_member` | `verify_admin_access()` returns `False` for unrelated users | ✅ PASSED |

### `TestLockWeek` — Weekly lock and auto-pick

| Test | What it verifies | Result |
|---|---|---|
| `test_lock_week_creates_auto_pick` | Admin locking a week auto-assigns the most popular team to entries with no pick | ✅ PASSED |
| `test_lock_week_idempotent` | Locking the same week twice does not create duplicate picks | ✅ PASSED |
| `test_lock_week_non_admin_forbidden` | Non-admin calling lock-week returns 403 | ✅ PASSED |
| `test_lock_week_skips_entry_that_already_picked` | Entries that already have a pick for the week are not overwritten | ✅ PASSED |

### `TestAdminPickEdit` — Direct pick override

| Test | What it verifies | Result |
|---|---|---|
| `test_admin_update_pick_success` | Admin can change the team on a locked pick | ✅ PASSED |
| `test_admin_update_pick_team_conflict` | Changing to a team already used by the entry in another week returns 400 | ✅ PASSED |
| `test_admin_update_pick_non_admin_forbidden` | Regular user cannot use the admin pick edit endpoint | ✅ PASSED |
| `test_admin_update_pick_not_in_pool` | Editing a pick that belongs to a different pool returns 404 | ✅ PASSED |

---

## Authentication (`test_auth.py`) — 11 tests

### `TestAuthFunctions` — Cryptographic utilities

| Test | What it verifies | Result |
|---|---|---|
| `test_verify_password_success` | Correct password passes bcrypt verification | ✅ PASSED |
| `test_verify_password_failure` | Wrong password fails bcrypt verification | ✅ PASSED |
| `test_get_password_hash` | Password is hashed with bcrypt (starts with `$2b$`) | ✅ PASSED |
| `test_create_access_token` | JWT is created with correct `sub` and `exp` claims | ✅ PASSED |

### `TestAuthEndpoints` — Registration and login

| Test | What it verifies | Result |
|---|---|---|
| `test_register_success` | New user registration returns 200 with user data (no password hash exposed) | ✅ PASSED |
| `test_register_duplicate_email` | Registering with an existing email returns 400 | ✅ PASSED |
| `test_register_invalid_email` | Malformed email address returns 422 validation error | ✅ PASSED |
| `test_login_success` | Valid credentials return a JWT access token | ✅ PASSED |
| `test_login_invalid_credentials` | Wrong password returns 401 | ✅ PASSED |
| `test_login_nonexistent_user` | Login attempt for unknown email returns 401 | ✅ PASSED |
| `test_login_audit_logging` | Successful login triggers an audit log event | ✅ PASSED |

---

## Entry Lock Enforcement (`test_entries.py`) — 7 tests

### `TestEntryLockEnforcement` — Pool lock time enforcement

| Test | What it verifies | Result |
|---|---|---|
| `test_create_entry_locked_pool_returns_423` | Creating an entry in a pool past its lock time returns 423 | ✅ PASSED |
| `test_create_entry_unlocked_pool_returns_200` | Creating an entry before lock time succeeds | ✅ PASSED |
| `test_create_entry_null_lock_time_returns_200` | Pools with no lock time set accept entries freely | ✅ PASSED |
| `test_delete_entry_locked_pool_returns_423` | Deleting an entry after lock time returns 423 | ✅ PASSED |
| `test_delete_entry_unlocked_pool_returns_200` | Deleting an entry before lock time succeeds | ✅ PASSED |
| `test_delete_entry_null_lock_time_returns_200` | Deleting from a pool with no lock time succeeds | ✅ PASSED |
| `test_create_entry_no_token_returns_403` | Unauthenticated entry creation returns 401 or 403 | ✅ PASSED |

---

## Application Health (`test_main.py`) — 4 tests

| Test | What it verifies | Result |
|---|---|---|
| `test_read_root` | `GET /` returns 200 | ✅ PASSED |
| `test_health_check` | `GET /health` returns 200 with `{"status": "healthy"}` | ✅ PASSED |
| `test_app_title` | FastAPI app is named "RunMyPool API" | ✅ PASSED |
| `test_cors_headers` | CORS headers are present on OPTIONS requests | ✅ PASSED |

---

## Message Board (`test_message_board.py`) — 14 tests

### `TestMessageBoardEndpoints` — Core message board operations

| Test | What it verifies | Result |
|---|---|---|
| `test_list_messages_requires_auth` | Unauthenticated message listing returns 401 or 403 | ✅ PASSED |
| `test_list_messages_requires_pool_membership` | Authenticated users without an entry in the pool cannot view messages | ✅ PASSED |
| `test_list_messages_empty_pool` | Pool members can list messages from an empty pool | ✅ PASSED |
| `test_post_message_success` | Pool member can post a message; response includes `user_email` | ✅ PASSED |
| `test_post_message_too_long` | Message exceeding 250 characters returns 400 | ✅ PASSED |
| `test_post_message_empty` | Empty message returns 400 | ✅ PASSED |
| `test_post_message_requires_pool_membership` | Non-member cannot post messages | ✅ PASSED |
| `test_delete_message_success` | Message owner can delete their own message | ✅ PASSED |
| `test_delete_message_wrong_user` | User cannot delete another user's message (403) | ✅ PASSED |
| `test_delete_message_not_found` | Deleting a non-existent message returns 404 | ✅ PASSED |

### `TestMessageBoardRateLimit` — Spam prevention

| Test | What it verifies | Result |
|---|---|---|
| `test_rate_limit_allows_five_messages` | First 5 messages in 10 minutes all succeed | ✅ PASSED |
| `test_rate_limit_blocks_sixth_message` | Sixth message within 10 minutes returns 429 | ✅ PASSED |
| `test_rate_limit_resets_after_window` | After the 10-minute window passes, new posts succeed | ✅ PASSED |
| `test_rate_limit_is_per_user_per_pool` | Rate limit is scoped per user per pool; other users and pools are unaffected | ✅ PASSED |

---

## Models & Schemas (`test_models.py`) — 10 tests

### `TestModels` — ORM model construction

| Test | What it verifies | Result |
|---|---|---|
| `test_user_creation` | `User` model can be instantiated with all fields | ✅ PASSED |
| `test_pool_creation` | `Pool` model can be instantiated with all fields | ✅ PASSED |
| `test_user_pool_relationship` | `User.pools` relationship is accessible | ✅ PASSED |
| `test_team_model` | `Team` model fields (id, name, abbrv, logo) are correct | ✅ PASSED |
| `test_user_enum_role` | `UserRole` enum has USER, POOL_ADMIN, SUPER_ADMIN values | ✅ PASSED |
| `test_model_string_representations` | Model objects have readable string representations | ✅ PASSED |

### `TestSchemas` — Pydantic schema validation

| Test | What it verifies | Result |
|---|---|---|
| `test_user_create_schema` | `UserCreate` validates email and password fields | ✅ PASSED |
| `test_user_out_schema` | `UserOut` serialises correctly with orm_mode | ✅ PASSED |
| `test_pool_schema_validation` | `PoolCreate` validates required and optional fields | ✅ PASSED |
| `test_invalid_email_validation` | Invalid email addresses are rejected by Pydantic `EmailStr` | ✅ PASSED |

---

## Picks (`test_picks.py`) — 11 tests

### `TestPickEndpoints` — Pick lifecycle

| Test | What it verifies | Result |
|---|---|---|
| `test_create_pick_success` | Creating a pick returns 200 with correct PickOut fields | ✅ PASSED |
| `test_create_pick_upserts_existing_week` | Submitting a pick for the same entry+week replaces the existing pick | ✅ PASSED |
| `test_create_pick_duplicate_team_rejected` | Using the same team in a different week returns 400 | ✅ PASSED |
| `test_create_pick_wrong_entry_rejected` | Creating a pick for another user's entry returns 404 | ✅ PASSED |
| `test_create_pick_no_auth_rejected` | Unauthenticated pick creation returns 401 or 403 | ✅ PASSED |
| `test_get_picks_for_entry_success` | Fetching picks for an owned entry returns the correct list | ✅ PASSED |
| `test_get_picks_for_entry_wrong_user` | Fetching picks for another user's entry returns 404 | ✅ PASSED |
| `test_update_pick_success` | Updating an unlocked pick changes the team | ✅ PASSED |
| `test_update_locked_pick_rejected` | Updating a locked pick returns 400 | ✅ PASSED |
| `test_delete_pick_success` | Deleting an unlocked pick returns 200 | ✅ PASSED |
| `test_delete_locked_pick_rejected` | Deleting a locked pick returns 400 | ✅ PASSED |

---

## Pools (`test_pools.py`) — 13 tests

### `TestPoolEndpoints` — Pool CRUD

| Test | What it verifies | Result |
|---|---|---|
| `test_create_pool_success` | Authenticated user can create a pool | ✅ PASSED |
| `test_create_pool_unauthorized` | Unauthenticated pool creation returns 401 or 403 | ✅ PASSED |
| `test_get_my_pools` | `GET /pools/my-pools` returns pools owned by the current user | ✅ PASSED |
| `test_get_pool_by_id_success` | Fetching a pool by ID returns correct data | ✅ PASSED |
| `test_get_pool_nonexistent` | Fetching a non-existent pool returns 404 | ✅ PASSED |
| `test_get_pool_unauthorized` | Unauthenticated pool fetch returns 401 or 403 | ✅ PASSED |
| `test_pool_validation_missing_name` | Pool creation without a name returns 422 | ✅ PASSED |
| `test_pool_validation_empty_name` | Pool creation with empty name is accepted (known gap — no server-side validation) | ✅ PASSED |
| `test_pool_creation_audit_logging` | Pool creation triggers an audit log entry | ✅ PASSED |

### `TestPoolRules` — Pool rule configuration

| Test | What it verifies | Result |
|---|---|---|
| `test_get_available_rules` | `GET /rules?pool_type=survivor` returns a list of rules | ✅ PASSED |
| `test_pool_with_custom_rules` | Pool can be created with custom rule values (lock day, time, mode) | ✅ PASSED |

### `TestPoolAdminOperations` — Admin access checks

| Test | What it verifies | Result |
|---|---|---|
| `test_check_admin_access_owner` | Pool owner is identified as having admin access | ✅ PASSED |
| `test_check_admin_access_non_owner` | Unauthenticated request to admin check returns 401 or 403 | ✅ PASSED |

---

## Season Scenarios (`test_scenario_season.py`) — 8 tests *(mark: `scenario`)*

Story-driven tests that simulate realistic survivor pool usage across multiple weeks. Each test is independent and builds its own state from scratch.

### `TestSeasonScenario`

| Test | Scenario | Result |
|---|---|---|
| `test_week1_picks_submitted_before_lock` | 3 users register, create entries, and each submits a pick for week 1 before lock; all succeed | ✅ PASSED |
| `test_week1_pick_change_before_lock` | User changes their week 1 pick; only one pick exists (upsert, not duplicate) | ✅ PASSED |
| `test_pick_rejected_after_lock` | User attempts to submit a pick after the pool lock time; returns 423 | ✅ PASSED |
| `test_auto_pick_for_missing_entry` | One entry has no pick at lock time; admin calls lock-week; auto-pick assigned as most popular team | ✅ PASSED |
| `test_results_and_elimination` | Game results set, losing entries eliminated; winner survives, loser has `alive=False` | ✅ PASSED |
| `test_week2_team_reuse_rejected` | User picks the same team they used in week 1; returns 400 | ✅ PASSED |
| `test_admin_corrects_locked_pick` | Regular user blocked from changing locked pick; admin override succeeds | ✅ PASSED |
| `test_audit_trail_for_pick_operations` | After pick operations, at least one audit log record with "pick" in action exists | ✅ PASSED |

---

## Schedule (`test_schedule.py`) — 5 tests

### `TestScheduleEndpoints`

| Test | What it verifies | Result |
|---|---|---|
| `test_get_schedule_for_week_returns_games` | `GET /schedule/week/1` returns games with home/away team details | ✅ PASSED |
| `test_get_schedule_for_week_empty` | Week with no games returns an empty list (not 404) | ✅ PASSED |
| `test_get_teams_for_week_returns_both_teams` | `GET /schedule/teams/1` returns both the home and away teams | ✅ PASSED |
| `test_get_teams_for_week_empty` | Week with no games returns empty team list | ✅ PASSED |
| `test_get_all_schedules` | `GET /schedule/` returns all seeded games | ✅ PASSED |

---

## Security — OWASP Top 10 (`test_security.py`) — 12 tests *(mark: `security`)*

Adversarial tests verifying that the application correctly rejects unauthorized, malformed, and malicious requests. Maps to the OWASP Top 10 Web Application Security Risks.

### `TestA01BrokenAccessControl`

| Test | Attack scenario | Expected defence | Result |
|---|---|---|---|
| `test_user_cannot_modify_another_users_pick` | User B tries to update User A's pick with a valid token | 404 — pick not found for User B's identity | ✅ PASSED |
| `test_user_cannot_delete_another_users_entry` | User B tries to delete User A's entry | 404 — entry not found for User B | ✅ PASSED |
| `test_non_admin_cannot_call_lock_week` | Non-owner calls `lock-week` on another user's pool | 403 Forbidden | ✅ PASSED |
| `test_user_cannot_read_another_pools_messages` | User with no entry in pool attempts to read its messages | 403 Forbidden | ✅ PASSED |

### `TestA03Injection`

| Test | Attack scenario | Expected defence | Result |
|---|---|---|---|
| `test_sql_metacharacters_in_pool_name` | Pool created with name `'; DROP TABLE pools; --` | Stored as literal string; database unaffected | ✅ PASSED |
| `test_xss_payload_in_message_stored_as_text` | Message posted as `<script>alert(1)</script>` | Stored and returned as plain text in JSON response | ✅ PASSED |
| `test_oversized_message_rejected` | Message body of 251 characters submitted | 400 Bad Request | ✅ PASSED |

### `TestA07AuthFailures`

| Test | Attack scenario | Expected defence | Result |
|---|---|---|---|
| `test_expired_jwt_rejected` | Request made with a JWT whose `exp` is 1 second in the past | 401 Unauthorized | ✅ PASSED |
| `test_tampered_jwt_rejected` | Valid JWT with payload modified (sub changed) and re-encoded without valid signature | 401 Unauthorized | ✅ PASSED |
| `test_missing_token_returns_401_or_403` | Request to protected endpoint with no Authorization header | 401 or 403 | ✅ PASSED |

### `TestA05SecurityMisconfiguration`

| Test | What it verifies | Result |
|---|---|---|
| `test_user_enumeration_endpoint_unauthenticated_known_gap` | `GET /users/` returns 200 without authentication — **documented known gap** requiring future fix | ✅ PASSED |
| `test_cors_allows_configured_origin` | CORS headers present on OPTIONS requests to the API | ✅ PASSED |

---

## Users (`test_users.py`) — 10 tests

### `TestUserEndpoints`

| Test | What it verifies | Result |
|---|---|---|
| `test_list_users_no_auth` | `GET /users/` returns 200 without a token (known security gap) | ✅ PASSED |
| `test_list_users_returns_list` | Registered user appears in the user list | ✅ PASSED |
| `test_get_user_not_found` | Integer `0` as user ID returns 404 | ✅ PASSED |
| `test_delete_user_requires_auth` | Unauthenticated delete request returns 401 or 403 | ✅ PASSED |
| `test_delete_user_not_found` | Authenticated delete for integer `0` returns 404 | ✅ PASSED |
| `test_delete_user_success` | UUID string user ID returns 422 — documents `user_id: int` type mismatch bug | ✅ PASSED |
| `test_update_email_requires_auth` | Unauthenticated email update returns 401 or 403 | ✅ PASSED |
| `test_update_email_not_found` | Email update for integer `0` returns 404 | ✅ PASSED |
| `test_update_email_success` | UUID string returns 422 — documents type mismatch bug; plaintext password storage also flagged | ✅ PASSED |
| `test_reset_password_security_bug` | Admin password reset stores value as-is — **documents known security bug** | ✅ PASSED |

---

## Utilities & Configuration (`test_utils.py`) — 16 tests

### `TestDependencies`

| Test | What it verifies | Result |
|---|---|---|
| `test_get_db_dependency` | `get_db()` returns a generator | ✅ PASSED |
| `test_current_user_dependency` | `get_current_user()` returns the mocked user object | ✅ PASSED |

### `TestUtilities`

| Test | What it verifies | Result |
|---|---|---|
| `test_audit_logging_functions` | `log_create_operation` and `log_authentication_event` are callable | ✅ PASSED |
| `test_password_utilities` | Hashing and verification functions produce correct results | ✅ PASSED |
| `test_jwt_utilities` | JWT is created and decoded using the same `SECRET_KEY` | ✅ PASSED |

### `TestDatabaseConnection`

| Test | What it verifies | Result |
|---|---|---|
| `test_database_url_configuration` | `DATABASE_URL` configuration — skipped in test environment | ⏭ SKIPPED |
| `test_session_creation` | Database session can be created and closed | ✅ PASSED |

### `TestErrorHandling`

| Test | What it verifies | Result |
|---|---|---|
| `test_invalid_token_handling` | Malformed JWT returns 401 | ✅ PASSED |
| `test_missing_token_handling` | Missing token returns 401 or 403 | ✅ PASSED |
| `test_malformed_request_handling` | Invalid JSON body returns 422 | ✅ PASSED |
| `test_database_error_handling` | Placeholder — no assertion (DB errors tested indirectly) | ✅ PASSED |

### `TestPerformance`

| Test | What it verifies | Result |
|---|---|---|
| `test_password_hashing_performance` | bcrypt hash completes in under 1 second | ✅ PASSED |
| `test_token_creation_performance` | JWT creation completes in under 100ms | ✅ PASSED |

### `TestConfiguration`

| Test | What it verifies | Result |
|---|---|---|
| `test_environment_variables` | `SECRET_KEY` environment variable is accessible | ✅ PASSED |
| `test_cors_configuration` | CORS middleware is configured (verified via successful cross-origin requests elsewhere) | ✅ PASSED |
| `test_full_application_startup` | FastAPI app object is created and named correctly | ✅ PASSED |

---

## Known Gaps Documented by Tests

The following tests pass but explicitly document behaviours that require future work:

| Gap | Test | Severity |
|---|---|---|
| `GET /users/` is publicly accessible without authentication | `test_list_users_no_auth`, `test_user_enumeration_endpoint_unauthenticated_known_gap` | High |
| `PATCH /users/{id}/password` stores password in plaintext | `test_reset_password_security_bug` | Critical |
| `PUT /users/{id}` accepts integer IDs but `User.id` is a UUID string (`user_id: int` type mismatch) | `test_delete_user_success`, `test_update_email_success` | Medium |
| Empty pool name passes validation (no server-side min-length check) | `test_pool_validation_empty_name` | Low |

---

## Coverage

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

*One-off scripts (`create_schema.py`, `db_init.py`, `fix_duplicate_constraints.py`, `seed_schedule.py`, etc.) are excluded from coverage measurement.*
