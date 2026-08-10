## ADDED Requirements

### Requirement: Any picked team is consumed forever for that entry
The system SHALL prevent an entry from picking any team it has previously selected in any prior week, regardless of whether that pick resulted in a win or a loss. Team eligibility is per-entry, not per-user.

#### Scenario: Winning team cannot be repicked
- **WHEN** an entry picked team X in week N and the game resulted in a win (Pick.result="win")
- **THEN** a POST /picks/create or PUT /picks/{pick_id} selecting team X in any subsequent week returns HTTP 400 with detail containing "already been selected"

#### Scenario: Losing team cannot be repicked
- **WHEN** an entry picked team X in week N and the game resulted in a loss (Pick.result="loss")
- **THEN** a POST /picks/create or PUT /picks/{pick_id} selecting team X in any subsequent week returns HTTP 400 with detail containing "already been selected"

#### Scenario: Team with no result yet cannot be repicked
- **WHEN** an entry picked team X in week N and the game has not yet resolved (Pick.result=null)
- **THEN** a POST /picks/create selecting team X in week N+1 returns HTTP 400 with detail containing "already been selected"

### Requirement: Team uniqueness is scoped per entry, not per user
The system SHALL allow two different entries owned by the same user to pick the same team in the same week.

#### Scenario: Same user, two entries, same team same week
- **WHEN** a user has Entry A and Entry B, and Entry A picks team X in week N
- **THEN** Entry B can also pick team X in week N and receive HTTP 200

#### Scenario: Same user, two entries, same team different weeks
- **WHEN** a user has Entry A and Entry B, and Entry A picked team X in week 1
- **THEN** Entry B can pick team X in week 2 and receive HTTP 200

### Requirement: Updating a pick to a previously used team is rejected
The system SHALL reject PUT /picks/{pick_id} when the new team has already been used by the same entry in any other week.

#### Scenario: Update pick to already-used team returns 400
- **WHEN** an entry has picks for team X in week 1 and team Y in week 2, and a PUT request changes the week 2 pick to team X
- **THEN** the response is HTTP 400 with detail containing "already been selected"

#### Scenario: Update pick to different unused team succeeds
- **WHEN** an entry updates an unlocked pick to a team it has never selected before
- **THEN** the response is HTTP 200 and the pick is updated

### Requirement: Eligible team list shrinks as picks are made each season
The system SHALL track all teams used by an entry across all weeks, and the eligible team pool for that entry SHALL shrink by exactly one for each pick made or locked.

#### Scenario: Eligible teams decrease after each pick
- **WHEN** an entry has made picks for K distinct teams across K weeks
- **THEN** the remaining eligible teams for that entry equals 32 minus K

#### Scenario: Full season does not exhaust eligibility before week 17
- **WHEN** an entry survives all 17 weeks with one pick per week
- **THEN** the entry has used 17 of 32 teams and 15 teams remain eligible
