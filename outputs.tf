output "function_arn" {
  description = "ARN of the CloudFront Function that routes requests"
  value       = null
}

output "key_value_store_arn" {
  description = "ARN of the CloudFront KeyValueStore holding rollout state"
  value       = null
}

output "sync_lambda_arn" {
  description = "ARN of the Lambda function that syncs Parameter Store into the KeyValueStore"
  value       = null
}

output "parameter_name" {
  description = "Name of the Parameter Store entry that is the source of truth"
  value       = null
}
