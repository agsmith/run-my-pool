## ADDED Requirements

### Requirement: Breakdown endpoint returns only revealed picks
The system SHALL provide an endpoint `GET /picks/pool/{pool_id}/week/{week}/breakdown` that returns per-team pick counts. A pick SHALL only be included in the response if the game containing that team has already started (`Schedule.start_time < current UTC time`). The endpoint SHALL return an empty array if no games have started yet for the given week.

#### Scenario: Games have not started yet
- **WHEN** a client requests the breakdown for a week where no games have kicked off
- **THEN** the endpoint returns an empty array

#### Scenario: Some games have started
- **WHEN** a client requests the breakdown for a week where a subset of games have kicked off
- **THEN** the endpoint returns pick counts only for teams in those started games

#### Scenario: All games have started
- **WHEN** a client requests the breakdown for a week where all games have kicked off
- **THEN** the endpoint returns pick counts for all teams that received at least one pick

---

### Requirement: Breakdown counts alive entries only
The system SHALL count only entries where `Entry.alive = True`. Eliminated entries SHALL NOT contribute to pick counts.

#### Scenario: Eliminated entries are excluded
- **WHEN** an eliminated entry picked team A and an alive entry picked team A
- **THEN** team A's count in the breakdown is 1, not 2

---

### Requirement: Breakdown reflects current pick state
The system SHALL always query the current value of `Pick.team` and `Pick.team_id`. Admin-overridden picks SHALL be reflected in the breakdown immediately with their updated team.

#### Scenario: Admin changes a pick after game starts
- **WHEN** an admin changes an entry's pick from team A to team B after team A's game has kicked off
- **THEN** the breakdown shows team B's count incremented and team A's count decremented

---

### Requirement: Frontend panel is hidden when no reveals exist
The system SHALL NOT render the pick breakdown panel when `breakdownData` is empty (no games started yet for the selected week).

#### Scenario: No games started
- **WHEN** the user views the entries page for a week where no games have kicked off
- **THEN** the breakdown panel is not present in the DOM

#### Scenario: At least one game started
- **WHEN** the user views the entries page for a week where at least one game has kicked off
- **THEN** the breakdown panel is visible above the entries grid

---

### Requirement: Frontend panel updates when selected week changes
The system SHALL fetch a new breakdown whenever the user changes the selected week on the entries page.

#### Scenario: User changes week
- **WHEN** the user clicks a different week on the entries grid
- **THEN** the breakdown panel updates to show data for the newly selected week (or hides if no games started)

---

### Requirement: Breakdown is sorted by pick count descending
The system SHALL return breakdown items ordered from highest pick count to lowest.

#### Scenario: Multiple teams with picks
- **WHEN** the breakdown contains multiple teams
- **THEN** the team with the most picks appears first in the list
