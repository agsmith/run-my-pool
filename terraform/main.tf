# ==============================================================================
# RunMyPool — ECS Infrastructure
#
# What this creates:
#   - ECS Cluster (run-my-pool-cluster)
#   - CloudWatch Log Groups for backend and frontend
#   - ECS Task Definitions for backend (port 8000) and frontend (port 3000)
#   - ECS Services for backend and frontend (Fargate, awsvpc networking)
#
# What this DOES NOT create (already exists in the account):
#   - VPC, subnets, security groups        → referenced via variables
#   - IAM roles (execution + task)         → referenced via variables
#   - ECR repositories                     → CI pushes to them already
#   - RDS instance                         → referenced by the Lambda Terraform
#   - ALB / target groups / listeners      → see alb.tf if you want to add one
#   - Secrets Manager secrets              → referenced via variables
# ==============================================================================

locals {
  backend_image  = "${var.aws_account_id}.dkr.ecr.${var.aws_region}.amazonaws.com/runmypool-backend:${var.backend_image_tag}"
  frontend_image = "${var.aws_account_id}.dkr.ecr.${var.aws_region}.amazonaws.com/runmypool-frontend:${var.frontend_image_tag}"
}

# ──────────────────────────────────────────────────────────────────────────────
# ECS Cluster
# ──────────────────────────────────────────────────────────────────────────────

resource "aws_ecs_cluster" "main" {
  name = "run-my-pool-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = {
    Project = "runmypool"
  }
}

# Keep enough images for quick rollback while preventing old CI builds from
# accumulating indefinitely in ECR.
resource "aws_ecr_lifecycle_policy" "application_images" {
  for_each = toset(["runmypool-backend", "runmypool-frontend"])

  repository = each.value
  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Expire untagged images after one day"
        selection = {
          tagStatus   = "untagged"
          countType   = "sinceImagePushed"
          countUnit   = "days"
          countNumber = 1
        }
        action = {
          type = "expire"
        }
      },
      {
        rulePriority = 2
        description  = "Keep the ten most recent images"
        selection = {
          tagStatus   = "any"
          countType   = "imageCountMoreThan"
          countNumber = 10
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}

resource "aws_ecs_cluster_capacity_providers" "main" {
  cluster_name       = aws_ecs_cluster.main.name
  capacity_providers = ["FARGATE", "FARGATE_SPOT"]

  default_capacity_provider_strategy {
    capacity_provider = "FARGATE"
    weight            = 1
  }
}

# ──────────────────────────────────────────────────────────────────────────────
# CloudWatch Log Groups
# ──────────────────────────────────────────────────────────────────────────────

resource "aws_cloudwatch_log_group" "backend" {
  name              = "/ecs/runmypool-backend"
  retention_in_days = 30

  tags = {
    Project = "runmypool"
  }
}

resource "aws_cloudwatch_log_group" "frontend" {
  name              = "/ecs/runmypool-frontend"
  retention_in_days = 30

  tags = {
    Project = "runmypool"
  }
}

# ──────────────────────────────────────────────────────────────────────────────
# Backend Task Definition
# ──────────────────────────────────────────────────────────────────────────────

resource "aws_ecs_task_definition" "backend" {
  family                   = "runmypool-backend"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "512"
  memory                   = "1024"
  execution_role_arn       = var.execution_role_arn
  task_role_arn            = var.task_role_arn
  skip_destroy             = false

  container_definitions = jsonencode([
    {
      name      = "backend"
      image     = local.backend_image
      essential = true

      portMappings = [
        {
          containerPort = 8000
          protocol      = "tcp"
        }
      ]

      environment = [
        {
          name  = "CORS_ORIGINS"
          value = var.cors_origins
        },
        {
          name  = "FRONTEND_URL"
          value = "https://runmypool.net"
        },
        {
          name  = "AWS_SES_REGION"
          value = var.aws_region
        },
        {
          name  = "EMAIL_FROM"
          value = "Run My Pool Accounts <accounts@runmypool.net>"
        },
        {
          name  = "EMAIL_REPLY_TO"
          value = "support@runmypool.net"
        },
        {
          name  = "STRIPE_PRICE_SQUARES_PLUS"
          value = var.stripe_price_squares_plus
        },
        {
          name  = "STRIPE_PRICE_COMMISSIONER"
          value = var.stripe_price_commissioner
        },
        {
          name  = "STRIPE_PRICE_PRO"
          value = var.stripe_price_pro
        },
        {
          name  = "STRIPE_PRICE_CLUB"
          value = var.stripe_price_club
        },
        {
          name  = "STRIPE_PRICE_CLUB_UNLIMITED"
          value = var.stripe_price_club_unlimited
        },
        {
          name  = "STRIPE_AUTOMATIC_TAX"
          value = tostring(var.stripe_automatic_tax)
        },
        {
          name  = "DB_POOL_SIZE"
          value = tostring(var.backend_db_pool_size)
        },
        {
          name  = "DB_MAX_OVERFLOW"
          value = tostring(var.backend_db_max_overflow)
        },
        {
          name  = "DB_POOL_TIMEOUT_SECONDS"
          value = "10"
        },
        {
          name  = "DB_POOL_RECYCLE_SECONDS"
          value = "1800"
        },
        {
          name  = "REQUIRE_EMAIL_VERIFICATION"
          value = tostring(var.require_email_verification)
        }
      ]

      secrets = concat([
        {
          name      = "DATABASE_URL"
          valueFrom = var.database_url_secret_arn
        },
        {
          name      = "SECRET_KEY"
          valueFrom = var.jwt_secret_arn
        }
        ], var.stripe_secret_key_secret_arn == null ? [] : [{
          name      = "STRIPE_SECRET_KEY"
          valueFrom = var.stripe_secret_key_secret_arn
          }], var.stripe_webhook_secret_arn == null ? [] : [{
          name      = "STRIPE_WEBHOOK_SECRET"
          valueFrom = var.stripe_webhook_secret_arn
      }])

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.backend.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }

      healthCheck = {
        command     = ["CMD-SHELL", "curl -f http://localhost:8000/ || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 60
      }
    }
  ])

}

# ──────────────────────────────────────────────────────────────────────────────
# Frontend Task Definition
# ──────────────────────────────────────────────────────────────────────────────

resource "aws_ecs_task_definition" "frontend" {
  family                   = "runmypool-frontend"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "256"
  memory                   = "512"
  execution_role_arn       = var.execution_role_arn
  task_role_arn            = var.task_role_arn
  skip_destroy             = false

  container_definitions = jsonencode([
    {
      name      = "frontend"
      image     = local.frontend_image
      essential = true

      portMappings = [
        {
          containerPort = 3000
          hostPort      = 3000
          protocol      = "tcp"
        }
      ]

      environment = [
        {
          name  = "NODE_ENV"
          value = "production"
        },
        {
          name  = "NEXT_PUBLIC_API_URL"
          value = "https://run-my-pool-alb-1079058824.us-east-1.elb.amazonaws.com"
        }
      ]

      mountPoints    = []
      volumesFrom    = []
      systemControls = []

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.frontend.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }

      healthCheck = {
        command     = ["CMD-SHELL", "node /app/healthcheck.js || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 60
      }
    }
  ])

}

# ──────────────────────────────────────────────────────────────────────────────
# Backend ECS Service
# ──────────────────────────────────────────────────────────────────────────────

resource "aws_ecs_service" "backend" {
  name            = "runmypool-backend-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.backend.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = [aws_subnet.public_a.id, aws_subnet.public_b.id]
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.backend.arn
    container_name   = "backend"
    container_port   = 8000
  }

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  deployment_controller {
    type = "ECS"
  }

  tags = {
    Project = "runmypool"
  }

  lifecycle {
    # Prevent Terraform from rolling back image changes made by CI
    ignore_changes = [task_definition, desired_count]
  }

  depends_on = [aws_lb_listener.https]
}

# ──────────────────────────────────────────────────────────────────────────────
# Frontend ECS Service
# ──────────────────────────────────────────────────────────────────────────────

resource "aws_ecs_service" "frontend" {
  name            = "runmypool-frontend-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.frontend.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = [aws_subnet.public_a.id, aws_subnet.public_b.id]
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.frontend.arn
    container_name   = "frontend"
    container_port   = 3000
  }

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  deployment_controller {
    type = "ECS"
  }

  tags = {
    Project = "runmypool"
  }

  lifecycle {
    ignore_changes = [task_definition, desired_count]
  }

  depends_on = [aws_lb_listener.https]
}

resource "aws_appautoscaling_target" "backend" {
  max_capacity       = var.backend_max_tasks
  min_capacity       = var.backend_min_tasks
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.backend.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

resource "aws_appautoscaling_policy" "backend_cpu" {
  name               = "runmypool-backend-cpu"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.backend.resource_id
  scalable_dimension = aws_appautoscaling_target.backend.scalable_dimension
  service_namespace  = aws_appautoscaling_target.backend.service_namespace

  target_tracking_scaling_policy_configuration {
    target_value       = var.ecs_cpu_target_percent
    scale_in_cooldown  = 300
    scale_out_cooldown = 60
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
  }
}

resource "aws_appautoscaling_policy" "backend_memory" {
  name               = "runmypool-backend-memory"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.backend.resource_id
  scalable_dimension = aws_appautoscaling_target.backend.scalable_dimension
  service_namespace  = aws_appautoscaling_target.backend.service_namespace

  target_tracking_scaling_policy_configuration {
    target_value       = var.ecs_memory_target_percent
    scale_in_cooldown  = 300
    scale_out_cooldown = 60
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageMemoryUtilization"
    }
  }
}

resource "aws_appautoscaling_target" "frontend" {
  max_capacity       = var.frontend_max_tasks
  min_capacity       = var.frontend_min_tasks
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.frontend.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

resource "aws_appautoscaling_policy" "frontend_cpu" {
  name               = "runmypool-frontend-cpu"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.frontend.resource_id
  scalable_dimension = aws_appautoscaling_target.frontend.scalable_dimension
  service_namespace  = aws_appautoscaling_target.frontend.service_namespace

  target_tracking_scaling_policy_configuration {
    target_value       = var.ecs_cpu_target_percent
    scale_in_cooldown  = 300
    scale_out_cooldown = 60
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
  }
}

resource "aws_appautoscaling_policy" "frontend_memory" {
  name               = "runmypool-frontend-memory"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.frontend.resource_id
  scalable_dimension = aws_appautoscaling_target.frontend.scalable_dimension
  service_namespace  = aws_appautoscaling_target.frontend.service_namespace

  target_tracking_scaling_policy_configuration {
    target_value       = var.ecs_memory_target_percent
    scale_in_cooldown  = 300
    scale_out_cooldown = 60
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageMemoryUtilization"
    }
  }
}
