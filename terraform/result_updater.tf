locals {
  result_updater_family = "runmypool-results-updater"
  common_tags = {
    Project   = "runmypool"
    Component = "result-updater"
  }
}

resource "aws_cloudwatch_log_group" "result_updater" {
  name              = "/ecs/runmypool-results-updater"
  retention_in_days = 30
  tags              = local.common_tags
}

resource "aws_cloudwatch_log_group" "result_updater_workflow" {
  name              = "/aws/vendedlogs/states/runmypool-results-updater"
  retention_in_days = 30
  tags              = local.common_tags
}

resource "aws_security_group" "result_updater" {
  name        = "run-my-pool-results-updater-sg"
  description = "Outbound-only access for the NFL result updater"
  vpc_id      = aws_vpc.main.id

  egress {
    description = "HTTPS for ECR, Secrets Manager, and ESPN"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "DNS over UDP"
    from_port   = 53
    to_port     = 53
    protocol    = "udp"
    cidr_blocks = [aws_vpc.main.cidr_block]
  }

  egress {
    description = "DNS over TCP"
    from_port   = 53
    to_port     = 53
    protocol    = "tcp"
    cidr_blocks = [aws_vpc.main.cidr_block]
  }

  egress {
    description = "MySQL to Run My Pool RDS"
    from_port   = 3306
    to_port     = 3306
    protocol    = "tcp"
    cidr_blocks = [aws_vpc.main.cidr_block]
  }

  tags = merge(local.common_tags, { Name = "run-my-pool-results-updater-sg" })
}

data "aws_iam_policy_document" "ecs_tasks_assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "result_updater_execution" {
  name               = "runmypool-results-updater-execution"
  assume_role_policy = data.aws_iam_policy_document.ecs_tasks_assume_role.json
  tags               = local.common_tags
}

resource "aws_iam_role_policy_attachment" "result_updater_execution" {
  role       = aws_iam_role.result_updater_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

data "aws_iam_policy_document" "result_updater_secret" {
  statement {
    effect    = "Allow"
    actions   = ["secretsmanager:GetSecretValue"]
    resources = [var.database_url_secret_arn]
  }
}

resource "aws_iam_role_policy" "result_updater_secret" {
  name   = "database-url-only"
  role   = aws_iam_role.result_updater_execution.id
  policy = data.aws_iam_policy_document.result_updater_secret.json
}

resource "aws_iam_role" "result_updater_task" {
  name               = "runmypool-results-updater-task"
  assume_role_policy = data.aws_iam_policy_document.ecs_tasks_assume_role.json
  tags               = local.common_tags
}

data "aws_iam_policy_document" "result_updater_email" {
  statement {
    effect    = "Allow"
    actions   = ["ses:SendEmail"]
    resources = [aws_ses_domain_identity.runmypool.arn]
    condition {
      test     = "StringEquals"
      variable = "ses:FromAddress"
      values   = ["accounts@runmypool.net"]
    }
  }
}

resource "aws_iam_role_policy" "result_updater_email" {
  name   = "weekly-owner-report-email"
  role   = aws_iam_role.result_updater_task.id
  policy = data.aws_iam_policy_document.result_updater_email.json
}

resource "aws_ecs_task_definition" "result_updater" {
  family                   = local.result_updater_family
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "256"
  memory                   = "512"
  execution_role_arn       = aws_iam_role.result_updater_execution.arn
  task_role_arn            = aws_iam_role.result_updater_task.arn

  container_definitions = jsonencode([
    {
      name                   = "result-updater"
      image                  = local.backend_image
      essential              = true
      command                = ["python", "-m", "result_updater"]
      readonlyRootFilesystem = true
      environment = [
        { name = "DB_POOL_SIZE", value = "1" },
        { name = "DB_MAX_OVERFLOW", value = "0" },
        { name = "DB_POOL_TIMEOUT_SECONDS", value = "10" },
        { name = "DB_POOL_RECYCLE_SECONDS", value = "300" },
        { name = "IMAGE_REVISION", value = var.backend_image_tag },
        { name = "PYTHONDONTWRITEBYTECODE", value = "1" },
        { name = "AWS_SES_REGION", value = var.aws_region },
        { name = "EMAIL_FROM", value = "Run My Pool <accounts@runmypool.net>" },
        { name = "EMAIL_REPLY_TO", value = "support@runmypool.net" },
        { name = "FRONTEND_URL", value = "https://runmypool.net" },
      ]
      secrets = [
        { name = "DATABASE_URL", valueFrom = var.database_url_secret_arn }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.result_updater.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }
    }
  ])

  tags = local.common_tags
}

resource "aws_sns_topic" "result_updater_alerts" {
  name              = "runmypool-results-updater-alerts"
  kms_master_key_id = "alias/aws/sns"
  tags              = local.common_tags
}

resource "aws_sns_topic_subscription" "result_updater_email" {
  topic_arn = aws_sns_topic.result_updater_alerts.arn
  protocol  = "email"
  endpoint  = var.result_updater_alert_email
}

resource "aws_sqs_queue" "result_updater_dlq" {
  name                      = "runmypool-results-updater-dlq"
  message_retention_seconds = 1209600
  sqs_managed_sse_enabled   = true
  tags                      = local.common_tags
}

data "aws_iam_policy_document" "step_functions_assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["states.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "result_updater_workflow" {
  name               = "runmypool-results-updater-workflow"
  assume_role_policy = data.aws_iam_policy_document.step_functions_assume_role.json
  tags               = local.common_tags
}

data "aws_iam_policy_document" "result_updater_workflow" {
  statement {
    effect    = "Allow"
    actions   = ["ecs:RunTask"]
    resources = ["arn:aws:ecs:${var.aws_region}:${var.aws_account_id}:task-definition/${local.result_updater_family}:*"]
    condition {
      test     = "ArnEquals"
      variable = "ecs:cluster"
      values   = [aws_ecs_cluster.main.arn]
    }
  }

  statement {
    effect    = "Allow"
    actions   = ["ecs:StopTask", "ecs:DescribeTasks"]
    resources = ["*"]
    condition {
      test     = "ArnEquals"
      variable = "ecs:cluster"
      values   = [aws_ecs_cluster.main.arn]
    }
  }

  statement {
    effect    = "Allow"
    actions   = ["iam:PassRole"]
    resources = [aws_iam_role.result_updater_execution.arn, aws_iam_role.result_updater_task.arn]
    condition {
      test     = "StringEquals"
      variable = "iam:PassedToService"
      values   = ["ecs-tasks.amazonaws.com"]
    }
  }

  statement {
    effect    = "Allow"
    actions   = ["events:PutTargets", "events:PutRule", "events:DescribeRule"]
    resources = ["arn:aws:events:${var.aws_region}:${var.aws_account_id}:rule/StepFunctionsGetEventsForECSTaskRule"]
  }

  statement {
    effect    = "Allow"
    actions   = ["sns:Publish"]
    resources = [aws_sns_topic.result_updater_alerts.arn]
  }

  statement {
    effect = "Allow"
    actions = [
      "logs:CreateLogDelivery",
      "logs:GetLogDelivery",
      "logs:UpdateLogDelivery",
      "logs:DeleteLogDelivery",
      "logs:ListLogDeliveries",
      "logs:PutResourcePolicy",
      "logs:DescribeResourcePolicies",
      "logs:DescribeLogGroups",
    ]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "result_updater_workflow" {
  name   = "run-updater-and-report-failures"
  role   = aws_iam_role.result_updater_workflow.id
  policy = data.aws_iam_policy_document.result_updater_workflow.json
}

resource "aws_sfn_state_machine" "result_updater" {
  name     = "runmypool-results-updater"
  role_arn = aws_iam_role.result_updater_workflow.arn
  type     = "STANDARD"

  logging_configuration {
    include_execution_data = true
    level                  = "ERROR"
    log_destination        = "${aws_cloudwatch_log_group.result_updater_workflow.arn}:*"
  }

  definition = jsonencode({
    Comment = "Run scheduled Run My Pool jobs and retry container failures"
    StartAt = "SelectJob"
    States = {
      SelectJob = {
        Type = "Choice"
        Choices = [
          {
            Variable     = "$.job"
            StringEquals = "owner_reports"
            Next         = "RunOwnerReports"
          },
          {
            Variable     = "$.job"
            StringEquals = "email_verification_reminders"
            Next         = "RunEmailVerificationReminders"
          }
        ]
        Default = "RunUpdater"
      }
      RunUpdater = {
        Type           = "Task"
        Resource       = "arn:aws:states:::ecs:runTask.sync"
        TimeoutSeconds = 300
        Parameters = {
          Cluster        = aws_ecs_cluster.main.arn
          TaskDefinition = local.result_updater_family
          LaunchType     = "FARGATE"
          NetworkConfiguration = {
            AwsvpcConfiguration = {
              Subnets        = [aws_subnet.public_a.id, aws_subnet.public_b.id]
              SecurityGroups = [aws_security_group.result_updater.id]
              AssignPublicIp = "ENABLED"
            }
          }
        }
        Retry = [{
          ErrorEquals     = ["States.TaskFailed", "States.Timeout", "AmazonECS.Unknown"]
          IntervalSeconds = 30
          MaxAttempts     = 3
          BackoffRate     = 2
        }]
        Catch = [{
          ErrorEquals = ["States.ALL"]
          ResultPath  = "$.failure"
          Next        = "NotifyFailure"
        }]
        End = true
      }
      RunOwnerReports = {
        Type           = "Task"
        Resource       = "arn:aws:states:::ecs:runTask.sync"
        TimeoutSeconds = 300
        Parameters = {
          Cluster        = aws_ecs_cluster.main.arn
          TaskDefinition = local.result_updater_family
          LaunchType     = "FARGATE"
          Overrides = {
            ContainerOverrides = [{
              Name    = "result-updater"
              Command = ["python", "-m", "pool_reports"]
            }]
          }
          NetworkConfiguration = {
            AwsvpcConfiguration = {
              Subnets        = [aws_subnet.public_a.id, aws_subnet.public_b.id]
              SecurityGroups = [aws_security_group.result_updater.id]
              AssignPublicIp = "ENABLED"
            }
          }
        }
        Retry = [{
          ErrorEquals     = ["States.TaskFailed", "States.Timeout", "AmazonECS.Unknown"]
          IntervalSeconds = 30
          MaxAttempts     = 3
          BackoffRate     = 2
        }]
        Catch = [{
          ErrorEquals = ["States.ALL"]
          ResultPath  = "$.failure"
          Next        = "NotifyFailure"
        }]
        End = true
      }
      RunEmailVerificationReminders = {
        Type           = "Task"
        Resource       = "arn:aws:states:::ecs:runTask.sync"
        TimeoutSeconds = 300
        Parameters = {
          Cluster        = aws_ecs_cluster.main.arn
          TaskDefinition = local.result_updater_family
          LaunchType     = "FARGATE"
          Overrides = {
            ContainerOverrides = [{
              Name    = "result-updater"
              Command = ["python", "-m", "email_verification_reminders"]
            }]
          }
          NetworkConfiguration = {
            AwsvpcConfiguration = {
              Subnets        = [aws_subnet.public_a.id, aws_subnet.public_b.id]
              SecurityGroups = [aws_security_group.result_updater.id]
              AssignPublicIp = "ENABLED"
            }
          }
        }
        Retry = [{
          ErrorEquals     = ["States.TaskFailed", "States.Timeout", "AmazonECS.Unknown"]
          IntervalSeconds = 30
          MaxAttempts     = 3
          BackoffRate     = 2
        }]
        Catch = [{
          ErrorEquals = ["States.ALL"]
          ResultPath  = "$.failure"
          Next        = "NotifyFailure"
        }]
        End = true
      }
      NotifyFailure = {
        Type     = "Task"
        Resource = "arn:aws:states:::sns:publish"
        Parameters = {
          TopicArn    = aws_sns_topic.result_updater_alerts.arn
          Subject     = "Run My Pool scheduled job failed"
          "Message.$" = "States.JsonToString($)"
        }
        Next = "Failed"
      }
      Failed = {
        Type  = "Fail"
        Error = "ResultUpdaterFailed"
      }
    }
  })

  tags = local.common_tags
}

data "aws_iam_policy_document" "scheduler_assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["scheduler.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "result_updater_scheduler" {
  name               = "runmypool-results-updater-scheduler"
  assume_role_policy = data.aws_iam_policy_document.scheduler_assume_role.json
  tags               = local.common_tags
}

data "aws_iam_policy_document" "result_updater_scheduler" {
  statement {
    effect    = "Allow"
    actions   = ["states:StartExecution"]
    resources = [aws_sfn_state_machine.result_updater.arn]
  }
  statement {
    effect    = "Allow"
    actions   = ["sqs:SendMessage"]
    resources = [aws_sqs_queue.result_updater_dlq.arn]
  }
}

resource "aws_iam_role_policy" "result_updater_scheduler" {
  name   = "start-result-updater"
  role   = aws_iam_role.result_updater_scheduler.id
  policy = data.aws_iam_policy_document.result_updater_scheduler.json
}

locals {
  result_updater_game_windows = {
    thursday-evening  = "cron(0/15 19-23 ? SEP-DEC THU *)"
    friday-overnight  = "cron(0/15 0-2 ? SEP-DEC FRI *)"
    saturday-games    = "cron(0/15 12-23 ? DEC,JAN SAT *)"
    sunday-overnight  = "cron(0/15 0-2 ? DEC,JAN SUN *)"
    sunday-games      = "cron(0/15 12-23 ? SEP-DEC,JAN SUN *)"
    monday-overnight  = "cron(0/15 0-2 ? SEP-DEC,JAN MON *)"
    monday-evening    = "cron(0/15 19-23 ? SEP-DEC,JAN MON *)"
    tuesday-overnight = "cron(0/15 0-2 ? SEP-DEC,JAN TUE *)"
  }
}

resource "aws_scheduler_schedule" "result_updater_game_windows" {
  for_each = local.result_updater_game_windows

  name                         = "runmypool-results-updater-${each.key}"
  state                        = var.result_updater_schedule_enabled ? "ENABLED" : "DISABLED"
  schedule_expression          = each.value
  schedule_expression_timezone = "America/New_York"

  flexible_time_window {
    mode = "OFF"
  }

  target {
    arn      = aws_sfn_state_machine.result_updater.arn
    role_arn = aws_iam_role.result_updater_scheduler.arn

    retry_policy {
      maximum_event_age_in_seconds = 3600
      maximum_retry_attempts       = 3
    }

    dead_letter_config {
      arn = aws_sqs_queue.result_updater_dlq.arn
    }
  }
}

resource "aws_scheduler_schedule" "result_updater_corrections" {
  name                         = "runmypool-results-updater-corrections"
  state                        = var.result_updater_schedule_enabled ? "ENABLED" : "DISABLED"
  schedule_expression          = "cron(0 9 ? SEP-DEC,JAN-FEB * *)"
  schedule_expression_timezone = "America/New_York"

  flexible_time_window {
    mode = "OFF"
  }

  target {
    arn      = aws_sfn_state_machine.result_updater.arn
    role_arn = aws_iam_role.result_updater_scheduler.arn

    retry_policy {
      maximum_event_age_in_seconds = 3600
      maximum_retry_attempts       = 3
    }

    dead_letter_config {
      arn = aws_sqs_queue.result_updater_dlq.arn
    }
  }
}

resource "aws_scheduler_schedule" "owner_pool_reports" {
  name                         = "runmypool-weekly-owner-pool-reports"
  state                        = var.owner_pool_reports_schedule_enabled ? "ENABLED" : "DISABLED"
  schedule_expression          = "cron(0 10 ? * TUE *)"
  schedule_expression_timezone = "America/New_York"

  flexible_time_window { mode = "OFF" }

  target {
    arn      = aws_sfn_state_machine.result_updater.arn
    role_arn = aws_iam_role.result_updater_scheduler.arn
    input    = jsonencode({ job = "owner_reports" })

    retry_policy {
      maximum_event_age_in_seconds = 3600
      maximum_retry_attempts       = 3
    }
    dead_letter_config { arn = aws_sqs_queue.result_updater_dlq.arn }
  }
}

resource "aws_scheduler_schedule" "email_verification_reminders" {
  name                         = "runmypool-email-verification-reminders"
  state                        = var.email_verification_reminders_schedule_enabled ? "ENABLED" : "DISABLED"
  schedule_expression          = "cron(15 * ? * * *)"
  schedule_expression_timezone = "America/New_York"

  flexible_time_window { mode = "OFF" }

  target {
    arn      = aws_sfn_state_machine.result_updater.arn
    role_arn = aws_iam_role.result_updater_scheduler.arn
    input    = jsonencode({ job = "email_verification_reminders" })

    retry_policy {
      maximum_event_age_in_seconds = 3600
      maximum_retry_attempts       = 3
    }
    dead_letter_config { arn = aws_sqs_queue.result_updater_dlq.arn }
  }
}

resource "aws_cloudwatch_metric_alarm" "result_updater_workflow_failed" {
  alarm_name          = "runmypool-results-updater-failed"
  alarm_description   = "The NFL result updater workflow failed"
  namespace           = "AWS/States"
  metric_name         = "ExecutionsFailed"
  dimensions          = { StateMachineArn = aws_sfn_state_machine.result_updater.arn }
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.result_updater_alerts.arn]
  tags                = local.common_tags
}

resource "aws_cloudwatch_metric_alarm" "result_updater_dlq" {
  alarm_name          = "runmypool-results-updater-dlq-not-empty"
  alarm_description   = "A scheduled updater execution could not be delivered"
  namespace           = "AWS/SQS"
  metric_name         = "ApproximateNumberOfMessagesVisible"
  dimensions          = { QueueName = aws_sqs_queue.result_updater_dlq.name }
  statistic           = "Maximum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.result_updater_alerts.arn]
  tags                = local.common_tags
}

resource "aws_cloudwatch_event_rule" "result_updater_nonzero_exit" {
  name        = "runmypool-results-updater-nonzero-exit"
  description = "Secondary alert for an updater container that exits nonzero"
  event_pattern = jsonencode({
    source      = ["aws.ecs"]
    detail-type = ["ECS Task State Change"]
    detail = {
      lastStatus        = ["STOPPED"]
      taskDefinitionArn = [{ prefix = "arn:aws:ecs:${var.aws_region}:${var.aws_account_id}:task-definition/${local.result_updater_family}:" }]
      containers = {
        exitCode = [{ anything-but = 0 }]
      }
    }
  })
  tags = local.common_tags
}

resource "aws_cloudwatch_event_target" "result_updater_nonzero_exit" {
  rule = aws_cloudwatch_event_rule.result_updater_nonzero_exit.name
  arn  = aws_sns_topic.result_updater_alerts.arn
}

data "aws_iam_policy_document" "result_updater_sns_events" {
  statement {
    sid    = "TopicOwnerFullAccess"
    effect = "Allow"
    actions = [
      "sns:GetTopicAttributes",
      "sns:SetTopicAttributes",
      "sns:AddPermission",
      "sns:RemovePermission",
      "sns:DeleteTopic",
      "sns:Subscribe",
      "sns:ListSubscriptionsByTopic",
      "sns:Publish",
    ]
    resources = [aws_sns_topic.result_updater_alerts.arn]
    principals {
      type        = "AWS"
      identifiers = ["arn:aws:iam::${var.aws_account_id}:root"]
    }
  }

  statement {
    sid     = "EventBridgePublish"
    effect  = "Allow"
    actions = ["sns:Publish"]
    principals {
      type        = "Service"
      identifiers = ["events.amazonaws.com"]
    }
    resources = [aws_sns_topic.result_updater_alerts.arn]
    condition {
      test     = "ArnEquals"
      variable = "aws:SourceArn"
      values   = [aws_cloudwatch_event_rule.result_updater_nonzero_exit.arn]
    }
  }

  statement {
    sid       = "CloudWatchAlarmsPublish"
    effect    = "Allow"
    actions   = ["sns:Publish"]
    resources = [aws_sns_topic.result_updater_alerts.arn]
    principals {
      type        = "Service"
      identifiers = ["cloudwatch.amazonaws.com"]
    }
    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [var.aws_account_id]
    }
  }
}

resource "aws_sns_topic_policy" "result_updater_alerts" {
  arn    = aws_sns_topic.result_updater_alerts.arn
  policy = data.aws_iam_policy_document.result_updater_sns_events.json
}
