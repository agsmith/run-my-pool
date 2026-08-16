## 1. Dependencies

- [x] 1.1 Add `alembic` to `rmp/backend/requirements.txt`

## 2. Alembic Initialization

- [x] 2.1 Run `alembic init alembic` inside `rmp/backend/` to scaffold the Alembic directory structure
- [x] 2.2 Update `alembic/env.py` to import `Base` from `models.py` and set `target_metadata = Base.metadata`
- [x] 2.3 Update `alembic/env.py` to read `DATABASE_URL` from environment and inject into config at runtime (both offline and online modes)
- [x] 2.4 Update `alembic.ini` to remove any hardcoded `sqlalchemy.url` value

## 3. Baseline Revision

- [x] 3.1 Run `alembic revision --autogenerate -m "initial_schema"` to generate the baseline revision
- [x] 3.2 Review the generated revision file and correct any autogenerate gaps (e.g., server defaults, index types, `winning_team_id` nullability)
- [x] 3.3 Add `INSERT INTO teams` data (all 34 rows) to the `upgrade()` function using `ON DUPLICATE KEY UPDATE`
- [x] 3.4 Add `INSERT INTO rules` data (all 6 rows) to the `upgrade()` function using `ON DUPLICATE KEY UPDATE`
- [x] 3.5 Add `DROP TABLE` statements in correct dependency order to the `downgrade()` function

## 4. Schedule Seed Script

- [x] 4.1 Create `rmp/backend/seed_schedule.py` with the full 2025 season schedule data (extracted from `datamodel.sql`)
- [x] 4.2 Implement idempotent inserts using `INSERT ... ON DUPLICATE KEY UPDATE`
- [x] 4.3 Verify the script reads `DATABASE_URL` from environment and loads `.env` via `python-dotenv`

## 5. Update `main.py`

- [x] 5.1 Replace the `print("Database schema is managed by datamodel.sql...")` line with a comment directing developers to use `alembic upgrade head`

## 6. Verification — Local

- [x] 6.1 Run `alembic upgrade head` against a fresh local MySQL database and verify all tables are created correctly
- [x] 6.2 Verify NFL teams (34 rows) and rules (6 rows) are present after upgrade
- [x] 6.3 Run `python seed_schedule.py` and verify schedule rows are inserted
- [x] 6.4 Run `python seed_schedule.py` a second time and verify no errors and no duplicates (idempotency)
- [x] 6.5 Run `alembic downgrade base` and verify all tables are dropped cleanly
- [x] 6.6 Run `alembic upgrade head` again after downgrade and verify full restoration

## 7. Production Baselining (one-time deployment step)

- [x] 7.1 Document the one-time prod baselining procedure in `rmp/backend/README.md` (or `DEPLOYMENT.md`): run `alembic stamp head` before any future `alembic upgrade head` calls
- [x] 7.2 On first deploy to production: run `alembic stamp head` to record current state without re-running DDL
- [x] 7.3 Verify `alembic current` shows the head revision ID on production after stamping
