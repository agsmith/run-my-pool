## ADDED Requirements

### Requirement: Every user action produces a correctly structured audit log entry
The system SHALL produce exactly one AuditLog row for each of the following actions, with the correct action string, entity_type, entity_id, and details structure.

#### Scenario: User registration creates audit entry
- **WHEN** POST /auth/register succeeds
- **THEN** an AuditLog row exists with action="LOGIN_SUCCESS" or action="CREATE_USER" and user_id matching the new user

#### Scenario: Failed login creates audit entry
- **WHEN** POST /auth/login fails due to incorrect credentials
- **THEN** an AuditLog row exists with action="LOGIN_FAILURE"

#### Scenario: Pool creation creates audit entry
- **WHEN** POST /pools/create succeeds
- **THEN** an AuditLog row exists with action="CREATE_POOL" and entity_id matching the new pool's id

#### Scenario: Entry creation creates audit entry
- **WHEN** POST /entries/create succeeds
- **THEN** an AuditLog row exists with action="CREATE_ENTRY" and entity_id matching the new entry's id

#### Scenario: Pick creation creates audit entry
- **WHEN** POST /picks/create succeeds
- **THEN** an AuditLog row exists with action="CREATE_PICK" and entity_id matching the pick's id

#### Scenario: Pick update creates audit entry
- **WHEN** PUT /picks/{pick_id} succeeds
- **THEN** an AuditLog row exists with action="UPDATE_PICK" and details containing before and after values

#### Scenario: Pick deletion creates audit entry
- **WHEN** DELETE /picks/{pick_id} succeeds
- **THEN** an AuditLog row exists with action="DELETE_PICK" and entity_id matching the deleted pick's id

#### Scenario: Message creation creates audit entry
- **WHEN** POST /messages/pool/{pool_id} succeeds
- **THEN** an AuditLog row exists with action="CREATE_MESSAGEBOARD" or equivalent action string

### Requirement: Admin actions produce audit entries prefixed with ADMIN_
All admin operations SHALL produce AuditLog entries with action strings prefixed "ADMIN_".

#### Scenario: Admin lock-week creates audit entry
- **WHEN** POST /admin/pools/{pool_id}/lock-week/{week} succeeds
- **THEN** an AuditLog row exists with action starting with "ADMIN_" related to lock or auto-pick

#### Scenario: Admin pick override creates audit entry
- **WHEN** PATCH /admin/pools/{pool_id}/picks/{pick_id} succeeds
- **THEN** an AuditLog row exists with action="ADMIN_OVERRIDE_PICK" or equivalent ADMIN_ prefix

#### Scenario: Admin entry transfer creates audit entry
- **WHEN** POST /admin/pools/{pool_id}/transfer-entry succeeds
- **THEN** an AuditLog row exists with action="ADMIN_TRANSFER_ENTRY"

### Requirement: Audit log failure does not break the triggering operation
The system SHALL continue processing the main operation even if writing the audit log fails.

#### Scenario: Audit write failure is swallowed
- **WHEN** the audit log write raises an exception (simulated)
- **THEN** the main API operation still returns its success response

### Requirement: Audit logs are immutable — no delete endpoint exists
The system SHALL NOT expose any endpoint that deletes or modifies audit log entries.

#### Scenario: No DELETE route for audit logs
- **WHEN** a DELETE request is made to any /audit/ path
- **THEN** the response is HTTP 405 Method Not Allowed or HTTP 404
