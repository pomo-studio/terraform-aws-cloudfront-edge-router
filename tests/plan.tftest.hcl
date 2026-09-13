# Offline plan tests for terraform-aws-cloudfront-edge-router.
#
# The router is still being implemented, so these tests pin the input contract
# and the weight validation. They run with no AWS credentials; the live
# acceptance workflow is added once the resources land.

variables {
  name              = "acceptance"
  deployments       = ["blue", "green"]
  active_deployment = "blue"
}

run "plans_with_valid_input" {
  command = plan
}

run "rejects_a_weight_over_100" {
  command = plan

  variables {
    weight = 150
  }

  expect_failures = [var.weight]
}
