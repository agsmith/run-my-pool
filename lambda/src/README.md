# NFL game result updater

This Lambda polls ESPN during NFL game windows, updates official schedule
results, scores Survivor and Pick 'Em selections, and reconciles Survivor entry
status. Terraform in `lambda/main.tf` is the only supported infrastructure and
deployment definition; the former CloudFormation template and imperative deploy
script were retired to prevent configuration drift.

## Runtime behavior

- EventBridge Scheduler uses `America/New_York`, so schedules follow DST.
- The current season and week come from the database schedule, including the
  January portion of the prior NFL season.
- Final results overwrite stale pick results so official corrections propagate.
- Pick 'Em losses never eliminate entries. Survivor entries are reconciled from
  their complete resolved pick history.
- Lambda reserved concurrency is one, preventing overlapping updater runs.
- Scheduler retries a failed invocation three times for up to one hour, then
  sends it to an encrypted SQS dead-letter queue.
- CloudWatch alarms notify `support@runmypool.net` after the SNS subscription is
  confirmed.

## Local validation

```bash
python -m pytest lambda/tests -q
terraform fmt -check lambda/main.tf
terraform -chdir=lambda validate
```

Tests stub AWS and external HTTP calls. They do not require AWS credentials.

## First Terraform deployment

The live resources predate this consolidated Terraform definition. After AWS
authentication, inspect Terraform state and import any existing Lambda, S3
object, IAM policy, and log-group resources before applying. Do not apply while
the legacy EventBridge rules remain enabled, or the updater can run twice.

Recommended migration sequence:

1. Authenticate with AWS and initialize the `lambda` Terraform directory.
2. Inspect state and import existing resources represented by `main.tf`.
3. Run `terraform plan` and verify no database, Lambda, role, or package bucket
   replacement is proposed.
4. Apply the new Scheduler, DLQ, alarms, concurrency, and IAM changes.
5. Confirm the SNS email subscription sent to `support@runmypool.net`.
6. Invoke once with `{"force": true}` and verify schedule, pick, and entry data.
7. Disable and then remove the four legacy `nfl-game-updater-*` EventBridge
   rules after the Scheduler schedules have been observed successfully.

The function requires `SECRETS_MANAGER_ARN` and access to the configured SSM
completion marker. A forced invocation bypasses the game-time and daily-complete
guards, but still uses the database-derived season and week.
