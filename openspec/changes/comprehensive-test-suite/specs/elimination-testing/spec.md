## ADDED Requirements

### Requirement: Lambda simulation sets game results and eliminates entries
The test suite SHALL provide helpers that replicate the Lambda function's core logic: setting Schedule.winning_team_id, updating Pick.result to "win" or "loss", and calling eliminate_losing_entries() — without invoking the actual Lambda or ESPN API.

#### Scenario: simulate_game_result marks correct picks as win
- **WHEN** simulate_game_result(db, game_id, winner_team_id) is called
- **THEN** all picks for the winning team in that game week have result="win"

#### Scenario: simulate_game_result marks incorrect picks as loss
- **WHEN** simulate_game_result(db, game_id, winner_team_id) is called
- **THEN** all picks for the losing team in that game week have result="loss"

#### Scenario: Entries with loss picks are eliminated
- **WHEN** simulate_game_result is called and one or more entries picked the losing team
- **THEN** all such entries have alive=False after the call

#### Scenario: Entries with win picks remain alive
- **WHEN** simulate_game_result is called and one or more entries picked the winning team
- **THEN** those entries retain alive=True

### Requirement: Eliminated entries cannot make picks in subsequent weeks
After elimination, an entry with alive=False SHALL be treated as non-existent for pick purposes.

#### Scenario: Dead entry pick returns 404
- **WHEN** an attempt is made to POST /picks/create for an entry with alive=False
- **THEN** the response is HTTP 404 with detail "Entry not found or doesn't belong to you"

### Requirement: Auto-pick fires for entries with no pick at lock-week
When lock-week is triggered, entries with alive=True that have no pick for the current week SHALL receive an auto-assigned pick using the most-popular-team algorithm.

#### Scenario: Auto-pick assigned to entry with no pick
- **WHEN** lock-week is called and an alive entry has no pick for that week
- **THEN** the entry has a new pick with locked=True after the call

#### Scenario: Auto-pick respects team uniqueness
- **WHEN** auto-pick is assigned to an entry
- **THEN** the assigned team has not been previously picked by that entry in any prior week

#### Scenario: Auto-pick skipped when no eligible teams remain
- **WHEN** auto-pick would be assigned but the entry has used all available teams
- **THEN** no pick is created and an AUTO_PICK_SKIPPED audit log entry exists

### Requirement: Admin entry operations preserve correct state
Admin transfer and delete operations SHALL leave the system in a consistent state with respect to entries, picks, and pool membership.

#### Scenario: Admin transfer moves entry to new user
- **WHEN** a pool admin calls POST /admin/pools/{pool_id}/transfer-entry with a target user email
- **THEN** the entry's user_id is updated to the target user and all picks are preserved

#### Scenario: Admin delete removes entry and its picks
- **WHEN** a pool admin calls DELETE /admin/pools/{pool_id}/entries/{entry_id}
- **THEN** the entry and all associated picks are removed from the database

#### Scenario: Non-admin cannot call admin entry endpoints
- **WHEN** a non-admin user calls any /admin/ route
- **THEN** the response is HTTP 403
