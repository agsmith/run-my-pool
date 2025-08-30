output "alb_dns_name" {
  description = "DNS name of the load balancer"
  value       = aws_lb.app_alb.dns_name
}

output "alb_zone_id" {
  description = "Zone ID of the load balancer"
  value       = aws_lb.app_alb.zone_id
}

output "target_group_arn" {
  description = "ARN of the target group"
  value       = aws_lb_target_group.app_tg.arn
}

output "alb_security_group_id" {
  description = "Security group ID of the ALB"
  value       = aws_security_group.alb_sg.id
}

output "certificate_arn" {
  description = "ARN of the SSL certificate"
  value       = aws_acm_certificate.app_cert.arn
}

output "certificate_domain_validation_options" {
  description = "Domain validation options for the certificate"
  value       = aws_acm_certificate.app_cert.domain_validation_options
}
