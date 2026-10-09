"""Offline smoke check of a frozen sidecar with isolated, disposable user data."""

from __future__ import annotations

import argparse
import json
import os
import queue
import secrets
import socket
import subprocess
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen


def verify(executable: Path, *, eof: bool = False, source: Path | None = None) -> dict:
    env = {key: value for key, value in os.environ.items() if not key.startswith("XILIU_")}
    token = secrets.token_hex(32)
    env["XILIU_DESKTOP_TOKEN"] = token
    lines: queue.Queue[str] = queue.Queue()
    with (
        tempfile.TemporaryDirectory(prefix="xiliu-desktop-check-") as temporary,
        open(Path(temporary) / "service.log", "w", encoding="utf-8") as log,
    ):
        process = subprocess.Popen(
            [
                str(executable.resolve()),
                *([str(source.resolve())] if source else []),
                "--data-dir",
                temporary,
            ],
            cwd=temporary,
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=log,
            text=True,
            encoding="utf-8",
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )

        def read_stdout():
            assert process.stdout
            for line in process.stdout:
                lines.put(line.strip())

        threading.Thread(target=read_stdout, daemon=True).start()
        try:
            deadline = time.monotonic() + 60
            base = ""
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    raise RuntimeError("Service exited before readiness")
                try:
                    line = lines.get(timeout=0.2)
                except queue.Empty:
                    continue
                if line.startswith("XILIU_READY "):
                    base = line.split(" ", 1)[1]
                    break
            assert base, "Service readiness timeout"

            def request(route, body=None, private=False, method=None, timeout=10):
                headers = {"Content-Type": "application/json"}
                if private:
                    headers["X-Xiliu-Desktop-Token"] = token
                data = json.dumps(body).encode() if body is not None else None
                with urlopen(
                    Request(base + route, data=data, headers=headers, method=method),
                    timeout=timeout,
                ) as response:
                    return response.read()

            assert json.loads(request("/api/desktop/ready", private=True))["ready"]
            try:
                request("/api/desktop/ready")
                raise AssertionError("Owner token was not enforced")
            except HTTPError as error:
                assert error.code == 403
            assert b"<html" in request("/").lower()
            assert b"<html" in request("/intro/").lower()
            assert not json.loads(request("/api/settings/model"))["api_key_set"]
            assert not (Path(temporary) / ".env").exists()
            item = json.loads(
                request(
                    "/api/content",
                    {
                        "type": "note",
                        "status": "knowledge",
                        "title": "Frozen knowledge check",
                        "content": "PackagingSmokeMarker: frozen local RAG evidence.",
                    },
                )
            )
            result = json.loads(request("/api/knowledge/search?q=" + quote("PackagingSmokeMarker")))
            assert item["id"] in json.dumps(result), (
                "Frozen Knowledge retrieval missed the document"
            )

            # Exercise actual frozen SDK/Graph streaming with a local fake provider.
            # No real credentials or external model requests are involved.
            class Provider(BaseHTTPRequestHandler):
                calls = 0

                def log_message(self, *_args):
                    pass

                def do_POST(self):
                    Provider.calls += 1
                    body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                    router = "intent router" in body["messages"][0]["content"]
                    answer = (
                        '{"route":"chat","reason":"Greeting","confidence":1}'
                        if router
                        else "Frozen model reply"
                    )
                    deltas = [{"reasoning_content": "Packaged thought"}] if not router else []
                    deltas += [{"content": answer}, {}]
                    chunks = [
                        {
                            "id": "fake",
                            "object": "chat.completion.chunk",
                            "created": 1,
                            "model": "deepseek-v4-flash",
                            "choices": [
                                {
                                    "index": 0,
                                    "delta": delta,
                                    "finish_reason": "stop" if index == len(deltas) - 1 else None,
                                }
                            ],
                        }
                        for index, delta in enumerate(deltas)
                    ]
                    raw = "".join("data: " + json.dumps(chunk) + "\n\n" for chunk in chunks)
                    raw += "data: [DONE]\n\n"
                    data = raw.encode()
                    self.send_response(200)
                    self.send_header("Content-Type", "text/event-stream")
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)

            provider = ThreadingHTTPServer(("127.0.0.1", 0), Provider)
            threading.Thread(target=provider.serve_forever, daemon=True).start()
            try:
                configured = json.loads(
                    request(
                        "/api/settings/model",
                        {
                            "provider": "deepseek",
                            "model": "deepseek-v4-flash",
                            "base_url": f"http://127.0.0.1:{provider.server_port}/v1",
                            "api_key": "fake-offline-key",
                        },
                        method="PUT",
                    )
                )
                assert configured["api_key_set"]
                cid = json.loads(request("/api/conversations", {}))["id"]
                try:
                    events = [
                        json.loads(line)
                        for line in request(
                            f"/api/conversations/{cid}/chat", {"text": "Hello"}, timeout=60
                        )
                        .decode()
                        .splitlines()
                    ]
                except TimeoutError as exc:
                    print((Path(temporary) / "service.log").read_text(encoding="utf-8"))
                    raise RuntimeError(
                        f"Frozen chat timed out after {Provider.calls} local model requests"
                    ) from exc
                assert events[-1].get("text") == "Frozen model reply", events
                assert events[-1]["metadata"]["thinking"]["reasoning"] == "Packaged thought", events
                assert (
                    json.loads(request(f"/api/conversations/{cid}/messages"))[-1]["content"]
                    == "Frozen model reply"
                )
            finally:
                provider.shutdown()
                provider.server_close()
            assert (Path(temporary) / "mcp/aihot/mcp.json").is_file(), (
                "Packaged AIHot defaults missing"
            )
            if eof:
                assert process.stdin
                process.stdin.close()
            else:
                assert json.loads(request("/api/desktop/shutdown", {}, private=True))["closing"]
            assert process.wait(timeout=35) == 0
            port = int(base.rsplit(":", 1)[1])
            with socket.socket() as check:
                assert check.connect_ex(("127.0.0.1", port)) != 0, "Port is still listening"
            return {
                "ready": True,
                "owner_token": True,
                "frontend": True,
                "intro": True,
                "model_key_unset": True,
                "knowledge_retrieval": True,
                "configured_chat": True,
                "reasoning_stream": True,
                "aihot_defaults": True,
                "exit_code": 0,
                "port_released": True,
                "shutdown": "stdin_eof" if eof else "private_route",
            }
        finally:
            if process.poll() is None:
                if process.stdin and not process.stdin.closed:
                    process.stdin.close()
                try:
                    process.wait(timeout=35)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
            if process.stdout:
                process.stdout.close()
            if process.stdin and not process.stdin.closed:
                process.stdin.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("executable", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--source", type=Path)
    args = parser.parse_args()
    report = {
        "executable": str(args.executable),
        "checks": [
            verify(args.executable, source=args.source),
            verify(args.executable, eof=True, source=args.source),
        ],
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
