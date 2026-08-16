## 1. Lambda — Score Updater Fixes

- [x] 1.1 In `lambda_handler()`, uncomment the `is_nfl_game_time()` guard block (lines 88–97)
- [x] 1.2 In `lambda_handler()`, replace `for current_week in range(1, 18):` loop with `current_week = get_current_nfl_week()` and de-indent the loop body
- [x] 1.3 Remove the duplicate `get_current_nfl_week()` definition at line 190 (keep only the one at line 19)

## 2. Backend Tests — Auth Fixes

- [x] 2.1 Fix `test_login_success` — change `data=login_data` to `json={"email": ..., "password": ...}`
- [x] 2.2 Fix `test_login_invalid_credentials` — same fix as 2.1
- [x] 2.3 Fix `test_login_nonexistent_user` — same fix
- [x] 2.4 Fix `test_login_audit_logging` — same fix
- [x] 2.5 Fix `test_create_access_token` — import `SECRET_KEY` from `auth` and use it for JWT decode instead of reading from env

## 3. Verification

- [x] 3.1 Run `pytest tests/test_auth.py -v` — all tests pass (target: 0 failures, previously 5)
- [x] 3.2 Run `pytest tests/ -v` — no regressions in passing tests
- [x] 3.3 Review `lambda_handler()` body visually — confirm single-week flow, guard restored, no loop
