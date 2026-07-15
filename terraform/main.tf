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
        }
      ]

      secrets = [
        {
          name      = "DATABASE_URL"
          valueFrom = var.database_url_secret_arn
        },
        {
          name      = "SECRET_KEY"
          valueFrom = var.jwt_secret_arn
        }
      ]

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

  tags = {
    Project = "runmypool"
  }
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

  container_definitions = jsonencode([
    {
      name      = "frontend"
      image     = local.frontend_image
      essential = true

      portMappings = [
        {
          containerPort = 3000
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

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.frontend.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }

      healthCheck = {
        command     = ["CMD-SHELL", "wget --no-verbose --tries=1 --spider http://localhost:3000/ || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 60
      }
    }
  ])

  tags = {
    Project = "runmypool"
  }
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

  # Allow Terraform to update the service when CI deploys a new image tag
  force_new_deployment = true

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
    ignore_changes = [task_definition]
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

  force_new_deployment = true

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
    ignore_changes = [task_definition]
  }

  depends_on = [aws_lb_listener.https]
}
