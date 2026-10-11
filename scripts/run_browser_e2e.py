"""Run real browser/HTTP flows against a disposable, keyless Xiliu database.

Uses an existing Playwright package and installed browser; never downloads either.
Only the external Feed provider boundary is replaced with deterministic fixtures.
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
from contextlib import closing
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]


def serve(data_dir: Path, port: int) -> None:
    import uvicorn

    from xiliu.api.app import create_app
    from xiliu.api.services.feed import normalize_aihot

    app = create_app(data_dir=data_dir, env_file=data_dir / ".env", static_dir=ROOT / "web/dist")
    app.state.feed._fetch_aihot = lambda: normalize_aihot(
        [{"title": "E2E external story", "url": "https://example.com/external", "tags": ["外部"]}]
    )
    app.state.feed._fetch_github = lambda: []
    app.state.feed.refresh()
    # A delayed local OpenAI-compatible boundary lets the browser stop a real
    # SDK request while it is in flight. Services, cancellation and storage are real.
    provider_started = threading.Event()
    provider_finished = threading.Event()

    class DelayedProvider(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def do_POST(self):
            self.rfile.read(int(self.headers["Content-Length"]))
            provider_started.set()
            time.sleep(2)
            chunk = {
                "id": "browser-stop-probe",
                "object": "chat.completion.chunk",
                "created": 1,
                "model": "deepseek-v4-flash",
                "choices": [
                    {
                        "index": 0,
                        "delta": {
                            "role": "assistant",
                            "content": "Late provider reply must not persist",
                        },
                        "finish_reason": "stop",
                    }
                ],
            }
            data = ("data: " + json.dumps(chunk) + "\n\ndata: [DONE]\n\n").encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            try:
                self.wfile.write(data)
            except (BrokenPipeError, ConnectionResetError):
                pass
            finally:
                provider_finished.set()

    provider = ThreadingHTTPServer(("127.0.0.1", 0), DelayedProvider)
    threading.Thread(target=provider.serve_forever, daemon=True).start()

    @app.post("/__e2e/provider")
    def provider_state():
        return {
            "base_url": f"http://127.0.0.1:{provider.server_port}/v1",
            "started": provider_started.is_set(),
            "finished": provider_finished.is_set(),
        }

    @app.post("/__e2e/seed-pending")
    def seed_pending(body: dict):
        item = (
            app.state.content.get(body["item_id"])
            if "item_id" in body
            else app.state.content.create(body)
        )
        return app.state.content.update(
            item["id"],
            {
                "processing_status": "pending",
                **({"tags": body["tags"]} if "item_id" in body and "tags" in body else {}),
            },
            internal=True,
        )

    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--port", type=int)
    runtime = Path.home() / ".cache/codex-runtimes/codex-primary-runtime/dependencies/node"
    parser.add_argument("--node", type=Path, default=runtime / "bin/node.exe")
    parser.add_argument("--module-dir", type=Path, default=runtime / "node_modules")
    parser.add_argument(
        "--browser",
        type=Path,
        default=Path("C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"),
    )
    parser.add_argument("--report-dir", type=Path, default=ROOT / "docs/audit/browser-e2e")
    args = parser.parse_args()
    if args.serve:
        serve(args.data_dir, args.port)
        return 0
    for path in (
        args.node,
        args.module_dir / "playwright",
        args.browser,
        ROOT / "web/dist/index.html",
    ):
        if not path.exists():
            parser.error(f"Required existing dependency missing: {path}")
    report_dir = args.report_dir.resolve()
    report_dir.mkdir(parents=True, exist_ok=True)
    env = {
        k: v for k, v in os.environ.items() if not k.startswith(("XILIU_", "OPENAI_", "DEEPSEEK_"))
    }
    env.update(PYTHONPATH=str(ROOT / "src"), PYTHONUTF8="1")
    with tempfile.TemporaryDirectory(prefix="xiliu-browser-e2e-") as temporary:
        data_dir = Path(temporary)
        (data_dir / ".env").write_text("", encoding="utf-8")
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]
        base_url = f"http://127.0.0.1:{port}"
        report = {
            "base_url": base_url,
            "disposable_data": True,
            "provider_fixture_only": True,
            "phases": [],
        }
        for phase in ("ui", "ui_restart", "agent", "agent_restart"):
            with (report_dir / f"server-{phase}.log").open("w", encoding="utf-8") as log:
                server = subprocess.Popen(
                    [
                        sys.executable,
                        str(Path(__file__).resolve()),
                        "--serve",
                        "--data-dir",
                        str(data_dir),
                        "--port",
                        str(port),
                    ],
                    cwd=ROOT,
                    env=env,
                    stdout=log,
                    stderr=log,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                try:
                    for _ in range(100):
                        if server.poll() is not None:
                            raise RuntimeError(f"Server exited; inspect {log.name}")
                        try:
                            with urlopen(base_url + "/api/health", timeout=1) as response:
                                if response.status == 200:
                                    break
                        except OSError:
                            time.sleep(0.1)
                    else:
                        raise RuntimeError("Disposable server did not become ready")
                    result = subprocess.run(
                        [
                            str(args.node),
                            str(ROOT / "tests/e2e/all_pages.mjs"),
                            base_url,
                            phase,
                            str(report_dir),
                            str(args.module_dir),
                            str(args.browser),
                        ],
                        cwd=ROOT,
                        env=env,
                        text=True,
                        encoding="utf-8",
                        capture_output=True,
                    )
                    print(result.stdout, end="")
                    print(result.stderr, end="", file=sys.stderr)
                    phase_path = report_dir / f"{phase}.json"
                    report["phases"].append(
                        json.loads(phase_path.read_text("utf-8"))
                        if phase_path.exists()
                        else {"phase": phase, "status": "failed", "error": result.stderr}
                    )
                    if result.returncode:
                        break
                finally:
                    server.terminate()
                    try:
                        server.wait(timeout=15)
                    except subprocess.TimeoutExpired:
                        server.kill()
                        server.wait(timeout=5)
        # Independently read the actual persisted database after every server is stopped.
        with closing(sqlite3.connect(data_dir / "app.sqlite3")) as db:
            report["database_counts"] = {
                table: db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                for table in (
                    "feed_manual_items",
                    "feed_hidden_items",
                    "content_items",
                    "tasks",
                    "app_requests",
                )
                if db.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
                ).fetchone()
            }
        report["status"] = (
            "passed"
            if len(report["phases"]) == 4 and all(p["status"] == "passed" for p in report["phases"])
            else "failed"
        )
        target = report_dir / "report.json"
        target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Browser E2E {report['status']}: {target}")
        return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
