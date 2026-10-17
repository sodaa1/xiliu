"""Cloud HTTP clients validate DNS at every connection and connect to the vetted IP.

SNI and Host retain the original authority. A fresh inner transport per request
prevents TLS pool reuse across different authorities sharing an IP address.
"""

from __future__ import annotations

import asyncio
import ipaddress
import socket

import httpx


def _resolve(host: str, port: int) -> list[str]:
    return list(
        {str(record[4][0]) for record in socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)}
    )


class OutboundPolicy:
    def __init__(self, *, resolver=_resolve):
        self.resolver = resolver

    def pin(self, request: httpx.Request) -> httpx.Request:
        url = request.url
        try:
            if (
                url.scheme not in {"https", "http"}
                or not url.host
                or url.userinfo
                or url.port not in {None, 80, 443}
            ):
                raise ValueError("unsupported destination")
            try:
                literal = ipaddress.ip_address(url.host)
            except ValueError:
                addresses = self.resolver(
                    url.host, url.port or (443 if url.scheme == "https" else 80)
                )
            else:
                addresses = [str(literal)]
            if not addresses:
                raise ValueError("no addresses")
            for address in addresses:
                ip = ipaddress.ip_address(address)
                if (
                    not ip.is_global
                    or ip.is_multicast
                    or ip.is_reserved
                    or (
                        isinstance(ip, ipaddress.IPv6Address)
                        and (ip.ipv4_mapped or ip.sixtofour or ip.teredo)
                    )
                ):
                    raise ValueError("non-public destination")
            headers = request.headers.copy()
            headers["host"] = url.netloc.decode("ascii")
            headers["accept-encoding"] = "identity"
            addresses = sorted(addresses, key=lambda address: ipaddress.ip_address(address).version)
            return httpx.Request(
                request.method,
                url.copy_with(host=addresses[0]),
                headers=headers,
                stream=request.stream,
                extensions={**request.extensions, "sni_hostname": url.host},
            )
        except (ValueError, OSError):
            raise httpx.ConnectError("云端仅允许连接公共 HTTP(S) 服务。", request=request) from None


class _Stream(httpx.SyncByteStream):
    def __init__(self, stream, transport):
        self.stream, self.transport = stream, transport

    def __iter__(self):
        size = 0
        for chunk in self.stream:
            size += len(chunk)
            if size > 8 * 1024 * 1024:
                raise httpx.ReadError("云端响应超过大小限制。")
            yield chunk

    def close(self):
        try:
            self.stream.close()
        finally:
            self.transport.close()


class SafeTransport(httpx.BaseTransport):
    def __init__(self, *, policy=None, factory=None):
        self.policy = policy or OutboundPolicy()
        self.factory = factory or (lambda: httpx.HTTPTransport(trust_env=False, retries=0))

    def handle_request(self, request):
        pinned = self.policy.pin(request)
        inner = self.factory()
        try:
            response = inner.handle_request(pinned)
            if response.headers.get("content-encoding", "identity") != "identity":
                response.close()
                raise httpx.ReadError("云端不接受压缩响应。", request=request)
            response.stream = _Stream(response.stream, inner)
            return response
        except BaseException:
            inner.close()
            raise


class _AsyncStream(httpx.AsyncByteStream):
    def __init__(self, stream, transport):
        self.stream, self.transport = stream, transport

    async def __aiter__(self):
        size = 0
        async for chunk in self.stream:
            size += len(chunk)
            if size > 8 * 1024 * 1024:
                raise httpx.ReadError("云端响应超过大小限制。")
            yield chunk

    async def aclose(self):
        try:
            await self.stream.aclose()
        finally:
            await self.transport.aclose()


class SafeAsyncTransport(httpx.AsyncBaseTransport):
    def __init__(self, *, policy=None, factory=None):
        self.policy = policy or OutboundPolicy()
        self.factory = factory or (lambda: httpx.AsyncHTTPTransport(trust_env=False, retries=0))

    async def handle_async_request(self, request):
        pinned = await asyncio.to_thread(self.policy.pin, request)
        inner = self.factory()
        try:
            response = await inner.handle_async_request(pinned)
            if response.headers.get("content-encoding", "identity") != "identity":
                await response.aclose()
                raise httpx.ReadError("云端不接受压缩响应。", request=request)
            response.stream = _AsyncStream(response.stream, inner)
            return response
        except BaseException:
            await inner.aclose()
            raise


def cloud_http_clients():
    return (
        httpx.Client(transport=SafeTransport(), trust_env=False, timeout=30),
        httpx.AsyncClient(transport=SafeAsyncTransport(), trust_env=False, timeout=30),
    )
