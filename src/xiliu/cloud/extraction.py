"""Bound untrusted document parsing independently of the web process."""

from __future__ import annotations

import json
import subprocess
import sys
from threading import BoundedSemaphore

from xiliu.api.errors import WebError

_PARSERS = BoundedSemaphore(2)
_FAILED = "正文提取超时或超过资源限制，已保留原件。"


def extract_cloud_text(filename: str, data: bytes) -> tuple[str, str | None]:
    if not _PARSERS.acquire(blocking=False):
        raise WebError("parser_busy", "文件解析繁忙，请稍后再试。", 429)
    try:
        result = subprocess.run(
            [sys.executable, "-m", "xiliu.cloud.extraction", filename],
            input=data,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=12,
        )
        if result.returncode or len(result.stdout) > 1_300_000:
            return "", _FAILED
        text, error = json.loads(result.stdout)
        if not isinstance(text, str) or (error is not None and not isinstance(error, str)):
            return "", _FAILED
        return text[:200_000], error
    except (ValueError, OSError, subprocess.TimeoutExpired, TimeoutError):
        return "", _FAILED
    finally:
        _PARSERS.release()


def _main():
    if sys.platform != "win32":
        import resource

        resource.setrlimit(resource.RLIMIT_AS, (384 * 1024 * 1024,) * 2)
        resource.setrlimit(resource.RLIMIT_CPU, (8, 8))
        resource.setrlimit(resource.RLIMIT_FSIZE, (0, 0))
    from xiliu.api.services.extract_text import extract_text

    data = sys.stdin.buffer.read(20 * 1024 * 1024 + 1)
    if len(data) > 20 * 1024 * 1024:
        raise ValueError("attachment limit")
    result = extract_text(sys.argv[1], data)
    sys.stdout.buffer.write(json.dumps(result, ensure_ascii=False).encode("utf-8"))


if __name__ == "__main__":
    _main()
