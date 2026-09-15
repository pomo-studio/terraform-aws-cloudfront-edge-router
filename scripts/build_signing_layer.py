"""Repack the pinned AWS CRT wheel as a reproducible Lambda layer."""
import hashlib
from pathlib import Path
import sys
import zipfile

wheel = Path(sys.argv[1])
root = Path(__file__).resolve().parents[1]
output = root / "functions/signing/awscrt.zip"
with zipfile.ZipFile(wheel) as source, zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as dest:
    for name in sorted(source.namelist()):
        if name.endswith("/"):
            continue
        info = zipfile.ZipInfo("python/" + name, (2020, 1, 1, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o644 << 16
        dest.writestr(info, source.read(name))
print("wheel SHA256:", hashlib.sha256(wheel.read_bytes()).hexdigest())
print("layer SHA256:", hashlib.sha256(output.read_bytes()).hexdigest())