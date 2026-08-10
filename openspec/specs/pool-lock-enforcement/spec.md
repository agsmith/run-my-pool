### Requirement: Entry creation blocked after pool lock time
The system SHALL reject entry creation requests when the pool's `lock_time` is set and in the past, returning HTTP 423 with a descriptive message.

#### Scenario: Create entry on locked pool
- **WHEN** a user sends `POST /entries/create` for a pool whose `lock_time` is in the past
- **THEN** the system returns HTTP 423
- **AND** the response body contains a `detail` field explaining the pool is locked

#### Scenario: Create entry on unlocked pool
- **WHEN** a user sends `POST /entries/create` for a pool whose `lock_time` is in the future
- **THEN** the entry is created normally and HTTP 200 is returned

#### Scenario: Create entry on pool with no lock time
- **WHEN** a user sends `POST /entries/create` for a pool where `lock_time` is null
- **THEN** the entry is created normally and HTTP 200 is returned

### Requirement: Entry deletion blocked after pool lock time
The system SHALL reject entry deletion requests when the associated pool's `lock_time` is set and in the past, returning HTTP 423 with a descriptive message.

#### Scenario: Delete entry on locked pool
- **WHEN** a user sends `DELETE /entries/{entry_id}` for an entry in a pool whose `lock_time` is in the past
- **THEN** the system returns HTTP 423
- **AND** the response body contains a `detail` field explaining the pool is locked

#### Scenario: Delete entry on unlocked pool
- **WHEN** a user sends `DELETE /entries/{entry_id}` for an entry in a pool whose `lock_time` is in the future
- **THEN** the entry is deleted normally and HTTP 200 is returned

#### Scenario: Delete entry on pool with no lock time
- **WHEN** a user sends `DELETE /entries/{entry_id}` for an entry in a pool where `lock_time` is null
- **THEN** the entry is deleted normally and HTTP 200 is returned

### Requirement: Lock enforcement is server-side
The system SHALL enforce pool lock time at the API layer regardless of client-side state. A user who bypasses the UI (e.g., via direct HTTP request) SHALL receive the same 423 response.

#### Scenario: Direct API call bypassing frontend
- **WHEN** a user sends `POST /entries/create` directly via HTTP with a valid token for a locked pool
- **THEN** the system returns HTTP 423
- **AND** no entry is created in the database

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

## REMOVED

### Requirement: Admin password reset via PATCH /users/{id}/password
**Reason**: The endpoint has three compounding defects: wrong path parameter type (`int` instead of UUID string), plaintext password storage, and no role check. The working password reset flow in `POST /auth/forgot-password` + `POST /auth/reset-password` covers the same use case correctly. The admin UI "Reset Password" button is being wired to the working flow instead.

**Migration**: Use `POST /auth/forgot-password` with the target user's email to trigger a password reset. The backend generates a token; the user receives a reset link (currently logged to stdout; email delivery is a future change). No API callers exist for `PATCH /users/{id}/password` — the frontend button was never wired up.

## MODIFIED Requirements

### Requirement: Lock enforcement extends to auto-pick triggering

The existing pool-lock-enforcement spec covers entry create/delete being blocked after lock time. This delta adds: when the admin explicitly locks a week, the system must also trigger auto-pick for any alive entry that has not submitted a pick for that week.

#### Scenario: Lock-week endpoint triggers auto-pick as part of lock
- **WHEN** `POST /admin/pools/{pool_id}/lock-week/{week}` is called
- **THEN** the pool's `lock_time` is set to now (if not already in the past) AND auto-picks are created for entries missing a pick, in a single atomic operation

#### Scenario: Lock-week is idempotent
- **WHEN** `POST /admin/pools/{pool_id}/lock-week/{week}` is called a second time after already being called
- **THEN** the pool remains locked, no duplicate picks are created, and the response reports `auto_picks_created: 0`

### Requirement: Pool lock time is configurable in the admin console
The admin console SHALL provide a datetime picker with timezone selector for configuring `pool.lock_time`. The UI SHALL convert the selected local time to UTC before sending to the backend.

#### Scenario: Admin sets pool lock time via admin console
- **WHEN** a pool admin selects a date, time, and timezone in the admin console lock time picker and submits
- **THEN** `PATCH /pools/{pool_id}` is called with the correct UTC-converted ISO datetime string and the pool's `lock_time` is updated

#### Scenario: Timezone selection converts to UTC correctly
- **WHEN** an admin selects 1:00 PM Eastern Time on a Sunday
- **THEN** the value sent to the backend is `17:00:00 UTC` (ET is UTC-4 during daylight saving)

#### Scenario: Lock time picker shows current lock time if set
- **WHEN** the admin console loads for a pool with an existing `lock_time`
- **THEN** the picker is pre-populated with the current lock time converted to the admin's selected timezone

#### Scenario: PATCH /pools/{pool_id} parses lock_time consistently with POST
- **WHEN** `PATCH /pools/{pool_id}` is called with a `lock_time` string in ISO or `YYYY-MM-DD HH:MM:SS` format
- **THEN** the datetime is parsed using the same logic as `POST /pools/create` — no raw assignment without parsing
