# NFL Result Updater Runbook

The ECS result updater replaces the legacy Lambda only after a controlled cutover. All Terraform schedules default to `DISABLED` and must remain disabled during build and canary testing. Fifteen-minute schedules cover expected live-game windows; a daily correction run catches delayed official changes without polling continuously all week.

## Safety invariants

- Never enable the Lambda EventBridge rules and the ECS Scheduler as writers at the same time.
- Deploy only immutable backend image tags to the updater task family.
- Run `--dry-run` before every manual writer canary.
- A second invocation exits successfully without writing when the MySQL advisory lock is held.
- A scoring discrepancy rolls back schedule, pick, and entry changes together.
- The current Lambda is not a safe rollback until its outbound VPC connectivity is repaired.

## Local verification

From `rmp/backend`:

```bash
python -m pytest tests/ -q --tb=short
python -m result_updater --help
```

From the repository root:

```bash
terraform -chdir=terraform fmt -check
terraform -chdir=terraform validate
```

Review a full Terraform plan before applying. Do not use a placeholder `db_password`: the existing root stack manages the database URL secret, and a placeholder would rotate production credentials.

## Infrastructure deployment

1. Build and push the backend image through CI.
2. Review a Terraform plan and confirm the result updater schedule is `DISABLED`.
3. Confirm the plan does not replace the database secret, RDS instance, API task definition, or existing ECS services.
4. Apply only the reviewed plan.
5. Confirm the SNS subscription email delivered to `support@runmypool.net`.
6. Confirm the task family, state machine, disabled schedule, log groups, DLQ, and alarms exist.

## Production dry-run canary

Start a task using the latest immutable `runmypool-results-updater` revision and override its command:

```text
python -m result_updater --dry-run --season 2026 --week 1
```

Run it once in each configured public subnet. Confirm:

- The image and database secret load.
- RDS and ESPN are reachable.
- The task exits zero within five minutes.
- The `updater_runs` row has status `dry_run`.
- Proposed counts are plausible.
- Schedule, picks, and entries did not change.
- Logs contain no credentials or tokens.

Then deliberately run an invalid command and verify Step Functions retries, the execution fails, the ECS nonzero-exit event is emitted, and `support@runmypool.net` receives an alert.

## Cutover

1. Export the affected schedule, picks, entries, and current updater-run rows.
2. Disable all legacy Lambda EventBridge rules.
3. Confirm no Lambda invocation is running.
4. Run one manual ECS writer task.
5. Verify its exit code, audit record, schedule result, Pick 'Em score, Survivor state, and UI display.
6. Set `result_updater_schedule_enabled = true` in a reviewed Terraform plan.
7. Apply and observe the first scheduled Step Functions execution.
8. Keep the Lambda deployed but unscheduled during the observation window.

## Rollback

1. Disable the ECS Scheduler.
2. Stop any running updater task or Step Functions execution.
3. Register or select the previous known-good immutable task revision.
4. Run that revision in dry-run mode.
5. Run it in writer mode against authoritative ESPN results.
6. Use the affected run's audit data to reverse rows if necessary. Use RDS point-in-time recovery only as a last resort.

## Retirement

After one complete NFL week without unexplained discrepancies:

- Remove the four legacy EventBridge rules and targets.
- Remove the Lambda function, broad Lambda IAM policies, obsolete S3 packages, SSM done marker, and Lambda deployment workflow.
- Retain logs for the agreed audit period.
- Exercise the documented rollback procedure once more.
