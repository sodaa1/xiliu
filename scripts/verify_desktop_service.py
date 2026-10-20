"""Offline smoke check of a frozen sidecar with isolated, disposable user data."""

from __future__ import annotations

import argparse
import json
import os
import queue
import secrets
import socket
import subprocess
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

LINK = "https://github.com/CHENG-LIANG1/real-company-interview-ai-coding-projects"
FOLDER_TASK = (
    f"{LINK} 在知识库创建一个叫面试的文件夹把这个链接放进去，"
    "只放链接不用克隆，先放入inbox生成标签再放入知识库"
)


def verify(
    executable: Path,
    *,
    eof: bool = False,
    source: Path | None = None,
    workflow: bool = False,
    empty_path: bool = False,
    live_search: bool = False,
    app_folder: bool = False,
    mcp_probe: bool = False,
) -> dict:
    env = {key: value for key, value in os.environ.items() if not key.startswith("XILIU_")}
    if live_search:
        env["TAVILY_API_KEY"] = ""  # Verify the same keyless path as a fresh desktop.
    if empty_path:
        env["PATH"] = ""
    token = secrets.token_hex(32)
    env["XILIU_DESKTOP_TOKEN"] = token
    lines: queue.Queue[str] = queue.Queue()
    with (
        tempfile.TemporaryDirectory(prefix="xiliu-desktop-check-") as temporary,
        open(Path(temporary) / "service.log", "w", encoding="utf-8") as log,
    ):
        probe_marker = Path(temporary) / "packaged-mcp-marker.txt"
        probe_transcript = Path(temporary) / "packaged-mcp-transcript.jsonl"
        if mcp_probe:
            # All process/network permissions are explicit fixtures in disposable data.
            root = Path(temporary) / "mcp"
            (root / "aihot").mkdir(parents=True)
            (root / "aihot/mcp.json").write_text(
                json.dumps({"servers": {"aihot": {"enabled": False}}}), encoding="utf-8"
            )
            (root / "packaging_probe").mkdir()
            (root / "packaging_probe/mcp.json").write_text(
                json.dumps(
                    {
                        "servers": {
                            "packaging_probe": {
                                "enabled": True,
                                "trust": "explicit",
                                "transport": "stdio",
                                "command": str(Path(sys.executable).resolve()),
                                "args": [
                                    "-u",
                                    str(
                                        Path(__file__).resolve().parents[1]
                                        / "tests/e2e/mcp_probe.py"
                                    ),
                                    str(probe_marker),
                                    str(probe_transcript),
                                ],
                                "permissions": ["process.execute"],
                                "tool_allowlist": ["tool_marker"],
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            (Path(temporary) / "policy.json").write_text(
                json.dumps(
                    {
                        "profiles": {
                            "interactive": {
                                **dict.fromkeys(
                                    (
                                        "compute.safe",
                                        "time.read",
                                        "knowledge.read",
                                        "knowledge.write",
                                        "filesystem.read.workspace",
                                        "filesystem.write.workspace",
                                        "process.execute.safe",
                                        "process.execute",
                                        "agent.delegate",
                                        "automation.manage",
                                        "automation.read",
                                        "today.read",
                                        "tasks.read",
                                        "tasks.write",
                                        "feed.read",
                                        "feed.write",
                                        "conversations.read",
                                        "conversations.write",
                                        "preferences.read",
                                        "preferences.write",
                                        "settings.read",
                                        "capabilities.read",
                                    ),
                                    "allow",
                                ),
                                "network.read": "allow",
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
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

            def json_request(route, body=None, **kwargs):
                return json.loads(request(route, body, **kwargs))

            app_folder_receipts = []
            if app_folder:
                local_cid = json_request("/api/conversations", {})["id"]
                local_events = [
                    json.loads(line)
                    for line in request(
                        f"/api/conversations/{local_cid}/chat", {"text": FOLDER_TASK}, timeout=30
                    )
                    .decode()
                    .splitlines()
                ]
                final = local_events[-1]
                assert final["type"] == "final", local_events
                assert final["metadata"]["model_calls"] == 0, local_events
                app_folder_receipts = final["metadata"]["app_receipts"]
                assert app_folder_receipts and all(
                    receipt.get("verification", {}).get("passed") for receipt in app_folder_receipts
                ), local_events
                folder = next(
                    f for f in json_request("/api/knowledge/folders") if f["name"] == "面试"
                )
                cards = json_request(f"/api/knowledge/folders/{folder['id']}/items")
                assert len(cards) == 1, cards
                card = cards[0]
                assert card["source"] == card["content"] == LINK, card
                assert card["type"] == "link" and card["filename"] is None, card
                assert card["processing_status"] == "ready", card

            version = json.loads(request("/openapi.json"))["info"]["version"]
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
                probing = False
                probe_chain_verified = False

                def log_message(self, format: str, *args: object) -> None:
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
                    search_call = (
                        live_search
                        and not router
                        and not any(message.get("role") == "tool" for message in body["messages"])
                    )
                    probe_call = None
                    if Provider.probing:
                        names = {entry["function"]["name"] for entry in body.get("tools", [])}
                        outputs = {
                            m["tool_call_id"]: json.loads(m["content"])
                            for m in body["messages"]
                            if m.get("role") == "tool"
                        }
                        if not names:
                            # The final Verifier model has no tools. It may answer only
                            # after the preceding real planner round validated all tool outputs.
                            assert Provider.probe_chain_verified
                            assert "Verifier" in body["messages"][0]["content"]
                            assert probe_marker.read_text("utf-8") == "FrozenMCPMarker"
                            answer = json.dumps(
                                {
                                    "status": "passed",
                                    "reason": "Real MCP discovery, invocation and marker verified",
                                }
                            )
                        elif "probe-search" not in outputs:
                            assert {"capability_search", "mcp_call"} <= names
                            probe_call = (
                                "probe-search",
                                "capability_search",
                                {"query": "tool_marker", "kind": "mcp", "limit": 5},
                            )
                        elif "probe-call" not in outputs:
                            found = outputs["probe-search"]
                            assert found["ok"] and any(
                                r["id"] == "mcp:packaging_probe:tool_marker"
                                for r in found["results"]
                            ), found
                            probe_call = (
                                "probe-call",
                                "mcp_call",
                                {
                                    "capability_id": "mcp:packaging_probe:tool_marker",
                                    "arguments": {"value": "FrozenMCPMarker"},
                                },
                            )
                        else:
                            # /mcp confines this turn to discovery and MCP invocation.
                            # TODO writes are separate capabilities, not part of this probe.
                            assert outputs["probe-call"]["ok"], outputs["probe-call"]
                            assert probe_marker.read_text("utf-8") == "FrozenMCPMarker"
                            Provider.probe_chain_verified = True
                            answer = json.dumps(
                                {
                                    "summary": "Frozen MCP probe complete",
                                    "plan_summary": "Discover and invoke the local MCP tool",
                                    "acceptance_criteria": [
                                        "Marker persisted by actual stdio MCP invocation"
                                    ],
                                    "ready_for_verification": True,
                                }
                            )
                    if probe_call:
                        call_id, name, arguments = probe_call
                        deltas += [
                            {
                                "tool_calls": [
                                    {
                                        "index": 0,
                                        "id": call_id,
                                        "type": "function",
                                        "function": {
                                            "name": name,
                                            "arguments": json.dumps(arguments),
                                        },
                                    }
                                ]
                            },
                            {},
                        ]
                    elif search_call:
                        deltas += [
                            {
                                "tool_calls": [
                                    {
                                        "index": 0,
                                        "id": "weather-search",
                                        "type": "function",
                                        "function": {
                                            "name": "web_search",
                                            "arguments": json.dumps(
                                                {"query": "北京 天气", "max_results": 1}
                                            ),
                                        },
                                    }
                                ]
                            },
                            {},
                        ]
                    else:
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
                                    "finish_reason": (
                                        "tool_calls" if search_call or probe_call else "stop"
                                    )
                                    if index == len(deltas) - 1
                                    else None,
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
                            f"/api/conversations/{cid}/chat",
                            {"text": "北京天气如何"}
                            if live_search
                            else {"text": "联网查询北京天气"}
                            if workflow
                            else {"text": "Hello"},
                            timeout=60,
                        )
                        .decode()
                        .splitlines()
                    ]
                except TimeoutError as exc:
                    print((Path(temporary) / "service.log").read_text(encoding="utf-8"))
                    raise RuntimeError(
                        f"Frozen chat timed out after {Provider.calls} local model requests"
                    ) from exc
                assert not any(event.get("code") == "checkpoint_error" for event in events), events
                if workflow or live_search:
                    assert events[-1].get("type") == "final", events
                    assert (
                        Path(temporary) / "workspaces" / cid / ".xiliu/checkpoints/checkpoint.json"
                    ).is_file()
                else:
                    assert events[-1].get("text") == "Frozen model reply", events
                if live_search:
                    assert "来源：" in events[-1]["text"] and "http" in events[-1]["text"], events
                    assert Provider.calls == 2, "Weather must use a single search and one answer"
                expected_thought = "Packaged thought" * (2 if live_search else 1)
                assert events[-1]["metadata"]["thinking"]["reasoning"] == expected_thought, events
                assert (
                    json.loads(request(f"/api/conversations/{cid}/messages"))[-1]["content"]
                    == events[-1]["text"]
                )
                ordinary_model_calls = Provider.calls
                probe_methods = []
                probe_execution_events = []
                if mcp_probe:
                    Provider.probing = True
                    probe_cid = json_request("/api/conversations", {})["id"]
                    probe_events = [
                        json.loads(line)
                        for line in request(
                            f"/api/conversations/{probe_cid}/chat",
                            {
                                "text": "/mcp packaging_probe Invoke the packaging marker",
                            },
                            timeout=60,
                        )
                        .decode()
                        .splitlines()
                    ]
                    assert probe_events[-1]["type"] == "final", probe_events
                    execution = probe_events[-1].get("metadata", {}).get("execution_result", {})
                    if execution.get("status") != "completed" or not execution.get("verified"):
                        checkpoints = list(
                            (Path(temporary) / "workspaces" / probe_cid).rglob("checkpoint.json")
                        )
                        diagnostic = {
                            "events": probe_events,
                            "mcp_methods": probe_transcript.read_text("utf-8")
                            if probe_transcript.exists()
                            else "not_started",
                            "checkpoints": [json.loads(p.read_text("utf-8")) for p in checkpoints],
                        }
                        raise AssertionError(diagnostic)
                    assert probe_marker.read_text("utf-8") == "FrozenMCPMarker"
                    probe_methods = [
                        json.loads(line)["method"]
                        for line in probe_transcript.read_text("utf-8").splitlines()
                    ]
                    assert {"initialize", "tools/list", "tools/call"} <= set(probe_methods)
                    checkpoints = list(
                        (Path(temporary) / "workspaces" / probe_cid).rglob("checkpoint.json")
                    )
                    assert checkpoints, "The real workflow must persist its execution evidence"
                    checkpoint = json.loads(checkpoints[-1].read_text("utf-8"))
                    tool_events = checkpoint["state_summary"]["tool_events"]
                    discovery = next(
                        event for event in tool_events if event["tool"] == "capability_search"
                    )
                    invocation = next(event for event in tool_events if event["tool"] == "mcp_call")
                    assert discovery["ok"] and invocation["ok"]
                    assert discovery["args"]["kind"] == "mcp"
                    assert invocation["args"]["capability_id"] == "mcp:packaging_probe:tool_marker"
                    assert (
                        json.loads(discovery["output"])["ok"]
                        and json.loads(invocation["output"])["ok"]
                    )
                    assert tool_events.index(discovery) < tool_events.index(invocation)
                    probe_execution_events = [discovery, invocation]
            finally:
                provider.shutdown()
                provider.server_close()

            # Real frozen HTTP/Service/SQLite chain, with no network or model calls.
            feed_item = json_request(
                "/api/feed/manual",
                {
                    "url": "https://example.com/frozen#original",
                    "title": "Frozen Feed",
                    "tags": ["包装"],
                    "fetch_title": False,
                },
            )
            feed_item = json_request(
                f"/api/feed/manual/{feed_item['id']}",
                {"title": "Frozen Feed edited"},
                method="PATCH",
            )
            removed = json_request(f"/api/feed/manual/{feed_item['id']}", method="DELETE")
            assert removed["deleted_at"]
            restored = json_request(f"/api/feed/manual/{feed_item['id']}/restore", {})
            assert restored["deleted_at"] is None
            saved = json_request(f"/api/feed/{feed_item['id']}/save", {})
            saved_item = saved.get("item", saved)
            folder = json_request(
                "/api/knowledge/folders", {"name": "Frozen chain", "tags": ["包装"]}
            )
            archived = json_request(
                "/api/inbox/classify-batch",
                {
                    "item_ids": [saved_item["id"]],
                    "folder_id": folder["id"],
                    "save_to_knowledge": True,
                    "use_ai": False,
                },
            )["items"][0]
            assert archived["status"] == "knowledge" and archived["folder_id"] == folder["id"]
            task = json_request("/api/tasks", {"title": "Frozen chain task"})
            task = json_request(f"/api/tasks/{task['id']}", {"completed": True}, method="PATCH")
            assert task["completed"]
            automation = json_request(
                "/api/automations",
                {
                    "name": "Frozen chain automation",
                    "prompt": "检查我的 Inbox",
                    "hour": 23,
                    "minute": 59,
                    "timezone": "Asia/Shanghai",
                },
            )
            automation = json_request(
                f"/api/automations/{automation['id']}", {"enabled": False}, method="PATCH"
            )
            assert not automation["enabled"]
            assert any(i["id"] == feed_item["id"] for i in json_request("/api/today")["feed"])
            assert Provider.calls >= 1, "Ordinary configured frozen SDK chat was not exercised"
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

            # Start the same frozen executable against the same disposable database.
            if process.stdout:
                process.stdout.close()
            if process.stdin and not process.stdin.closed:
                process.stdin.close()
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
            threading.Thread(target=read_stdout, daemon=True).start()
            deadline = time.monotonic() + 60
            base = ""
            while time.monotonic() < deadline:
                assert process.poll() is None, "Restart exited before readiness"
                try:
                    line = lines.get(timeout=0.2)
                except queue.Empty:
                    continue
                if line.startswith("XILIU_READY "):
                    base = line.split(" ", 1)[1]
                    break
            assert base, "Frozen restart readiness timeout"
            assert any(
                i["id"] == feed_item["id"] and i["title"] == "Frozen Feed edited"
                for i in json_request("/api/feed")["items"]
            )
            persisted = json_request(f"/api/content/{saved_item['id']}")
            assert persisted["status"] == "knowledge" and persisted["folder_id"] == folder["id"]
            assert any(t["id"] == task["id"] and t["completed"] for t in json_request("/api/tasks"))
            assert any(
                a["id"] == automation["id"] and not a["enabled"]
                for a in json_request("/api/automations")
            )
            assert json_request("/api/desktop/shutdown", {}, private=True)["closing"]
            assert process.wait(timeout=35) == 0
            with socket.socket() as check:
                assert check.connect_ex(("127.0.0.1", int(base.rsplit(":", 1)[1]))) != 0
            return {
                "version": version,
                "ready": True,
                "owner_token": True,
                "frontend": True,
                "intro": True,
                "model_key_unset": True,
                "knowledge_retrieval": True,
                "configured_chat": True,
                "workflow_checkpoint": workflow,
                "app_folder_workflow": app_folder,
                "app_folder_model_calls": 0 if app_folder else None,
                "app_folder_verified_receipts": len(app_folder_receipts),
                "http_feed_inbox_knowledge_today_automation_chain": True,
                "same_data_restart_persistence": True,
                "empty_path": empty_path,
                "live_keyless_search": live_search,
                "local_model_calls": Provider.calls,
                "ordinary_sdk_model_calls": ordinary_model_calls,
                "real_stdio_mcp_client": mcp_probe,
                "mcp_model_calls": Provider.calls - ordinary_model_calls,
                "mcp_protocol_methods": probe_methods,
                "mcp_execution_events": probe_execution_events,
                "mcp_workflow_checkpoint": bool(probe_execution_events),
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
    parser.add_argument("--workflow", action="store_true")
    parser.add_argument("--empty-path", action="store_true")
    parser.add_argument("--app-folder", action="store_true")
    parser.add_argument("--mcp-probe", action="store_true")
    parser.add_argument(
        "--live-search",
        action="store_true",
        help="One real keyless Tavily search; model remains local and fake",
    )
    args = parser.parse_args()
    report = {
        "executable": str(args.executable),
        "checks": [
            verify(
                args.executable,
                source=args.source,
                workflow=args.workflow,
                empty_path=args.empty_path,
                live_search=args.live_search,
                app_folder=args.app_folder,
                mcp_probe=args.mcp_probe,
            ),
            verify(
                args.executable,
                eof=True,
                source=args.source,
                workflow=args.workflow,
                empty_path=args.empty_path,
                app_folder=args.app_folder,
                mcp_probe=args.mcp_probe,
            ),
        ],
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
