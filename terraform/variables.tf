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

variable "stripe_secret_key_secret_arn" {
  description = "ARN of the Secrets Manager secret holding the Stripe secret API key"
  type        = string
  default     = "arn:aws:secretsmanager:us-east-1:739444271939:secret:runmypool/stripe-live-secret-key-RHRbB5"
  nullable    = true
}

variable "stripe_webhook_secret_arn" {
  description = "ARN of the Secrets Manager secret holding the Stripe webhook signing secret"
  type        = string
  default     = "arn:aws:secretsmanager:us-east-1:739444271939:secret:runmypool/stripe-live-webhook-signing-secret-R4gAKT"
  nullable    = true
}

# ──────────────────────────────────────────────────────────────────────────────
# Application
# ──────────────────────────────────────────────────────────────────────────────

variable "cors_origins" {
  description = "Allowed CORS origins for the backend (comma-separated or full URL)"
  type        = string
  default     = "https://runmypool.net,https://www.runmypool.net"
}

variable "stripe_price_commissioner" {
  description = "Stripe one-time Price ID for the Commissioner seasonal plan"
  type        = string
  default     = "price_1U5VOvHzJHWFhiJuXZRgMQOG"
}

variable "stripe_price_squares_plus" {
  description = "Stripe Price ID for the Squares Plus seasonal plan"
  type        = string
  default     = "price_1U5VOUHzJHWFhiJuiW7WXtyc"
}

variable "stripe_price_pro" {
  description = "Stripe one-time Price ID for the Pro seasonal plan"
  type        = string
  default     = "price_1U5VQ9HzJHWFhiJuEOF3KYQe"
}

variable "stripe_price_club" {
  description = "Stripe one-time Price ID for the Club seasonal plan"
  type        = string
  default     = "price_1U5VQXHzJHWFhiJug6zLilzx"
}

variable "stripe_price_club_unlimited" {
  description = "Stripe one-time Price ID for the Club Unlimited seasonal plan"
  type        = string
  default     = "price_1U5VQwHzJHWFhiJu9yMmGkO1"
}

variable "stripe_automatic_tax" {
  description = "Enable Stripe Tax in Checkout after tax registrations are configured"
  type        = bool
  default     = false
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

variable "backend_min_tasks" {
  description = "Minimum backend tasks; one is appropriate for current low traffic"
  type        = number
  default     = 1
}

variable "backend_max_tasks" {
  description = "Maximum backend tasks for the expected 700-user population"
  type        = number
  default     = 3
}

variable "frontend_min_tasks" {
  description = "Minimum frontend tasks"
  type        = number
  default     = 1
}

variable "frontend_max_tasks" {
  description = "Maximum frontend tasks for burst traffic"
  type        = number
  default     = 3
}

variable "ecs_cpu_target_percent" {
  description = "ECS target-tracking CPU utilization"
  type        = number
  default     = 60
}

variable "ecs_memory_target_percent" {
  description = "Backend ECS target-tracking memory utilization"
  type        = number
  default     = 70
}

variable "backend_db_pool_size" {
  description = "Persistent SQLAlchemy connections per backend task"
  type        = number
  default     = 5
}

variable "backend_db_max_overflow" {
  description = "Temporary SQLAlchemy connections per backend task"
  type        = number
  default     = 5
}

variable "require_email_verification" {
  description = "Require new accounts to verify their email before signing in"
  type        = bool
  default     = true
}

variable "result_updater_schedule_enabled" {
  description = "Enable the new ECS result updater only after dry-run validation and Lambda cutover"
  type        = bool
  default     = false
}

variable "owner_pool_reports_schedule_enabled" {
  description = "Enable weekly email reports for pool owners who explicitly opt in"
  type        = bool
  default     = true
}

variable "result_updater_alert_email" {
  description = "Email address that receives result updater failure notifications"
  type        = string
  default     = "support@runmypool.net"
}

# ──────────────────────────────────────────────────────────────────────────────
# Database
# ──────────────────────────────────────────────────────────────────────────────

variable "db_password" {
  description = "Master password for the RDS MySQL instance. Pass on the CLI: -var='db_password=...'"
  type        = string
  sensitive   = true
}
