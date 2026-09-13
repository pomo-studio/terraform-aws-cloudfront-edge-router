output "function_associations" {
  description = "Associations to pass to cloudfront-frontdoor's function_associations input"
  value = [
    {
      event_type   = "viewer-request"
      function_arn = aws_cloudfront_function.viewer_request.arn
    },
    {
      event_type   = "viewer-response"
      function_arn = aws_cloudfront_function.viewer_response.arn
    },
  ]
}

output "deployment_header" {
  description = "Request header the router stamps, for cloudfront-frontdoor's deployment_header input"
  value       = local.deployment_header
}

output "viewer_request_function_arn" {
  description = "ARN of the viewer-request function that selects the origin"
  value       = aws_cloudfront_function.viewer_request.arn
}

output "viewer_response_function_arn" {
  description = "ARN of the viewer-response function that sets the pin cookie"
  value       = aws_cloudfront_function.viewer_response.arn
}

output "key_value_store_arn" {
  description = "ARN of the KeyValueStore that holds the rollout state"
  value       = aws_cloudfront_key_value_store.this.arn
}

output "parameter_name" {
  description = "Parameter Store entry that is the source of truth"
  value       = aws_ssm_parameter.rollout.name
}

output "sync_function_name" {
  description = "Name of the Lambda function that syncs Parameter Store into the KeyValueStore"
  value       = aws_lambda_function.sync.function_name
}
