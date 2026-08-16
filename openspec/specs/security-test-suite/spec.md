## ADDED Requirements

### Requirement: Security tests cover OWASP Top 10 attack categories

All security tests are marked `@pytest.mark.security` and run in CI on every push. They take an adversarial stance, verifying that the application correctly rejects unauthorized and malicious requests.

#### Scenario: A01 — User cannot access another user's pick (IDOR)
- **WHEN** User A submits a pick and User B tries to read, update, or delete it using a valid token
- **THEN** all requests by User B return HTTP 403 or 404

#### Scenario: A01 — User cannot modify another user's entry
- **WHEN** User A creates an entry and User B attempts to delete it
- **THEN** the delete request returns HTTP 404 (entry not found for User B's user_id)

#### Scenario: A01 — Non-admin cannot call admin endpoints
- **WHEN** a regular authenticated user calls `POST /admin/pools/{pool_id}/lock-week/{week}`
- **THEN** the request returns HTTP 403

#### Scenario: A03 — SQL injection in pool name is stored safely
- **WHEN** a user creates a pool with name `'; DROP TABLE pools; --`
- **THEN** the pool is created with the literal string as its name and the database is unaffected

#### Scenario: A03 — XSS payload in message board is stored as plain text
- **WHEN** a user posts `<script>alert(1)</script>` as a message
- **THEN** the stored message value equals the literal string (no execution context; API returns JSON, not HTML)

#### Scenario: A03 — Oversized payload is rejected
- **WHEN** a user posts a message body of 10,000 characters
- **THEN** the request is rejected with HTTP 400 (max 250 chars)

#### Scenario: A07 — Expired JWT is rejected
- **WHEN** a request is made with a JWT whose `exp` claim is in the past
- **THEN** the request returns HTTP 401

#### Scenario: A07 — Tampered JWT is rejected
- **WHEN** a valid JWT has its payload modified (e.g., `sub` changed to another user's email) without re-signing
- **THEN** the request returns HTTP 401

#### Scenario: A07 — Password reset token cannot be replayed
- **WHEN** a valid password reset token is used to reset a password successfully
- **THEN** using the same token a second time returns HTTP 400 with "Invalid or expired reset token"

#### Scenario: A05 — User enumeration endpoint requires admin role
- **WHEN** `GET /users/` is called without a token or by a non-admin user
- **THEN** the response returns HTTP 403

#### Scenario: A01 — Cross-pool message access is blocked
- **WHEN** a user with an entry in Pool A tries to read messages from Pool B (where they have no entry)
- **THEN** the request returns HTTP 403

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

### Requirement: Auth flows have comprehensive pytest test coverage
All auth endpoints (register, login, forgot-password, reset-password, me) SHALL have test coverage including happy paths, all documented failure paths, and known behavioral gaps documented with `# KNOWN GAP` comments.

#### Scenario: GET /auth/me is covered
- **WHEN** the auth test suite runs
- **THEN** tests exist for: valid token → 200, expired token → 401, no token → 401/403, tampered token → 401, token for deleted user → 401, reset token used as access token → documented gap

#### Scenario: Forgot-password flow is covered
- **WHEN** the auth test suite runs
- **THEN** tests exist for: registered email → 200, unregistered email → 200 (no info leak), invalid format → 422, token type claim is correct

#### Scenario: Reset-password flow is covered
- **WHEN** the auth test suite runs
- **THEN** tests exist for: valid token + new password → 200, expired token → 400, malformed token → 400, access token used as reset token → 400, token reuse → documented gap (no blacklist), password updates correctly in DB

#### Scenario: Known behavioral gaps are documented in TestKnownBehaviorGaps
- **WHEN** the auth test suite runs
- **THEN** tests marked `# KNOWN GAP` exist for: is_active not enforced at login, is_active not enforced at GET /auth/me, deleted-user token not revoked, no password complexity requirement, registration audit event, reset-password audit event
