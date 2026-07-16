## ADDED Requirements

### Requirement: Baseline migration exists
The system SHALL include an Alembic baseline revision that creates all current database tables and inserts static reference data (NFL teams and survivor pool rules), such that running `alembic upgrade head` on a blank database produces a fully functional schema.

#### Scenario: Fresh database setup
- **WHEN** a developer runs `alembic upgrade head` against a blank MySQL database
- **THEN** all tables are created with correct columns, types, constraints, and indexes
- **AND** all 34 NFL team records (32 teams + NT/LT sentinels) are present in the `teams` table
- **AND** all 6 survivor pool rule records are present in the `rules` table
- **AND** the `alembic_version` table records the head revision ID

#### Scenario: Idempotent re-run
- **WHEN** `alembic upgrade head` is run against a database that is already at head
- **THEN** the command completes successfully with no SQL changes applied

### Requirement: Production baselining via stamp
The system SHALL support baselining an existing production database using `alembic stamp head`, which records the current revision without executing any DDL.

#### Scenario: Stamp existing production database
- **WHEN** `alembic stamp head` is run against a database that already has the schema applied manually
- **THEN** the `alembic_version` table is created and populated with the head revision ID
- **AND** no DDL statements are executed against existing tables

#### Scenario: Normal upgrades after stamp
- **WHEN** a new Alembic revision is added after the database has been stamped
- **THEN** `alembic upgrade head` applies only the new revision
- **AND** previously stamped revisions are not re-applied

### Requirement: Environment-driven database URL
The system SHALL read the database connection URL from the `DATABASE_URL` environment variable and SHALL NOT require a hardcoded URL in `alembic.ini`.

#### Scenario: Database URL from environment
- **WHEN** `DATABASE_URL` is set in the environment
- **THEN** Alembic uses that URL for all migration operations
- **AND** no credentials are stored in version-controlled configuration files

#### Scenario: Missing DATABASE_URL
- **WHEN** `DATABASE_URL` is not set
- **THEN** Alembic fails with a clear error indicating the variable is missing

### Requirement: Rollback support
The system SHALL support rolling back one or more applied revisions using `alembic downgrade`.

#### Scenario: Roll back one revision
- **WHEN** `alembic downgrade -1` is run
- **THEN** the most recently applied revision is reversed
- **AND** the `alembic_version` table reflects the prior revision

### Requirement: Season schedule seeded separately
The system SHALL provide a standalone `seed_schedule.py` script for inserting season schedule data, separate from Alembic migrations.

#### Scenario: Seed schedule on fresh environment
- **WHEN** `python seed_schedule.py` is run after `alembic upgrade head`
- **THEN** all schedule rows for the current season are inserted into the `schedule` table

#### Scenario: Idempotent schedule seeding
- **WHEN** `python seed_schedule.py` is run against a database that already contains schedule data
- **THEN** the script completes without error and no duplicate rows are created
