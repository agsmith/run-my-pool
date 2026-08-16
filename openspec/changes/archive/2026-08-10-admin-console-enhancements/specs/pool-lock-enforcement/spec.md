## MODIFIED Requirements

### Requirement: Pool lock time is configurable in the admin console
The admin console SHALL provide a datetime picker with timezone selector for configuring `pool.lock_time`. The UI SHALL convert the selected local time to UTC before sending to the backend.

#### Scenario: Admin sets pool lock time via admin console
- **WHEN** a pool admin selects a date, time, and timezone in the admin console lock time picker and submits
- **THEN** `PATCH /pools/{pool_id}` is called with the correct UTC-converted ISO datetime string and the pool's `lock_time` is updated

#### Scenario: Timezone selection converts to UTC correctly
- **WHEN** an admin selects 1:00 PM Eastern Time on a Sunday
- **THEN** the value sent to the backend is `17:00:00 UTC` (ET is UTC-4 during daylight saving)

#### Scenario: Lock time picker shows current lock time if set
- **WHEN** the admin console loads for a pool with an existing `lock_time`
- **THEN** the picker is pre-populated with the current lock time converted to the admin's selected timezone

#### Scenario: PATCH /pools/{pool_id} parses lock_time consistently with POST
- **WHEN** `PATCH /pools/{pool_id}` is called with a `lock_time` string in ISO or `YYYY-MM-DD HH:MM:SS` format
- **THEN** the datetime is parsed using the same logic as `POST /pools/create` — no raw assignment without parsing
