import threading
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib import import_module

from langchain_core.messages import HumanMessage
from openai import DefaultHttpxClient

from xiliu.config import Settings
from xiliu.providers.openai_compatible import create_chat_model


def test_loopback_model_address_bypasses_system_proxy(monkeypatch):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def do_POST(self):
            data = (
                b'data: {"id":"test","object":"chat.completion.chunk","created":1,'
                b'"model":"fake","choices":[{"index":0,"delta":{"content":"Local reply"},'
                b'"finish_reason":"stop"}]}\n\ndata: [DONE]\n\n'
            )
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    # An invalid proxy models the observed Windows system-proxy interception.
    monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:1")
    monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.1:1")
    monkeypatch.delenv("NO_PROXY", raising=False)
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    model = create_chat_model(
        Settings.from_env(
            {
                "XILIU_API_KEY": "fake",
                "XILIU_MODEL": "fake",
                "XILIU_BASE_URL": f"http://127.0.0.1:{server.server_port}/v1",
                "XILIU_TIMEOUT_SECONDS": "1",
            }
        )
    )
    try:
        assert model.invoke([HumanMessage(content="Hello")]).content == "Local reply"
    finally:
        model.root_client.close()
        server.shutdown()
        server.server_close()


def test_intent_router_propagates_provider_failure_without_checkpoint_or_retries(tmp_path):
    from uuid import uuid4

    from xiliu.events import ErrorEvent
    from xiliu.runtime import Runtime

    class AuthenticationError(Exception):
        status_code = 401

    class Model:
        calls = 0

        def invoke(self, _messages):
            self.calls += 1
            raise AuthenticationError("Never reveal a credential")

    model = Model()
    runtime = Runtime(model, data_dir=tmp_path, checkpoint_mode="off", trace_mode="off")
    try:
        events = list(runtime.stream_session("Hello", str(uuid4()), ""))
    finally:
        runtime.close()
    assert isinstance(events[-1], ErrorEvent)
    assert events[-1].code == "authentication"
    assert model.calls == 1
    assert "credential" not in events[-1].message


def test_external_model_address_uses_system_proxy(monkeypatch):
    received = []

    class Proxy(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def do_POST(self):
            received.append(self.path)
            data = (
                b'data: {"id":"proxy","object":"chat.completion.chunk","created":1,'
                b'"model":"fake","choices":[{"index":0,"delta":{"content":"Proxy reply"},'
                b'"finish_reason":"stop"}]}\n\ndata: [DONE]\n\n'
            )
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    proxy = ThreadingHTTPServer(("127.0.0.1", 0), Proxy)
    threading.Thread(target=proxy.serve_forever, daemon=True).start()
    for key in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY"):
        monkeypatch.delenv(key, raising=False)
        monkeypatch.delenv(key.lower(), raising=False)
    http_package = DefaultHttpxClient.__mro__[1].__module__.split(".")[0]
    def system_proxies():
        return {"http": f"http://127.0.0.1:{proxy.server_port}"}

    # LangChain checks urllib before selecting its Linux socket-tuned transport;
    # HTTPX retains a separately imported reference to the same proxy boundary.
    monkeypatch.setattr(urllib.request, "getproxies", system_proxies)
    monkeypatch.setattr(import_module(f"{http_package}._utils"), "getproxies", system_proxies)
    model = create_chat_model(
        Settings.from_env(
            {
                "XILIU_API_KEY": "fake",
                "XILIU_MODEL": "fake",
                "XILIU_BASE_URL": "http://provider.example.test/v1",
                "XILIU_TIMEOUT_SECONDS": "1",
            }
        )
    )
    try:
        assert model.invoke([HumanMessage(content="Hello")]).content == "Proxy reply"
        assert received == ["http://provider.example.test/v1/chat/completions"]
    finally:
        model.root_client.close()
        proxy.shutdown()
        proxy.server_close()
