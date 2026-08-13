from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_terraform_uses_timezone_aware_scheduler_with_retries_and_dlq():
    terraform = (ROOT / "main.tf").read_text()

    assert 'resource "aws_scheduler_schedule" "game_results"' in terraform
    assert 'schedule_expression_timezone = "America/New_York"' in terraform
    assert "maximum_retry_attempts       = 3" in terraform
    assert 'resource "aws_sqs_queue" "scheduler_dlq"' in terraform
    assert "sqs_managed_sse_enabled   = true" in terraform


def test_terraform_prevents_overlapping_updater_invocations_and_alarms_failures():
    terraform = (ROOT / "main.tf").read_text()

    assert "reserved_concurrent_executions = 1" in terraform
    assert 'resource "aws_cloudwatch_metric_alarm" "lambda_errors"' in terraform
    assert 'resource "aws_cloudwatch_metric_alarm" "dlq_messages"' in terraform
    assert 'default     = "support@runmypool.net"' in terraform


def test_terraform_is_the_only_infrastructure_definition():
    assert not (ROOT / "cloudformation-template.yaml").exists()
    assert not (ROOT / "deploy.sh").exists()
