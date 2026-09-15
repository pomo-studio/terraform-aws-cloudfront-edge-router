"""Make synthetic requests only to this fixture's CloudFront distribution."""
from concurrent.futures import ThreadPoolExecutor
import os
import urllib.error
import urllib.request

def handler(event, context):
    path = event.get("path", "/probe")
    if not isinstance(path, str) or not path.startswith("/") or "\r" in path or "\n" in path:
        raise ValueError("Invalid test path")
    count = int(event.get("count", 20))
    if not 1 <= count <= 100:
        raise ValueError("Invalid sample count")
    pin = event.get("pin")
    if pin not in (None, "blue", "green", "invalid"):
        raise ValueError("Invalid test pin")
    def request(_):
        headers = {} if pin is None else {"Cookie": os.environ["PIN_COOKIE"] + "=" + pin}
        try:
            response = urllib.request.urlopen(
                urllib.request.Request(os.environ["TARGET_URL"] + path, headers=headers), timeout=20)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            return {"status": response.status, "body": response.read().decode(),
                    "cache": response.headers.get("X-Cache", ""),
                    "set_cookie": response.headers.get_all("Set-Cookie", []),
                    "pop": response.headers.get("X-Amz-Cf-Pop")}
    with ThreadPoolExecutor(max_workers=5) as pool:
        return {"samples": list(pool.map(request, range(count)))}