from __future__ import annotations

import asyncio
from collections import Counter
from contextlib import contextmanager
from pathlib import Path
from threading import BoundedSemaphore, Lock

from xiliu.api.errors import WebError
from xiliu.cloud.auth import error_response

MAX_BODY = 1024 * 1024
MAX_UPLOAD_BODY = 29 * 1024 * 1024  # 20 MiB attachment encoded in JSON, plus metadata
MAX_WORKSPACE_BYTES = 100 * 1024 * 1024


def check_storage(
    directory: Path,
    *,
    limit: int = MAX_WORKSPACE_BYTES,
    previous: int | None = None,
    measure: bool = False,
):
    total = 0
    count = 0
    for path in directory.rglob("*"):
        count += 1
        if path.is_file():
            total += path.stat().st_size
    if (
        not measure
        and (total > limit or count > 20_000)
        and (previous is None or total >= previous)
    ):
        raise WebError("storage_limit", "工作区空间已满，请先删除部分资料。", 413)
    return total


class RequestSlots:
    def __init__(self):
        self.counts = Counter()
        self.lock = Lock()

    @contextmanager
    def acquire(self, workspace: str):
        with self.lock:
            if self.counts[workspace] >= 8 or self.counts.total() >= 64:
                raise WebError("request_limit", "请求过于频繁，请稍后再试。", 429)
            self.counts[workspace] += 1
        try:
            yield
        finally:
            with self.lock:
                self.counts[workspace] -= 1
                if not self.counts[workspace]:
                    del self.counts[workspace]


class BodyLimit:
    """Count streamed bytes, even with missing or false Content-Length headers."""

    def __init__(self, app):
        self.app = app
        self.uploads = BoundedSemaphore(4)

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] not in {"POST", "PUT", "PATCH"}:
            return await self.app(scope, receive, send)
        if not self.uploads.acquire(blocking=False):
            return await error_response(WebError("upload_busy", "上传请求繁忙，请稍后再试。", 429))(
                scope, receive, send
            )
        try:
            return await self._bounded(scope, receive, send)
        finally:
            self.uploads.release()

    async def _bounded(self, scope, receive, send):
        path = scope["path"]
        if path.startswith("/api/appearance/models/"):
            return await error_response(
                WebError("cloud_unavailable", "云端不支持上传桌面形象模型。", 403)
            )(scope, receive, send)
        limit = MAX_UPLOAD_BODY if path.startswith(("/api/content", "/api/inbox")) else MAX_BODY
        body = bytearray()
        try:
            async with asyncio.timeout(30):
                while True:
                    message = await receive()
                    if message["type"] == "http.disconnect":
                        return
                    body.extend(message.get("body", b""))
                    if len(body) > limit:
                        raise WebError("request_too_large", "请求或附件超过大小限制。", 413)
                    if not message.get("more_body", False):
                        break
        except TimeoutError:
            return await error_response(WebError("request_timeout", "请求上传超时。", 408))(
                scope, receive, send
            )
        except WebError as error:
            return await error_response(error)(scope, receive, send)
        delivered = False

        async def replay():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}
            return await receive()

        return await self.app(scope, replay, send)
