# terraform-aws-cloudfront-edge-router

[![Terraform Validation](https://github.com/pomo-studio/terraform-aws-cloudfront-edge-router/actions/workflows/terraform.yml/badge.svg)](https://github.com/pomo-studio/terraform-aws-cloudfront-edge-router/actions/workflows/terraform.yml)
[![Terraform Registry](https://img.shields.io/badge/terraform-registry-844FBA?logo=terraform)](https://registry.terraform.io/modules/pomo-studio/cloudfront-edge-router/aws)

[Changelog](CHANGELOG.md)

Pick the deployment at the edge. A CloudFront Function reads rollout state from a KeyValueStore on every request, selects the deployment's VPC origin, and stamps the choice so the cache stays per-deployment. A sync Lambda keeps the store current from Parameter Store.

## When to use it

Reach for this module when two deployments sit behind one distribution and you want to shift traffic between them without a `terraform apply`. It owns the routing function, its key-value store, the sync Lambda, and the Parameter Store entry that is the source of truth.

Use a different tool when there is only one origin, or when CloudFront Continuous Deployment is the axis you want: that promotes a whole configuration, while this module shifts requests.

## Quickstart

```hcl
module "edge_router" {
  source  = "pomo-studio/cloudfront-edge-router/aws"
  version = "~> 0.1"

  name = "orders"

  deployments       = ["blue", "green"]
  active_deployment = "blue"
  weight            = 0

  tags = { Environment = "production" }
}
```

## What it creates

| Resource | Count |
|----------|-------|
| Parameter Store entry (source of truth) | 1 |
| CloudFront KeyValueStore | 1 |
| Viewer-request CloudFront Function | 1 |
| Viewer-response CloudFront Function | 1 |
| Sync Lambda and its role | 1 |
| EventBridge rules (on change, and a reconciling schedule) | 2 |

## Design decisions

- **CloudFront Functions, not Lambda@Edge.** VPC origins do not support Lambda@Edge origin request or response triggers. Origin selection runs in a CloudFront Function on the JavaScript runtime 2.0, which can select a VPC origin by ID with `selectRequestOriginById`.
- **Parameter Store is the source of truth.** CloudFront Functions cannot reach the network, so they cannot read Parameter Store. A sync Lambda copies the rollout state into a KeyValueStore, and the function reads it per request.
- **Why not write the KeyValueStore directly?** It is possible, but the rollout state is three keys, and a promotion changes more than one of them. The sync Lambda writes them in a single `UpdateKeys` call, so the function never reads a half-applied state; writing keys one at a time from a pipeline would. Parameter Store also gives the state a history, an IAM path, and a change event, none of which the store has on its own.
- **Rollout state is data, not infrastructure.** Active colour, weight, and pin cookie live in one Parameter Store entry, so promotion is a parameter update rather than a plan. Terraform seeds the value and then ignores it, so a later apply does not put the seed back.
- **The cache key carries the deployment.** Selecting an origin does not change the cache key, so the function stamps the deployment header and the distribution keys its cache on it. The module returns the header name and the function associations for that wiring.
- **Near-instant, not atomic.** A parameter change triggers the sync through EventBridge, and a schedule reconciles in case an event is missed. The store then propagates to the edge on its own clock; the switch is quick but not transactional.
- **Pin by cookie.** A viewer-response function sets a cookie the viewer-request function reads, so one viewer can stay on a deployment without opening the switch.

## Operating a rollout

Attach both function associations to the distribution and include the returned
deployment header in its cache key. Each deployment name must match an origin ID.
The [live integration fixture](tests/live/) shows this wiring with private origins.

Update the JSON value at the returned Parameter Store path to change traffic.
For example, active blue with weight 25 sends about 25% of unpinned requests to
green. Weight 0 sends unpinned requests to the active deployment. Weight 100 sends
them to the other deployment. Percentages describe new routing decisions;
existing cookie pins take precedence.

A normal rollback sets the healthy deployment active and weight to 0. For an
emergency rollback that also moves pinned viewers, set pin_cookie to JSON null
in the same update. The sync writes an explicit disabled-pin value to KVS.
Use the original cookie name when restoring pinning after the incident.

The sync rejects unknown deployments, invalid weights, and invalid cookie names
without changing KVS. It retries conflicting writes using freshly read rollout
state. Parameter changes and edge propagation are asynchronous; confirm actual
traffic before completing a promotion. There is no health-based automatic
failover. If rollout keys cannot be read, routing falls back to the first
deployment in alphabetical order with zero canary weight and no pinning.
Keep that fallback origin available.

The module initializes KVS before returning its function associations. Both edge
functions use the same request ID to reproduce the routing sample. They read
rollout state independently, so a request spanning a promotion can receive a pin
reflecting the newer state. Promotions are not transactional across a response.

The sync Lambda includes its required AWS CRT signing layer. No local Python
build is required to deploy the module. The [acceptance runner](tests/live/)
checks real requests, state propagation, rollback, cache separation, and cleanup.

## Examples

- [Basic](examples/basic/): two deployments, active blue, no weight.

## Reference

<details>
<summary>Reference</summary>

<!-- BEGIN_TF_DOCS -->
## Requirements

| Name | Version |
|------|---------|
| <a name="requirement_terraform"></a> [terraform](#requirement\_terraform) | >= 1.9.0 |
| <a name="requirement_archive"></a> [archive](#requirement\_archive) | >= 2.4 |
| <a name="requirement_aws"></a> [aws](#requirement\_aws) | >= 5.43, < 7.0 |

## Providers

| Name | Version |
|------|---------|
| <a name="provider_archive"></a> [archive](#provider\_archive) | >= 2.4 |
| <a name="provider_aws"></a> [aws](#provider\_aws) | >= 5.43, < 7.0 |

## Modules

No modules.

## Resources

| Name | Type |
|------|------|
| [aws_cloudfront_function.viewer_request](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudfront_function) | resource |
| [aws_cloudfront_function.viewer_response](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudfront_function) | resource |
| [aws_cloudfront_key_value_store.this](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudfront_key_value_store) | resource |
| [aws_cloudwatch_event_rule.on_change](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudwatch_event_rule) | resource |
| [aws_cloudwatch_event_rule.sync](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudwatch_event_rule) | resource |
| [aws_cloudwatch_event_target.on_change](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudwatch_event_target) | resource |
| [aws_cloudwatch_event_target.sync](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudwatch_event_target) | resource |
| [aws_iam_role.sync](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_role) | resource |
| [aws_iam_role_policy.sync](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_role_policy) | resource |
| [aws_lambda_function.sync](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/lambda_function) | resource |
| [aws_lambda_invocation.initialize](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/lambda_invocation) | resource |
| [aws_lambda_layer_version.signing](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/lambda_layer_version) | resource |
| [aws_lambda_permission.on_change](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/lambda_permission) | resource |
| [aws_lambda_permission.sync](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/lambda_permission) | resource |
| [aws_ssm_parameter.rollout](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ssm_parameter) | resource |
| [archive_file.sync](https://registry.terraform.io/providers/hashicorp/archive/latest/docs/data-sources/file) | data source |

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| <a name="input_active_deployment"></a> [active\_deployment](#input\_active\_deployment) | Deployment that receives traffic when weight is zero | `string` | n/a | yes |
| <a name="input_deployment_header"></a> [deployment\_header](#input\_deployment\_header) | Request header the router stamps with the chosen deployment, so the distribution can key its cache on it. Defaults to x-postmodern-deployment. | `string` | `null` | no |
| <a name="input_deployments"></a> [deployments](#input\_deployments) | Deployment names the router chooses between. Each must match an origin ID on the distribution it serves. | `set(string)` | n/a | yes |
| <a name="input_function_runtime"></a> [function\_runtime](#input\_function\_runtime) | CloudFront Functions runtime. Origin selection needs cloudfront-js-2.0. | `string` | `"cloudfront-js-2.0"` | no |
| <a name="input_lambda_runtime"></a> [lambda\_runtime](#input\_lambda\_runtime) | Runtime for the sync Lambda | `string` | `"python3.12"` | no |
| <a name="input_name"></a> [name](#input\_name) | Name of the router and its supporting resources | `string` | n/a | yes |
| <a name="input_parameter_path"></a> [parameter\_path](#input\_parameter\_path) | Parameter Store path holding the rollout state. Defaults to /<name>/rollout. | `string` | `null` | no |
| <a name="input_pin_cookie"></a> [pin\_cookie](#input\_pin\_cookie) | Cookie the router sets and reads to keep a viewer on one deployment. Defaults to <name>-deployment. | `string` | `null` | no |
| <a name="input_sync_schedule"></a> [sync\_schedule](#input\_sync\_schedule) | EventBridge schedule that syncs Parameter Store into the key value store | `string` | `"rate(1 minute)"` | no |
| <a name="input_tags"></a> [tags](#input\_tags) | Tags applied to all resources | `map(string)` | `{}` | no |
| <a name="input_weight"></a> [weight](#input\_weight) | Percentage of requests sent to the other deployment during a canary | `number` | `0` | no |

## Outputs

| Name | Description |
|------|-------------|
| <a name="output_deployment_header"></a> [deployment\_header](#output\_deployment\_header) | Request header the router stamps, for cloudfront-frontdoor's deployment\_header input |
| <a name="output_function_associations"></a> [function\_associations](#output\_function\_associations) | Associations to pass to cloudfront-frontdoor's function\_associations input |
| <a name="output_key_value_store_arn"></a> [key\_value\_store\_arn](#output\_key\_value\_store\_arn) | ARN of the KeyValueStore that holds the rollout state |
| <a name="output_parameter_name"></a> [parameter\_name](#output\_parameter\_name) | Parameter Store entry that is the source of truth |
| <a name="output_sync_function_name"></a> [sync\_function\_name](#output\_sync\_function\_name) | Name of the Lambda function that syncs Parameter Store into the KeyValueStore |
| <a name="output_viewer_request_function_arn"></a> [viewer\_request\_function\_arn](#output\_viewer\_request\_function\_arn) | ARN of the viewer-request function that selects the origin |
| <a name="output_viewer_response_function_arn"></a> [viewer\_response\_function\_arn](#output\_viewer\_response\_function\_arn) | ARN of the viewer-response function that sets the pin cookie |
<!-- END_TF_DOCS -->

</details>

## Support and license

Part of the [pomo-studio](https://github.com/pomo-studio) Terraform modules. Regenerate the reference with `terraform-docs` v0.20.0 (`terraform-docs .`); CI fails on drift.

See the [contribution guide](https://github.com/pomo-studio/.github/blob/main/CONTRIBUTING.md) and [security policy](https://github.com/pomo-studio/.github/blob/main/SECURITY.md).

MIT licensed. See [LICENSE](LICENSE).
