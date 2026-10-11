"""Offline real-Service benchmark. Every measured operation gets disposable fresh data."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import shutil
import socket
import statistics
import tempfile
import time
from contextlib import ExitStack
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import patch

from xiliu.api.app import create_app
from xiliu.app.dispatch import AppDispatcher
from xiliu.app.fast import run_app_fast
from xiliu.execution.gateway import RunContext

ROOT = Path(__file__).resolve().parents[1]
LAYERS = ("service", "dispatch", "fast", "chat")


def summary(values: list[float]) -> dict[str, Any]:
    ordered = sorted(values)
    return {
        "samples": len(values),
        "first_ms": round(values[0], 3),
        "p50_ms": round(statistics.median(values), 3),
        "p95_ms": round(ordered[math.ceil(len(values) * 0.95) - 1], 3),
        "min_ms": round(ordered[0], 3),
        "max_ms": round(ordered[-1], 3),
        "values_ms": [round(value, 3) for value in values],
    }


def service_operation(state: Any, case: str, size: int) -> None:
    if case == "inbox.archive_all":
        ids = [item["id"] for item in state.content.list("inbox")]
        for offset in range(0, size, 100):
            state.inbox.classify_batch(
                ids[offset : offset + 100], use_ai=False, save_to_knowledge=True
            )
    elif case == "link.folder.workflow":
        item = state.inbox.import_item({"text": "https://example.com/benchmark", "use_ai": False})
        folder = state.knowledge.ensure_folder({"name": "基准文件夹"})
        state.inbox.classify_batch(
            [item["id"]], folder_id=folder["id"], use_ai=False, save_to_knowledge=True
        )
    elif case == "feed.create":
        state.feed.add_manual({"url": "https://example.com/benchmark", "fetch_title": False})
    elif case == "today.task.create":
        state.tasks.create({"title": "基准待办"})
    elif case == "preferences.update":
        revision = state.preferences.get()["revision"]
        state.preferences.update({"theme": "dark"}, expected_revision=revision)
    elif case == "preferences.read":
        state.preferences.get()


def dispatch_operation(dispatcher: AppDispatcher, case: str) -> None:
    def execute(action: str, arguments: dict, suffix: str):
        receipt = dispatcher.execute(action, arguments, request_id="benchmark:" + suffix)
        assert receipt["ok"] and receipt["verification"]["passed"], receipt
        return receipt["data"]

    if case == "inbox.archive_all":
        execute("inbox.classify_all", {"use_ai": False}, "archive")
    elif case == "link.folder.workflow":
        item = execute(
            "inbox.import_url", {"url": "https://example.com/benchmark", "use_ai": False}, "import"
        )
        folder = execute("knowledge.folders.ensure", {"name": "基准文件夹"}, "folder")
        execute(
            "inbox.classify_selected",
            {"item_ids": [item["id"]], "folder_id": folder["id"], "use_ai": False},
            "archive",
        )
    elif case == "feed.create":
        execute(
            "feed.add_manual",
            {"url": "https://example.com/benchmark", "fetch_title": False},
            "feed",
        )
    elif case == "today.task.create":
        execute("tasks.create", {"title": "基准待办"}, "task")
    elif case == "preferences.update":
        revision = execute("preferences.get", {}, "pref-read")["revision"]
        execute(
            "preferences.update",
            {"changes": {"theme": "dark"}, "expected_revision": revision},
            "pref-write",
        )
    elif case == "preferences.read":
        execute("preferences.get", {}, "pref-read")


def verify(state: Any, case: str, size: int) -> None:
    if case == "inbox.archive_all":
        assert not state.content.list("inbox")
        assert len(state.content.list("knowledge")) == size
    elif case == "link.folder.workflow":
        items = state.content.list("knowledge")
        assert len(items) == 1 and items[0]["source"] == "https://example.com/benchmark"
        assert items[0]["processing_status"] == "ready" and items[0]["folder_id"]
    elif case == "feed.create":
        assert len(state.feed.list()["items"]) == 1
    elif case == "today.task.create":
        assert len(state.tasks.list()) == 1
    elif case == "preferences.update":
        assert state.preferences.get()["preferences"]["theme"] == "dark"
    elif case == "unknown.clarify":
        assert not state.tasks.list()


def benchmark(samples: int, bulk_sizes: list[int], *, profile: str = "full") -> dict[str, Any]:
    started_at = datetime.now(UTC).isoformat()
    sources = [
        "src/xiliu/app/fast.py",
        "src/xiliu/app/dispatch.py",
        "src/xiliu/app/actions.py",
        "src/xiliu/execution/gateway.py",
        "src/xiliu/tools/app.py",
        "src/xiliu/api/services/chat.py",
        "src/xiliu/api/services/inbox.py",
    ]
    source_sha256 = {
        path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in sources
    }
    counters = {
        "provider_model_calls": 0,
        "supervisor_runtime_calls": 0,
        "network_attempts": 0,
        "reported_model_calls": 0,
    }

    def forbidden_model(*args, **kwargs):
        counters["provider_model_calls"] += 1
        raise AssertionError("benchmark unexpectedly attempted provider construction")

    def forbidden_runtime(*args, **kwargs):
        counters["supervisor_runtime_calls"] += 1
        raise AssertionError("benchmark unexpectedly entered Supervisor runtime")

    def forbidden_network(*args, **kwargs):
        counters["network_attempts"] += 1
        raise AssertionError("benchmark networking is blocked")

    # Preserve ordinary process settings, exclude credentials and provider configuration.
    safe_environment = {
        key: value
        for key, value in os.environ.items()
        if not any(
            marker in key.upper() for marker in ("API_KEY", "TOKEN", "SECRET", "XILIU_", "OPENAI_")
        )
    }
    cases = [
        ("inbox.archive_all", size, "把Inbox里面内容全部分类归入知识库") for size in bulk_sizes
    ] + [
        (
            "link.folder.workflow",
            1,
            "创建知识库文件夹‘基准文件夹’把https://example.com/benchmark先放入Inbox生成标签再归档",
        ),
        ("feed.create", 1, "给Feed加入https://example.com/benchmark，只保存链接"),
        ("today.task.create", 1, "创建待办‘基准待办’"),
        ("preferences.update", 1, "把主题改为深色"),
        ("preferences.read", 1, "查看个人设置"),
        ("unknown.clarify", 0, "帮我处理待办"),
    ]
    if profile == "gateway":
        cases = [case for case in cases if case[0] in {"inbox.archive_all", "link.folder.workflow"}]
    layers = ("fast", "chat") if profile == "gateway" else LAYERS
    results = []
    with ExitStack() as stack:
        stack.enter_context(patch.dict(os.environ, safe_environment, clear=True))
        stack.enter_context(
            patch(
                "xiliu.providers.openai_compatible.create_chat_model", side_effect=forbidden_model
            )
        )
        stack.enter_context(patch.object(socket.socket, "connect", forbidden_network))
        stack.enter_context(patch("socket.create_connection", side_effect=forbidden_network))
        temporary = Path(
            stack.enter_context(tempfile.TemporaryDirectory(prefix="xiliu-fast-bench-"))
        )
        env_file = temporary / "empty.env"
        env_file.write_text("", encoding="utf-8")
        for case, size, command in cases:
            template = temporary / f"template-{case}-{size}"
            seed = create_app(data_dir=template, env_file=env_file).state
            assert not seed.model_settings.read()["api_key_set"]
            if case == "inbox.archive_all":
                seed.knowledge.create_folder({"name": "Python", "tags": ["Python"]})
                for index in range(size):
                    seed.content.create(
                        {
                            "type": "note",
                            "title": f"benchmark {index}",
                            "content": f"Python benchmark note {index}",
                        }
                    )
            seed.inbox.shutdown()
            for layer in layers:
                if case == "unknown.clarify" and layer in {"service", "dispatch"}:
                    continue
                durations, initialization = [], []
                reported_models = 0
                for index in range(samples):
                    data = temporary / f"run-{case}-{size}-{layer}-{index}"
                    shutil.copytree(template, data)
                    before = time.perf_counter()
                    state = create_app(data_dir=data, env_file=env_file).state
                    initialization.append((time.perf_counter() - before) * 1000)
                    state.chat.runtime_factory = forbidden_runtime
                    context = RunContext(
                        f"sample-{index}",
                        "benchmark",
                        data,
                        data_dir=data,
                        app_services=state.app_services,
                    )
                    dispatcher = AppDispatcher(state.app_services, context)
                    cid = state.store.create()["id"] if layer == "chat" else None
                    before = time.perf_counter()
                    if layer == "service":
                        service_operation(state, case, size)
                    elif layer == "dispatch":
                        dispatch_operation(dispatcher, case)
                    elif layer == "fast":
                        result = run_app_fast(command, state.app_services, context)
                        assert result is not None
                        expected = (
                            "clarification_required" if case == "unknown.clarify" else "completed"
                        )
                        assert result["status"] == expected, result
                        reported_models += result["model_calls"]
                        assert all(r["verification"]["passed"] for r in result["receipts"])
                    else:
                        events = list(state.chat.stream_turn(cid, command))
                        assert events[-1]["type"] == "final", events
                        metadata = events[-1]["metadata"]
                        reported_models += metadata["model_calls"]
                        assert metadata["mode"] == "fast"
                        assert all(r["verification"]["passed"] for r in metadata["app_receipts"])
                    durations.append((time.perf_counter() - before) * 1000)
                    verify(state, case, size)
                    state.inbox.shutdown()
                    shutil.rmtree(data)
                counters["reported_model_calls"] += reported_models
                row = {
                    "scenario": case,
                    "items": size,
                    "layer": layer,
                    "latency": summary(durations),
                    "app_initialization": summary(initialization),
                    "model_calls": reported_models,
                    "supervisor_calls": 0,
                }
                results.append(row)
                print(
                    f"{case}/{size}/{layer}: p50={row['latency']['p50_ms']}ms "
                    f"p95={row['latency']['p95_ms']}ms",
                    flush=True,
                )
    assert not any(counters.values()), counters
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "started_at": started_at,
        "profile": profile,
        "source_sha256": source_sha256,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "samples_per_layer": samples,
        "method": {
            "percentile": "nearest rank p95; median p50",
            "data": "fresh disposable SQLite+Markdown copies per operation, outside timing",
            "cold": "app_initialization measures fresh Service/App; first_ms is first observation",
            "warm": "modules imported once; operations use warm interpreter and fresh App/data",
            "cache": "OS cache not flushed; true cold process/import/device latency not measured",
            "excluded": "seeding/copy, assertions, shutdown, HTTP/SSE/browser rendering",
            "workers": "workers not started; synchronous local Service/Dispatcher/Fast/Chat path",
            "comparisons": "independent layers; subtracting medians only estimates overhead",
            "credentials": "empty env file; credential/provider env removed; model/network blocked",
        },
        "counters": counters,
        "results": results,
    }


def markdown(report: dict) -> str:
    gateway = report.get("profile") == "gateway"
    sizes = sorted(
        {row["items"] for row in report["results"] if row["scenario"] == "inbox.archive_all"}
    )
    reproduction = (
        "PYTHONPATH=src python scripts/benchmark_app_fast.py "
        f"--samples {report['samples_per_layer']}"
        + " --bulk-sizes "
        + " ".join(str(size) for size in sizes)
        + (" --profile gateway" if gateway else "")
    )
    lines = [
        "# Offline Fast performance",
        "",
        f"Generated: {report['generated_at']}",
        "",
        f"Python {report['python']}; {report['platform']}; "
        f"{report['samples_per_layer']} samples per scenario/layer.",
        "",
        "| Scenario | Items | Layer | p50 ms | p95 ms | First ms | Model / Supervisor |",
        "|---|---:|---|---:|---:|---:|---:|",
    ]
    for row in report["results"]:
        latency = row["latency"]
        lines.append(
            f"| {row['scenario']} | {row['items']} | {row['layer']} | "
            f"{latency['p50_ms']} | {latency['p95_ms']} | {latency['first_ms']} | "
            f"{row['model_calls']} / {row['supervisor_calls']} |"
        )
    lines += [
        "",
        "All model calls, Supervisor runtime calls and network attempts: **0**.",
        "",
        "Each measured write is new, verified durable state; receipt replay is not timed. "
        + (
            "Latest Gateway samples cover 100-item Inbox archival and link→folder workflow. "
            "The earlier 1000-item full matrix is separately labeled below."
            if gateway
            else "The 100/1000-item Inbox cases run real local classification "
            "and Markdown/SQLite writes. "
            "Today uses the shared TaskService, without an inferred date. Unknown commands clarify "
            "through Fast/Chat and have no comparable Service action."
        ),
        "",
    ]
    lines += [f"- {key}: {value}" for key, value in report["method"].items()]
    lines += [
        "",
        "Raw samples and separate fresh App initialization timings are in fast-performance.json.",
        "Chat timing includes real conversation reads, user/assistant persistence and in-process "
        "event construction. It excludes HTTP/SSE transfer and frontend rendering.",
        "",
        f"Reproduce this phase: `{reproduction}`",
        "",
    ]
    return "\n".join(lines)


def combined_markdown(report: dict, baseline: dict) -> str:
    return (
        "# Final Gateway performance and earlier core baseline\n\n"
        "Latest measurements include ExecutionGateway policy/hooks/audit. "
        "Source SHA256 fingerprints are in JSON.\n\n"
        + markdown(report).replace("# Offline Fast performance", "## Latest Gateway measurements")
        + "\n\n## Earlier measurements — before Gateway integration\n\n"
        + baseline["source_scope"]
        + "\n\n"
        + markdown(baseline).replace("# Offline Fast performance", "### Earlier full matrix")
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samples", type=int, default=12)
    parser.add_argument("--bulk-sizes", type=int, nargs="+", default=[100, 1000])
    parser.add_argument("--profile", choices=["full", "gateway"], default="full")
    parser.add_argument(
        "--baseline", type=Path, help="Pre-Gateway JSON to label separately in the combined report"
    )
    parser.add_argument("--output", type=Path, default=ROOT / "docs" / "audit")
    args = parser.parse_args()
    if args.samples < 1 or any(size < 1 for size in args.bulk_sizes):
        parser.error("samples and bulk sizes must be positive")
    baseline = json.loads(args.baseline.read_text(encoding="utf-8")) if args.baseline else None
    report = benchmark(args.samples, args.bulk_sizes, profile=args.profile)
    args.output.mkdir(parents=True, exist_ok=True)
    if baseline is not None:
        baseline["source_scope"] = (
            "Earlier process loaded Fast before ExecutionGateway integration. Its Fast/Chat data "
            "does not prove final Gateway overhead; 1000-item Service is a core-write baseline."
        )
        (args.output / "fast-performance-before-gateway.json").write_text(
            json.dumps(baseline, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        (args.output / "fast-performance-before-gateway.md").write_text(
            baseline["source_scope"] + "\n\n" + markdown(baseline), encoding="utf-8"
        )
        (args.output / "fast-performance-gateway.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        final_text = combined_markdown(report, baseline)
        report["baseline_before_gateway"] = baseline
        report["source_scope"] = "Latest Gateway samples; earlier full baseline nested separately"
    else:
        final_text = markdown(report)
    (args.output / "fast-performance.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (args.output / "fast-performance.md").write_text(final_text, encoding="utf-8")


if __name__ == "__main__":
    main()
