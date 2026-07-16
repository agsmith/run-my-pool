## ADDED Requirements

### Requirement: Auto-pick fires at pool lock time for entries with no pick

When a pool admin triggers week lock via `POST /admin/pools/{pool_id}/lock-week/{week}`, the system must automatically create a pick for every alive entry in the pool that has not submitted a pick for that week.

#### Scenario: Entry has no pick when week is locked
- **WHEN** an alive entry has no pick for the current week and the pool admin calls lock-week
- **THEN** a pick is created for that entry with `locked=True` and the team set to the most popular team among other alive entries that week

#### Scenario: Most popular team is already used by the entry
- **WHEN** the most popular team has already been picked by the entry in a prior week
- **THEN** the system selects the next most popular available team not yet used by that entry

#### Scenario: All teams have been used by the entry
- **WHEN** an entry has used every team that other alive entries picked this week
- **THEN** no auto-pick is created for that entry; it is skipped and logged as a warning

#### Scenario: Entry already has a pick for the week
- **WHEN** an alive entry already has a pick submitted for the week being locked
- **THEN** the existing pick is left unchanged; no new pick is created

#### Scenario: Auto-pick is audit logged
- **WHEN** an auto-pick is created for an entry
- **THEN** an audit log entry with action `AUTO_PICK` is written containing `pool_id`, `entry_id`, `week`, `team`, and `reason: no_pick_at_lock`
