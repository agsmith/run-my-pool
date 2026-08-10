## ADDED Requirements

### Requirement: Pool user lock is pool-scoped and does not affect global login
The system SHALL support locking a specific user within a specific pool. A locked user SHALL still be able to log in and access any other pool they belong to. The lock affects only their ability to create, modify, or delete entries and picks within the locked pool.

#### Scenario: Admin locks a user in a pool
- **WHEN** a pool admin calls `POST /admin/pools/{pool_id}/users/{user_id}/lock`
- **THEN** the response is HTTP 200 and the user is recorded as locked in that pool

#### Scenario: Admin unlocks a user in a pool
- **WHEN** a pool admin calls `DELETE /admin/pools/{pool_id}/users/{user_id}/lock`
- **THEN** the response is HTTP 200 and the lock record is removed

#### Scenario: Non-admin cannot lock a user
- **WHEN** a non-admin user calls the lock endpoint
- **THEN** the response is HTTP 403

#### Scenario: Locked user cannot create entries in locked pool
- **WHEN** a user locked in pool P calls `POST /entries/create` with `pool_id = P`
- **THEN** the response is HTTP 423 with detail indicating their account is locked in this pool

#### Scenario: Locked user cannot modify picks in locked pool
- **WHEN** a user locked in pool P calls `POST /picks/create` or `PUT /picks/{pick_id}` for an entry in pool P
- **THEN** the response is HTTP 423

#### Scenario: Locked user can still log in
- **WHEN** a user locked in pool P calls `POST /auth/login` with valid credentials
- **THEN** the response is HTTP 200 with a valid JWT — login is not affected by the pool lock

#### Scenario: Locked user retains full access to other pools
- **WHEN** a user locked in pool P performs any action in pool Q (a different pool)
- **THEN** the action proceeds normally — the lock is not applied outside pool P

#### Scenario: Admin can still transfer a locked user's entries
- **WHEN** a pool admin calls `POST /admin/pools/{pool_id}/transfer-entry` for an entry owned by a locked user
- **THEN** the transfer succeeds — admin operations are not blocked by user locks

#### Scenario: Admin console shows lock status per user
- **WHEN** a pool admin views the entry list in the admin console
- **THEN** each user row shows a lock toggle (checkbox) reflecting current lock state; toggling it calls the lock or unlock endpoint

### Requirement: Pool user lock is stored in pool_user_locks table
The system SHALL store lock records in a `pool_user_locks` join table with columns `pool_id`, `user_id`, `locked_at`, and optional `reason`. The combination of `(pool_id, user_id)` SHALL be unique.

#### Scenario: Lock record exists after locking
- **WHEN** a user is locked in a pool
- **THEN** a row exists in `pool_user_locks` with the correct `pool_id` and `user_id`

#### Scenario: Lock record is removed after unlocking
- **WHEN** a user is unlocked in a pool
- **THEN** the corresponding row in `pool_user_locks` is deleted
