## MODIFIED Requirements

### Requirement: User enumeration restricted to pool admins
The existing `pool-lock-enforcement` spec covered entry creation/deletion lock. This delta adds the restriction of user listing endpoints.

`GET /users/` and `GET /users/{user_id}` SHALL require authentication and SHALL only be accessible to users with role `POOL_ADMIN` or `SUPER_ADMIN`. Unauthenticated requests and requests from users with role `USER` SHALL be rejected with HTTP 403.

#### Scenario: Unauthenticated GET /users/ is rejected
- **WHEN** `GET /users/` is called without an Authorization header
- **THEN** the response is HTTP 403

#### Scenario: Regular user GET /users/ is rejected
- **WHEN** `GET /users/` is called by an authenticated user with role USER
- **THEN** the response is HTTP 403

#### Scenario: Pool admin GET /users/ succeeds
- **WHEN** `GET /users/` is called by an authenticated user with role POOL_ADMIN or SUPER_ADMIN
- **THEN** the response is HTTP 200 with the user list

#### Scenario: Unauthenticated GET /users/{id} is rejected
- **WHEN** `GET /users/{user_id}` is called without an Authorization header
- **THEN** the response is HTTP 403

#### Scenario: Pool admin GET /users/{id} succeeds
- **WHEN** `GET /users/{user_id}` is called by an authenticated user with role POOL_ADMIN or SUPER_ADMIN
- **THEN** the response is HTTP 200 with the user record if it exists, HTTP 404 otherwise

## REMOVED Requirements

### Requirement: Admin password reset via PATCH /users/{id}/password
**Reason**: The endpoint has three compounding defects: wrong path parameter type (`int` instead of UUID string), plaintext password storage, and no role check. The working password reset flow in `POST /auth/forgot-password` + `POST /auth/reset-password` covers the same use case correctly. The admin UI "Reset Password" button is being wired to the working flow instead.

**Migration**: Use `POST /auth/forgot-password` with the target user's email to trigger a password reset. The backend generates a token; the user receives a reset link (currently logged to stdout; email delivery is a future change). No API callers exist for `PATCH /users/{id}/password` — the frontend button was never wired up.
