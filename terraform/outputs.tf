output "cluster_name" {
  description = "ECS cluster name (used in CI aws ecs update-service commands)"
  value       = aws_ecs_cluster.main.name
}

output "cluster_arn" {
  description = "ECS cluster ARN"
  value       = aws_ecs_cluster.main.arn
}

output "backend_service_name" {
  description = "ECS backend service name"
  value       = aws_ecs_service.backend.name
}

output "frontend_service_name" {
  description = "ECS frontend service name"
  value       = aws_ecs_service.frontend.name
}

output "backend_task_definition_arn" {
  description = "Latest backend task definition ARN"
  value       = aws_ecs_task_definition.backend.arn
}

output "frontend_task_definition_arn" {
  description = "Latest frontend task definition ARN"
  value       = aws_ecs_task_definition.frontend.arn
}

output "backend_log_group" {
  description = "CloudWatch log group for backend containers"
  value       = aws_cloudwatch_log_group.backend.name
}

output "frontend_log_group" {
  description = "CloudWatch log group for frontend containers"
  value       = aws_cloudwatch_log_group.frontend.name
}

output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.main.id
}

output "public_subnet_ids" {
  description = "Public subnet IDs (used by ECS tasks)"
  value       = [aws_subnet.public_a.id, aws_subnet.public_b.id]
}

output "ecs_security_group_id" {
  description = "Security group ID for ECS tasks"
  value       = aws_security_group.ecs.id
}

output "rds_security_group_id" {
  description = "Security group ID for RDS — allow this on your RDS instance"
  value       = aws_security_group.rds.id
}

output "result_updater_task_definition" {
  description = "Task definition family used for manual result updater canaries"
  value       = aws_ecs_task_definition.result_updater.family
}

output "db_access_task_definition" {
  description = "Task definition family used for on-demand SSM database tunnels"
  value       = aws_ecs_task_definition.db_access.family
}

output "db_access_security_group_id" {
  description = "Outbound-only security group for the database access task"
  value       = aws_security_group.db_access.id
}

output "db_access_operator_role_arn" {
  description = "Least-privilege role for starting and using the production database tunnel"
  value       = aws_iam_role.db_access_operator.arn
}

output "result_updater_state_machine_arn" {
  description = "Step Functions workflow that runs and monitors the updater task"
  value       = aws_sfn_state_machine.result_updater.arn
}

output "result_updater_schedule_state" {
  description = "Updater schedules remain disabled until the controlled cutover"
  value = merge(
    { for name, schedule in aws_scheduler_schedule.result_updater_game_windows : name => schedule.state },
    { corrections = aws_scheduler_schedule.result_updater_corrections.state },
  )
}

output "rds_endpoint" {
  description = "RDS instance endpoint (hostname)"
  value       = aws_db_instance.main.address
}

output "rds_port" {
  description = "RDS instance port"
  value       = aws_db_instance.main.port
}

output "rds_db_name" {
  description = "Database name"
  value       = aws_db_instance.main.db_name
}

output "alb_dns_name" {
  description = "ALB DNS name — use this as the CNAME target if not using Route 53 alias"
  value       = aws_lb.main.dns_name
}

output "route53_name_servers" {
  description = "Name servers for the runmypool.net hosted zone — update your registrar if these changed"
  value       = aws_route53_zone.main.name_servers
}
