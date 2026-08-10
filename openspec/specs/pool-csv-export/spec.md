### Requirement: Admin can export all pool entries as CSV
The system SHALL provide an endpoint that returns a CSV file containing the email address and entry name for every entry in a pool. The endpoint SHALL be restricted to pool admins.

#### Scenario: Admin downloads entries CSV
- **WHEN** a pool admin calls `GET /admin/pools/{pool_id}/export/entries.csv`
- **THEN** the response is HTTP 200 with `Content-Type: text/csv`, `Content-Disposition: attachment; filename="entries.csv"`, and a CSV body with header row `email,entry_name` followed by one row per entry in the pool

#### Scenario: CSV includes all users' entries, not just the admin's
- **WHEN** the CSV is downloaded for a pool with multiple participants
- **THEN** every entry in the pool appears in the CSV regardless of which user owns it

#### Scenario: Non-admin cannot download CSV
- **WHEN** a non-admin user calls the CSV export endpoint
- **THEN** the response is HTTP 403

#### Scenario: CSV is sorted by email then entry name
- **WHEN** the CSV is generated
- **THEN** rows are ordered alphabetically by email address, then by entry name within each user

#### Scenario: Admin console has an Export CSV button
- **WHEN** a pool admin views the admin console for a pool
- **THEN** an "Export CSV" button is present that triggers a browser download of the entries CSV
