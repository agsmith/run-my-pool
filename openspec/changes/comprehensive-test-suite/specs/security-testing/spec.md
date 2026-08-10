## ADDED Requirements

### Requirement: All protected routes require a valid JWT
The system SHALL return HTTP 401 or 403 for any protected route accessed without a valid Bearer token.

#### Scenario: No token returns 401 or 403
- **WHEN** a request is made to any protected route without an Authorization header
- **THEN** the response is HTTP 401 or HTTP 403

#### Scenario: Expired JWT returns 401
- **WHEN** a request is made with a JWT whose exp claim is in the past
- **THEN** the response is HTTP 401

#### Scenario: Tampered JWT payload returns 401
- **WHEN** a request is made with a JWT whose payload has been base64-modified without re-signing
- **THEN** the response is HTTP 401

### Requirement: Horizontal privilege escalation is blocked at all pick and entry endpoints
A user SHALL NOT be able to read, modify, or delete picks or entries belonging to another user's entries.

#### Scenario: User cannot pick for another user's entry
- **WHEN** User A submits POST /picks/create with an entry_id belonging to User B
- **THEN** the response is HTTP 404 (obscures existence)

#### Scenario: User cannot update another user's pick
- **WHEN** User A submits PUT /picks/{pick_id} for a pick on User B's entry
- **THEN** the response is HTTP 404

#### Scenario: User cannot delete another user's pick
- **WHEN** User A submits DELETE /picks/{pick_id} for a pick on User B's entry
- **THEN** the response is HTTP 404

#### Scenario: User cannot delete another user's entry
- **WHEN** User A submits DELETE /entries/{entry_id} for User B's entry
- **THEN** the response is HTTP 404

### Requirement: Pool admin access is scoped to owned pools only
A pool admin of Pool A SHALL NOT be able to exercise admin privileges on Pool B.

#### Scenario: Pool admin cannot lock week on another pool
- **WHEN** a user who is admin of Pool A calls POST /admin/pools/{pool_b_id}/lock-week/{week}
- **THEN** the response is HTTP 403

#### Scenario: Pool admin cannot override picks in another pool
- **WHEN** a user who is admin of Pool A calls PATCH /admin/pools/{pool_b_id}/picks/{pick_id}
- **THEN** the response is HTTP 403

### Requirement: Known documented security bugs are asserted and labeled
The test suite SHALL explicitly assert the current (broken) behavior of known security bugs, labeling each test as a documentation of a bug rather than a passing requirement.

#### Scenario: GET /users/ is accessible without authentication (BUG)
- **WHEN** GET /users/ is called without any Authorization header
- **THEN** the response is HTTP 200 — this test documents a known access control gap

#### Scenario: PATCH /users/{id}/password stores plaintext password (BUG)
- **WHEN** PATCH /users/{id}/password is called with a new password
- **THEN** the stored value is the plaintext string — this test documents a known critical security bug

### Requirement: Input validation prevents malformed pick and pool data
The system SHALL reject pick requests with out-of-range week numbers and pool requests with invalid data, returning HTTP 422.

#### Scenario: Pick week=0 is rejected
- **WHEN** POST /picks/create is submitted with week=0
- **THEN** the response is HTTP 422

#### Scenario: Pick week=18 is rejected
- **WHEN** POST /picks/create is submitted with week=18 (beyond 2025 season)
- **THEN** the response is HTTP 422 or HTTP 400

#### Scenario: Pick week=-1 is rejected
- **WHEN** POST /picks/create is submitted with week=-1
- **THEN** the response is HTTP 422

#### Scenario: SQL injection in pool name does not cause 500
- **WHEN** POST /pools/create is submitted with a pool name containing SQL injection payload
- **THEN** the response is HTTP 200 or HTTP 422, never HTTP 500

#### Scenario: Password reset token cannot be reused
- **WHEN** a valid password reset token is used once to reset a password
- **THEN** a second attempt to use the same token returns HTTP 400 or HTTP 401
