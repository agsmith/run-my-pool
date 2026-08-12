import os
import subprocess
import sys

import models


def test_schedule_has_week_and_time_indexes():
    indexes = {index.name: tuple(column.name for column in index.columns) for index in models.Schedule.__table__.indexes}
    assert indexes["ix_schedule_week_start"] == ("week_num", "start_time")
    assert indexes["ix_schedule_start_time"] == ("start_time",)


def test_mysql_pool_configuration_is_bounded():
    env = {
        **os.environ,
        "DATABASE_URL": "mysql+mysqlconnector://user:password@127.0.0.1/runmypool",
        "DB_POOL_SIZE": "7",
        "DB_MAX_OVERFLOW": "3",
        "DB_POOL_TIMEOUT_SECONDS": "12",
        "DB_POOL_RECYCLE_SECONDS": "900",
    }
    script = """
import database
pool = database.engine.pool
assert pool.size() == 7
assert pool._max_overflow == 3
assert pool._timeout == 12
assert pool._recycle == 900
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=os.path.dirname(os.path.dirname(__file__)),
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
