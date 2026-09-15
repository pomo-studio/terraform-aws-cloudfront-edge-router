# Live blue/green validation

This opt-in test creates a disposable VPC, two private Application Load Balancers
with distinct fixed responses, two CloudFront VPC origins, a distribution, and the
router's supporting resources. It incurs AWS charges. It uses no production
applications, domains, certificates, or existing networking.

The router comes from the current checkout. The origin and frontdoor modules
come from their published Registry version 0.1.0. A passing candidate run does
not prove an older published router version works.

## Run

Requires Terraform >= 1.9, Python >= 3.10, AWS CLI v2, and credentials authorized
to create and delete the fixture's networking, ELB, IAM, Lambda, SSM, EventBridge,
and CloudFront resources. Run from this repository:

    python3 tests/live/run.py       --profile YOUR_SANDBOX_PROFILE       --expected-account YOUR_SANDBOX_ACCOUNT_ID

The runner checks the account, rejects populated fixture state and an initial
plan that changes existing resources, applies the saved plan, exercises real
HTTPS requests, and destroys resources in a finally block. Do not run two
instances concurrently: they share the fixture's local Terraform state.

Allow time for AWS to deploy and delete CloudFront resources. Progress is printed.
Results, identity, revision, source diff, request observations, propagation times,
Terraform logs, and cleanup status are saved under tests/live/results/RUN_NAME.
The directory is ignored by Git because plans and logs contain account details.

If interrupted forcibly or cleanup fails, inspect the saved output and destroy
the same fixture with the same profile and variables:

    cd tests/live
    AWS_PROFILE=YOUR_SANDBOX_PROFILE terraform destroy       -var=name=router-it-RUN_ID       -var=expected_account=YOUR_SANDBOX_ACCOUNT_ID

Do not delete the state before cleanup completes.

## What it checks

- A new deployment starting on green, rather than the alphabetically first origin.
- Parameter Store changes reaching KVS and actual edge traffic.
- Pin creation, valid and invalid pins, and pins surviving promotion and rollback.
- Blue and green serving distinct bodies at the same cached URL, with cache hits.
- A 25% canary across 200 unpinned requests, with broad statistical bounds.
- 100% canary, promotion, and rollback.
- A green origin returning 503 while blue continues serving; recovery afterward.
- Scheduled reconciliation with the parameter-change event rule disabled.
- Missing KVS settings, fallback behavior, and recovery.
- A later Terraform apply preserving the operational rollout state.
- Destruction leaving no resources in Terraform state.

Pins currently take precedence over rollout weight and active deployment.
Rollback therefore moves unpinned traffic; it does not evacuate pinned users from
an unhealthy deployment. The module does not implement automatic origin failover.
The test records those behaviors rather than asserting capabilities it lacks.

This is an integration acceptance test, not a load test, a global propagation
guarantee, or validation of a customer's application cache policy. Fixed ALB
responses establish origin selection without introducing application bootstrapping.

## Release evidence

Run on a committed candidate and retain the result JSON and logs. After releasing,
repeat with a temporary router_override.tf in this directory containing the
published source and exact version:

    module "router" {
      source  = "pomo-studio/cloudfront-edge-router/aws"
      version = "EXACT_RELEASE_VERSION"
    }

Terraform override files replace the local module source. Reinitialize and rerun.
Remove the override after the release check. Record the exact version alongside
the evidence; successful local-checkout results alone are not release evidence.
