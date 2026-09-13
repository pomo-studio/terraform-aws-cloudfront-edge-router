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
