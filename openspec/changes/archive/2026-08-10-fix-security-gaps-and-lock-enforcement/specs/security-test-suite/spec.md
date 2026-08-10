## MODIFIED Requirements

### Requirement: Gap tests for lock enforcement become correctness tests
Tests previously marked `@pytest.mark.gap` that documented missing pick lock enforcement SHALL be updated to assert the now-enforced behavior. Tests previously marked `@pytest.mark.known_bug` for the plaintext password and unauthenticated user list SHALL be updated to assert the corrected behavior.

#### Scenario: test_lock_time.py gap test becomes passing correctness test
- **WHEN** `test_lock_week_sets_existing_picks_to_locked` runs after this change
- **THEN** it SHALL pass asserting `Pick.locked == True` on existing picks (removing the gap assertion)

#### Scenario: test_lock_time.py per-game start_time gap test becomes correctness test
- **WHEN** `test_thursday_pick_not_blocked_gap` runs after this change
- **THEN** it SHALL pass asserting HTTP 423 for a pick submitted after Thursday kickoff (removing the gap assertion)

#### Scenario: test_security.py known_bug tests become correctness tests
- **WHEN** `test_get_users_accessible_without_auth_BUG` runs after this change
- **THEN** it SHALL pass asserting HTTP 403 (not 200) for unauthenticated user list

#### Scenario: Dead entry pick test becomes correctness test
- **WHEN** `test_dead_entry_cannot_pick` runs after this change
- **THEN** it SHALL pass asserting HTTP 403 "Entry has been eliminated" (not HTTP 200)

### Requirement: New tests cover the wired admin password reset
A new test SHALL verify the admin "Reset Password" button calls `POST /auth/forgot-password` and receives a success response.

#### Scenario: Admin reset password button triggers forgot-password flow
- **WHEN** a pool admin enters a user's email and clicks Reset Password in the admin UI
- **THEN** `POST /auth/forgot-password` is called with that email and the UI shows a success message
