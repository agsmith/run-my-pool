# ==============================================================================
# RunMyPool — RDS MySQL 8.4
#
# Creates a fresh db.t3.micro MySQL 8.4 instance in the private subnets.
# The DB password is passed in via a sensitive variable and is never written
# to any file — pass it on the CLI:
#
#   terraform apply -var="db_password=<password>"
#
# After apply, the runmypool/database-url secret is updated automatically.
# ==============================================================================

resource "aws_db_instance" "main" {
  identifier                  = "runmypool-db-encrypted"
  engine                      = "mysql"
  engine_version              = "8.4.10"
  allow_major_version_upgrade = true
  apply_immediately           = true
  instance_class              = "db.t4g.small"
  allocated_storage           = 20
  max_allocated_storage       = 100
  storage_type                = "gp2"
  storage_encrypted           = true
  kms_key_id                  = data.aws_kms_alias.rds.target_key_arn

  db_name  = "runmypooldb"
  username = "admin"
  password = var.db_password

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]

  # Disable multi-AZ and public access for cost and security
  multi_az            = false
  publicly_accessible = false

  # Backups — 30-day point-in-time recovery plus a mandatory final snapshot.
  backup_retention_period   = 30
  copy_tags_to_snapshot     = true
  skip_final_snapshot       = false
  final_snapshot_identifier = "runmypool-db-final"

  # Allow compatible minor upgrades within the pinned MySQL 8.4 major version.
  auto_minor_version_upgrade = true
  deletion_protection        = true

  tags = {
    Project = "runmypool"
  }

  lifecycle {
    # The imported password is write-only in RDS and cannot be read back into state.
    # Password rotation is managed through the database URL secret, not Terraform.
    ignore_changes = [password]
  }
}

data "aws_kms_alias" "rds" {
  name = "alias/aws/rds"
}

# Update the existing Secrets Manager secret with the new connection string
resource "aws_secretsmanager_secret_version" "database_url" {
  secret_id     = var.database_url_secret_arn
  secret_string = "mysql+mysqlconnector://${aws_db_instance.main.username}:${var.db_password}@${aws_db_instance.main.address}:${aws_db_instance.main.port}/${aws_db_instance.main.db_name}"
}
