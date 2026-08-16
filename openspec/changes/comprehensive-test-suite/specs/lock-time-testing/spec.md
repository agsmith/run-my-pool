## ADDED Requirements

### Requirement: Pool lock_time blocks entry creation and deletion
The system SHALL block entry creation and entry deletion with HTTP 423 when the pool's lock_time has passed, and SHALL allow both operations when lock_time is null or in the future.

#### Scenario: Entry creation blocked after lock_time
- **WHEN** a POST /entries/create is made after pool.lock_time has passed
- **THEN** the response is HTTP 423 with detail containing "locked"

#### Scenario: Entry deletion blocked after lock_time
- **WHEN** a DELETE /entries/{entry_id} is made after pool.lock_time has passed
- **THEN** the response is HTTP 423 with detail containing "locked"

#### Scenario: Entry creation allowed with null lock_time
- **WHEN** a POST /entries/create is made and pool.lock_time is null
- **THEN** the response is HTTP 200

#### Scenario: Entry creation allowed before lock_time
- **WHEN** a POST /entries/create is made before pool.lock_time
- **THEN** the response is HTTP 200

### Requirement: Pick.locked boolean blocks user pick modification
The system SHALL block pick updates and deletes with HTTP 400 when Pick.locked is True, and SHALL allow admin overrides regardless of lock state.

#### Scenario: Locked pick update blocked for user
- **WHEN** a PUT /picks/{pick_id} is made on a pick with locked=True by the owning user
- **THEN** the response is HTTP 400 with detail containing "locked"

#### Scenario: Locked pick deletion blocked for user
- **WHEN** a DELETE /picks/{pick_id} is made on a pick with locked=True by the owning user
- **THEN** the response is HTTP 400 with detail containing "locked"

#### Scenario: Admin can override a locked pick
- **WHEN** a PATCH /admin/pools/{pool_id}/picks/{pick_id} is made by a pool admin on a locked pick
- **THEN** the response is HTTP 200 and the pick is updated

### Requirement: Per-game start_time creates early lock for pre-Sunday games
The system's effective lock time for any given pick SHALL be the earlier of pool.lock_time and the picked game's start_time. Picks for teams playing Thursday night games SHALL be locked at Thursday kickoff, before the Sunday pool.lock_time. This requirement documents a known gap: the current picks.py does NOT enforce this — the test SHALL assert current behavior and label the gap explicitly.

#### Scenario: Thursday game pick is not blocked before pool.lock_time (current behavior — gap)
- **WHEN** a pick is made for a team in a Thursday night game after Thursday kickoff but before pool.lock_time (Sunday 1pm)
- **THEN** the pick succeeds (HTTP 200) — documenting that per-game locking is not currently enforced

#### Scenario: Sunday 1pm picks all blocked after pool.lock_time
- **WHEN** a pick is made for any team after pool.lock_time has passed
- **THEN** the pick for a Sunday game requires Pick.locked=True to be rejected — the lock must be set explicitly via lock-week

### Requirement: lock-week sets all week picks to locked and auto-picks missing entries
The admin POST /admin/pools/{pool_id}/lock-week/{week} SHALL set locked=True on all existing picks for that week and create auto-picks for entries that have no pick.

#### Scenario: Existing picks are locked
- **WHEN** lock-week is called for week N
- **THEN** all picks for week N in that pool have locked=True

#### Scenario: Missing picks receive auto-pick
- **WHEN** lock-week is called for week N and some alive entries have no pick for week N
- **THEN** each such entry receives a new pick with locked=True for an eligible team not previously used by that entry

#### Scenario: Auto-pick skipped when no eligible teams remain
- **WHEN** lock-week is called and an entry has used all 32 teams across prior weeks
- **THEN** an AUTO_PICK_SKIPPED audit event is logged and no pick is created for that entry
