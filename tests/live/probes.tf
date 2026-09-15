provider "aws" {
  alias               = "west"
  region              = "us-west-2"
  allowed_account_ids = [var.expected_account]
  default_tags {
    tags = { Purpose = "edge-router-integration", TestRun = var.name }
  }
}
provider "aws" {
  alias               = "europe"
  region              = "eu-west-1"
  allowed_account_ids = [var.expected_account]
  default_tags {
    tags = { Purpose = "edge-router-integration", TestRun = var.name }
  }
}
resource "aws_iam_role" "probe" {
  name = "${var.name}-probe"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Action    = "sts:AssumeRole"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}
data "archive_file" "probe" {
  type        = "zip"
  source_file = "${path.module}/probe.py"
  output_path = "${path.module}/build/probe.zip"
}
resource "aws_lambda_function" "probe_west" {
  provider         = aws.west
  function_name    = "${var.name}-probe"
  role             = aws_iam_role.probe.arn
  handler          = "probe.handler"
  runtime          = "python3.12"
  timeout          = 120
  memory_size      = 256
  filename         = data.archive_file.probe.output_path
  source_code_hash = data.archive_file.probe.output_base64sha256
  environment {
    variables = {
      TARGET_URL = "https://${module.frontdoor.domain_name}"
      PIN_COOKIE = "${var.name}-deployment"
    }
  }
}
resource "aws_lambda_function" "probe_europe" {
  provider         = aws.europe
  function_name    = "${var.name}-probe"
  role             = aws_iam_role.probe.arn
  handler          = "probe.handler"
  runtime          = "python3.12"
  timeout          = 120
  memory_size      = 256
  filename         = data.archive_file.probe.output_path
  source_code_hash = data.archive_file.probe.output_base64sha256
  environment {
    variables = {
      TARGET_URL = "https://${module.frontdoor.domain_name}"
      PIN_COOKIE = "${var.name}-deployment"
    }
  }
}