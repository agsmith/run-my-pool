terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.38.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.4.2"
    }
  }
  required_version = "~> 1.2"
}

# Data source to reference the existing RDS database
data "aws_db_instance" "runmypool_db" {
  db_instance_identifier = "terraform-20250830124351453200000003"
}


resource "null_resource" "install_python_dependencies" {
  triggers = {
    requirements_sha256 = filesha256("${path.module}/src/requirements.txt")
  }

  provisioner "local-exec" {
    command = "bash ${path.module}/src/create-pkg.sh"

    environment = {
      source_code_path = "${path.module}"
      function_name    = "nfl-game-updater"
      runtime          = "python3.12"
      path_cwd         = "${path.module}"
    }
  }
}


data "archive_file" "function_zip" {
  source_dir  = "src"
  type        = "zip"
  output_path = "${path.module}/nfl-game-updater.zip"
  depends_on  = [null_resource.install_python_dependencies]
}

resource "aws_s3_object" "file_upload" {
  bucket     = "nfl-game-updater-us-east-1-lambda"
  key        = "nfl-game-updater.zip"
  source     = "nfl-game-updater.zip"
  depends_on = [data.archive_file.function_zip]
}

resource "aws_lambda_function" "function" {
  s3_bucket     = "nfl-game-updater-us-east-1-lambda"
  s3_key        = "nfl-game-updater.zip"
  function_name = "nfl-game-updater"
  handler       = "nfl_game_updater.lambda_handler"
  runtime       = "python3.12"
  timeout       = 900
  memory_size   = 128
  role          = "arn:aws:iam::739444271939:role/nfl-game-updater-lambda-role"
  depends_on    = [aws_s3_object.file_upload]

  vpc_config {
    subnet_ids         = toset(["subnet-07d85747fe7504912", "subnet-080737ebc3b299dcd"])
    security_group_ids = toset(["sg-022ad503e1afbef4a"])
  }

  environment {
    variables = {
      DB_HOST     = data.aws_db_instance.runmypool_db.address
      DB_PORT     = data.aws_db_instance.runmypool_db.port
      DB_NAME     = data.aws_db_instance.runmypool_db.db_name
      DB_USERNAME = data.aws_db_instance.runmypool_db.master_username
      # Note: Password should be retrieved from AWS Secrets Manager for security
      SECRETS_MANAGER_ARN = "arn:aws:secretsmanager:us-east-1:739444271939:secret:runmypool/database-url-nRqy5o"
    }
  }
}

# IAM policy for Secrets Manager access (if not already included in the role)
resource "aws_iam_role_policy" "lambda_secrets_manager" {
  name = "nfl-game-updater-secrets-manager-policy"
  role = "nfl-game-updater-lambda-role"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ]
        Resource = "arn:aws:secretsmanager:us-east-1:739444271939:secret:runmypool/database-url-nRqy5o"
      }
    ]
  })
}

# Outputs for reference
output "lambda_function_name" {
  description = "Name of the Lambda function"
  value       = aws_lambda_function.function.function_name
}

output "database_endpoint" {
  description = "RDS database endpoint"
  value       = data.aws_db_instance.runmypool_db.address
}

output "database_port" {
  description = "RDS database port"
  value       = data.aws_db_instance.runmypool_db.port
}

output "database_name" {
  description = "RDS database name"
  value       = data.aws_db_instance.runmypool_db.db_name
}
