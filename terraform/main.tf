provider "aws" {
  region = "us-east-1"
}

module "networking" {
  source = "./networking"
}

module "ecr" {
  source = "./ecr"
}

module "alb" {
  source            = "./alb"
  vpc_id            = module.networking.vpc_id
  public_subnet_ids = module.networking.public_subnet_ids
  domain_name       = "runmypool.net"
}

module "rds" {
  source              = "./rds"
  vpc_id              = module.networking.vpc_id
  private_subnet_ids  = module.networking.private_subnet_ids
  db_sg_id            = module.networking.db_sg_id
}

module "ecs" {
  source              = "./ecs"
  subnet_ids          = module.networking.public_subnet_ids
  security_group_id   = module.networking.app_sg_id
  db_secret_arn       = module.rds.db_secret_arn
  image_url           = "${module.ecr.repository_url}:latest"
  execution_role_arn  = module.networking.ecs_execution_role_arn
  target_group_arn    = module.alb.target_group_arn
}

output "ecr_repository_url" {
  value = module.ecr.repository_url
}

output "alb_dns_name" {
  value = module.alb.alb_dns_name
}

output "certificate_arn" {
  value = module.alb.certificate_arn
}

output "certificate_domain_validation_options" {
  value = module.alb.certificate_domain_validation_options
}
