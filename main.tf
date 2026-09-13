# The edge router is being designed against the Internet Ingress blueprint.
# This module will create:
#
#   - an aws_ssm_parameter holding the rollout state (active deployment,
#     weight, optional pin cookie), the source of truth for promotion
#   - an aws_lambda_function that reads the parameter and writes to the store
#   - an aws_cloudfront_key_value_store that the function serves from
#   - an aws_cloudfront_function that reads the store on each request and
#     selects the deployment, honouring the pin cookie and weight
#
# CloudFront Functions cannot reach the network, which is why a Lambda syncs the
# parameter into the key-value store rather than the function reading SSM.
