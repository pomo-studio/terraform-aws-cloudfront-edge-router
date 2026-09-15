locals {
  deployment_list   = sort(tolist(var.deployments))
  deployment_header = var.deployment_header != null ? lower(var.deployment_header) : "x-postmodern-deployment"
  pin_cookie        = var.pin_cookie != null ? var.pin_cookie : "${var.name}-deployment"
  parameter_path    = var.parameter_path != null ? var.parameter_path : "/${var.name}/rollout"
  kvs_name          = "${var.name}-edge-router"
  sync_name         = "${var.name}-edge-router-sync"
}

resource "aws_ssm_parameter" "rollout" {
  name = local.parameter_path
  type = "String"
  value = jsonencode({
    active     = var.active_deployment
    weight     = var.weight
    pin_cookie = local.pin_cookie
  })

  tags = var.tags

  lifecycle {
    # Terraform seeds the rollout state; promotions then happen by updating
    # the parameter, and a later apply must not put the seed back.
    ignore_changes = [value]

    precondition {
      condition     = length(local.deployment_list) > 0
      error_message = "At least one deployment is required."
    }

    precondition {
      condition     = contains(local.deployment_list, var.active_deployment)
      error_message = "active_deployment must name one of the deployments."
    }
  }
}

resource "aws_cloudfront_key_value_store" "this" {
  name    = local.kvs_name
  comment = "Rollout state for ${var.name}, synced from Parameter Store"
}

resource "aws_cloudfront_function" "viewer_request" {
  name    = "${var.name}-viewer-request"
  runtime = var.function_runtime
  comment = "Select the ${var.name} deployment origin per request"
  publish = true

  code = templatefile("${path.module}/functions/viewer-request.js.tftpl", {
    deployments_json       = jsonencode(local.deployment_list)
    deployment_header_json = jsonencode(local.deployment_header)
  })

  key_value_store_associations = [aws_cloudfront_key_value_store.this.arn]
}

resource "aws_cloudfront_function" "viewer_response" {
  name    = "${var.name}-viewer-response"
  runtime = var.function_runtime
  comment = "Set the ${var.name} deployment pin cookie"
  publish = true

  code = templatefile("${path.module}/functions/viewer-response.js.tftpl", {
    deployment_header_json = jsonencode(local.deployment_header)
    pin_cookie_json        = jsonencode(local.pin_cookie)
  })
}

data "archive_file" "sync" {
  type        = "zip"
  source_dir  = "${path.module}/functions/sync"
  output_path = "${path.module}/build/sync.zip"
}

resource "aws_iam_role" "sync" {
  name = local.sync_name

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow"
        Action    = "sts:AssumeRole"
        Principal = { Service = "lambda.amazonaws.com" }
      },
    ]
  })

  tags = var.tags
}

resource "aws_iam_role_policy" "sync" {
  name = local.sync_name
  role = aws_iam_role.sync.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["ssm:GetParameter"]
        Resource = [aws_ssm_parameter.rollout.arn]
      },
      {
        Effect = "Allow"
        Action = [
          "cloudfront-keyvaluestore:DescribeKeyValueStore",
          "cloudfront-keyvaluestore:UpdateKeys",
        ]
        Resource = [aws_cloudfront_key_value_store.this.arn]
      },
      {
        Effect   = "Allow"
        Action   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
        Resource = ["*"]
      },
    ]
  })
}

resource "aws_lambda_function" "sync" {
  function_name    = local.sync_name
  role             = aws_iam_role.sync.arn
  handler          = "index.handler"
  runtime          = var.lambda_runtime
  filename         = data.archive_file.sync.output_path
  source_code_hash = data.archive_file.sync.output_base64sha256
  timeout          = 30

  environment {
    variables = {
      PARAMETER_NAME = local.parameter_path
      KVS_ARN        = aws_cloudfront_key_value_store.this.arn
    }
  }

  tags = var.tags
}

resource "aws_cloudwatch_event_rule" "sync" {
  name                = local.sync_name
  description         = "Sync ${var.name} rollout state into the CloudFront key value store"
  schedule_expression = var.sync_schedule
  tags                = var.tags
}

resource "aws_cloudwatch_event_target" "sync" {
  rule = aws_cloudwatch_event_rule.sync.name
  arn  = aws_lambda_function.sync.arn
}

resource "aws_lambda_permission" "sync" {
  statement_id  = "AllowEventBridgeInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.sync.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.sync.arn
}

# Sync as soon as the parameter changes; the schedule above is the reconciler.
resource "aws_cloudwatch_event_rule" "on_change" {
  name        = "${local.sync_name}-on-change"
  description = "Sync ${var.name} rollout state when its parameter changes"
  event_pattern = jsonencode({
    source      = ["aws.ssm"]
    detail-type = ["Parameter Store Change"]
    detail = {
      name      = [local.parameter_path]
      operation = ["Create", "Update"]
    }
  })
  tags = var.tags
}

resource "aws_cloudwatch_event_target" "on_change" {
  rule = aws_cloudwatch_event_rule.on_change.name
  arn  = aws_lambda_function.sync.arn
}

resource "aws_lambda_permission" "on_change" {
  statement_id  = "AllowEventBridgeInvokeOnChange"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.sync.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.on_change.arn
}
