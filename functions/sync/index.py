import json
import math
import os
import re

import boto3

ssm = boto3.client("ssm")
kvs = boto3.client("cloudfront-keyvaluestore")

PARAMETER_NAME = os.environ["PARAMETER_NAME"]
KVS_ARN = os.environ["KVS_ARN"]
DEPLOYMENTS = json.loads(os.environ["DEPLOYMENTS"])


def rollout_values(state):
    active = state.get("active")
    weight = state.get("weight")
    pin = state.get("pin_cookie")
    if active not in DEPLOYMENTS:
        raise ValueError("active must name a configured deployment")
    if (isinstance(weight, bool) or not isinstance(weight, (int, float))
            or not math.isfinite(weight) or not 0 <= weight <= 100):
        raise ValueError("weight must be a finite number between 0 and 100")
    if pin is not None and (not isinstance(pin, str) or
            not re.fullmatch(r"[!#$%&'*+.^_~0-9A-Za-z|-]+", pin)):
        raise ValueError("pin_cookie must be a valid cookie name or null")
    return {"active": active, "weight": str(weight),
            "pin_cookie": pin if pin is not None else "null"}


def handler(event, context):
    # Re-read the source of truth on a write conflict so an older invocation
    # cannot overwrite a newer promotion using its stale state.
    for attempt in range(3):
        etag = kvs.describe_key_value_store(KvsARN=KVS_ARN)["ETag"]
        parameter = ssm.get_parameter(Name=PARAMETER_NAME)["Parameter"]["Value"]
        values = rollout_values(json.loads(parameter))
        try:
            kvs.update_keys(
                KvsARN=KVS_ARN,
                IfMatch=etag,
                Puts=[{"Key": key, "Value": value} for key, value in values.items()],
            )
            return {"updated": values}
        except kvs.exceptions.ConflictException:
            if attempt == 2:
                raise