## 1. Infrastructure and Fixtures

- [x] 1.1 Extend `conftest.py` with `nfl_schedule_2025` session-scoped fixture that loads and filters the 2025 regular season games from `nfl-schedule-2025.json`
- [x] 1.2 Add `season_db` session-scoped SQLAlchemy session fixture backed by a named SQLite file (`test_season.db`)
- [x] 1.3 Add `season_client` session-scoped `TestClient` wired to `season_db` via dependency override
- [x] 1.4 Add `season_pool` session-scoped pool fixture with `lock_time=None` initially
- [x] 1.5 Add `create_season_users_and_entries()` helper: 750 users, 2000 entries (first 500 users get 3 entries, last 250 get 2 entries)
- [x] 1.6 Add `seed_season_schedule()` helper that inserts all 256 games and 32 teams from the 2025 JSON into the `season_db`
- [x] 1.7 Add `season_fixture` session-scoped fixture that calls user/entry creation and schedule seeding; verify counts
- [x] 1.8 Create `tests/helpers.py` with `simulate_game_result(db, game_id, winner_team_id)` replicating Lambda logic
- [x] 1.9 Add `_eliminate_losing_entries(db)` helper in `helpers.py`
- [x] 1.10 Add `simulate_week_results(db, week, winners)` helper in `helpers.py`
- [x] 1.11 Add `advance_time(target)` context manager in `helpers.py` using `unittest.mock.patch` on `entries.datetime` and `picks.datetime`
- [x] 1.12 Add `get_alive_entries(db, pool_id)` and `get_entry_used_teams(db, entry_id)` helpers in `helpers.py`
- [x] 1.13 Create `tests/constants.py` with `NFL_2025_WEEK_COUNT`, `NFL_2025_GAME_COUNT`, `NFL_2025_TEAM_COUNT`, week 1 kickoff UTC constants, `SEASON_USER_COUNT`, `SEASON_ENTRY_COUNT`, and cohort elimination week constants
- [x] 1.14 Register `pytest.mark.season`, `pytest.mark.gap`, and `pytest.mark.known_bug` marks in `pytest.ini` or `pyproject.toml`

## 2. Season Simulation Tests

- [x] 2.1 Create `tests/test_full_season.py` with `TestFullSeason` class
- [x] 2.2 Write `test_season_fixture_counts` — assert 750 users, 2000 entries, 256 schedule rows exist after fixture initialization
- [x] 2.3 Implement `pick_strategy(entry_index, week, game)` function with cohort 0/1/2 logic; add preflight validation that no entry is assigned a duplicate team across weeks
- [x] 2.4 Write `test_week_1_picks_before_lock` — all alive entries make a pick via `POST /picks/create`; assert HTTP 200 for each
- [x] 2.5 Write `test_week_1_lock_and_autopick` — call `POST /admin/pools/{pool_id}/lock-week/1`; verify every alive entry has a pick for week 1 with `locked=True`
- [x] 2.6 Write `test_week_1_picks_blocked_after_lock` — attempt `PUT` and `DELETE` on locked picks; assert HTTP 400
- [x] 2.7 Write `test_week_1_results_and_elimination` — call `simulate_week_results` with controlled winners; assert alive entry count matches expected cohort survival
- [x] 2.8 Write `test_week_N_picks_and_results` parameterized over weeks 2–17; each week: picks before lock, lock-week, results, alive count assertion
- [x] 2.9 Write `test_season_no_duplicate_teams` — after all 17 weeks, query all picks per entry and assert no team abbreviation appears twice
- [x] 2.10 Write `test_season_dead_entries_have_losses` — assert every entry with `alive=False` has at least one pick with `result="loss"`
- [x] 2.11 Write `test_season_survivors_all_wins` — assert every entry with `alive=True` has no pick with `result="loss"`
- [x] 2.12 Write `test_season_eligible_team_count` — assert surviving entries have used exactly 17 teams, leaving 15 eligible

## 3. Lock Time Tests

- [x] 3.1 Create `tests/test_lock_time.py`
- [x] 3.2 Write `TestPoolLockTime.test_entry_create_after_lock` — set `pool.lock_time` to past via `db_session`; assert `POST /entries/create` returns HTTP 423
- [x] 3.3 Write `TestPoolLockTime.test_entry_delete_after_lock` — same setup; assert `DELETE /entries/{entry_id}` returns HTTP 423
- [x] 3.4 Write `TestPoolLockTime.test_entry_create_before_lock` — set `lock_time` to future; assert HTTP 200
- [x] 3.5 Write `TestPoolLockTime.test_entry_create_null_lock` — `lock_time=None`; assert HTTP 200
- [x] 3.6 Write `TestPoolLockTime.test_lock_time_boundary` — set `lock_time` to exactly `datetime.utcnow()`; document and assert observed behavior (blocked or not)
- [x] 3.7 Write `TestPickLocked.test_locked_pick_update_blocked` — set `Pick.locked=True` via `db_session`; assert `PUT /picks/{pick_id}` returns HTTP 400 with "locked" in detail
- [x] 3.8 Write `TestPickLocked.test_locked_pick_delete_blocked` — same setup; assert `DELETE /picks/{pick_id}` returns HTTP 400 with "locked" in detail
- [x] 3.9 Write `TestPickLocked.test_admin_overrides_locked_pick` — assert `PATCH /admin/pools/{pool_id}/picks/{pick_id}` returns HTTP 200
- [x] 3.10 Write `TestPerGameStartTimeGap.test_thursday_pick_not_blocked_gap` (mark: `gap`) — assert pick for a Thursday team succeeds after Thursday kickoff but before Sunday `pool.lock_time`; annotate with gap description
- [x] 3.11 Write `TestLockWeek.test_lock_week_sets_all_picks_locked` — call lock-week, query all week-N picks; assert all have `locked=True`
- [x] 3.12 Write `TestLockWeek.test_lock_week_autopick_for_missing` — create entry with no pick, call lock-week; assert entry now has a pick with `locked=True`
- [x] 3.13 Write `TestLockWeek.test_lock_week_autopick_skip_no_eligible_teams` — exhaust all 32 teams on an entry across 32 mock picks, call lock-week; assert `AUTO_PICK_SKIPPED` audit entry exists

## 4. Team Eligibility Tests

- [x] 4.1 Create `tests/test_eligibility.py`
- [x] 4.2 Write `test_winning_team_cannot_be_repicked` — create pick, set `result="win"`, attempt to pick same team in next week; assert HTTP 400 with "already been selected"
- [x] 4.3 Write `test_losing_team_cannot_be_repicked` — create pick, set `result="loss"`, attempt repick; assert HTTP 400
- [x] 4.4 Write `test_unresolved_pick_team_cannot_be_repicked` — pick with `result=None`; attempt repick different week; assert HTTP 400
- [x] 4.5 Write `test_same_user_two_entries_same_team_allowed` — user has two entries; both pick same team in same week; assert both return HTTP 200
- [x] 4.6 Write `test_same_user_two_entries_same_team_different_weeks` — entry A picks team X week 1; entry B picks team X week 2; assert HTTP 200
- [x] 4.7 Write `test_put_pick_to_used_team_rejected` — entry picks team X week 1 and team Y week 2; PUT week 2 pick to team X; assert HTTP 400
- [x] 4.8 Write `test_put_pick_to_unused_team_succeeds` — update unlocked pick to a team not previously used; assert HTTP 200
- [x] 4.9 Write `test_eligible_team_count_decreases_per_pick` — after K picks, verify K distinct teams were used; assert no repeats
- [x] 4.10 Write `test_full_season_17_picks_leaves_15_eligible` — after 17 weeks of picks on one entry, assert 15 teams remain unpicked

## 5. Elimination Tests

- [x] 5.1 Create `tests/test_elimination.py`
- [x] 5.2 Write `TestSimulateGameResult.test_win_pick_gets_win_result` — call `simulate_game_result`; assert winning team picks have `result="win"`
- [x] 5.3 Write `TestSimulateGameResult.test_loss_pick_gets_loss_result` — assert losing team picks have `result="loss"`
- [x] 5.4 Write `TestSimulateGameResult.test_entry_eliminated_after_loss` — assert `Entry.alive=False` for entry with loss pick
- [x] 5.5 Write `TestSimulateGameResult.test_entry_alive_after_win` — assert `Entry.alive=True` for entry with win pick
- [x] 5.6 Write `test_dead_entry_cannot_pick` — eliminate entry, attempt `POST /picks/create`; assert HTTP 404
- [x] 5.7 Write `TestAutoPick.test_autopick_assigned_when_no_pick` — create entry with no pick; call lock-week; assert pick exists with `locked=True`
- [x] 5.8 Write `TestAutoPick.test_autopick_respects_team_uniqueness` — entry has prior picks; call lock-week; assert new pick team not in prior pick teams
- [x] 5.9 Write `TestAutoPick.test_autopick_skipped_no_eligible_teams` — manually create picks for all 32 teams on an entry; call lock-week; assert no new pick and `AUTO_PICK_SKIPPED` audit log exists
- [x] 5.10 Write `TestAdminOps.test_admin_transfer_entry` — call transfer-entry; assert `Entry.user_id` changed and all picks preserved
- [x] 5.11 Write `TestAdminOps.test_admin_delete_entry` — call admin delete; assert entry and its picks are removed
- [x] 5.12 Write `TestAdminOps.test_non_admin_cannot_use_admin_routes` — non-admin user hits each `/admin/` route; assert HTTP 403

## 6. Message Board Tests

- [x] 6.1 Create `tests/test_message_board.py`
- [x] 6.2 Write `TestMessageBoardAccess.test_alive_entry_user_can_post` — user with alive entry posts; assert HTTP 200
- [x] 6.3 Write `TestMessageBoardAccess.test_eliminated_entry_user_can_post` — set entry `alive=False`, post message; assert HTTP 200
- [x] 6.4 Write `TestMessageBoardAccess.test_no_entry_user_cannot_post` — user with no entry in pool posts; assert HTTP 403 with "must be a member"
- [x] 6.5 Write `TestMessageBoardAccess.test_deleted_entry_user_cannot_post` — delete user's only entry, attempt post; assert HTTP 403
- [x] 6.6 Write `TestMessageBoardAccess.test_no_entry_user_cannot_read` — user with no entry calls `GET /messages/pool/{pool_id}`; assert HTTP 403
- [x] 6.7 Write `TestRateLimit.test_fifth_message_succeeds` — post 5 messages in quick succession; assert all HTTP 200
- [x] 6.8 Write `TestRateLimit.test_sixth_message_rejected_429` — post 6th message within 10-minute window; assert HTTP 429 with exact rate limit message
- [x] 6.9 Write `TestRateLimit.test_rate_limit_resets_after_window` — mock time to advance 10 minutes past the window; assert next post returns HTTP 200
- [x] 6.10 Write `TestContentConstraints.test_empty_message_rejected` — post empty string; assert HTTP 400
- [x] 6.11 Write `TestContentConstraints.test_whitespace_message_rejected` — post whitespace-only string; assert HTTP 400
- [x] 6.12 Write `TestContentConstraints.test_250_char_message_accepted` — post exactly 250 chars; assert HTTP 200
- [x] 6.13 Write `TestContentConstraints.test_251_char_message_rejected` — post 251 chars; assert HTTP 400
- [x] 6.14 Write `TestDeletion.test_user_deletes_own_message` — user deletes their own message; assert HTTP 200 and message absent
- [x] 6.15 Write `TestDeletion.test_user_cannot_delete_others_message` — user deletes another user's message; assert HTTP 403 with "own messages"

## 7. Audit Trail Tests

- [x] 7.1 Create `tests/test_audit.py`
- [x] 7.2 Write `test_register_creates_audit` — register user, query `AuditLog`; assert row with matching `user_id` exists
- [x] 7.3 Write `test_failed_login_creates_audit` — bad credentials login, query `AuditLog`; assert `action="LOGIN_FAILURE"` row exists
- [x] 7.4 Write `test_create_pool_creates_audit` — create pool, query `AuditLog`; assert `action="CREATE_POOL"` with `entity_id` matching pool id
- [x] 7.5 Write `test_create_entry_creates_audit` — create entry; assert `action="CREATE_ENTRY"` with correct `entity_id`
- [x] 7.6 Write `test_create_pick_creates_audit` — create pick; assert `action="CREATE_PICK"` with correct `entity_id`
- [x] 7.7 Write `test_update_pick_creates_audit_with_diff` — update pick team; assert `action="UPDATE_PICK"` row exists with `entity_id` matching pick
- [x] 7.8 Write `test_delete_pick_creates_audit` — delete pick; assert `action="DELETE_PICK"` row exists
- [x] 7.9 Write `test_create_message_creates_audit` — post message; assert audit row with message-related action exists
- [x] 7.10 Write `test_lock_week_creates_admin_audit` — call lock-week; assert at least one audit row with action starting `"ADMIN_"` exists
- [x] 7.11 Write `test_pick_override_creates_admin_audit` — admin PATCH pick; assert `action="ADMIN_OVERRIDE_PICK"` or similar `ADMIN_` prefix row exists
- [x] 7.12 Write `test_transfer_entry_creates_admin_audit` — transfer entry; assert `action="ADMIN_TRANSFER_ENTRY"` row exists
- [x] 7.13 Write `test_audit_failure_does_not_break_operation` — mock `create_audit_log` to raise an exception; assert the triggering API call still returns its success response
- [x] 7.14 Write `test_no_audit_delete_endpoint` — attempt `DELETE /audit/` and `DELETE /audit/{id}`; assert HTTP 404 or 405

## 8. Security Tests

- [x] 8.1 Create `tests/test_security.py`
- [x] 8.2 Write `TestJWT.test_no_token_returns_401_or_403` — call each protected route without Authorization header; assert HTTP 401 or 403
- [x] 8.3 Write `TestJWT.test_expired_jwt_returns_401` — craft JWT with `exp` in the past using `python-jose`; assert HTTP 401
- [x] 8.4 Write `TestJWT.test_tampered_jwt_returns_401` — base64-decode payload, alter sub field, re-encode without resigning; assert HTTP 401
- [x] 8.5 Write `TestHorizontalEscalation.test_user_cannot_pick_for_others_entry` — User A submits pick for User B's entry_id; assert HTTP 404
- [x] 8.6 Write `TestHorizontalEscalation.test_user_cannot_update_others_pick` — User A submits PUT for User B's pick_id; assert HTTP 404
- [x] 8.7 Write `TestHorizontalEscalation.test_user_cannot_delete_others_pick` — User A submits DELETE for User B's pick_id; assert HTTP 404
- [x] 8.8 Write `TestHorizontalEscalation.test_user_cannot_delete_others_entry` — User A submits DELETE for User B's entry_id; assert HTTP 404
- [x] 8.9 Write `TestAdminBoundary.test_admin_a_cannot_lock_pool_b` — admin of Pool A calls lock-week on Pool B; assert HTTP 403
- [x] 8.10 Write `TestAdminBoundary.test_admin_a_cannot_override_pick_in_pool_b` — admin of Pool A calls PATCH on a pick in Pool B; assert HTTP 403
- [x] 8.11 Write `TestKnownBugs.test_get_users_accessible_without_auth_BUG` (mark: `known_bug`) — call `GET /users/` without token; assert HTTP 200; annotate as documented bug
- [x] 8.12 Write `TestKnownBugs.test_patch_password_stores_plaintext_BUG` (mark: `known_bug`) — call `PATCH /users/{id}/password`; query DB for stored password; assert it is the plaintext string; annotate as documented critical bug
- [x] 8.13 Write `TestInputValidation.test_pick_week_zero_rejected` — submit pick with `week=0`; assert HTTP 422
- [x] 8.14 Write `TestInputValidation.test_pick_week_18_rejected` — submit pick with `week=18`; assert HTTP 422 or 400
- [x] 8.15 Write `TestInputValidation.test_pick_week_negative_rejected` — submit pick with `week=-1`; assert HTTP 422
- [x] 8.16 Write `TestInputValidation.test_sql_injection_in_pool_name_no_500` — submit pool name with SQL injection payload; assert response is never HTTP 500
- [x] 8.17 Write `TestPasswordReset.test_reset_token_cannot_be_reused` — generate reset token, use it once, attempt reuse; assert second attempt returns HTTP 400 or 401

## 9. Verification and Cleanup

- [x] 9.1 Run full test suite with `cd rmp/backend && venv/bin/python -m pytest tests/ -v`; confirm all new tests pass and no existing tests regress
- [x] 9.2 Run season simulation tests in isolation with `pytest -m season -v`; confirm deterministic alive counts at weeks 2, 8, and 17
- [x] 9.3 Run gap and known_bug tests with `pytest -m "gap or known_bug" -v`; confirm they pass (asserting broken behavior) and are clearly labeled in output
- [x] 9.4 Run coverage report with `pytest --cov=rmp/backend --cov-report=term-missing`; confirm overall coverage increases from 80%
- [x] 9.5 Update `TESTING.md` to document new marks (`season`, `gap`, `known_bug`), how to run each subset, and the session-scoped `test_season.db` lifecycle
