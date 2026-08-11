# RunMyPool OWASP Top 10 Security Assessment

Assessment date: 2026-08-11
Scope: FastAPI API, Next.js client, authentication/authorization paths, data
validation, outbound HTTP calls, operational configuration, and declared
dependencies in this repository.

## Executive summary

The application has meaningful authorization checks, ORM parameterization,
password hashing, signed JWT validation, CORS origin restriction, audit events,
message throttling, and fixed outbound service URLs. It is not ready to be
described as security-hardened, however. The assessment confirmed one critical
dependency finding, several high-impact authentication and data-integrity gaps,
and missing browser/configuration defenses.

Remediation status after the initial hardening tranche:

1. **Remaining:** Upgrade and pin Next.js and the vulnerable frontend dependency tree. The
   production `npm audit` reported 13 vulnerable packages: 1 critical, 8 high,
   and 4 moderate. The installed direct dependencies include Next.js 15.5.2
   and `@ducanh2912/next-pwa` 10.2.9.
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
| A06 Vulnerable and Outdated Components | Critical finding | Versions are not pinned. `npm audit --omit=dev` found 13 production vulnerabilities. `pip-audit` resolved the unpinned Python requirements and found 9 advisories in 5 packages, including Starlette, python-dotenv, pytest, Click, and ecdsa. Applicability varies, but the lack of a lock makes the deployed set unverifiable. |
| A07 Identification and Authentication Failures | Partially remediated | Token purpose and inactive accounts are enforced and login is throttled. Access tokens still last 24 hours without general revocation. |
| A08 Software and Data Integrity Failures | Partially remediated | Unsigned JWTs and client-supplied adjudication fields are rejected. Unpinned dependencies still undermine build integrity. |
| A09 Security Logging and Monitoring Failures | Partially remediated | Security events are audited and reset credentials are not logged. Alerting and retention controls remain outside this repository. |
| A10 Server-Side Request Forgery | Control verified | Reviewed ESPN integrations use fixed HTTPS endpoint constants and timeouts; no user-supplied URL fetch path was found. Reassess whenever imports, avatars, webhooks, or arbitrary URL previews are introduced. |

## Dependency scan details

The frontend result reflects the checked-in lockfile and installed production
tree. The critical direct finding is the installed Next.js 15.5.2 release;
the audit also reports vulnerable transitive versions of PostCSS, Sharp,
brace-expansion, fast-uri, minimatch, nanoid, picomatch, and Workbox-related
packages. Do not run a blind force-fix: upgrade Next.js and the PWA integration
deliberately, rebuild, and run the complete Jest/browser suite.

Because `requirements.txt` has no versions, the Python scan is a resolution as
of the assessment date rather than proof of what production runs. It found nine
advisories across five packages. Several Starlette findings may not be reachable
by RunMyPool's route patterns or deployment OS, while the unpinned supply-chain
and reproducibility problem remains independently valid.

## Test strategy

`rmp/backend/tests/test_owasp_top10.py` maps executable tests to every OWASP
category. Repaired findings are normal regression tests. The dependency-pinning
requirement remains a non-strict `xfail` until its migration is complete.

Run the focused assessment with:

```bash
cd rmp/backend
PYTHONPATH=. pytest tests/test_owasp_top10.py -rxX
```

Dependency checks should also become CI gates after versions are pinned:

```bash
cd rmp/frontend && npm audit --omit=dev
pip-audit -r rmp/backend/requirements.txt
```

## Limitations

This is a repository-level assessment with API tests and live advisory-database
queries. It is not a substitute for an authenticated infrastructure penetration
test. Cloud IAM, TLS/CDN configuration, database/network exposure, runtime
secrets, production images, logging destinations, WAF/rate limiting, and the
currently deployed artifact were not available for direct validation in this
scope.
