variable "name" {
  description = "Name of the router and its supporting resources"
  type        = string
}

variable "deployments" {
  description = "Deployment names the router chooses between. Each must match an origin ID on the distribution it serves."
  type        = set(string)
}

variable "active_deployment" {
  description = "Deployment that receives traffic when weight is zero"
  type        = string
}

variable "weight" {
  description = "Percentage of requests sent to the other deployment during a canary"
  type        = number
  default     = 0

  validation {
    condition     = var.weight >= 0 && var.weight <= 100
    error_message = "weight must be between 0 and 100."
  }
}

variable "pin_cookie" {
  description = "Cookie the router sets and reads to keep a viewer on one deployment. Defaults to <name>-deployment."
  type        = string
  default     = null
}

variable "deployment_header" {
  description = "Request header the router stamps with the chosen deployment, so the distribution can key its cache on it. Defaults to x-postmodern-deployment."
  type        = string
  default     = null
}

variable "parameter_path" {
  description = "Parameter Store path holding the rollout state. Defaults to /<name>/rollout."
  type        = string
  default     = null
}

variable "sync_schedule" {
  description = "EventBridge schedule that syncs Parameter Store into the key value store"
  type        = string
  default     = "rate(1 minute)"
}

variable "function_runtime" {
  description = "CloudFront Functions runtime. Origin selection needs cloudfront-js-2.0."
  type        = string
  default     = "cloudfront-js-2.0"
}

variable "lambda_runtime" {
  description = "Runtime for the sync Lambda"
  type        = string
  default     = "python3.12"
}

variable "tags" {
  description = "Tags applied to all resources"
  type        = map(string)
  default     = {}
}
