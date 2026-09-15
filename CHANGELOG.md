# Changelog

All notable changes to this module are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- Require AWS provider 5.43 or later and test that minimum in CI.

- Retry initial IAM propagation failures while seeding the rollout store.

- Use CloudFront-compatible await syntax and share deterministic request-ID
  routing between request and response functions so new viewers receive pins.
- Initialize KVS before returning function associations to a distribution.

- Package the AWS CRT signing dependency required by the Python sync Lambda.
- Reject invalid rollout updates and retry conflicting KVS writes with fresh state.
- Clear pinning when rollout state specifies a null cookie, allowing emergency
  rollback to move viewers pinned to an unhealthy deployment.
- Preserve fractional canary weights in the viewer-request function.

- Use the KeyValueStore data API's actual method and parameter names in the sync
  Lambda, and grant its required UpdateKeys IAM permission.
- Add an offline SDK contract test and an opt-in AWS integration runner covering
  private origins, rollout propagation, caching, pinning, failures, and cleanup.

- Await CloudFront KeyValueStore reads before selecting an origin, so active
  deployment, canary weight, and pinning settings take effect. Rejected reads
  now use the existing fallback instead of causing unhandled rejections.
- Exercise request routing with asynchronous KeyValueStore mocks in local and
  CI tests, including promotions, canary boundaries, pins, and read failures.

## [0.1.0] - 2026-09-13

### Added

- The `cloudfront-edge-router`: a Parameter Store entry as the source of truth,
  a sync Lambda that projects it into CloudFront KeyValueStore, a viewer-request
  CloudFront Function that selects the deployment's VPC origin with
  `selectRequestOriginById` and stamps the deployment header, and a
  viewer-response function that sets the pin cookie.
- An EventBridge rule that runs the sync as soon as the rollout parameter
  changes; the schedule remains as a reconciler.

### Fixed

- Require AWS provider 5.43 or later and test that minimum in CI.

- Retry initial IAM propagation failures while seeding the rollout store.

- Use CloudFront-compatible await syntax and share deterministic request-ID
  routing between request and response functions so new viewers receive pins.
- Initialize KVS before returning function associations to a distribution.

- Package the AWS CRT signing dependency required by the Python sync Lambda.
- Reject invalid rollout updates and retry conflicting KVS writes with fresh state.
- Clear pinning when rollout state specifies a null cookie, allowing emergency
  rollback to move viewers pinned to an unhealthy deployment.
- Preserve fractional canary weights in the viewer-request function.

- Use the KeyValueStore data API's actual method and parameter names in the sync
  Lambda, and grant its required UpdateKeys IAM permission.
- Add an offline SDK contract test and an opt-in AWS integration runner covering
  private origins, rollout propagation, caching, pinning, failures, and cleanup.

- The rollout parameter's value is ignored after creation, so a promotion made
  by updating the parameter survives the next `terraform apply`.

[Unreleased]: https://github.com/pomo-studio/terraform-aws-cloudfront-edge-router/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/pomo-studio/terraform-aws-cloudfront-edge-router/releases/tag/v0.1.0
