"""Measure an existing sidecar on disposable empty data; never refresh external sources."""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import queue
import secrets
import subprocess
import tempfile
import threading
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def memory_bytes(pid: int) -> dict:
    from ctypes import wintypes

    class Counters(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD)] + [
            (name, ctypes.c_size_t)
            for name in (
                "PeakWorkingSetSize",
                "WorkingSetSize",
                "QuotaPeakPagedPoolUsage",
                "QuotaPagedPoolUsage",
                "QuotaPeakNonPagedPoolUsage",
                "QuotaNonPagedPoolUsage",
                "PagefileUsage",
                "PeakPagefileUsage",
            )
        ]

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    psapi.GetProcessMemoryInfo.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(Counters),
        wintypes.DWORD,
    ]
    handle = kernel.OpenProcess(0x0400 | 0x0010, False, pid)
    if not handle:
        return {"status": "failed", "reason": "OpenProcess unavailable"}
    try:
        data = Counters()
        data.cb = ctypes.sizeof(data)
        if not psapi.GetProcessMemoryInfo(handle, ctypes.byref(data), data.cb):
            return {"status": "failed", "reason": "GetProcessMemoryInfo unavailable"}
        return {
            "status": "passed",
            "working_set_bytes": data.WorkingSetSize,
            "peak_working_set_bytes": data.PeakWorkingSetSize,
            "private_commit_bytes": data.PagefileUsage,
        }
    finally:
        kernel.CloseHandle(handle)


def probe(executable: Path) -> dict:
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("XILIU_")
        and not any(word in key.upper() for word in ("API_KEY", "TOKEN", "SECRET"))
    }
    token = secrets.token_hex(32)
    env["XILIU_DESKTOP_TOKEN"] = token
    env["PYTHONUTF8"] = "1"
    with tempfile.TemporaryDirectory(prefix="xiliu-baseline-") as directory:
        messages: queue.Queue = queue.Queue()
        started = time.perf_counter()
        process = subprocess.Popen(
            [str(executable), "--data-dir", directory],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            env=env,
            cwd=directory,
            text=True,
            encoding="utf-8",
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )

        stdout, stdin = process.stdout, process.stdin
        assert stdout is not None and stdin is not None

        def read_ready():
            for line in stdout:
                if line.startswith("XILIU_READY "):
                    messages.put(line.strip().split(" ", 1)[1])
                    break

        thread = threading.Thread(target=read_ready, daemon=True)
        thread.start()
        try:
            origin = messages.get(timeout=60)
            launch_ms = (time.perf_counter() - started) * 1000

            def request(path, method="GET", body=None):
                data = None if body is None else json.dumps(body).encode()
                req = urllib.request.Request(
                    origin + path,
                    data=data,
                    method=method,
                    headers={"X-Xiliu-Desktop-Token": token, "Content-Type": "application/json"},
                )
                before = time.perf_counter()
                with urllib.request.urlopen(req, timeout=10) as response:
                    raw = response.read()
                return (json.loads(raw) if raw else None), (time.perf_counter() - before) * 1000

            ready, _ = request("/api/desktop/ready")
            assert isinstance(ready, dict)
            result = {
                "status": "passed",
                "launch_to_ready_ms": launch_ms,
                "memory_at_ready": memory_bytes(process.pid),
                "desktop_ready": ready.get("ready"),
            }
            reads = []
            for _ in range(10):
                _, ms = request("/api/today")
                reads.append(ms)
            writes = []
            for _ in range(10):
                task, ms = request("/api/tasks", "POST", {"title": "Disposable baseline task"})
                writes.append(ms)
                assert isinstance(task, dict)
                updated, _ = request("/api/tasks/" + task["id"], "PATCH", {"completed": True})
                assert isinstance(updated, dict) and updated["completed"] is True
                request("/api/tasks/" + task["id"], "DELETE")
            result["today_read_ms"] = reads
            result["task_create_persisted_ms"] = writes
            result["memory_after_local_workflow"] = memory_bytes(process.pid)
            request("/api/desktop/shutdown", "POST", {})
            stdin.close()
            process.wait(timeout=15)
            result["exit_code"] = process.returncode
            result["local_workflow"] = (
                "passed: 10 Task create/complete/delete cycles against disposable SQLite"
            )
            return result
        except Exception as exc:
            return {"status": "failed", "error_type": type(exc).__name__}
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=10)
            if process.stdout:
                process.stdout.close()
            if process.stdin and not process.stdin.closed:
                stdin.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--executable", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "docs/audit/startup-baseline.json")
    args = parser.parse_args()
    runs = [probe(args.executable) for _ in range(3)]
    report = {
        "status": "passed" if all(run["status"] == "passed" for run in runs) else "failed",
        "executable": str(args.executable),
        "executable_sha256": hashlib.sha256(args.executable.read_bytes()).hexdigest(),
        "environment": (
            "Windows, frozen desktop sidecar at the recorded executable path; "
            "empty TemporaryDirectory each run; "
            "XILIU/provider credential environment stripped; "
            "no model calls, Feed refresh or user data."
        ),
        "cold_limit": (
            "First process launch and two subsequent launches measured. "
            "OS disk cache was not flushed: these are not guaranteed cold-disk measurements."
        ),
        "runs": runs,
        "installed_ui_workflow": "not_run",
    }
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": report["status"],
                "launch_ms": [run.get("launch_to_ready_ms") for run in runs],
                "output": str(args.output),
            }
        )
    )


if __name__ == "__main__":
    main()
