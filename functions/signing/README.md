# KeyValueStore signing dependency

The sync Lambda needs AWS CRT for SigV4A signing. AWS's Python 3.12 runtime
does not include it. The module ships this layer so deploying it needs no
local Python installation, package download, or external build step.

The archive contains the official awscrt 0.36.3 CPython 3.11+ ABI3 wheel for
manylinux2014 x86_64, including its upstream licenses and package metadata.

Source wheel SHA256:
3466b3a2dcc93e9977c65745a49dd92312a8e461a3ea3ce793f8476bb236db1e

Layer archive SHA256:
6708e17137ca0643092b85f790294916b96f7690bd7203dc6819aed7fd5a2b73

To rebuild from the repository root:

    python3 -m pip download --only-binary=:all: --platform manylinux2014_x86_64       --python-version 312 --implementation cp --abi abi3 --no-deps       awscrt==0.36.3 -d /tmp/edge-router-signing
    python3 scripts/build_signing_layer.py /tmp/edge-router-signing/awscrt-0.36.3-cp311-abi3-manylinux2014_x86_64.manylinux_2_17_x86_64.whl

Verify both hashes before committing an update. The build script sets stable
timestamps and ordering. Run the live acceptance test after dependency updates.
