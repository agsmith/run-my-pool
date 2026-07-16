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

#### Scenario: A05 — User enumeration endpoint is unauthenticated (known gap)
- **WHEN** `GET /users/` is called without a token
- **THEN** the response returns HTTP 200 with the user list — this scenario documents a known security misconfiguration gap to be tracked

#### Scenario: A01 — Cross-pool message access is blocked
- **WHEN** a user with an entry in Pool A tries to read messages from Pool B (where they have no entry)
- **THEN** the request returns HTTP 403
