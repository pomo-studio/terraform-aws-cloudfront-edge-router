# Blue/green validation for v0.1.1

The release candidate passed its live routing and recovery checks on AWS on
September 15, 2026. All 32 test resources were destroyed and Terraform state was empty.

The test deployed two private ALB origins with distinct blue and green responses,
a CloudFront distribution, the router, and temporary probes in Oregon and Ireland.
Requests reached JFK50-P14, HIO52-P3, and DUB56-P1. At least 4,492 recorded requests
covered the checks below, including traffic during propagation.

## Candidate and environment

- Clean candidate: ed9c1771f9e88b14d35331d6a046c4485d55ed89.
- Terraform 1.14.6, AWS provider 6.64.0, archive provider 2.8.1.
- Python 3.12 on x86_64, bundled AWS CRT 0.36.3, cloudfront-js-2.0.
- Published companion modules: cloudfront-frontdoor 0.1.0 and
  cloudfront-vpc-origin 0.1.0.
- Later release edits add runtime input guards, an explicit fixture provider
  requirement, and documentation. The deployed runtime files are unchanged.

The [sanitized result](validation-v0.1.1-candidate.json) records observations and
versions. Raw Terraform plans, AWS identity, resource addresses, and logs remain
outside the public repository.

## Observed results

| Check | Result |
| --- | --- |
| Fresh deployment | Initial green response; both explicit pins work |
| New viewer | Green pin matches green response |
| Promotion | All three locations converge to blue; existing green pins persist |
| Invalid pin | Ignored; request follows the active rollout |
| Cache isolation | 12 alternating blue/green requests at one URL; 10 cache hits, all correct |
| 25% canary | Final consecutive batches: 40/210 and 52/210 green; pins match every response |
| 100% canary | All locations converge to green; another 100 requests succeed after a 45-second hold |
| Normal rollback | Unpinned traffic returns to blue; existing green pins persist |
| Failed green origin | Green pins see the injected 503; unpinned blue remains healthy |
| Emergency rollback | Setting pin_cookie to JSON null moves green-pinned requests to healthy blue |
| Origin recovery | Green pins serve green again after restoring the origin and pinning |
| Missed event | Scheduled reconciliation updates KVS with the change-event rule disabled |
| Missing settings | With both triggers paused and keys deleted, requests fall back to blue |
| Restored settings | Routing and pinning recover at all three locations |
| Terraform reapply | Zero changes; operational rollout state is preserved |

## Propagation and operating requirements

The normal parameter-to-KVS updates took roughly 0.5 to 0.9 seconds. The deliberately
missed event required about 50 seconds for the scheduled reconciler. Those timings
do not include propagation to edge locations.

Traffic acceptance required two consecutive all-correct 60-request batches across
three locations, with at least 45 seconds of observation. The measured acceptance
times after KVS synchronization ranged from 57 to 83 seconds. These are observations
from this run, not global propagation guarantees or fixed rollout sleep durations.

Keep both origins available during changes. Confirm traffic before retiring an
origin. Normal rollback preserves existing cookie pins; emergency rollback must
disable pinning to evacuate those viewers. There is no automatic health failover.

These checks validate the documented routing workflow against private origins.
They do not establish application correctness, load capacity, every edge location,
or a customer's cache policy. The test uses fixed ALB responses to isolate routing.
The [runner](../tests/live/) makes these checks repeatable.

## Automated checks

CI passes 20 JavaScript routing tests, six Python API/signing tests, and nine
Terraform tests with both AWS provider 5.43.0 and the latest provider. It also
checks formatting, lint, documentation generation, and example validation.

## Published package

A fresh Registry-package deployment is performed after publication. Its evidence
will be attached to the GitHub release; candidate evidence alone does not establish
that a downloaded version was deployed successfully.
