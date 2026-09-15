"""Exercise SigV4A signing with the exact layer bytes shipped to customers."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

class SigningLayerTest(unittest.TestCase):
    def test_packaged_layer_can_sign_a_kvs_request(self):
        archive = Path(__file__).resolve().parents[1] / "functions/signing/awscrt.zip"
        code = """
import boto3
import awscrt
assert awscrt.__version__ == '0.36.3'
client = boto3.client('cloudfront-keyvaluestore', region_name='us-east-1',
    aws_access_key_id='testing', aws_secret_access_key='testing')
class Signed(Exception):
    pass
def before_send(request, **kwargs):
    authorization = request.headers['Authorization']
    if isinstance(authorization, bytes):
        authorization = authorization.decode()
    assert authorization.startswith('AWS4-ECDSA-P256-SHA256 '), authorization
    raise Signed()
client.meta.events.register('before-send.cloudfront-keyvaluestore.DescribeKeyValueStore', before_send)
try:
    client.describe_key_value_store(KvsARN='arn:aws:cloudfront::123456789012:key-value-store/12345678-1234-1234-1234-123456789012')
except Signed:
    print('Packaged CRT signed the request; no network request sent')
else:
    raise AssertionError('Signing hook was not reached')
"""
        with tempfile.TemporaryDirectory() as temp:
            with zipfile.ZipFile(archive) as source:
                source.extractall(temp)
            env = dict(os.environ, PYTHONPATH=str(Path(temp) / "python"))
            result = subprocess.run([sys.executable, "-c", code], env=env,
                                    capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

if __name__ == "__main__":
    unittest.main()