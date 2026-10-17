import httpx
import pytest

from xiliu.cloud.network import OutboundPolicy, SafeAsyncTransport, SafeTransport


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/",
        "http://[::1]/",
        "http://169.254.169.254/",
        "http://10.0.0.1/",
        "http://[::ffff:127.0.0.1]/",
        "file:///etc/passwd",
        "https://user:secret@example.com/",
        "https://example.com:8443/",
    ],
)
def test_rejects_internal_or_unsupported_targets(url):
    policy = OutboundPolicy(resolver=lambda host, port: ["127.0.0.1"])
    with pytest.raises(httpx.RequestError):
        policy.pin(httpx.Request("GET", url))


def test_rejects_mixed_dns_and_rechecks_each_connection():
    addresses = ["93.184.216.34"]
    policy = OutboundPolicy(resolver=lambda host, port: addresses)
    assert policy.pin(httpx.Request("GET", "https://example.com/x")).url.host == addresses[0]
    addresses.append("192.168.1.2")
    with pytest.raises(httpx.RequestError):
        policy.pin(httpx.Request("GET", "https://example.com/x"))


def test_actual_transport_uses_pinned_ip_and_preserves_tls_host():
    seen = []

    def respond(request):
        seen.append(request)
        return httpx.Response(200, text="ok")

    transport = SafeTransport(
        policy=OutboundPolicy(resolver=lambda host, port: ["93.184.216.34"]),
        factory=lambda: httpx.MockTransport(respond),
    )
    with httpx.Client(transport=transport, trust_env=False) as client:
        assert client.get("https://example.com/path").text == "ok"
    assert seen[0].url.host == "93.184.216.34"
    assert seen[0].headers["host"] == "example.com"
    assert seen[0].extensions["sni_hostname"] == "example.com"


def test_redirect_cannot_reach_private_network():
    seen = []

    def respond(request):
        seen.append(request.url)
        return httpx.Response(302, headers={"location": "http://127.0.0.1/secret"})

    with (
        httpx.Client(
            transport=SafeTransport(
                policy=OutboundPolicy(resolver=lambda host, port: ["93.184.216.34"]),
                factory=lambda: httpx.MockTransport(respond),
            ),
            follow_redirects=True,
        ) as client,
        pytest.raises(httpx.RequestError),
    ):
        client.get("https://example.com/")
    assert len(seen) == 1


@pytest.mark.asyncio
async def test_async_transport_also_pins_actual_connection_and_rechecks_dns():
    addresses = ["93.184.216.34"]
    seen = []

    async def respond(request):
        seen.append(request)
        return httpx.Response(200, text="ok")

    async with httpx.AsyncClient(
        transport=SafeAsyncTransport(
            policy=OutboundPolicy(resolver=lambda host, port: addresses),
            factory=lambda: httpx.MockTransport(respond),
        )
    ) as client:
        assert (await client.get("https://example.com/")).text == "ok"
        addresses[:] = ["169.254.169.254"]
        with pytest.raises(httpx.ConnectError):
            await client.get("https://example.com/")
    assert len(seen) == 1
    assert seen[0].url.host == "93.184.216.34"
    assert seen[0].headers["accept-encoding"] == "identity"


def test_response_limit_closes_transport():
    closed = []

    class Large(httpx.SyncByteStream):
        def __iter__(self):
            for _ in range(9):
                yield b"x" * 1024 * 1024

        def close(self):
            closed.append(True)

    transport = SafeTransport(
        policy=OutboundPolicy(resolver=lambda host, port: ["93.184.216.34"]),
        factory=lambda: httpx.MockTransport(lambda request: httpx.Response(200, stream=Large())),
    )
    with httpx.Client(transport=transport) as client, pytest.raises(httpx.ReadError):
        client.get("https://example.com/")
    assert closed
