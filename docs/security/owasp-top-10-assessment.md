# RunMyPool OWASP Top 10 Security Assessment

Assessment date: 2026-08-11
Scope: FastAPI API, Next.js client, authentication/authorization paths, data
validation, outbound HTTP calls, operational configuration, and declared
dependencies in this repository.

## Executive summary

The application has meaningful authorization checks, ORM parameterization,
password hashing, signed JWT validation, CORS origin restriction, audit events,
message throttling, and fixed outbound service URLs. It is not ready to be
described as fully security-hardened, however. The dependency, authentication,
data-integrity, and baseline browser/configuration findings identified by this
assessment have been remediated in code; the remaining limitations require
runtime and infrastructure validation.

Remediation status after the initial hardening tranche:

1. **Resolved:** Next.js is upgraded to 16.3.0, the abandoned PWA integration is
   replaced with Serwist 9.5.12, and the complete npm graph is locked. Both the
   production-only and full development-tree npm audits report zero known
   vulnerabilities.
2. **Resolved:** Player updates accept only `team`; extra adjudication fields are rejected.
3. **Resolved:** The application requires a deployment-supplied JWT secret.
4. **Resolved:** Reset tokens are not logged and their digests are consumed once.
5. **Resolved:** Password length, inactive-account enforcement, and persistent
   database-backed login throttling are implemented.

## OWASP Top 10 results

| Category | Status | Evidence and risk |
| --- | --- | --- |
| A01 Broken Access Control | Remediated in code | Cross-user and cross-league controls work; player updates reject server-owned fields and registration rejects client-controlled roles. |
| A02 Cryptographic Failures | Partially remediated | Passwords use bcrypt and JWT signing requires an environment secret. Tokens remain in browser `localStorage`, increasing impact of any XSS. |
| A03 Injection | Control verified | SQLAlchemy treats SQL probes as data and API output is JSON. React rendering must continue to avoid raw HTML for user content; `Seo.js` is the only reviewed `dangerouslySetInnerHTML` usage and receives structured data. |
| A04 Insecure Design | Remediated in code | Password length, single-use reset tokens, login throttling, and league-scoped message throttling are enforced. |
| A05 Security Misconfiguration | Partially remediated | CORS rejects untrusted origins, API docs default to disabled, and baseline security headers are present. CORS methods and headers can still be narrowed. |
| A06 Vulnerable and Outdated Components | Remediated in code | Frontend dependencies are exactly pinned in npm's lockfile. Python production and development dependencies are compiled into hash-verified lockfiles. Full npm and pip-audit scans report zero known vulnerabilities. |
| A07 Identification and Authentication Failures | Partially remediated | Token purpose and inactive accounts are enforced and login is throttled. Access tokens still last 24 hours without general revocation. |
| A08 Software and Data Integrity Failures | Remediated in code | Unsigned JWTs and client-supplied adjudication fields are rejected. npm lock integrity and hash-verified Python requirements make dependency installation reproducible. |
| A09 Security Logging and Monitoring Failures | Partially remediated | Security events are audited and reset credentials are not logged. Alerting and retention controls remain outside this repository. |
| A10 Server-Side Request Forgery | Control verified | Reviewed ESPN integrations use fixed HTTPS endpoint constants and timeouts; no user-supplied URL fetch path was found. Reassess whenever imports, avatars, webhooks, or arbitrary URL previews are introduced. |

## Dependency scan details

The frontend result reflects the checked-in npm lockfile. Next.js 16.3.0 and
Serwist 9.5.12 replace the vulnerable Next.js 15 and Workbox-based PWA tree.
The production-only and full development-tree npm audits both report zero known
vulnerabilities.

Python direct requirements are exactly pinned in `requirements.in`; transitive
production and development graphs are compiled with SHA-256 hashes in
`requirements.txt` and `requirements-dev.txt`. The JWT implementation now uses
PyJWT instead of the vulnerable python-jose/ecdsa tree. FastAPI, Starlette,
Click, and pytest are pinned to patched releases, and the complete development
lock reports zero known vulnerabilities.

## Test strategy

`rmp/backend/tests/test_owasp_top10.py` maps executable tests to every OWASP
category. Repaired findings are normal regression tests, including an A06 test
that verifies exact direct pins, hashed Python locks, exact npm versions, and a
current npm lockfile. There are no expected failures in this suite.

Run the focused assessment with:

```bash
cd rmp/backend
PYTHONPATH=. pytest tests/test_owasp_top10.py -rxX
```

Dependency checks can be used as CI gates:

```bash
cd rmp/frontend && npm audit
pip-audit --require-hashes -r rmp/backend/requirements.txt
```

## Limitations

This is a repository-level assessment with API tests and live advisory-database
queries. It is not a substitute for an authenticated infrastructure penetration
test. Cloud IAM, TLS/CDN configuration, database/network exposure, runtime
secrets, production images, logging destinations, WAF/rate limiting, and the
currently deployed artifact were not available for direct validation in this
scope.
