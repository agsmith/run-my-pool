# RunMyPool Backend

[![Build and Deploy Backend](https://github.com/agsmith/run-my-pool/actions/workflows/build-backend.yml/badge.svg)](https://github.com/agsmith/run-my-pool/actions/workflows/build-backend.yml)
[![codecov](https://codecov.io/gh/agsmith/run-my-pool/graph/badge.svg?flag=backend)](https://codecov.io/gh/agsmith/run-my-pool)

This is the FastAPI backend for the RunMyPool application.

## Getting Started

1. Create a virtual environment and activate it:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set up environment variables — copy `.env` and fill in values:
   ```bash
   cp .env.example .env   # or set DATABASE_URL directly
   ```
4. Apply database migrations:
   ```bash
   alembic upgrade head
   ```
5. Seed the season schedule:
   ```bash
   python seed_schedule.py
   ```
6. Run the development server:
   ```bash
   uvicorn main:app --reload
   ```

The API will be available at http://localhost:8000

---

## Database Migrations (Alembic)

Schema changes are managed with [Alembic](https://alembic.sqlalchemy.org/).

### Environment variable

All Alembic commands require `DATABASE_URL` to be set:

```bash
export DATABASE_URL="mysql+mysqlconnector://user:password@host:3306/dbname"
```

Or place it in `.env` — the backend loads it automatically.

### Common commands

| Command | Description |
|---|---|
| `alembic upgrade head` | Apply all pending migrations |
| `alembic downgrade -1` | Roll back the last migration |
| `alembic current` | Show the currently applied revision |
| `alembic history` | Show full migration history |
| `alembic revision --autogenerate -m "description"` | Generate a new revision from model changes |

### Authoring a schema change

1. Edit `models.py` with your changes
2. Generate a revision: `alembic revision --autogenerate -m "your description"`
3. Review the generated file in `alembic/versions/` — autogenerate is not perfect, always inspect it
4. Apply it locally: `alembic upgrade head`
5. Commit the revision file with your code changes

---

## Production Baselining (one-time, first deploy only)

The production RDS instance has the schema applied manually. Before running `alembic upgrade head` in production for the first time, you must stamp the database to tell Alembic where it currently stands — without re-running DDL.

**Run this once on production after deploying Alembic:**

```bash
# 1. Verify DATABASE_URL points to production RDS
alembic stamp head

# 2. Confirm it worked
alembic current
# Expected: 67ecb851b587 (head)
```

After stamping, all future schema changes deploy normally via `alembic upgrade head`.

---

## Season Schedule

The NFL season schedule is **not** managed by Alembic migrations (it changes annually). Synchronize a season from ESPN with a dry run first:

```bash
python sync_schedule.py --season 2026
python sync_schedule.py --season 2026 --apply
```

The synchronizer is idempotent and validates all 18 regular-season weeks before writing. It rejects duplicate teams, invalid game counts, missing team mappings, and removal of stale games referenced by frozen pool lines. The static `seed_schedule.py` file is retained only for legacy 2025 development data.
