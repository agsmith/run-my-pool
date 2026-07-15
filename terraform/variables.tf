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
# Networking — reuse the existing VPC / subnets / security groups
# ──────────────────────────────────────────────────────────────────────────────

variable "vpc_id" {
  description = "ID of the existing VPC"
  type        = string
  default     = "vpc-0593914a220fcfc80"
}

variable "subnet_ids" {
  description = "Subnet IDs for ECS tasks and the ALB (must span >= 2 AZs)"
  type        = list(string)
  default     = ["subnet-07d85747fe7504912", "subnet-080737ebc3b299dcd"]
}

variable "ecs_security_group_id" {
  description = "Security group ID for ECS tasks"
  type        = string
  default     = "sg-022ad503e1afbef4a"
}

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
