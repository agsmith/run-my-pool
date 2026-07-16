## MODIFIED Requirements

### Requirement: Lock enforcement extends to auto-pick triggering

The existing pool-lock-enforcement spec covers entry create/delete being blocked after lock time. This delta adds: when the admin explicitly locks a week, the system must also trigger auto-pick for any alive entry that has not submitted a pick for that week.

#### Scenario: Lock-week endpoint triggers auto-pick as part of lock
- **WHEN** `POST /admin/pools/{pool_id}/lock-week/{week}` is called
- **THEN** the pool's `lock_time` is set to now (if not already in the past) AND auto-picks are created for entries missing a pick, in a single atomic operation

#### Scenario: Lock-week is idempotent
- **WHEN** `POST /admin/pools/{pool_id}/lock-week/{week}` is called a second time after already being called
- **THEN** the pool remains locked, no duplicate picks are created, and the response reports `auto_picks_created: 0`
