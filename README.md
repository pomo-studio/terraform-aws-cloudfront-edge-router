# terraform-aws-cloudfront-edge-router

[![Terraform Validation](https://github.com/pomo-studio/terraform-aws-cloudfront-edge-router/actions/workflows/terraform.yml/badge.svg)](https://github.com/pomo-studio/terraform-aws-cloudfront-edge-router/actions/workflows/terraform.yml)
[![Terraform Registry](https://img.shields.io/badge/terraform-registry-844FBA?logo=terraform)](https://registry.terraform.io/modules/pomo-studio/cloudfront-edge-router/aws)

[Changelog](CHANGELOG.md)

Pick the deployment at the edge. A CloudFront Function reads rollout state from a KeyValueStore on every request and sends the viewer to the active colour, with optional weight and cookie pinning. A sync Lambda keeps the store current from Parameter Store.

> **Status:** work in progress. The interface is being designed against the [Internet Ingress](https://pomo.dev/blueprints) blueprint and should be treated as unstable until the first tagged release.

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

## Design decisions

- **Parameter Store is the source of truth.** CloudFront Functions cannot reach the network, so they cannot read Parameter Store directly. A sync Lambda copies the rollout state into a KeyValueStore, and the function reads it per request.
- **Rollout state is data, not infrastructure.** Active colour, weight, and pin cookie live in one Parameter Store entry, so promotion is a parameter update rather than a plan.
- **Near-instant, not atomic.** A weight change propagates with the store; it is not a transactional switch. Cache keys must include the colour so promoted responses are not served from the previous deployment's cache.
- **Pin by cookie.** Sticky testing is a cookie the function recognises, so a single viewer can stay on a non-active colour without opening the switch.

## Examples

- [Basic](examples/basic/): two deployments, active blue, no weight.

## Reference

<details>
<summary>Reference</summary>

<!-- BEGIN_TF_DOCS -->
## Requirements

| Name | Version |
|------|---------|
| <a name="requirement_terraform"></a> [terraform](#requirement\_terraform) | >= 1.5.0 |
| <a name="requirement_aws"></a> [aws](#requirement\_aws) | >= 5.0, < 7.0 |

## Providers

No providers.

## Modules

No modules.

## Resources

No resources.

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| <a name="input_active_deployment"></a> [active\_deployment](#input\_active\_deployment) | Deployment that receives traffic when weight is zero | `string` | n/a | yes |
| <a name="input_deployments"></a> [deployments](#input\_deployments) | Deployment names the router chooses between, such as blue and green | `set(string)` | n/a | yes |
| <a name="input_name"></a> [name](#input\_name) | Name of the router and its supporting resources | `string` | n/a | yes |
| <a name="input_parameter_path"></a> [parameter\_path](#input\_parameter\_path) | Parameter Store path holding the rollout state. Defaults to /<name>/routing. | `string` | `null` | no |
| <a name="input_pin_cookie"></a> [pin\_cookie](#input\_pin\_cookie) | Cookie the function reads to keep a viewer on a specific deployment | `string` | `null` | no |
| <a name="input_tags"></a> [tags](#input\_tags) | Tags applied to all resources | `map(string)` | `{}` | no |
| <a name="input_weight"></a> [weight](#input\_weight) | Percentage of requests sent to the non-active deployment during a canary | `number` | `0` | no |

## Outputs

| Name | Description |
|------|-------------|
| <a name="output_function_arn"></a> [function\_arn](#output\_function\_arn) | ARN of the CloudFront Function that routes requests |
| <a name="output_key_value_store_arn"></a> [key\_value\_store\_arn](#output\_key\_value\_store\_arn) | ARN of the CloudFront KeyValueStore holding rollout state |
| <a name="output_parameter_name"></a> [parameter\_name](#output\_parameter\_name) | Name of the Parameter Store entry that is the source of truth |
| <a name="output_sync_lambda_arn"></a> [sync\_lambda\_arn](#output\_sync\_lambda\_arn) | ARN of the Lambda function that syncs Parameter Store into the KeyValueStore |
<!-- END_TF_DOCS -->

</details>

## Support and license

Part of the [pomo-studio](https://github.com/pomo-studio) Terraform modules, run in production by [postmodern.](https://pomo.studio). Regenerate the reference with `terraform-docs` v0.20.0 (`terraform-docs .`); CI fails on drift.

See the [contribution guide](https://github.com/pomo-studio/.github/blob/main/CONTRIBUTING.md) and [security policy](https://github.com/pomo-studio/.github/blob/main/SECURITY.md).

MIT licensed. See [LICENSE](LICENSE).
