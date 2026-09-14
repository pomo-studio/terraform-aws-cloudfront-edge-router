# Edge router basics

Route requests between two deployments with CloudFront Functions and a key value store.

## What it creates

- An SSM parameter with the rollout state: active deployment, weight, and pin cookie.
- A CloudFront key value store that holds the synced state.
- Two CloudFront Functions. `viewer-request` picks the origin, `viewer-response` sets the pin cookie.
- A Lambda that syncs the parameter into the key value store, with its IAM role and policy.
- EventBridge rules on a schedule and on parameter change to run the sync.

## Before you start

- Provider `hashicorp/aws` with credentials for the target account.
- Uses a local source, `../../`.
- No resources need to exist first. The deployments input is just a list of names here.

## Run it

```bash
terraform init
terraform plan
terraform apply
```

## Clean up

```bash
terraform destroy
```
