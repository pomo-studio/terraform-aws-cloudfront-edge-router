terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0, < 7.0"
    }
  }
}

module "edge_router" {
  source = "../../"

  name = "orders"

  deployments       = ["blue", "green"]
  active_deployment = "blue"
  weight            = 0

  tags = {
    Environment = "production"
  }
}
