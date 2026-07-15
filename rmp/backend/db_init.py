#!/usr/bin/env python3
"""
One-shot database initialization script.
Runs inside the ECS container on a fresh database.

Steps:
  1. Create all tables via SQLAlchemy models
  2. Insert reference data (NFL teams + pool rules)
  3. Stamp Alembic as head (so future alembic upgrade head works)
  4. Run seed_schedule.py (2025 NFL schedule)
"""

import os
import sys
import subprocess

sys.path.insert(0, "/app")

from database import engine
from models import Base
from sqlalchemy import text


def create_schema():
    Base.metadata.create_all(bind=engine)
    print("✓ Schema created")


def seed_reference_data():
    with engine.connect() as conn:
        conn.execute(
            text("""
            INSERT INTO teams (id, name, abbrv, logo) VALUES
            (1,'Atlanta Falcons','ATL','/nfl/atl.svg'),
            (2,'Buffalo Bills','BUF','/nfl/buf.svg'),
            (3,'Chicago Bears','CHI','/nfl/chi.svg'),
            (4,'Cincinnati Bengals','CIN','/nfl/cin.svg'),
            (5,'Cleveland Browns','CLE','/nfl/cle.svg'),
            (6,'Dallas Cowboys','DAL','/nfl/dal.svg'),
            (7,'Denver Broncos','DEN','/nfl/den.svg'),
            (8,'Detroit Lions','DET','/nfl/det.svg'),
            (9,'Green Bay Packers','GB','/nfl/gb.svg'),
            (10,'Tennessee Titans','TEN','/nfl/ten.svg'),
            (11,'Indianapolis Colts','IND','/nfl/ind.svg'),
            (12,'Kansas City Chiefs','KC','/nfl/kc.svg'),
            (13,'Las Vegas Raiders','LV','/nfl/lv.svg'),
            (14,'Los Angeles Rams','LAR','/nfl/lar.svg'),
            (15,'Miami Dolphins','MIA','/nfl/mia.svg'),
            (16,'Minnesota Vikings','MIN','/nfl/min.svg'),
            (17,'New England Patriots','NE','/nfl/ne.svg'),
            (18,'New Orleans Saints','NO','/nfl/no.svg'),
            (19,'New York Giants','NYG','/nfl/nyg.svg'),
            (20,'New York Jets','NYJ','/nfl/nyj.svg'),
            (21,'Philadelphia Eagles','PHI','/nfl/phi.svg'),
            (22,'Arizona Cardinals','ARI','/nfl/ari.svg'),
            (23,'Pittsburgh Steelers','PIT','/nfl/pit.svg'),
            (24,'Los Angeles Chargers','LAC','/nfl/lac.svg'),
            (25,'San Francisco 49ers','SF','/nfl/sf.svg'),
            (26,'Seattle Seahawks','SEA','/nfl/sea.svg'),
            (27,'Tampa Bay Buccaneers','TB','/nfl/tb.svg'),
            (28,'Washington Commanders','WSH','/nfl/wsh.svg'),
            (29,'Carolina Panthers','CAR','/nfl/car.svg'),
            (30,'Jacksonville Jaguars','JAX','/nfl/jax.svg'),
            (33,'Baltimore Ravens','BAL','/nfl/bal.svg'),
            (34,'Houston Texans','HOU','/nfl/hou.svg'),
            (98,'Losing Team','LT','/nfl/red_x.svg'),
            (99,'No Team','NT','/nfl/green_plus.svg')
            ON DUPLICATE KEY UPDATE name=VALUES(name), logo=VALUES(logo)
        """)
        )
        conn.execute(
            text("""
            INSERT INTO rules (id, pool_type, rule_text, rule_type, default_value, enabled_by_default) VALUES
            ('weekly-lock-day','survivor','Weekly Lock Day','selection','0',true),
            ('weekly-lock-time','survivor','Weekly Lock Time','time','13:00:00',true),
            ('auto-pick-enabled','survivor','Auto-Pick Enabled','boolean','false',true),
            ('auto-pick-strategy','survivor','Auto-Pick Strategy','selection','random',true),
            ('game-mode','survivor','Game Mode','selection','pick_winner',true),
            ('message-board-enabled','survivor','Message Board Enabled','boolean','true',true)
            ON DUPLICATE KEY UPDATE rule_text=VALUES(rule_text), default_value=VALUES(default_value)
        """)
        )
        conn.commit()
    print("✓ Reference data seeded (teams + rules)")


def stamp_alembic():
    result = subprocess.run(
        ["alembic", "stamp", "head"], capture_output=True, text=True, cwd="/app"
    )
    print(result.stdout.strip())
    if result.stderr.strip():
        print(result.stderr.strip())
    if result.returncode != 0:
        print("ERROR: alembic stamp failed")
        sys.exit(1)
    print("✓ Alembic stamped as head")


def seed_schedule():
    # Import and run seed_schedule as a module
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "seed_schedule", "/app/seed_schedule.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    print("✓ 2025 NFL schedule seeded")


if __name__ == "__main__":
    print("=== RunMyPool DB Init ===")
    create_schema()
    seed_reference_data()
    stamp_alembic()
    seed_schedule()
    print("=== Init complete ===")
