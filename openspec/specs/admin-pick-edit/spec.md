## ADDED Requirements

### Requirement: Pool admin can override the team on any pick

A pool admin may update the `team` field on any pick in their pool, bypassing the normal lock enforcement. The override is fully audit logged and the pick remains locked after the change.

#### Scenario: Admin changes team on a locked pick
- **WHEN** a pool admin calls `PATCH /admin/pools/{pool_id}/picks/{pick_id}` with a new team
- **THEN** the pick's team is updated, `locked` remains `True`, and an audit log entry with action `ADMIN_PICK_EDIT` is written

#### Scenario: Admin attempts to set a team already used by the entry
- **WHEN** the new team has already been picked by the same entry in a different week
- **THEN** the request is rejected with HTTP 400 and the pick is unchanged

#### Scenario: Non-admin attempts admin pick edit
- **WHEN** a user who is not a pool admin or pool owner calls the endpoint
- **THEN** the request is rejected with HTTP 403

#### Scenario: Pick not in specified pool
- **WHEN** the pick_id exists but belongs to a different pool than pool_id
- **THEN** the request is rejected with HTTP 404

#### Scenario: Audit log contains before/after
- **WHEN** an admin pick edit succeeds
- **THEN** the audit log entry contains `old_team`, `new_team`, `week`, `entry_id`, `pool_id`, and `admin_email`
