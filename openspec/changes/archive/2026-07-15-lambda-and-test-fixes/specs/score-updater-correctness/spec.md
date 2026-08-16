## ADDED Requirements

### Requirement: Score updater processes only the current NFL week
The score updater Lambda SHALL process game results only for the current NFL week as determined by `get_current_nfl_week()`, not all historical weeks.

#### Scenario: Invocation during week 5
- **WHEN** the Lambda is triggered during NFL week 5
- **THEN** it fetches and processes game results only for week 5
- **AND** it does not make ESPN API calls for weeks 1–4

### Requirement: Score updater skips non-game-time invocations
The score updater Lambda SHALL return early without processing when the current time is outside NFL game hours.

#### Scenario: Invocation at 3am Tuesday
- **WHEN** the Lambda is triggered at a time outside NFL game hours (e.g., Tuesday 3am ET)
- **THEN** it returns a 200 response with message "Skipped - not during NFL game time"
- **AND** it makes no ESPN API calls and no database writes

#### Scenario: Invocation during Sunday afternoon games
- **WHEN** the Lambda is triggered during Sunday 1pm–11:30pm ET during NFL season
- **THEN** it proceeds with score fetching and database updates

### Requirement: Auth test suite passes cleanly
The backend auth test suite SHALL have all tests passing. Login tests SHALL send requests matching the actual endpoint contract (JSON body with `email` field).

#### Scenario: Login test sends correct request format
- **WHEN** the auth test suite runs
- **THEN** all login-related tests pass
- **AND** no tests return HTTP 422 due to request format mismatch
