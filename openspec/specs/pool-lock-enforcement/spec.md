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

## MODIFIED Requirements

### Requirement: Lock enforcement extends to auto-pick triggering

The existing pool-lock-enforcement spec covers entry create/delete being blocked after lock time. This delta adds: when the admin explicitly locks a week, the system must also trigger auto-pick for any alive entry that has not submitted a pick for that week.

#### Scenario: Lock-week endpoint triggers auto-pick as part of lock
- **WHEN** `POST /admin/pools/{pool_id}/lock-week/{week}` is called
- **THEN** the pool's `lock_time` is set to now (if not already in the past) AND auto-picks are created for entries missing a pick, in a single atomic operation

#### Scenario: Lock-week is idempotent
- **WHEN** `POST /admin/pools/{pool_id}/lock-week/{week}` is called a second time after already being called
- **THEN** the pool remains locked, no duplicate picks are created, and the response reports `auto_picks_created: 0`
