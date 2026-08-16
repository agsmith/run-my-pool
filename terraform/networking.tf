# ==============================================================================
# RunMyPool — VPC and Networking
#
# Creates a fresh VPC with:
#   - 2 public subnets (ECS tasks with public IPs)
#   - 2 private subnets (RDS)
#   - Internet gateway + route table for public subnets
#   - Security groups for ECS tasks, ALB, and RDS
# ==============================================================================

# ──────────────────────────────────────────────────────────────────────────────
# VPC
# ──────────────────────────────────────────────────────────────────────────────

resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = {
    Name    = "run-my-pool-vpc"
    Project = "runmypool"
  }
}

# ──────────────────────────────────────────────────────────────────────────────
# Internet Gateway
# ──────────────────────────────────────────────────────────────────────────────

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name    = "run-my-pool-igw"
    Project = "runmypool"
  }
}

# ──────────────────────────────────────────────────────────────────────────────
# Public Subnets (ECS tasks, ALB)
# ──────────────────────────────────────────────────────────────────────────────

resource "aws_subnet" "public_a" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.1.0/24"
  availability_zone       = "us-east-1a"
  map_public_ip_on_launch = true

  tags = {
    Name    = "run-my-pool-public-a"
    Project = "runmypool"
  }
}

resource "aws_subnet" "public_b" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.2.0/24"
  availability_zone       = "us-east-1b"
  map_public_ip_on_launch = true

  tags = {
    Name    = "run-my-pool-public-b"
    Project = "runmypool"
  }
}

# ──────────────────────────────────────────────────────────────────────────────
# Private Subnets (RDS)
# ──────────────────────────────────────────────────────────────────────────────

resource "aws_subnet" "private_a" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.3.0/24"
  availability_zone = "us-east-1a"

  tags = {
    Name    = "run-my-pool-private-a"
    Project = "runmypool"
  }
}

resource "aws_subnet" "private_b" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.4.0/24"
  availability_zone = "us-east-1b"

  tags = {
    Name    = "run-my-pool-private-b"
    Project = "runmypool"
  }
}

# ──────────────────────────────────────────────────────────────────────────────
# Route Tables
# ──────────────────────────────────────────────────────────────────────────────

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = {
    Name    = "run-my-pool-public-rt"
    Project = "runmypool"
  }
}

resource "aws_route_table_association" "public_a" {
  subnet_id      = aws_subnet.public_a.id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table_association" "public_b" {
  subnet_id      = aws_subnet.public_b.id
  route_table_id = aws_route_table.public.id
}

# ──────────────────────────────────────────────────────────────────────────────
# Security Groups
# ──────────────────────────────────────────────────────────────────────────────

# ALB — accepts HTTP/HTTPS from the internet
resource "aws_security_group" "alb" {
  name        = "run-my-pool-alb-sg"
  description = "Allow HTTP/HTTPS inbound to ALB"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTPS"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name    = "run-my-pool-alb-sg"
    Project = "runmypool"
  }
}

# ECS tasks — accepts traffic from ALB; full outbound (for ECR pulls, Secrets Manager, etc.)
resource "aws_security_group" "ecs" {
  name        = "run-my-pool-ecs-sg"
  description = "Allow traffic from ALB to ECS tasks"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "Backend from ALB"
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  ingress {
    description     = "Frontend from ALB"
    from_port       = 3000
    to_port         = 3000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name    = "run-my-pool-ecs-sg"
    Project = "runmypool"
  }
}

# RDS — accepts MySQL from ECS tasks only
resource "aws_security_group" "rds" {
  name        = "run-my-pool-rds-sg"
  description = "Allow MySQL from ECS tasks"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "MySQL from approved ECS tasks"
    from_port       = 3306
    to_port         = 3306
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs.id, aws_security_group.result_updater.id, aws_security_group.db_access.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name    = "run-my-pool-rds-sg"
    Project = "runmypool"
  }
}

# ──────────────────────────────────────────────────────────────────────────────
# DB Subnet Group (needed for RDS, even if RDS already exists)
# ──────────────────────────────────────────────────────────────────────────────

resource "aws_db_subnet_group" "main" {
  name       = "run-my-pool-db-subnet-group-v2"
  subnet_ids = [aws_subnet.private_a.id, aws_subnet.private_b.id]

  tags = {
    Name    = "run-my-pool-db-subnet-group-v2"
    Project = "runmypool"
  }
}
