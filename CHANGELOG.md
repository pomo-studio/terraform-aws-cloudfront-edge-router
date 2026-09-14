# Changelog

All notable changes to this module are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

- The rollout parameter's value is ignored after creation, so a promotion made
  by updating the parameter survives the next `terraform apply`.

[Unreleased]: https://github.com/pomo-studio/terraform-aws-cloudfront-edge-router/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/pomo-studio/terraform-aws-cloudfront-edge-router/releases/tag/v0.1.0
