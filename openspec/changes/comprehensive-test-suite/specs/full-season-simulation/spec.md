## ADDED Requirements

### Requirement: Season fixture seeds 750 users and 2000 entries
The test suite SHALL provide a session-scoped pytest fixture that creates 750 unique users and 2000 entries distributed across those users in a single pool, seeded from the actual 2025 NFL schedule JSON (17 weeks, 256 games, 32 teams).

#### Scenario: User and entry distribution
- **WHEN** the season fixture is initialized
- **THEN** exactly 750 users exist, exactly 2000 entries exist, and each entry belongs to one of the 750 users

#### Scenario: Schedule is fully seeded
- **WHEN** the season fixture is initialized
- **THEN** all 256 games from the 2025 regular season JSON are present in the Schedule table with correct week numbers, home/away team IDs, and start times

### Requirement: Each week picks are made before lock and verified after results
The test suite SHALL simulate all 17 weeks of the 2025 season by making picks for all alive entries before lock time, simulating game results, verifying elimination, and asserting correctness invariants at each week boundary.

#### Scenario: Alive entries make picks each week
- **WHEN** simulating week N before lock time
- **THEN** every alive entry that does not already have a pick for week N receives a pick for an eligible team (one not previously picked by that entry)

#### Scenario: Dead entries cannot make picks
- **WHEN** an entry has alive=False after a prior week's result
- **THEN** any attempt to create a pick for that entry returns a 404

#### Scenario: Elimination attrition reduces entry count each week
- **WHEN** game results are simulated for week N with a known set of winners and losers
- **THEN** the number of alive entries after week N is strictly less than or equal to the number before week N

### Requirement: Season-end invariants hold across all 17 weeks
The test suite SHALL assert a set of global invariants after all 17 weeks have been simulated.

#### Scenario: No entry has the same team twice
- **WHEN** all 17 weeks have been simulated
- **THEN** for every entry (alive or dead), no team abbreviation appears more than once across all its picks

#### Scenario: Every eliminated entry has exactly one loss pick
- **WHEN** all 17 weeks have been simulated
- **THEN** every entry with alive=False has at least one pick with result="loss"

#### Scenario: Every surviving entry has all winning picks
- **WHEN** all 17 weeks have been simulated
- **THEN** every entry with alive=True has no pick with result="loss"

### Requirement: simulate_game_result helper sets results and triggers elimination
The test suite SHALL provide a helper function `simulate_game_result(db, game_id, winner_team_id)` that sets `Schedule.winning_team_id`, updates all `Pick.result` values for that game's teams, and calls the elimination logic.

#### Scenario: Winning team picks get result=win
- **WHEN** simulate_game_result is called with a winner_team_id
- **THEN** all picks for that team in that week have result="win"

#### Scenario: Losing team picks get result=loss
- **WHEN** simulate_game_result is called with a winner_team_id
- **THEN** all picks for the opposing team in that game have result="loss"

#### Scenario: Entries with loss picks are eliminated
- **WHEN** simulate_game_result is called and some entries picked the losing team
- **THEN** those entries have alive=False after the call
