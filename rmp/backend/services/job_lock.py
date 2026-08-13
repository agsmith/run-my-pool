"""Cross-process exclusion for one-off database jobs."""

from contextlib import contextmanager

from sqlalchemy import text
from sqlalchemy.engine import Engine


class JobLockError(RuntimeError):
    pass


@contextmanager
def advisory_job_lock(engine: Engine, name: str):
    """Yield whether a nonblocking MySQL named lock was acquired.

    SQLite is used only for local tests and has no cross-process named locks,
    so it behaves as acquired there. MySQL locks are connection-scoped; the
    dedicated connection remains open through the entire context.
    """
    if engine.dialect.name != "mysql":
        yield True
        return

    connection = engine.connect()
    acquired = False
    try:
        value = connection.execute(
            text("SELECT GET_LOCK(:name, 0)"), {"name": name}
        ).scalar()
        if value is None:
            raise JobLockError("MySQL could not evaluate the updater lock")
        acquired = value == 1
        yield acquired
    finally:
        if acquired:
            connection.execute(text("SELECT RELEASE_LOCK(:name)"), {"name": name})
        connection.close()
