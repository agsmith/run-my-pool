# Long-term database recovery points complement the 30-day native RDS
# point-in-time recovery window. AWS Backup retains one monthly recovery point
# for one year. Cross-Region copies are intentionally omitted for now.

resource "aws_backup_vault" "rds" {
  name = "runmypool-rds-backups"

  tags = {
    Project = "runmypool"
  }
}

resource "aws_backup_plan" "rds_monthly" {
  name = "runmypool-rds-monthly"

  rule {
    rule_name         = "monthly-12-month-retention"
    target_vault_name = aws_backup_vault.rds.name
    schedule          = "cron(0 5 1 * ? *)"
    start_window      = 60
    completion_window = 180

    lifecycle {
      delete_after = 365
    }

    recovery_point_tags = {
      Project = "runmypool"
      Policy  = "monthly-12-month-retention"
    }
  }

  tags = {
    Project = "runmypool"
  }
}

data "aws_iam_policy_document" "backup_assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["backup.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "backup" {
  name               = "runmypool-rds-backup"
  assume_role_policy = data.aws_iam_policy_document.backup_assume_role.json

  tags = {
    Project = "runmypool"
  }
}

resource "aws_iam_role_policy_attachment" "backup" {
  role       = aws_iam_role.backup.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSBackupServiceRolePolicyForBackup"
}

resource "aws_backup_selection" "rds" {
  name         = "runmypool-production-database"
  iam_role_arn = aws_iam_role.backup.arn
  plan_id      = aws_backup_plan.rds_monthly.id
  resources    = [aws_db_instance.main.arn]
}
