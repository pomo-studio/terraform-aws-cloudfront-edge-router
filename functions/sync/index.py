import json
import math
import os
import re
import time

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
    initializing = event.get("reason") == "initialize"
    attempts = 10 if initializing else 3
    for attempt in range(attempts):
        try:
            # Capture the version before reading SSM so a newer writer
            # invalidates this update rather than being overwritten.
            etag = kvs.describe_key_value_store(KvsARN=KVS_ARN)["ETag"]
            parameter = ssm.get_parameter(Name=PARAMETER_NAME)["Parameter"]["Value"]
            values = rollout_values(json.loads(parameter))
            kvs.update_keys(
                KvsARN=KVS_ARN,
                IfMatch=etag,
                Puts=[{"Key": key, "Value": value} for key, value in values.items()],
            )
            return {"updated": values}
        except kvs.exceptions.ConflictException:
            if attempt == attempts - 1:
                raise
        except (kvs.exceptions.AccessDeniedException, kvs.exceptions.ResourceNotFoundException):
            # The newly created role/store may not have propagated globally.
            # Only initialization tolerates this, and only for a bounded time.
            if not initializing or attempt == attempts - 1:
                raise
        time.sleep(min(2 ** attempt, 8))