plugin "terraform" {
  enabled = true
  preset  = "recommended"
}

plugin "aws" {
  enabled = true
  version = "0.48.0"
  source  = "github.com/terraform-linters/tflint-ruleset-aws"
}

# Inputs are declared ahead of the resources that consume them while the module
# interface is settled. Re-enable once those resources land.
rule "terraform_unused_declarations" {
  enabled = false
}
