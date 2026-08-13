# Lower Environment and Production Promotion TODO

Status: planned for later; not yet implemented.

## Goal

Create a production-like lower environment at `staging.runmypool.net`, automatically deploy changes there after they merge to `main`, validate them, and promote the exact tested container images to production only after manual approval.

## Recommended architecture

The lower environment should have its own:

- Frontend and backend ECS services and task definitions
- ALB target groups and host-based routing rules
- MySQL 8.4 RDS database
- Security groups
- Secrets Manager secrets
- Stripe test-mode keys, prices, and webhook endpoint
- CloudWatch log groups and alarms
- Seeded test data

To control cost, it should share the existing VPC, ECS cluster, ECR repositories, Application Load Balancer, Route 53 hosted zone, and ACM certificate where practical. It must never share the production database or production application secrets.

## Estimated cost

Expected incremental cost in `us-east-1` for an always-running staging environment:

| Component | Proposed size | Approximate monthly cost |
| --- | --- | ---: |
| Backend ECS/Fargate | 0.5 vCPU, 1 GB | $18 |
| Frontend ECS/Fargate | 0.25 vCPU, 0.5 GB | $9 |
| Public IPv4 addresses | Two running task addresses | $7 |
| RDS MySQL 8.4 | `db.t4g.micro`, Single-AZ | $12 |
| RDS storage | 20 GB | $2-$3 |
| Secrets, logs, and DNS | Low usage | $2-$5 |
| Shared ALB | Existing ALB and low traffic | Approximately $0 incremental |

Budget approximately **$50-$55 per month**, excluding unusual traffic, heavy logging, taxes, and burst CPU-credit charges.

A scheduled weekday-only environment could reduce this to approximately **$25-$35 per month**, but it adds startup delays and RDS scheduling complexity. Start always-on, measure actual cost, and consider scheduling later.

Do not add a NAT Gateway or a second ALB for the first version.

## Target deployment flow

1. Develop on a feature branch.
2. Run backend, frontend, security, MySQL, and container checks on the pull request.
3. Merge the pull request to `main`.
4. Build backend and frontend containers once.
5. Tag both images with the Git commit SHA and record their immutable digests.
6. Register staging task definitions that reference those exact images.
7. Run staging migrations as a one-off task.
8. Deploy automatically to staging.
9. Run staging health, API, browser, and Stripe test-mode checks.
10. Require approval through the GitHub `production` environment.
11. Register production task definitions using the exact image digests already tested in staging. Do not rebuild.
12. Run backward-compatible production migrations.
13. Deploy with the ECS circuit breaker enabled.
14. Run production health checks and roll back to the previous task definitions if validation fails.

Code and container artifacts are promoted from staging to production. Staging data, secrets, and infrastructure are not promoted.

## Tranche 1: Safe deployment foundation

- [ ] Create GitHub `staging` and `production` Environments.
- [ ] Require the platform owner to approve the `production` Environment.
- [ ] Replace long-lived GitHub AWS access keys with GitHub OIDC.
- [ ] Create a least-privilege staging deployment role.
- [ ] Create a separate least-privilege production deployment role.
- [ ] Restrict each role to its environment's ECS services and task definitions.
- [ ] Build each backend and frontend image once per commit.
- [ ] Push immutable commit-SHA tags and capture image digests.
- [ ] Stop relying on mutable image tags plus `force-new-deployment`.
- [ ] Add an explicit workflow dispatch option for production promotion.
- [ ] Record the deployed commit, image digests, task-definition revisions, actor, and time.
- [ ] Add rollback to the immediately preceding task-definition revisions.

## Tranche 2: Terraform organization

- [ ] Refactor shared infrastructure into a reusable environment module.
- [ ] Preserve the existing production Terraform state and imported resources.
- [ ] Keep separate state paths:
  - `production/runmypool.tfstate`
  - `staging/runmypool.tfstate`
- [ ] Parameterize environment name, hostname, service names, database size, log retention, scaling, secrets, and image digests.
- [ ] Add environment tags to every new resource.
- [ ] Run `terraform plan` independently for staging and production.
- [ ] Document state recovery and rollback procedures before the first staging apply.

## Tranche 3: Staging AWS infrastructure

- [ ] Add `staging.runmypool.net` DNS and TLS coverage.
- [ ] Add staging frontend and backend target groups.
- [ ] Add host-based ALB rules for the staging frontend and API.
- [ ] Create staging frontend and backend ECS services.
- [ ] Use one task per service with autoscaling disabled initially.
- [ ] Create a dedicated staging ECS security group.
- [ ] Create a private, Single-AZ MySQL 8.4 `db.t4g.micro` instance.
- [ ] Allocate 20 GB of general-purpose database storage.
- [ ] Configure short staging backup retention.
- [ ] Create dedicated staging database and JWT secrets.
- [ ] Create separate staging CloudWatch log groups with short retention.
- [ ] Add basic service, target-health, database, and deployment alarms.
- [ ] Add a staging cost budget and alert.

## Tranche 4: Safe staging configuration

- [ ] Add Stripe test-mode secret key, Price IDs, and webhook secret.
- [ ] Register the staging webhook URL in Stripe test mode.
- [ ] Ensure staging can never use live Stripe credentials.
- [ ] Add a visible `STAGING` banner.
- [ ] Prefix staging email subjects with `[STAGING]`.
- [ ] Add an email-recipient allowlist.
- [ ] Use SES mailbox simulator addresses in automation.
- [ ] Disable the normal production result-updater schedule in staging.
- [ ] Provide a manual staging result-updater invocation.
- [ ] Ensure staging updater permissions cannot reach the production database.
- [ ] Add a repeatable seed command for users, pools, entries, schedules, and picks.
- [ ] Do not copy production personal data by default.
- [ ] If production-like data is ever required, create and document a sanitization process first.

## Tranche 5: Automated staging validation

- [ ] Verify frontend, backend, and load-balancer target health.
- [ ] Verify database migrations completed successfully.
- [ ] Test account creation and login.
- [ ] Test password-reset email with a controlled recipient.
- [ ] Test public and private pool discovery and joining.
- [ ] Test pool and entry creation.
- [ ] Test Survivor picks, locks, scoring, and elimination.
- [ ] Test Pick 'Em picks, configurable weekly selection counts, and scoring.
- [ ] Test pool-admin and platform-admin RBAC boundaries.
- [ ] Complete a Stripe test-mode checkout and verify persisted entitlement.
- [ ] Verify the webhook is idempotent.
- [ ] Test the result updater using controlled fixtures.
- [ ] Block production promotion when required checks fail.

## Tranche 6: Production promotion and rollback

- [ ] Require manual approval after staging validation.
- [ ] Promote the exact staging backend and frontend image digests.
- [ ] Never rebuild images during production promotion.
- [ ] Take or confirm a recent production database backup before risky migrations.
- [ ] Require backward-compatible expand-and-contract migrations.
- [ ] Deploy backend before frontend when API compatibility requires it.
- [ ] Verify production API health, site health, target health, and task stability.
- [ ] Verify critical account, pool-directory, entry, and pick routes.
- [ ] Automatically restore previous task definitions on failed health checks.
- [ ] Document manual rollback commands and ownership.

## Definition of done

- A merge to `main` automatically deploys an immutable build to staging.
- Staging is isolated from production data, secrets, Stripe, email recipients, and scheduled jobs.
- Automated staging validation covers the critical customer journey.
- Production requires an explicit approval.
- Production receives the exact image digests tested in staging.
- Deployments and promotions are auditable.
- Rollback is tested and documented.
- Actual staging cost is monitored against the expected $50-$55 monthly budget.
