# Design: auth-litmus-coverage

Comprehensive auth test coverage produced via the litmus test generation pipeline. 34 new tests added to `test_auth.py`.

## Context

The litmus pipeline ran 8 tasks: 4 parallel discover tasks (architecture, API surface, existing tests, use cases), then plan, gaps, generate, and execute. The workspace is preserved at `litmus/auth-coverage/`.

No production code was changed. All tests use the existing `client` and `db_session` fixtures from `conftest.py`. JWT tokens for edge-case tests are crafted directly using `python-jose` with `SECRET_KEY="test-secret-key"`.

No `docs/dev/architecture.md` exists in this project.

## References

- `litmus/auth-coverage/*/plan.md` — 28 planned tests T-01 through T-28
- `litmus/auth-coverage/*/gaps_review.md` — 6 additional gap tests G-01 through G-06
- `rmp/backend/tests/test_auth.py` — the extended test file

## Goals / Non-Goals

**Goals:**

- Full coverage of `GET /auth/me`, `POST /auth/forgot-password`, `POST /auth/reset-password`
- Extended edge-case coverage of `POST /auth/register` and `POST /auth/login`
- `TestKnownBehaviorGaps` class documenting `is_active` not enforced, no token revocation, no password complexity

**Non-Goals:**

- Fixing any of the documented gaps (separate changes)
- Frontend auth flow tests
- Rate limiting tests (not implemented)

## Decisions

### D1: Tests craft JWTs directly rather than going through the forgot-password flow

The `POST /auth/forgot-password` endpoint only logs the token to stdout — there is no way to intercept it in tests. Reset-password tests craft tokens directly:

```python
from jose import jwt
from datetime import datetime, timedelta

SECRET_KEY = "test-secret-key"
ALGORITHM = "HS256"

def _make_reset_token(email: str, expires_delta=timedelta(hours=1)) -> str:
    return jwt.encode(
        {"sub": email, "type": "password_reset",
         "exp": datetime.utcnow() + expires_delta},
        SECRET_KEY, algorithm=ALGORITHM,
    )

def _make_expired_reset_token(email: str) -> str:
    return _make_reset_token(email, expires_delta=timedelta(hours=-1))
```

**Alternative considered:** Send forgot-password then capture stdout. Rejected — fragile, couples test to stdout parsing.

### D2: Known-gap tests assert current broken behavior with explicit comments

Tests that document missing enforcement use `# KNOWN GAP` inline:

```python
def test_inactive_user_login_not_blocked(self, client):
    """KNOWN GAP: is_active=False does not block login."""  # KNOWN GAP
    ...
    assert resp.status_code == 200  # should be 401/403 once enforced
```

When the gap is fixed, these tests will fail and the developer will see the comment explaining what changed.

## Migrations

No migrations. No schema changes. No production code changes.

## Testing Philosophy

### Coverage completeness

The litmus gaps review confirmed 43 scenarios across 5 endpoints. After generate + execute, all 43 are covered (11 existing + 34 new). The `TestKnownBehaviorGaps` class covers the 6 behavioral gaps that are known but not yet fixed.

## Documentation Plan

### `TESTING.md` updates

**Audience:** Developers

Update test count to reflect 34 new tests. Add `TestGetMe`, `TestForgotPassword`, `TestResetPassword`, `TestRegisterExtended`, `TestLoginExtended`, `TestKnownBehaviorGaps` to the auth section. Note the litmus workspace location.

## Risks / Trade-offs

### Known-gap tests will break when gaps are fixed

**Risk:** When `is_active` enforcement, token revocation, or password complexity are implemented, the `TestKnownBehaviorGaps` tests will fail because they assert the old broken behavior.

**Mitigation:** Each gap test has a `# KNOWN GAP` comment explaining the expected future behavior. The test failure is intentional — it signals to the developer that the gap test needs updating.
