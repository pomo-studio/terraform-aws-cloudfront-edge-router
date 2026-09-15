import json
import os

import boto3

ssm = boto3.client("ssm")
kvs = boto3.client("cloudfront-keyvaluestore")

PARAMETER_NAME = os.environ["PARAMETER_NAME"]
KVS_ARN = os.environ["KVS_ARN"]


def handler(event, context):
    # Parameter Store is the source of truth. CloudFront Functions cannot read
    # it, so copy the current rollout state into the key value store they can.
    parameter = ssm.get_parameter(Name=PARAMETER_NAME)["Parameter"]["Value"]
    state = json.loads(parameter)

    puts = [
        {"Key": key, "Value": str(value)}
        for key, value in state.items()
        if value is not None
    ]

    etag = kvs.describe_key_value_store(KvsARN=KVS_ARN)["ETag"]
    kvs.update_keys(
        KvsARN=KVS_ARN,
        IfMatch=etag,
        Puts=puts,
    )

    return {"updated": {item["Key"]: item["Value"] for item in puts}}
