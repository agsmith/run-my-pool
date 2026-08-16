## MODIFIED Requirements

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
