# Offline plan tests for terraform-aws-cloudfront-edge-router.
#
# mock_provider keeps these running with no AWS credentials, so they gate every
# pull request. They pin the contract: the rollout parameter, the functions and
# their store association, and the input validation. The live acceptance
# workflow proves the same configuration on AWS.

mock_provider "aws" {
  mock_resource "aws_iam_role" {
    defaults = {
      arn = "arn:aws:iam::123456789012:role/acceptance-edge-router-sync"
    }
  }

  mock_resource "aws_ssm_parameter" {
    defaults = {
      arn = "arn:aws:ssm:us-east-1:123456789012:parameter/acceptance/rollout"
    }
  }

  mock_resource "aws_cloudfront_key_value_store" {
    defaults = {
      arn = "arn:aws:cloudfront::123456789012:key-value-store/acceptance"
    }
  }

  mock_resource "aws_cloudfront_function" {
    defaults = {
      arn = "arn:aws:cloudfront::123456789012:function/acceptance"
    }
  }

  mock_resource "aws_lambda_function" {
    defaults = {
      arn = "arn:aws:lambda:us-east-1:123456789012:function:acceptance-edge-router-sync"
    }
  }

  mock_resource "aws_cloudwatch_event_rule" {
    defaults = {
      arn = "arn:aws:events:us-east-1:123456789012:rule/acceptance-edge-router-sync"
    }
  }
}

variables {
  name              = "acceptance"
  deployments       = ["blue", "green"]
  active_deployment = "blue"
  weight            = 0
}

run "records_the_rollout_state" {
  command = apply

  assert {
    condition     = jsondecode(aws_ssm_parameter.rollout.value)["active"] == "blue"
    error_message = "The rollout parameter should record the active deployment."
  }

  assert {
    condition     = jsondecode(aws_ssm_parameter.rollout.value)["weight"] == 0
    error_message = "The rollout parameter should record the weight."
  }
}

run "associates_the_key_value_store" {
  command = apply

  assert {
    condition     = length(aws_cloudfront_function.viewer_request.key_value_store_associations) == 1
    error_message = "The viewer-request function should read the KeyValueStore."
  }
}

run "publishes_both_functions" {
  command = apply

  assert {
    condition     = aws_cloudfront_function.viewer_request.publish == true
    error_message = "The viewer-request function should be published."
  }

  assert {
    condition     = aws_cloudfront_function.viewer_response.publish == true
    error_message = "The viewer-response function should be published."
  }
}

run "syncs_on_parameter_change" {
  command = apply

  assert {
    condition     = contains(jsondecode(aws_cloudwatch_event_rule.on_change.event_pattern)["detail"]["name"], "/acceptance/rollout")
    error_message = "The on-change rule should match the rollout parameter by name."
  }

  assert {
    condition     = aws_cloudwatch_event_target.on_change.arn == aws_lambda_function.sync.arn
    error_message = "The on-change rule should target the sync Lambda."
  }
}

run "rejects_a_weight_over_100" {
  command = plan

  variables {
    weight = 150
  }

  expect_failures = [var.weight]
}
