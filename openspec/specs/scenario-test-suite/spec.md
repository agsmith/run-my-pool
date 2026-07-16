## ADDED Requirements

### Requirement: Season simulation covers a complete survivor pool lifecycle

The scenario test suite must simulate realistic usage of the application across multiple weeks, covering the full lifecycle from pool creation through final survivor determination.

#### Scenario: Week 1 — picks submitted before lock
- **WHEN** 10 users each register, create an entry, and submit a pick for week 1 before lock
- **THEN** all picks are accepted and each entry has exactly one pick for week 1

#### Scenario: Week 1 — pick change before lock
- **WHEN** a user submits a pick and then submits a different team for the same week before lock
- **THEN** the second pick replaces the first (upsert behavior) and only one pick exists for that entry/week

#### Scenario: Week 1 — pick rejected after lock
- **WHEN** a user attempts to submit or change a pick after the pool's lock_time has passed
- **THEN** the request is rejected with HTTP 423

#### Scenario: Week 1 — auto-pick for missing entry
- **WHEN** one entry has not submitted a pick and the admin calls lock-week
- **THEN** the system auto-assigns the most popular team for that entry and the pick is marked locked

#### Scenario: Week 1 — results processed, entries eliminated
- **WHEN** game results are written to the schedule table and eliminate_losing_entries is called
- **THEN** entries whose picked team lost have `alive=False` and entries whose team won remain `alive=True`

#### Scenario: Week 2 — eliminated entries cannot pick
- **WHEN** an eliminated entry's user attempts to submit a pick for week 2
- **THEN** — note: the current API does not block picks for dead entries; this scenario documents the gap for future enforcement

#### Scenario: Week 2 — team reuse rejected
- **WHEN** a user attempts to pick a team they already used in week 1
- **THEN** the request is rejected with HTTP 400

#### Scenario: Admin corrects a pick after lock
- **WHEN** a pool admin changes the team on a locked pick
- **THEN** the pick is updated, the audit log reflects the change, and the team uniqueness check still applies

#### Scenario: Full audit trail is complete
- **WHEN** the season simulation completes
- **THEN** audit log entries exist for: every pick creation/update, every auto-pick, every admin pick edit, every entry elimination, and all login events
