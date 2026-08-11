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
data-integrity, supply-chain, and baseline browser/configuration findings
identified by this assessment have been remediated in code. Remaining session
revocation, MFA, alerting, and infrastructure controls are documented below.

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
6. **Resolved:** Lambda production and test dependency graphs are upgraded and
   hash-locked, and advisory scans are CI gates for all application components.
7. **Resolved:** Private leagues are no longer publicly enumerable, invalid NFL
   weeks are rejected, and CSV exports neutralize spreadsheet formulas.
8. **Resolved:** Browser sessions use HttpOnly cookies instead of persistent
   bearer tokens, and the frontend now emits baseline security headers.

## OWASP Top 10 results

| Category | Status | Evidence and risk |
| --- | --- | --- |
| A01 Broken Access Control | Remediated in code | Cross-user and cross-league controls work, private league discovery is filtered, and outbound service URLs are fixed HTTPS endpoints. |
| A02 Security Misconfiguration | Remediated in code | API documentation defaults off, CORS is restricted, and both API and frontend responses declare baseline security headers. Production deployment must still be rechecked after release. |
| A03 Software Supply Chain Failures | Remediated in code | Frontend, backend, and Lambda graphs are locked; Python locks include hashes; CI runs npm and pip advisory scans; GitHub Actions use immutable SHAs. |
| A04 Cryptographic Failures | Partially remediated | Passwords use bcrypt, JWT signing requires a deployment secret, and browser credentials use HttpOnly cookies. Access and league-password encryption keys still share source key material. |
| A05 Injection | Remediated in reviewed paths | SQLAlchemy parameterizes application queries, React renders user data as text, and CSV export neutralizes spreadsheet-formula prefixes. |
| A06 Insecure Design | Remediated in reviewed paths | Password-reset tokens are single-use, abuse throttles exist, player adjudication fields are rejected, and pick weeks are constrained to 1-18. |
| A07 Authentication Failures | Partially remediated | Token purpose, inactive accounts, cookie flags, and login throttling are enforced. General token revocation, MFA, and email verification remain future controls. |
| A08 Software or Data Integrity Failures | Remediated in code | Unsigned JWTs and client-owned adjudication are rejected; lock integrity and hashed Python artifacts provide reproducible dependency installation. Artifact signing remains an infrastructure enhancement. |
| A09 Security Logging and Alerting Failures | Partially remediated | Security events are audited and credentials are not logged. Operational alert rules and incident-response verification remain outside this repository. |
| A10 Mishandling of Exceptional Conditions | Remediated in reviewed authentication path | Authentication failures return generic errors without logging sensitive exception strings; regression coverage verifies fail-closed behavior. Broader fault-injection remains recommended. |

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

Lambda production and test dependencies are independently compiled from `.in`
files into SHA-256-locked manifests. Requests, MySQL Connector/Python, boto3,
botocore, SQLAlchemy, and PyMySQL are upgraded to audited releases.

## Test strategy

`rmp/backend/tests/test_owasp_top10.py` maps executable tests to every OWASP Top
10:2025 category. Repaired findings are normal regression tests, including an
A03 test that verifies backend, frontend, and Lambda dependency locks. There
are no expected failures in this suite.

Run the focused assessment with:

```bash
cd rmp/backend
PYTHONPATH=. pytest tests/test_owasp_top10.py -rxX
```

Dependency checks can be used as CI gates:

```bash
cd rmp/frontend && npm audit
pip-audit --require-hashes -r rmp/backend/requirements.txt
pip-audit --require-hashes -r lambda/src/requirements.txt
```

## Limitations

This is a repository-level assessment with API tests and live advisory-database
queries. It is not a substitute for an authenticated infrastructure penetration
test. Cloud IAM, TLS/CDN configuration, database/network exposure, runtime
secrets, production images, logging destinations, WAF/rate limiting, and the
currently deployed artifact were not available for direct validation in this
scope.
