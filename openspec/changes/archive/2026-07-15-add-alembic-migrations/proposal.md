## Why

Schema changes are currently managed through raw SQL files (`datamodel.sql`, ad-hoc `.sql` files, and one-off Python scripts) with no version tracking, no guaranteed application order, and no way to know what has been applied to any given environment. This creates prod risk: a fresh environment cannot be reliably set up from scratch, and future schema changes have no safe, auditable path to production.

## What Changes

- Add Alembic to the backend as the sole schema migration tool
- Create a baseline revision (`001_initial_schema`) generated from `models.py`, which reflects the actual current prod state
- Include static reference data (NFL teams, survivor pool rules) in the baseline revision
- Add a separate `seed_schedule.py` script for season schedule data (changes annually — not suitable for migrations)
- Add `alembic` to `requirements.txt`
- Update `main.py` to no longer reference `datamodel.sql` for schema management
- Document the migration workflow for developers and deployments

## Capabilities

### New Capabilities

- `schema-migrations`: Versioned, auditable database schema management via Alembic — baseline revision from current models, with a defined workflow for authoring and applying future revisions

### Modified Capabilities

_(none — no existing spec-level behavior changes)_

## Impact

- **Backend**: `requirements.txt`, `main.py` (comment update), new `alembic/` directory, new `seed_schedule.py`
- **Dependencies**: `alembic` added
- **Prod deployment**: First deploy requires `alembic stamp head` to baseline existing RDS instance without re-running DDL
- **Dev onboarding**: `alembic upgrade head` + `python seed_schedule.py` replaces manual SQL execution
- **Ad-hoc SQL files**: `datamodel.sql`, `update_enum.sql`, `alter_schedule_winning_team_id.sql`, `fix_duplicate_constraints.py` become obsolete reference artifacts — not deleted, but no longer the source of truth
