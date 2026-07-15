# ──────────────────────────────────────────────────────────────────────────────
# Core
# ──────────────────────────────────────────────────────────────────────────────

variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "us-east-1"
}

variable "aws_account_id" {
  description = "AWS account ID (used for ECR image URIs and ARNs)"
  type        = string
  default     = "739444271939"
}

# ──────────────────────────────────────────────────────────────────────────────
# Networking — managed by networking.tf; these variables kept for reference only
# ──────────────────────────────────────────────────────────────────────────────

# subnet_ids and ecs_security_group_id are now derived from networking.tf resources.
# Remove these defaults if you want to use pre-existing network resources instead
# of letting Terraform create them.

# ──────────────────────────────────────────────────────────────────────────────
# IAM — existing roles
# ──────────────────────────────────────────────────────────────────────────────

variable "execution_role_arn" {
  description = "ARN of the ECS task execution role (ecs_task_execution_role)"
  type        = string
  default     = "arn:aws:iam::739444271939:role/ecs_task_execution_role"
}

variable "task_role_arn" {
  description = "ARN of the ECS task role (ecs_task_role)"
  type        = string
  default     = "arn:aws:iam::739444271939:role/ecs_task_role"
}

# ──────────────────────────────────────────────────────────────────────────────
# Secrets Manager — existing secrets
# ──────────────────────────────────────────────────────────────────────────────

variable "database_url_secret_arn" {
  description = "ARN of the Secrets Manager secret holding DATABASE_URL"
  type        = string
  default     = "arn:aws:secretsmanager:us-east-1:739444271939:secret:runmypool/database-url-nRqy5o"
}

variable "jwt_secret_arn" {
  description = "ARN of the Secrets Manager secret holding JWT_SECRET / SECRET_KEY"
  type        = string
  default     = "arn:aws:secretsmanager:us-east-1:739444271939:secret:runmypool/jwt-secret-s2S9FU"
}

# ──────────────────────────────────────────────────────────────────────────────
# Application
# ──────────────────────────────────────────────────────────────────────────────

variable "cors_origins" {
  description = "Allowed CORS origins for the backend (comma-separated or full URL)"
  type        = string
  default     = "https://runmypool.net"
}

variable "backend_image_tag" {
  description = "ECR image tag for the backend container"
  type        = string
  default     = "latest"
}

variable "frontend_image_tag" {
  description = "ECR image tag for the frontend container"
  type        = string
  default     = "latest"
}

variable "desired_count" {
  description = "Number of running tasks for each ECS service"
  type        = number
  default     = 1
}

# ──────────────────────────────────────────────────────────────────────────────
# Database
# ──────────────────────────────────────────────────────────────────────────────

variable "db_password" {
  description = "Master password for the RDS MySQL instance. Pass on the CLI: -var='db_password=...'"
  type        = string
  sensitive   = true
}
