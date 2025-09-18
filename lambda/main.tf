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


resource "null_resource" "install_python_dependencies" {
  provisioner "local-exec" {
    command = "bash ${path.module}/lambda/create_pkg.sh"

    environment = {
      source_code_path = "${path.module}/lambda"
      function_name = "nfl-game-updater"
      runtime = "python3.12"
      path_cwd = "${path.module}"
    }
  }
}


data "archive_file" "function_zip" {
  source_dir  = "src"
  type        = "zip"
  output_path = "${path.module}/nfl-game-updater.zip"
  depends_on = [ null_resource.install_python_dependencies ]
}

resource "aws_s3_object" "file_upload" {
  bucket = "nfl-game-updater-us-east-1-lambda"
  key    = "nfl-game-updater.zip"
  source = "nfl-game-updater.zip"
  depends_on = [ data.archive_file.function_zip ]
}

resource "aws_lambda_function" "function" {
  s3_bucket                       = "nfl-game-updater-us-east-1-lambda"
  s3_key                          = "nfl-game-updater.zip"
  function_name                   = "nfl-game-updater"
  handler                        = "nfl_game_updater.main"
  runtime                        = "python3.12"
  timeout                        = 900
  memory_size                    = 128
  role                           = "arn:aws:iam::739444271939:role/nfl-game-updater-lambda-role"
  depends_on = [ aws_s3_object.file_upload ]
}



