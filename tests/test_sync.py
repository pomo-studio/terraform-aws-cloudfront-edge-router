"""Validate the sync Lambda against botocore's AWS API shapes, offline."""
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import boto3
from botocore.stub import Stubber

sys.dont_write_bytecode = True
ARN = "arn:aws:cloudfront::123456789012:key-value-store/12345678-1234-1234-1234-123456789012"
PATH = "/acceptance/rollout"

class SyncTest(unittest.TestCase):
    def setUp(self):
        self.clients = {name: boto3.client(name, region_name="us-east-1",
            aws_access_key_id="testing", aws_secret_access_key="testing")
            for name in ("ssm", "cloudfront-keyvaluestore")}
        spec = importlib.util.spec_from_file_location("sync_handler",
            Path(__file__).resolve().parents[1] / "functions/sync/index.py")
        self.handler = importlib.util.module_from_spec(spec)
        with patch.dict(os.environ, PARAMETER_NAME=PATH, KVS_ARN=ARN,
                        DEPLOYMENTS=json.dumps(["blue", "green"])),              patch("boto3.client", side_effect=lambda name: self.clients[name]):
            spec.loader.exec_module(self.handler)
        sleeper = patch.object(self.handler.time, "sleep")
        sleeper.start()
        self.addCleanup(sleeper.stop)
        self.ssm = Stubber(self.clients["ssm"])
        self.kvs = Stubber(self.clients["cloudfront-keyvaluestore"])
        self.ssm.activate()
        self.kvs.activate()
        self.addCleanup(self.ssm.deactivate)
        self.addCleanup(self.kvs.deactivate)

    def queue_read(self, state, etag="version-1"):
        self.kvs.add_response("describe_key_value_store",
            {"ETag": etag, "ItemCount": 0, "TotalSizeInBytes": 0,
             "KvsARN": ARN, "Created": datetime.now(timezone.utc)}, {"KvsARN": ARN})
        self.ssm.add_response("get_parameter",
            {"Parameter": {"Value": json.dumps(state)}}, {"Name": PATH})

    def write_params(self, state, etag="version-1"):
        return {"KvsARN": ARN, "IfMatch": etag, "Puts": [
            {"Key": key, "Value": "null" if value is None else str(value)}
            for key, value in state.items()]}

    def queue_write(self, state, etag="version-1"):
        self.kvs.add_response("update_keys",
            {"ETag": "version-next", "ItemCount": 3, "TotalSizeInBytes": 50},
            self.write_params(state, etag))

    def test_sync_uses_the_real_kvs_api_contract(self):
        state = {"active": "green", "weight": 25, "pin_cookie": "deployment"}
        self.queue_read(state)
        self.queue_write(state)
        self.assertEqual(self.handler.handler({}, None), {"updated": {
            "active": "green", "weight": "25", "pin_cookie": "deployment"}})
        self.ssm.assert_no_pending_responses()
        self.kvs.assert_no_pending_responses()

    def test_null_pin_replaces_the_previous_value(self):
        state = {"active": "blue", "weight": 0, "pin_cookie": None}
        self.queue_read(state)
        self.queue_write(state)
        self.assertEqual(self.handler.handler({}, None)["updated"]["pin_cookie"], "null")
        self.kvs.assert_no_pending_responses()

    def test_invalid_states_are_rejected_before_writing(self):
        for changes in ({"active": "missing"}, {"weight": -1}, {"weight": 101},
                        {"weight": True}, {"weight": "25"}, {"weight": float("nan")},
                        {"pin_cookie": "bad;cookie"}, {"pin_cookie": ""}):
            state = {"active": "blue", "weight": 0, "pin_cookie": "deployment", **changes}
            with self.subTest(changes=changes):
                self.queue_read(state)
                with self.assertRaises(ValueError):
                    self.handler.handler({}, None)
        self.ssm.assert_no_pending_responses()
        self.kvs.assert_no_pending_responses()

    def test_initialization_waits_for_iam_propagation(self):
        state = {"active": "green", "weight": 0, "pin_cookie": "deployment"}
        self.kvs.add_client_error("describe_key_value_store", "AccessDeniedException",
            http_status_code=403, expected_params={"KvsARN": ARN})
        self.queue_read(state)
        self.queue_write(state)
        self.assertEqual(self.handler.handler({"reason": "initialize"}, None)["updated"]["active"], "green")
        self.handler.time.sleep.assert_called_once_with(1)
        self.kvs.assert_no_pending_responses()
    def test_conflict_rereads_the_latest_promotion(self):
        old = {"active": "blue", "weight": 25, "pin_cookie": "deployment"}
        new = {"active": "green", "weight": 0, "pin_cookie": "deployment"}
        self.queue_read(old)
        self.kvs.add_client_error("update_keys", "ConflictException",
            http_status_code=409, expected_params=self.write_params(old))
        self.queue_read(new, "version-2")
        self.queue_write(new, "version-2")
        self.assertEqual(self.handler.handler({}, None)["updated"]["active"], "green")
        self.ssm.assert_no_pending_responses()
        self.kvs.assert_no_pending_responses()

if __name__ == "__main__":
    unittest.main()