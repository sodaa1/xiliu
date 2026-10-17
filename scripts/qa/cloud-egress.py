"""Run inside the disposable app container; exercise kernel egress restrictions."""

import importlib.util
import os
import socket
import sys
from pathlib import Path

import httpx

from xiliu.cloud.extraction import extract_cloud_text
from xiliu.cloud.network import SafeTransport

assert os.getuid() == 10001
assert "CapEff:\t0000000000000000" in Path("/proc/self/status").read_text()
assert importlib.util.find_spec("pytest") is None
for name in ("/app/src", "/app/.env", "/app/.git", "/app/web/node_modules", "/app/tests"):
    assert not Path(name).exists(), name
assert extract_cloud_text("sample.txt", b"isolated parser") == ("isolated parser", None)
for target in ("127.0.0.2", "169.254.169.254", "10.0.0.1", "168.63.129.16", *sys.argv[1:]):
    try:
        with socket.create_connection((target, 80), timeout=2):
            raise AssertionError("Forbidden raw connection succeeded")
    except OSError:
        pass
with httpx.Client(transport=SafeTransport(), trust_env=False, timeout=15) as client:
    assert client.get("https://example.com/").status_code == 200
print("non-root, image contents, isolated parser and real kernel egress checks passed")
