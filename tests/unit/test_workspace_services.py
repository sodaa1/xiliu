import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier, Event, Thread
from types import SimpleNamespace
from typing import cast

import pytest

from xiliu.api.errors import WebError
from xiliu.api.services.automations import AutomationService
from xiliu.api.services.content import ContentService
from xiliu.api.services.feed import FeedService, normalize_aihot, normalize_github
from xiliu.api.services.model_settings import ModelSettingsService
from xiliu.api.services.tasks import TaskService
from xiliu.api.store import AppStore
from xiliu.capabilities.models import CapabilitySpec
from xiliu.events import FinalEvent, VerifierEvent


def test_feed_normalizes_real_source_payloads():
    html = (
        '<article class="Box-row"><h2><a href="/owner/repo">owner / repo</a></h2>'
        '<p>A tool</p><span itemprop="programmingLanguage">Python</span></article>'
    )
    github = normalize_github(html)
    assert github[0]["title"] == "owner/repo"
    assert github[0]["tags"] == ["Python"]
    assert github[0]["url"] == "https://github.com/owner/repo"
    news = normalize_aihot(
        {
            "items": [
                {
                    "title": "AI news",
                    "links": {
                        "original": "https://example.org/news",
                        "aihot": "https://aihot.example/news",
                    },
                    "summary": "Actual story",
                    "source": {"name": "Example"},
                    "category": "model",
                    "publishedAt": "2026-10-07T12:00:00Z",
                    "score": 42,
                }
            ]
        }
    )
    assert news[0]["source"] == "aihot"
    assert news[0]["summary"] == "Actual story"
    assert news[0]["url"] == "https://example.org/news"
    assert news[0]["tags"] == ["model"]
    assert news[0]["metadata"]["source_name"] == "Example"


def test_feed_preserves_cache_on_failure_and_save_is_idempotent(tmp_path, monkeypatch):
    store = AppStore(tmp_path)
    content = ContentService(store)
    feed = FeedService(store, content)
    story = normalize_aihot([{"title": "Story", "url": "https://example.org/story"}])
    monkeypatch.setattr(feed, "_fetch_aihot", lambda: story)
    monkeypatch.setattr(feed, "_fetch_github", lambda: [])
    assert feed.refresh()["items"] == story
    monkeypatch.setattr(feed, "_fetch_aihot", lambda: (_ for _ in ()).throw(TimeoutError()))
    cached = feed.refresh()
    assert cached["items"] == story
    assert cached["sources"][0]["status"] == "error"
    saved = feed.save(story[0]["id"])
    assert saved["type"] == "link"
    assert saved["status"] == "inbox"
    assert FeedService(feed.store, content).save(story[0]["id"])["id"] == saved["id"]
    content.delete(saved["id"])
    assert feed.save(story[0]["id"])["id"] != saved["id"]


def test_feed_save_deduplicates_between_service_instances(tmp_path, monkeypatch):
    store = AppStore(tmp_path)
    first_content, second_content = ContentService(store), ContentService(store)
    first, second = FeedService(store, first_content), FeedService(store, second_content)
    story = normalize_aihot([{"title": "Story", "url": "https://example.org/story"}])
    monkeypatch.setattr(first, "_fetch_aihot", lambda: story)
    monkeypatch.setattr(first, "_fetch_github", lambda: [])
    first.refresh()
    gate = Barrier(2)

    def coordinated(original):
        def create(payload, *, dedupe_key=None):
            gate.wait(timeout=5)
            return original(payload, dedupe_key=dedupe_key)

        return create

    monkeypatch.setattr(first_content, "create", coordinated(first_content.create))
    monkeypatch.setattr(second_content, "create", coordinated(second_content.create))
    with ThreadPoolExecutor(max_workers=2) as workers:
        results = list(workers.map(lambda service: service.save(story[0]["id"]), [first, second]))
    assert results[0]["id"] == results[1]["id"]
    assert len(first_content.list(status="inbox")) == 1


def test_task_crud_persists_and_validates(tmp_path):
    tasks = TaskService(AppStore(tmp_path))
    task = tasks.create({"title": "Write report", "due_at": "2026-10-07T12:00:00+00:00"})
    assert tasks.update(task["id"], {"completed": True})["completed"] is True
    assert TaskService(AppStore(tmp_path)).list()[0]["id"] == task["id"]
    with pytest.raises(WebError):
        tasks.create({"title": " "})
    with pytest.raises(WebError):
        tasks.update(task["id"], {"due_at": "tomorrow"})
    assert tasks.update(task["id"], {"due_at": "20261007"})["due_at"] == "2026-10-07T00:00:00"
    tasks.delete(task["id"])
    assert tasks.list() == []


def test_aihot_refresh_honors_policy_and_tool_hooks(tmp_path, monkeypatch):
    calls = []
    hooks = []

    class FakeMCP:
        def __init__(self, _root):
            pass

        def servers(self):
            return ["aihot"]

        def transport(self, _server):
            return "http"

        def tools(self, _server):
            return [
                CapabilitySpec(
                    id="mcp:aihot:aihot_get_latest",
                    kind="mcp",
                    name="aihot_get_latest",
                    description="Latest news",
                    source_id="aihot",
                )
            ]

        def schema(self, _capability):
            return {"properties": {"limit": {"default": 5}}, "required": ["limit"]}

        def permission_for_tool(self, _capability):
            return "network.read"

        def call(self, capability, arguments):
            calls.append((capability, arguments))
            return {
                "ok": True,
                "structured_content": {
                    "items": [{"title": "Actual story", "url": "https://example.org/news"}]
                },
            }

        def close(self):
            pass

    monkeypatch.setattr("xiliu.api.services.feed.MCPManager", FakeMCP)
    monkeypatch.setattr(
        "xiliu.api.services.feed.HookEngine.before",
        lambda _self, **kwargs: (hooks.append(kwargs["tool_name"]) or [], False),
    )
    policy = tmp_path / "policy.json"
    policy.write_text(json.dumps({"profiles": {"interactive": {"network.read": "deny"}}}))
    store = AppStore(tmp_path)
    feed = FeedService(store, ContentService(store))
    with pytest.raises(WebError):
        feed._fetch_aihot()
    assert calls == []
    policy.write_text(json.dumps({"profiles": {"interactive": {"network.read": "allow"}}}))
    assert feed._fetch_aihot()[0]["title"] == "Actual story"
    assert calls == [("mcp:aihot:aihot_get_latest", {"limit": 5})]
    assert hooks == ["mcp_call"]


def test_automation_crud_uses_existing_store_and_honors_owner(tmp_path):
    settings = SimpleNamespace(runtime_settings=lambda: None)
    service = AutomationService(Path(tmp_path), cast(ModelSettingsService, settings))
    task = service.create({"name": "Daily", "prompt": "Read news", "hour": 9, "minute": 0})
    stored = service.store.get(task["id"])
    assert stored is not None
    assert stored.trigger_type == "cron"
    assert service.toggle(task["id"], False)["enabled"] is False
    assert service.store.acquire_owner("existing-cli")
    service.start()
    assert service.scheduler_active is False
    service.shutdown()
    service.store.release_owner("existing-cli")
    service.start()
    try:
        assert service.scheduler_active is True
        service.toggle(task["id"], True)
        assert service.scheduler.get_job(task["id"]) is not None
    finally:
        service.shutdown()
    service.delete(task["id"])
    assert service.list() == []


def test_automation_runs_do_not_expose_provider_errors(tmp_path):
    service = AutomationService(
        tmp_path, cast(ModelSettingsService, SimpleNamespace(runtime_settings=lambda: None))
    )
    task = service.create({"name": "Daily", "prompt": "Read news", "hour": 9, "minute": 0})
    service.store.claim_run(task["id"], "manual:test", "run")
    service.store.finish_run(
        "run", status="failed", trace_id=None, result_path=None, error="api_key=secret"
    )
    run = service.runs(task["id"])[0]
    assert "secret" not in str(run)
    assert run["status"] == "failed"


def test_automation_resolves_fresh_settings_only_when_running(tmp_path, monkeypatch):
    reads = []
    models = []

    def settings():
        model = f"configured-model-{len(reads)}"
        reads.append(model)
        return SimpleNamespace(model_copy=lambda update: SimpleNamespace(model=model, **update))

    monkeypatch.setattr(
        "xiliu.api.services.automations.create_runtime",
        lambda config, **_kwargs: models.append((config.model, config.data_dir)),
    )
    service = AutomationService(
        tmp_path, cast(ModelSettingsService, SimpleNamespace(runtime_settings=settings))
    )
    service.create({"name": "Daily", "prompt": "Read news", "hour": 9, "minute": 0})
    assert reads == []
    service._runtime(None)
    service._runtime(None)
    assert models == [("configured-model-0", tmp_path), ("configured-model-1", tmp_path)]


def test_automation_shutdown_drains_run_and_retains_owner(tmp_path, monkeypatch):
    entered, release, closed, stopping = Event(), Event(), Event(), Event()
    observed_wait = []

    class BlockingRuntime:
        last_trace_id = None

        def stream(self, *_args):
            entered.set()
            assert release.wait(10)
            yield VerifierEvent(passed=True, reason="Verified", attempt=1)
            yield FinalEvent(text="Completed", session_id="test")

        def close(self):
            closed.set()

    settings = SimpleNamespace(
        runtime_settings=lambda: SimpleNamespace(model_copy=lambda **_: None)
    )
    monkeypatch.setattr(
        "xiliu.api.services.automations.create_runtime", lambda *_args, **_kwargs: BlockingRuntime()
    )
    service = AutomationService(tmp_path, cast(ModelSettingsService, settings))
    task = service.create({"name": "Daily", "prompt": "Read news", "hour": 9, "minute": 0})
    service.start()
    scheduler = service.scheduler
    original_shutdown = scheduler.shutdown

    def tracking_shutdown(*, wait=False):
        observed_wait.append(wait)
        stopping.set()
        original_shutdown(wait=wait)

    monkeypatch.setattr(scheduler, "shutdown", tracking_shutdown)
    scheduler._scheduler.add_job(scheduler._execute, trigger="date", args=[task["id"]])
    worker = Thread(target=service.shutdown)
    try:
        assert entered.wait(5)
        worker.start()
        assert stopping.wait(5)
        assert observed_wait == [True]
        assert worker.is_alive()
        service.sync()
        service.start()
        assert service.scheduler is scheduler
        assert not service.store.acquire_owner("contender")
        assert service.runs(task["id"])[0]["status"] == "running"
    finally:
        release.set()
        if worker.ident is not None:
            worker.join(timeout=5)
        else:
            service.shutdown()
    assert not worker.is_alive()
    assert closed.is_set()
    assert service.runs(task["id"])[0]["status"] == "success"
    service.sync()
    assert service.scheduler_active is False
    assert service.store.acquire_owner("contender")
    service.store.release_owner("contender")
