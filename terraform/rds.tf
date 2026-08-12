# ==============================================================================
# RunMyPool — RDS MySQL 8.0
#
# Creates a fresh db.t3.micro MySQL 8.0 instance in the private subnets.
# The DB password is passed in via a sensitive variable and is never written
# to any file — pass it on the CLI:
#
#   terraform apply -var="db_password=<password>"
#
# After apply, the runmypool/database-url secret is updated automatically.
# ==============================================================================

resource "aws_db_instance" "main" {
  identifier        = "runmypool-db"
  engine            = "mysql"
  engine_version    = "8.0.46"
  instance_class    = "db.t3.micro"
  allocated_storage = 20
  storage_type      = "gp2"

  db_name  = "runmypooldb"
  username = "admin"
  password = var.db_password

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]

  # Disable multi-AZ and public access for cost and security
  multi_az            = false
  publicly_accessible = false

  # Backups — 7-day retention, no specific window preference
  backup_retention_period = 7
  skip_final_snapshot     = true

  # Allow minor version auto-upgrades; pin major version
  auto_minor_version_upgrade = true
  deletion_protection        = false

  tags = {
    Project = "runmypool"
  }

  lifecycle {
    # The imported password is write-only in RDS and cannot be read back into state.
    # Password rotation is managed through the database URL secret, not Terraform.
    ignore_changes = [password]
  }
}

# Update the existing Secrets Manager secret with the new connection string
resource "aws_secretsmanager_secret_version" "database_url" {
  secret_id     = var.database_url_secret_arn
  secret_string = "mysql+mysqlconnector://${aws_db_instance.main.username}:${var.db_password}@${aws_db_instance.main.address}:${aws_db_instance.main.port}/${aws_db_instance.main.db_name}"
}
