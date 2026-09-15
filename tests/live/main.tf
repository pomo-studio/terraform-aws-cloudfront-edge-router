terraform {
  required_version = ">= 1.9.0"
  required_providers {
    archive = {
      source  = "hashicorp/archive"
      version = ">= 2.4"
    }
    aws = {
      source  = "hashicorp/aws"
      version = ">= 6.0, < 7.0"
    }
  }
}
variable "name" {
  type = string
  validation {
    condition     = can(regex("^router-it-[a-z0-9-]{1,16}$", var.name))
    error_message = "Use a unique router-it- name, up to 26 characters."
  }
}
variable "expected_account" {
  type = string
}
provider "aws" {
  region              = "us-east-1"
  allowed_account_ids = [var.expected_account]
  default_tags {
    tags = {
      Purpose = "edge-router-integration"
      TestRun = var.name
    }
  }
}
data "aws_availability_zones" "available" {
  state            = "available"
  exclude_zone_ids = ["use1-az3"]
}
data "aws_ec2_managed_prefix_list" "cloudfront" {
  name = "com.amazonaws.global.cloudfront.origin-facing"
}
resource "aws_vpc" "test" {
  cidr_block           = "10.237.0.0/16"
  enable_dns_hostnames = true
}
resource "aws_internet_gateway" "test" {
  vpc_id = aws_vpc.test.id
}
resource "aws_subnet" "private" {
  count             = 2
  vpc_id            = aws_vpc.test.id
  cidr_block        = cidrsubnet(aws_vpc.test.cidr_block, 8, count.index)
  availability_zone = data.aws_availability_zones.available.names[count.index]
}
resource "aws_security_group" "origin" {
  name   = var.name
  vpc_id = aws_vpc.test.id
  ingress {
    protocol        = "tcp"
    from_port       = 80
    to_port         = 80
    prefix_list_ids = [data.aws_ec2_managed_prefix_list.cloudfront.id]
  }
}
resource "aws_lb" "origin" {
  for_each           = toset(["blue", "green"])
  name               = "${var.name}-${each.key}"
  internal           = true
  load_balancer_type = "application"
  subnets            = aws_subnet.private[*].id
  security_groups    = [aws_security_group.origin.id]
}
# Fixed responses make origin identity deterministic without app bootstrap or NAT.
resource "aws_lb_listener" "origin" {
  for_each          = aws_lb.origin
  load_balancer_arn = each.value.arn
  port              = 80
  protocol          = "HTTP"
  default_action {
    type = "fixed-response"
    fixed_response {
      content_type = "text/plain"
      message_body = each.key
      status_code  = "200"
    }
  }
}
module "origin" {
  for_each               = aws_lb.origin
  source                 = "pomo-studio/cloudfront-vpc-origin/aws"
  version                = "0.1.0"
  name                   = "${var.name}-${each.key}"
  origin_arn             = each.value.arn
  origin_protocol_policy = "http-only"
  depends_on             = [aws_internet_gateway.test, aws_lb_listener.origin]
}
resource "aws_cloudwatch_log_group" "sync" {
  name              = "/aws/lambda/${var.name}-edge-router-sync"
  retention_in_days = 1
}
module "router" {
  depends_on  = [aws_cloudwatch_log_group.sync]
  source      = "../.."
  name        = var.name
  deployments = ["blue", "green"]
  # Start on the non-default colour to expose missing initial sync.
  active_deployment = "green"
  weight            = 0
}
module "frontdoor" {
  source  = "pomo-studio/cloudfront-frontdoor/aws"
  version = "0.1.0"
  name    = var.name
  deployments = {
    for name, lb in aws_lb.origin : name => {
      domain_name   = lb.dns_name
      vpc_origin_id = module.origin[name].id
    }
  }
  function_associations = module.router.function_associations
  deployment_header     = module.router.deployment_header
  enable_logging        = false
  price_class           = "PriceClass_100"
}
output "test" {
  value = {
    name               = var.name
    url                = "https://${module.frontdoor.domain_name}"
    distribution_id    = module.frontdoor.distribution_id
    parameter_name     = module.router.parameter_name
    kvs_arn            = module.router.key_value_store_arn
    sync_function_name = module.router.sync_function_name
    cookie             = "${var.name}-deployment"
    green_listener     = aws_lb_listener.origin["green"].arn
    probes = [
      { region = "us-west-2", name = aws_lambda_function.probe_west.function_name },
      { region = "eu-west-1", name = aws_lambda_function.probe_europe.function_name },
    ]
  }
}