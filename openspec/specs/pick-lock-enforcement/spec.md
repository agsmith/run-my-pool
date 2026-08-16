### Requirement: Picks are rejected after pool.lock_time
The system SHALL reject pick creation and pick updates when the pool's `lock_time` has passed, returning HTTP 423 with a message indicating the pool is locked.

#### Scenario: Create pick after pool lock_time returns 423
- **WHEN** a user submits `POST /picks/create` after `pool.lock_time` has passed
- **THEN** the response is HTTP 423 with detail containing "locked"

#### Scenario: Update pick after pool lock_time returns 423
- **WHEN** a user submits `PUT /picks/{pick_id}` after `pool.lock_time` has passed
- **THEN** the response is HTTP 423 with detail containing "locked"

#### Scenario: Create pick before pool lock_time succeeds
- **WHEN** a user submits `POST /picks/create` before `pool.lock_time`
- **THEN** the response is HTTP 200

#### Scenario: Create pick with null pool lock_time succeeds
- **WHEN** a user submits `POST /picks/create` and `pool.lock_time` is null
- **THEN** the response is HTTP 200

### Requirement: Picks for pre-Sunday games lock at that game's kickoff time
For any game that kicks off before Sunday 1pm ET (the pool lock_time), the pick for a team in that game SHALL be rejected once the game's `Schedule.start_time` has passed, even if `pool.lock_time` has not yet been reached.

The rule is: effective lock time for a pick = `min(pool.lock_time, game.start_time)`.

This applies to Thursday night games, Friday games, and Saturday games. Sunday 4pm, Sunday Night Football, and Monday Night Football games all lock at `pool.lock_time` (Sunday 1pm ET) — their kickoffs are after the pool lock window, so `pool.lock_time` is the binding constraint.

#### Scenario: Pick for Thursday game team is rejected after Thursday kickoff
- **WHEN** a user submits `POST /picks/create` for a team playing Thursday night after that game's `start_time` has passed but before Sunday `pool.lock_time`
- **THEN** the response is HTTP 423 with detail containing "locked"

#### Scenario: Switching from a Thursday pick to a Sunday pick is rejected after Thursday kickoff
- **WHEN** a user has an existing pick for a Thursday-night team and submits `PUT /picks/{pick_id}` to change to a Sunday-game team after Thursday kickoff but before Sunday `pool.lock_time`
- **THEN** the response is HTTP 423 — the pick was locked at Thursday kickoff, regardless of the new team's game time

#### Scenario: Pick for Sunday 4pm game is not locked before pool lock_time
- **WHEN** a user submits `POST /picks/create` for a team in a Sunday 4pm game at any time before `pool.lock_time`
- **THEN** the response is HTTP 200

#### Scenario: Pick for Monday Night Football team is not locked before pool lock_time
- **WHEN** a user submits `POST /picks/create` for a MNF team before `pool.lock_time`
- **THEN** the response is HTTP 200

### Requirement: Picks are rejected for eliminated entries
The system SHALL reject pick creation for entries with `Entry.alive == False`, returning HTTP 403.

#### Scenario: Create pick for eliminated entry returns 403
- **WHEN** a user submits `POST /picks/create` for an entry with `alive=False`
- **THEN** the response is HTTP 403 with detail "Entry has been eliminated"

#### Scenario: Create pick for alive entry succeeds
- **WHEN** a user submits `POST /picks/create` for an entry with `alive=True`
- **THEN** the response proceeds to other validation normally

### Requirement: lock-week sets locked=True on all existing week-N picks
When `POST /admin/pools/{pool_id}/lock-week/{week}` is called, the system SHALL set `Pick.locked = True` on all existing picks for week N in that pool (in addition to creating auto-picks for entries with no pick).

#### Scenario: Existing picks are locked after lock-week
- **WHEN** lock-week is called for week N
- **THEN** all picks for week N in that pool have `locked=True` regardless of whether they were manually submitted or auto-created

#### Scenario: User cannot update pick after lock-week
- **WHEN** lock-week has been called and a user attempts `PUT /picks/{pick_id}` on their week-N pick
- **THEN** the response is HTTP 400 with detail "Cannot update a locked pick"
