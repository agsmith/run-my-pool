variable "vpc_id" {
  description = "VPC ID where ALB will be created"
  type        = string
}

variable "public_subnet_ids" {
  description = "List of public subnet IDs for ALB"
  type        = list(string)
}

variable "domain_name" {
  description = "Domain name for SSL certificate"
  type        = string
  default     = "runmypool.net"
}
