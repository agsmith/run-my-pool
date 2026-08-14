"""Unit tests for advisory_job_lock in rmp/backend/services/job_lock.py."""

import threading
from contextlib import contextmanager

import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from services.job_lock import JobLockError, advisory_job_lock


@pytest.fixture
def sqlite_engine():
    """In-memory SQLite engine for job-lock testing."""
    return create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


class TestAdvisoryJobLock:
    """Tests for advisory_job_lock context manager."""

    def test_lock_acquired_on_sqlite_always_yields_true(self, sqlite_engine):
        """SQLite always yields True — no cross-process locking needed locally."""
        with advisory_job_lock(sqlite_engine, "test-lock") as acquired:
            assert acquired is True

    def test_lock_yields_without_error_on_sqlite(self, sqlite_engine):
        """Context manager enters and exits cleanly on SQLite."""
        entered = False
        with advisory_job_lock(sqlite_engine, "clean-lock") as acquired:
            entered = True
        assert entered

    def test_lock_can_be_reacquired_after_release(self, sqlite_engine):
        """The same lock name can be re-entered after the context exits."""
        with advisory_job_lock(sqlite_engine, "reuse-lock") as first:
            assert first is True
        with advisory_job_lock(sqlite_engine, "reuse-lock") as second:
            assert second is True

    def test_lock_with_empty_string_name(self, sqlite_engine):
        """Lock with empty string name does not raise on SQLite (no server-side enforcement)."""
        with advisory_job_lock(sqlite_engine, "") as acquired:
            assert acquired is True

    def test_lock_exception_inside_context_propagates(self, sqlite_engine):
        """Exceptions raised inside the context propagate out normally."""
        with pytest.raises(RuntimeError, match="inner error"):
            with advisory_job_lock(sqlite_engine, "error-lock"):
                raise RuntimeError("inner error")

    def test_two_sequential_acquisitions_of_same_name(self, sqlite_engine):
        """Two sequential acquisitions of the same lock name both succeed on SQLite."""
        results = []
        with advisory_job_lock(sqlite_engine, "seq-lock") as a:
            results.append(a)
        with advisory_job_lock(sqlite_engine, "seq-lock") as b:
            results.append(b)
        assert results == [True, True]

    def test_different_lock_names_are_independent(self, sqlite_engine):
        """Different lock names can be held simultaneously without conflict on SQLite."""
        with advisory_job_lock(sqlite_engine, "lock-alpha") as a:
            with advisory_job_lock(sqlite_engine, "lock-beta") as b:
                assert a is True
                assert b is True
