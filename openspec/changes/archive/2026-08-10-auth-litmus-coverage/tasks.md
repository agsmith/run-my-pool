## 1. Already complete (litmus pipeline ran)

- [x] 1.1 Run litmus discover tasks (architecture, API surface, existing tests, use cases) — all complete
- [x] 1.2 Run litmus plan task — 28 tests T-01 through T-28 planned
- [x] 1.3 Run litmus gaps task — 6 additional gap tests G-01 through G-06 identified
- [x] 1.4 Run litmus generate task — 34 tests written to `tests/test_auth.py`
- [x] 1.5 Run litmus execute task — 45 tests pass (11 existing + 34 new), 0 failures

## 2. Documentation

- [x] 2.1 Update `TESTING.md` — add new auth test classes to the auth section, update test count, note litmus workspace location
- [x] 2.2 Run full test suite `cd rmp/backend && venv/bin/python -m pytest tests/ -q` to confirm no regressions
