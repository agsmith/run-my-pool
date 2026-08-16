terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.38.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.4.2"
    }
  }
  required_version = "~> 1.2"
}

# Data source to reference the existing RDS database
data "aws_db_instance" "runmypool_db" {
  db_instance_identifier = "terraform-20250830124351453200000003"
}


resource "null_resource" "install_python_dependencies" {
  triggers = {
    requirements_sha256 = filesha256("${path.module}/src/requirements.txt")
  }

  provisioner "local-exec" {
    command = "bash ${path.module}/src/create-pkg.sh"

    environment = {
      source_code_path = "${path.module}"
      function_name    = "nfl-game-updater"
      runtime          = "python3.12"
      path_cwd         = "${path.module}"
    }
  }
}


data "archive_file" "function_zip" {
  source_dir  = "src"
  type        = "zip"
  output_path = "${path.module}/nfl-game-updater.zip"
  depends_on  = [null_resource.install_python_dependencies]
}

resource "aws_s3_object" "file_upload" {
  bucket     = "nfl-game-updater-us-east-1-lambda"
  key        = "nfl-game-updater.zip"
  source     = "nfl-game-updater.zip"
  depends_on = [data.archive_file.function_zip]
}

resource "aws_lambda_function" "function" {
  s3_bucket                      = "nfl-game-updater-us-east-1-lambda"
  s3_key                         = "nfl-game-updater.zip"
  function_name                  = "nfl-game-updater"
  handler                        = "nfl_game_updater.lambda_handler"
  runtime                        = "python3.12"
  timeout                        = 900
  memory_size                    = 128
  reserved_concurrent_executions = 1
  role                           = "arn:aws:iam::739444271939:role/nfl-game-updater-lambda-role"
  depends_on                     = [aws_s3_object.file_upload]

  vpc_config {
    subnet_ids         = toset(["subnet-07d85747fe7504912", "subnet-080737ebc3b299dcd"])
    security_group_ids = toset(["sg-022ad503e1afbef4a"])
  }

  environment {
    variables = {
      DB_HOST     = data.aws_db_instance.runmypool_db.address
      DB_PORT     = data.aws_db_instance.runmypool_db.port
      DB_NAME     = data.aws_db_instance.runmypool_db.db_name
      DB_USERNAME = data.aws_db_instance.runmypool_db.master_username
      # Note: Password should be retrieved from AWS Secrets Manager for security
      SECRETS_MANAGER_ARN = "arn:aws:secretsmanager:us-east-1:739444271939:secret:runmypool/database-url-nRqy5o"
    }
  }
}

resource "aws_cloudwatch_log_group" "function" {
  name              = "/aws/lambda/${aws_lambda_function.function.function_name}"
  retention_in_days = 30
}

resource "aws_sqs_queue" "scheduler_dlq" {
  name                      = "nfl-game-updater-scheduler-dlq"
  message_retention_seconds = 1209600
  sqs_managed_sse_enabled   = true
}

resource "aws_iam_role" "scheduler" {
  name = "nfl-game-updater-scheduler-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "scheduler.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "scheduler" {
  name = "invoke-nfl-game-updater"
  role = aws_iam_role.scheduler.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = "lambda:InvokeFunction"
        Resource = aws_lambda_function.function.arn
      },
      {
        Effect   = "Allow"
        Action   = "sqs:SendMessage"
        Resource = aws_sqs_queue.scheduler_dlq.arn
      }
    ]
  })
}

locals {
  # Times are interpreted in America/New_York, including DST transitions.
  nfl_updater_schedules = {
    saturday_games = "cron(0/15 12-23 ? SEP-DEC,JAN-FEB SAT *)"
    saturday_late  = "cron(0/15 0-1 ? SEP-DEC,JAN-FEB SUN *)"
    sunday_games   = "cron(0/15 12-23 ? SEP-DEC,JAN-FEB SUN *)"
    sunday_late    = "cron(0/15 0-1 ? SEP-DEC,JAN-FEB MON *)"
    monday_games   = "cron(0/15 19-23 ? SEP-DEC,JAN-FEB MON *)"
    monday_late    = "cron(0/15 0-1 ? SEP-DEC,JAN-FEB TUE *)"
    thursday_games = "cron(0/15 19-23 ? SEP-DEC,JAN-FEB THU *)"
    thursday_late  = "cron(0/15 0-1 ? SEP-DEC,JAN-FEB FRI *)"
  }
}

resource "aws_scheduler_schedule" "game_results" {
  for_each = local.nfl_updater_schedules

  name                         = "nfl-game-updater-${replace(each.key, "_", "-")}"
  schedule_expression          = each.value
  schedule_expression_timezone = "America/New_York"
  state                        = "ENABLED"

  flexible_time_window { mode = "OFF" }

  target {
    arn      = aws_lambda_function.function.arn
    role_arn = aws_iam_role.scheduler.arn

    retry_policy {
      maximum_event_age_in_seconds = 3600
      maximum_retry_attempts       = 3
    }

    dead_letter_config {
      arn = aws_sqs_queue.scheduler_dlq.arn
    }
  }
}

resource "aws_sns_topic" "alerts" {
  name = "nfl-game-updater-alerts"
}

resource "aws_sns_topic_subscription" "alerts_email" {
  count     = var.alert_email == null ? 0 : 1
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  alarm_name          = "nfl-game-updater-errors"
  alarm_description   = "NFL result updater reported one or more failed invocations."
  namespace           = "AWS/Lambda"
  metric_name         = "Errors"
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    FunctionName = aws_lambda_function.function.function_name
  }
}

resource "aws_cloudwatch_metric_alarm" "dlq_messages" {
  alarm_name          = "nfl-game-updater-dlq-not-empty"
  alarm_description   = "EventBridge Scheduler exhausted retries for an NFL result update."
  namespace           = "AWS/SQS"
  metric_name         = "ApproximateNumberOfMessagesVisible"
  statistic           = "Maximum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    QueueName = aws_sqs_queue.scheduler_dlq.name
  }
}

variable "alert_email" {
  description = "Optional email address for updater failure notifications. AWS sends a confirmation request."
  type        = string
  default     = "support@runmypool.net"
  nullable    = true
}

# IAM policy for Secrets Manager access (if not already included in the role)
resource "aws_iam_role_policy" "lambda_secrets_manager" {
  name = "nfl-game-updater-secrets-manager-policy"
  role = "nfl-game-updater-lambda-role"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ]
        Resource = "arn:aws:secretsmanager:us-east-1:739444271939:secret:runmypool/database-url-nRqy5o"
      },
      {
        Effect = "Allow"
        Action = [
          "ssm:GetParameter",
          "ssm:PutParameter"
        ]
        Resource = "arn:aws:ssm:us-east-1:739444271939:parameter/runmypool/nfl-games-done-date"
      }
    ]
  })
}

# Outputs for reference
output "lambda_function_name" {
  description = "Name of the Lambda function"
  value       = aws_lambda_function.function.function_name
}

output "database_endpoint" {
  description = "RDS database endpoint"
  value       = data.aws_db_instance.runmypool_db.address
}

output "database_port" {
  description = "RDS database port"
  value       = data.aws_db_instance.runmypool_db.port
}

output "database_name" {
  description = "RDS database name"
  value       = data.aws_db_instance.runmypool_db.db_name
}
