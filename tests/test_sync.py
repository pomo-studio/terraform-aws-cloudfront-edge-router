"""Validate the sync Lambda against botocore's actual AWS API shapes, offline."""
import importlib.util
import json
import os
from pathlib import Path
import unittest
import sys
sys.dont_write_bytecode = True
from unittest.mock import patch
import boto3
from botocore.stub import Stubber

ARN = "arn:aws:cloudfront::123456789012:key-value-store/12345678-1234-1234-1234-123456789012"
PATH = "/acceptance/rollout"

class SyncTest(unittest.TestCase):
    def test_sync_uses_the_real_kvs_api_contract(self):
        clients = {name: boto3.client(name, region_name="us-east-1",
                   aws_access_key_id="testing", aws_secret_access_key="testing")
                   for name in ("ssm", "cloudfront-keyvaluestore")}
        spec = importlib.util.spec_from_file_location("sync_handler",
            Path(__file__).resolve().parents[1] / "functions/sync/index.py")
        handler = importlib.util.module_from_spec(spec)
        with patch.dict(os.environ, PARAMETER_NAME=PATH, KVS_ARN=ARN), \
             patch("boto3.client", side_effect=lambda name: clients[name]):
            spec.loader.exec_module(handler)
        state = {"active": "green", "weight": 25, "pin_cookie": "deployment"}
        puts = [{"Key": key, "Value": str(value)} for key, value in state.items()]
        with Stubber(clients["ssm"]) as ssm, Stubber(clients["cloudfront-keyvaluestore"]) as kvs:
            ssm.add_response("get_parameter", {"Parameter": {"Value": json.dumps(state)}},
                             {"Name": PATH})
            from datetime import datetime, timezone
            kvs.add_response("describe_key_value_store",
                {"ETag": "version-1", "ItemCount": 0, "TotalSizeInBytes": 0,
                 "KvsARN": ARN, "Created": datetime.now(timezone.utc)},
                {"KvsARN": ARN})
            kvs.add_response("update_keys",
                {"ETag": "version-2", "ItemCount": 3, "TotalSizeInBytes": 50},
                {"KvsARN": ARN, "IfMatch": "version-1", "Puts": puts})
            self.assertEqual(handler.handler({}, None), {"updated": {
                "active": "green", "weight": "25", "pin_cookie": "deployment"}})
            ssm.assert_no_pending_responses()
            kvs.assert_no_pending_responses()

if __name__ == "__main__":
    unittest.main()