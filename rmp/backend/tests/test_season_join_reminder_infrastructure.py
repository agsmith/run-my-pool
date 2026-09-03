from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_daily_scheduler_routes_to_dedicated_reminder_command():
    terraform = (ROOT / "terraform" / "result_updater.tf").read_text()
    variables = (ROOT / "terraform" / "variables.tf").read_text()

    assert 'resource "aws_scheduler_schedule" "season_join_reminders"' in terraform
    assert 'schedule_expression          = "cron(0 10 ? * * *)"' in terraform
    assert 'schedule_expression_timezone = "America/New_York"' in terraform
    assert 'input    = jsonencode({ job = "season_join_reminders" })' in terraform
    assert 'StringEquals = "season_join_reminders"' in terraform
    assert 'Command = ["python", "-m", "season_join_reminders"]' in terraform
    assert 'variable "season_join_reminders_schedule_enabled"' in variables
    assert "default     = true" in variables


def test_entry_reminder_has_a_separate_daily_route_and_feature_flag():
    terraform = (ROOT / "terraform" / "result_updater.tf").read_text()
    variables = (ROOT / "terraform" / "variables.tf").read_text()

    assert 'resource "aws_scheduler_schedule" "season_entry_reminders"' in terraform
    assert 'schedule_expression          = "cron(5 10 ? * * *)"' in terraform
    assert 'schedule_expression_timezone = "America/New_York"' in terraform
    assert 'input    = jsonencode({ job = "season_entry_reminders" })' in terraform
    assert 'StringEquals = "season_entry_reminders"' in terraform
    assert 'Command = ["python", "-m", "season_entry_reminders"]' in terraform
    assert 'variable "season_entry_reminders_schedule_enabled"' in variables


def test_weekly_pick_reminder_runs_friday_afternoon_eastern():
    terraform = (ROOT / "terraform" / "result_updater.tf").read_text()
    variables = (ROOT / "terraform" / "variables.tf").read_text()

    assert 'resource "aws_scheduler_schedule" "weekly_pick_reminders"' in terraform
    assert 'schedule_expression          = "cron(0 15 ? * FRI *)"' in terraform
    assert 'schedule_expression_timezone = "America/New_York"' in terraform
    assert 'input    = jsonencode({ job = "weekly_pick_reminders" })' in terraform
    assert 'StringEquals = "weekly_pick_reminders"' in terraform
    assert 'Command = ["python", "-m", "weekly_pick_reminders"]' in terraform
    assert 'variable "weekly_pick_reminders_schedule_enabled"' in variables
