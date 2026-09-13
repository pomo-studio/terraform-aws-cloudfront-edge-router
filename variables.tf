variable "name" {
  description = "Name of the router and its supporting resources"
  type        = string
}

variable "deployments" {
  description = "Deployment names the router chooses between, such as blue and green"
  type        = set(string)
}

variable "active_deployment" {
  description = "Deployment that receives traffic when weight is zero"
  type        = string
}

variable "weight" {
  description = "Percentage of requests sent to the non-active deployment during a canary"
  type        = number
  default     = 0

  validation {
    condition     = var.weight >= 0 && var.weight <= 100
    error_message = "weight must be between 0 and 100."
  }
}

variable "pin_cookie" {
  description = "Cookie the function reads to keep a viewer on a specific deployment"
  type        = string
  default     = null
}

variable "parameter_path" {
  description = "Parameter Store path holding the rollout state. Defaults to /<name>/routing."
  type        = string
  default     = null
}

variable "tags" {
  description = "Tags applied to all resources"
  type        = map(string)
  default     = {}
}
