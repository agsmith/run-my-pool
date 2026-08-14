locals {
  db_access_family = "runmypool-db-access"
  db_access_tags = {
    Project   = "runmypool"
    Component = "db-access"
  }
}

resource "aws_cloudwatch_log_group" "db_access" {
  name              = "/ecs/runmypool-db-access"
  retention_in_days = 7
  tags              = local.db_access_tags
}

resource "aws_security_group" "db_access" {
  name        = "run-my-pool-db-access-sg"
  description = "Outbound-only access for on-demand SSM database tunnels"
  vpc_id      = aws_vpc.main.id

  egress {
    description = "HTTPS for ECR and Systems Manager"
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
    description = "MySQL within the Run My Pool VPC"
    from_port   = 3306
    to_port     = 3306
    protocol    = "tcp"
    cidr_blocks = [aws_vpc.main.cidr_block]
  }

  tags = merge(local.db_access_tags, { Name = "run-my-pool-db-access-sg" })
}

resource "aws_iam_role" "db_access_execution" {
  name               = "runmypool-db-access-execution"
  assume_role_policy = data.aws_iam_policy_document.ecs_tasks_assume_role.json
  tags               = local.db_access_tags
}

resource "aws_iam_role_policy_attachment" "db_access_execution" {
  role       = aws_iam_role.db_access_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role" "db_access_task" {
  name               = "runmypool-db-access-task"
  assume_role_policy = data.aws_iam_policy_document.ecs_tasks_assume_role.json
  tags               = local.db_access_tags
}

data "aws_iam_policy_document" "db_access_ssm_messages" {
  statement {
    effect = "Allow"
    actions = [
      "ssmmessages:CreateControlChannel",
      "ssmmessages:CreateDataChannel",
      "ssmmessages:OpenControlChannel",
      "ssmmessages:OpenDataChannel",
    ]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "db_access_ssm_messages" {
  name   = "ecs-exec-ssm-messages"
  role   = aws_iam_role.db_access_task.id
  policy = data.aws_iam_policy_document.db_access_ssm_messages.json
}

resource "aws_ecs_task_definition" "db_access" {
  family                   = local.db_access_family
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "256"
  memory                   = "512"
  execution_role_arn       = aws_iam_role.db_access_execution.arn
  task_role_arn            = aws_iam_role.db_access_task.arn

  container_definitions = jsonencode([
    {
      name      = "db-access"
      image     = local.backend_image
      essential = true
      command   = ["python", "-c", "import time; time.sleep(14400)"]
      linuxParameters = {
        initProcessEnabled = true
      }
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.db_access.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }
    }
  ])

  tags = local.db_access_tags
}

data "aws_secretsmanager_secret" "db_access_readonly_password" {
  name = "runmypool/dbeaver-readonly-password"
}

data "aws_iam_policy_document" "db_access_operator_assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "AWS"
      identifiers = [data.aws_iam_user.db_access_source.arn]
    }
  }
}

data "aws_iam_user" "db_access_source" {
  user_name = "runmypool-terraform"
}

resource "aws_iam_role" "db_access_operator" {
  name                 = "runmypool-db-access-operator"
  assume_role_policy   = data.aws_iam_policy_document.db_access_operator_assume_role.json
  max_session_duration = 3600
  tags                 = local.db_access_tags
}

data "aws_iam_policy_document" "db_access_operator" {
  statement {
    sid       = "RunTunnelTask"
    effect    = "Allow"
    actions   = ["ecs:RunTask"]
    resources = ["${aws_ecs_task_definition.db_access.arn_without_revision}:*"]
    condition {
      test     = "ArnEquals"
      variable = "ecs:cluster"
      values   = [aws_ecs_cluster.main.arn]
    }
  }

  statement {
    sid    = "InspectAndStopTunnelTask"
    effect = "Allow"
    actions = [
      "ecs:DescribeTasks",
      "ecs:StopTask",
      "ecs:TagResource",
    ]
    resources = ["arn:aws:ecs:${var.aws_region}:${var.aws_account_id}:task/${aws_ecs_cluster.main.name}/*"]
  }

  statement {
    sid       = "PassTunnelTaskRoles"
    effect    = "Allow"
    actions   = ["iam:PassRole"]
    resources = [aws_iam_role.db_access_execution.arn, aws_iam_role.db_access_task.arn]
    condition {
      test     = "StringEquals"
      variable = "iam:PassedToService"
      values   = ["ecs-tasks.amazonaws.com"]
    }
  }

  statement {
    sid     = "OpenTunnelSession"
    effect  = "Allow"
    actions = ["ssm:StartSession"]
    resources = [
      "arn:aws:ecs:${var.aws_region}:${var.aws_account_id}:task/${aws_ecs_cluster.main.name}/*",
      "arn:aws:ssm:${var.aws_region}::document/AWS-StartPortForwardingSessionToRemoteHost",
    ]
  }

  statement {
    sid    = "ManageOwnTunnelSession"
    effect = "Allow"
    actions = [
      "ssm:ResumeSession",
      "ssm:TerminateSession",
    ]
    resources = ["arn:aws:ssm:${var.aws_region}:${var.aws_account_id}:session/*"]
  }

  statement {
    sid       = "ReadDBeaverPassword"
    effect    = "Allow"
    actions   = ["secretsmanager:GetSecretValue"]
    resources = [data.aws_secretsmanager_secret.db_access_readonly_password.arn]
  }
}

resource "aws_iam_role_policy" "db_access_operator" {
  name   = "operate-db-tunnel"
  role   = aws_iam_role.db_access_operator.id
  policy = data.aws_iam_policy_document.db_access_operator.json
}

data "aws_iam_policy_document" "db_access_source_assume_operator" {
  statement {
    effect    = "Allow"
    actions   = ["sts:AssumeRole"]
    resources = [aws_iam_role.db_access_operator.arn]
  }
}

resource "aws_iam_user_policy" "db_access_source_assume_operator" {
  name   = "assume-runmypool-db-access-operator"
  user   = data.aws_iam_user.db_access_source.user_name
  policy = data.aws_iam_policy_document.db_access_source_assume_operator.json
}
