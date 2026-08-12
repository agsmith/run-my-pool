terraform {
  required_version = ">= 1.5"

  backend "s3" {
    bucket       = "runmypool-terraform-state-739444271939"
    key          = "production/runmypool.tfstate"
    region       = "us-east-1"
    encrypt      = true
    use_lockfile = true
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.38"
    }
  }
}

provider "aws" {
  region = var.aws_region
}
