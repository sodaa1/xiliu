import importlib
import importlib.util
import time
from threading import Event

import pytest

from xiliu.api.app import create_app
from xiliu.api.services.inbox import InboxService
from xiliu.app.dispatch import AppDispatcher
from xiliu.execution.gateway import RunContext
from xiliu.policy.engine import PolicyEngine


@pytest.fixture
def app(tmp_path):
    app = create_app(data_dir=tmp_path / "data", env_file=tmp_path / ".env")
    try:
        yield app
    finally:
        app.state.inbox.shutdown()


def run(text, app, **kwargs):
    module = "xiliu.app.fast"
    assert importlib.util.find_spec(module) is not None, "deterministic App Fast executor missing"
    path = app.state.store.path.parent
    context = kwargs.pop(
        "context",
        RunContext("same-turn", "session", path, policy_engine=PolicyEngine(path / "policy.json")),
    )
    return importlib.import_module(module).run_app_fast(text, app.state, context, **kwargs)


def test_local_task_create_and_replay_use_zero_model_calls_and_real_service(app):
    result = run("创建待办‘读书’", app)
    assert result["status"] == "completed" and result["model_calls"] == 0
    assert result["receipts"][-1]["verification"]["passed"]
    assert app.state.tasks.list()[0]["title"] == "读书"
    assert run("创建待办‘读书’", app)["status"] == "completed"
    assert len(app.state.tasks.list()) == 1


def test_screenshot_collection_saves_link_to_existing_folder_without_model(app):
    folder = app.state.knowledge.create_folder({"name": "科研"})
    text = "https://infmind.cn/ 帮我收藏一下这个网站，整理到知识库，归类到科研下面"
    result = run(text, app)
    assert result["status"] == "completed" and result["model_calls"] == 0
    assert all(receipt["verification"]["passed"] for receipt in result["receipts"])
    saved = app.state.content.list("knowledge")
    assert len(saved) == 1 and saved[0]["folder_id"] == folder["id"]
    assert saved[0]["source"] == saved[0]["content"] == "https://infmind.cn/"
    assert len(app.state.knowledge.list_folders()) == 1


def test_unique_task_completion_and_ambiguous_match_never_guess(app):
    first = app.state.tasks.create({"title": "读书"})
    assert run("完成待办‘读书’", app)["status"] == "completed"
    assert app.state.tasks.list()[0]["completed"] is True
    app.state.tasks.create({"title": "读书"})
    assert run("删除待办‘读书’", app)["status"] == "clarification_required"
    assert len(app.state.tasks.list()) == 2
    result = run(f"删除待办‘{first['id']}’", app)
    assert result["status"] == "confirmation_required"
    assert result["receipts"][-1]["confirmation_id"]
    assert len(app.state.tasks.list()) == 2


def test_negative_app_request_never_calls_model_or_writes(app):
    class Model:
        def with_structured_output(self, schema):
            pytest.fail("negative instructions must bypass the intent model")

    result = run("如果我要删除Feed资讯应该怎么做？", app, model=Model())
    assert result["status"] == "explanation" and result["receipts"] == []
    assert not app.state.feed.list()["items"]


def test_model_fallback_calls_once_and_cannot_select_restricted_actions(app):
    class Model:
        calls = 0

        def with_structured_output(self, schema):
            return self

        def invoke(self, messages):
            self.calls += 1
            return {
                "kind": "write",
                "domain": "conversations",
                "action_id": "conversations.delete",
                "arguments": {"cid": "whatever"},
                "selector": None,
                "scope": "single",
                "confidence": 0.99,
            }

    model = Model()
    result = run("帮我处理会话", app, model=model)
    assert model.calls == 1 and result["model_calls"] == 1
    assert result["status"] in {"clarification_required", "failed"}
    assert not app.state.store.list()


def test_valid_typed_model_fallback_can_only_execute_the_selected_registered_action(app):
    class Model:
        calls = 0

        def with_structured_output(self, schema):
            return self

        def invoke(self, messages):
            self.calls += 1
            return {
                "kind": "write",
                "domain": "tasks",
                "action_id": "tasks.create",
                "arguments": {"title": "读论文"},
                "selector": None,
                "scope": "single",
                "confidence": 0.99,
            }

    model = Model()
    result = run("帮我安排待办读论文", app, model=model)
    assert result["status"] == "completed" and model.calls == result["model_calls"] == 1
    assert app.state.tasks.list()[0]["title"] == "读论文"


def test_local_feed_url_save_never_fetches_or_uses_inbox(app, monkeypatch):
    monkeypatch.setattr(
        app.state.feed, "refresh", lambda: pytest.fail("URL saving must be offline")
    )
    result = run("给Feed加入https://example.com/story作为资讯，只存链接", app)
    assert result["status"] == "completed", result
    assert app.state.feed.list()["items"][0]["url"] == "https://example.com/story"
    assert not app.state.content.list("inbox")


def test_exact_folder_url_workflow_is_bounded_local_and_replay_safe(app):
    url = "https://github.com/CHENG-LIANG1/real-company-interview-ai-coding-projects"
    text = f"在知识库创建一个叫面试的文件夹，把 {url} 先放Inbox生成标签再归档，只保存链接不要克隆"
    app.state.inbox.metadata = lambda item: pytest.fail("local workflow cannot call AI metadata")
    before = time.monotonic()
    result = run(text, app)
    assert time.monotonic() - before < 2
    assert result["status"] == "completed" and result["model_calls"] == 0
    folder = app.state.knowledge.list_folders()[0]
    cards = app.state.knowledge.folder_items(folder["id"])
    assert folder["name"] == "面试" and len(cards) == 1
    assert cards[0]["source"] == cards[0]["content"] == url
    assert cards[0]["type"] == "link" and cards[0]["filename"] is None
    assert cards[0]["processing_status"] == "ready"
    assert all(receipt["verification"]["passed"] for receipt in result["receipts"])
    assert run(text, app)["status"] == "completed"
    assert len(app.state.knowledge.folder_items(folder["id"])) == 1


def test_bulk_archive_uses_current_inbox_snapshot_and_handles_empty(app):
    assert run("将Inbox里面内容分类归入知识库", app)["status"] == "completed"
    app.state.content.create({"type": "note", "title": "笔记", "content": "笔记"})
    context = RunContext("next-turn", "session", app.state.store.path.parent)
    result = run("把我收件箱里还没整理的内容都搬到知识库", app, context=context)
    assert result["status"] == "completed"
    assert len(app.state.content.list("knowledge")) == 1
    assert not app.state.content.list("inbox")


def test_scope_permission_and_ambiguous_dates_reject_without_writes(app):
    path = app.state.store.path.parent
    (path / "policy.json").write_text('{"profiles":{"interactive":{"tasks.write":"deny"}}}')
    assert run("创建待办‘被拒绝’", app)["status"] == "failed"
    assert run("帮我创建一个明天下午的待办‘读书’", app)["status"] == "clarification_required"
    assert not app.state.tasks.list()


def test_replayed_fast_receipt_still_respects_revoked_policy(app):
    assert run("创建待办‘读书’", app)["status"] == "completed"
    path = app.state.store.path.parent
    (path / "policy.json").write_text('{"profiles":{"interactive":{"tasks.write":"deny"}}}')
    assert run("创建待办‘读书’", app)["status"] == "failed"
    assert len(app.state.tasks.list()) == 1


@pytest.mark.parametrize(
    "payload",
    [
        {
            "kind": "write",
            "domain": "tasks",
            "action_id": "tasks.create",
            "arguments": {"title": "Invented task"},
        },
        {
            "kind": "write",
            "domain": "tasks",
            "action_id": "tasks.complete",
            "arguments": {},
            "selector": "Protected",
        },
        {"kind": "write", "domain": "tasks", "action_id": "conversations.create", "arguments": {}},
        {
            "kind": "write",
            "domain": "tasks",
            "action_id": "tasks.create",
            "arguments": {"title": "待办"},
            "extra_untrusted": "ignored?",
        },
    ],
)
def test_model_cannot_invent_entities_cross_domains_or_add_unvalidated_fields(app, payload):
    app.state.tasks.create({"title": "Protected"})

    class Model:
        calls = 0

        def with_structured_output(self, schema):
            return self

        def invoke(self, messages):
            self.calls += 1
            return {"selector": None, "scope": "single", "confidence": 0.99, **payload}

    model = Model()
    result = run("帮我处理待办", app, model=model)
    assert model.calls == 1 and result["status"] == "clarification_required"
    assert len(app.state.tasks.list()) == 1 and app.state.tasks.list()[0]["completed"] is False
    assert not app.state.store.list()


def test_ai_metadata_workflow_returns_pending_without_waiting_for_external_model(app):
    url = "https://example.com/interview"
    app.state.inbox.metadata = lambda item: pytest.fail("Fast must return before AI work")
    before = time.monotonic()
    result = run(f"创建知识库文件夹‘面试’把{url}先放入Inbox用AI生成标签再归档", app)
    assert time.monotonic() - before < 2
    assert result["status"] == "pending"
    assert app.state.content.list("inbox")[0]["processing_status"] == "pending"
    assert not app.state.content.list("knowledge")


def archive_receipt(result):
    receipt = result["receipts"][-1]
    assert receipt["action_id"] == "inbox.archive_after_metadata"
    assert receipt["verification"]["passed"]
    return receipt["data"]


def wait_archive(inbox, job_id):
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        job = inbox.get_archive_job(job_id)
        if job["status"] not in {"pending", "running"}:
            return job
        Event().wait(0.01)
    pytest.fail("owned Inbox worker did not finish the durable archive job")


def test_fast_ai_pending_job_completes_without_a_second_user_instruction(app):
    entered, release = Event(), Event()
    calls = []

    def metadata(item):
        calls.append(item["id"])
        entered.set()
        assert release.wait(3)
        return {"title": "面试资料", "summary": "内容摘要", "tags": ["面试"]}

    app.state.inbox.metadata = metadata
    app.state.inbox.start()
    text = "创建知识库文件夹‘面试’把https://example.com/interview先放入Inbox用AI生成标签再归档"
    try:
        before = time.monotonic()
        result = run(text, app)
        assert time.monotonic() - before < 2 and result["status"] == "pending"
        job = archive_receipt(result)
        assert entered.wait(1)
        assert app.state.inbox.get_archive_job(job["job_id"])["status"] == "pending"
        release.set()
        assert wait_archive(app.state.inbox, job["job_id"])["status"] == "completed"
        saved = app.state.content.get(job["item_id"])
        assert saved["folder_id"] == job["folder_id"] and saved["status"] == "knowledge"
        assert saved["source"] == "https://example.com/interview" and saved["tags"] == ["面试"]
        assert saved["processing_status"] == "ready" and calls == [saved["id"]]
        replayed = archive_receipt(run(text, app))
        assert replayed["job_id"] == job["job_id"]
        assert len(app.state.content.list("knowledge")) == 1
    finally:
        release.set()


def test_fast_ai_pending_archive_survives_service_restart_and_has_registered_readback(app):
    text = "创建知识库文件夹‘面试’把https://example.com/interview先放入Inbox用AI生成标签再归档"
    result = run(text, app)
    job = archive_receipt(result)
    assert result["status"] == "pending"
    restarted = InboxService(
        app.state.content,
        app.state.knowledge,
        metadata=lambda item: {
            "title": "重启整理",
            "summary": "摘要",
            "tags": ["面试"],
        },
    )
    try:
        restarted.start()
        assert wait_archive(restarted, job["job_id"])["status"] == "completed"
        context = RunContext("job-read", "session", app.state.store.path.parent)
        receipt = AppDispatcher(app.state, context).execute(
            "inbox.archive_job", {"job_id": job["job_id"]}, request_id="job-readback"
        )
        assert receipt["ok"] and receipt["data"]["status"] == "completed"
        assert receipt["data"]["folder_id"] == job["folder_id"]
        assert archive_receipt(run(text, app))["job_id"] == job["job_id"]
        assert len(app.state.content.list("knowledge")) == 1
    finally:
        restarted.shutdown()


@pytest.mark.parametrize(
    "text",
    [
        "帮我处理Feed‘资料’",
        "帮我处理Feed‘资料’，备注写‘抓取标题’",
        "帮我处理Feed‘资料’ https://example.com/抓取标题",
    ],
)
def test_model_nested_fetch_title_requires_explicit_instruction_before_any_write(
    app, monkeypatch, text
):
    item = app.state.feed.add_manual({"url": "https://example.com/story", "title": "资料"})
    monkeypatch.setattr(
        app.state.feed, "update_manual", lambda *a, **k: pytest.fail("unauthorized fetch")
    )

    class Model:
        def with_structured_output(self, schema):
            return self

        def invoke(self, messages):
            return {
                "kind": "write",
                "domain": "feed",
                "action_id": "feed.update_manual",
                "selector": "资料",
                "arguments": {"changes": {"fetch_title": True}},
                "confidence": 0.99,
            }

    result = run(text, app, model=Model())
    assert result["status"] == "clarification_required" and result["receipts"] == []
    assert app.state.feed.list()["items"][0]["id"] == item["id"]


@pytest.mark.parametrize(
    "text",
    [
        "创建知识库文件夹‘面试’把https://example.com/AI先放入Inbox生成标签再归档",
        "创建知识库文件夹‘AI’把https://example.com/interview先放入Inbox生成标签再归档",
        "创建知识库文件夹‘面试’把https://example.com/interview先放入Inbox生成标签再归档，AI是资料主题",
    ],
)
def test_ai_mentions_in_data_or_topic_do_not_enable_metadata_model(app, text):
    result = run(text, app)
    assert result["status"] == "completed" and result["model_calls"] == 0
    assert app.state.content.list("knowledge")[0]["ai_processed"] is False


def test_model_cannot_enable_ai_processing_without_explicit_tag_generation_request(app):
    class Model:
        def with_structured_output(self, schema):
            return self

        def invoke(self, messages):
            return {
                "kind": "write",
                "domain": "inbox",
                "action_id": "inbox.import_text",
                "arguments": {"text": "Inbox资料AI主题", "use_ai": True},
                "confidence": 0.99,
            }

    result = run("帮我处理Inbox资料AI主题", app, model=Model())
    assert result["status"] == "clarification_required" and not result["receipts"]
    assert not app.state.content.list("inbox")


def test_explicit_nested_title_fetch_is_allowed_with_real_saved_receipt(app, monkeypatch):
    item = app.state.feed.add_manual({"url": "https://example.com/story", "title": "资料"})
    original = app.state.feed.update_manual
    calls = []

    def fetch(item_id, changes):
        calls.append(changes)
        return original(item_id, {"title": "已抓取标题"})

    monkeypatch.setattr(app.state.feed, "update_manual", fetch)

    class Model:
        def with_structured_output(self, schema):
            return self

        def invoke(self, messages):
            return {
                "kind": "write",
                "domain": "feed",
                "action_id": "feed.update_manual",
                "selector": "资料",
                "arguments": {"changes": {"fetch_title": True}},
                "confidence": 0.99,
            }

    result = run("帮我处理Feed‘资料’，请抓取标题", app, model=Model())
    assert result["status"] == "completed" and calls == [{"fetch_title": True}]
    assert result["receipts"][-1]["verification"]["passed"]
    assert app.state.feed.list()["items"][0]["id"] == item["id"]
    assert app.state.feed.list()["items"][0]["title"] == "已抓取标题"


def test_explicit_ai_opt_out_remains_local(app):
    text = "创建知识库文件夹‘面试’把https://example.com/interview先放入Inbox，不用AI生成标签再归档"
    result = run(text, app)
    assert result["status"] == "completed" and result["model_calls"] == 0
    assert app.state.content.list("knowledge")[0]["ai_processed"] is False


def test_explicit_title_fetch_opt_out_only_saves_link(app, monkeypatch):
    original = app.state.feed.add_manual

    def save(payload):
        assert payload["fetch_title"] is False
        return original(payload)

    monkeypatch.setattr(app.state.feed, "add_manual", save)
    result = run("给Feed加入https://example.com/story，不用抓取标题，只保存链接", app)
    assert result["status"] == "completed"


def test_quoted_network_verb_cannot_authorize_model_feed_refresh(app, monkeypatch):
    monkeypatch.setattr(app.state.feed, "refresh", lambda: pytest.fail("no network instruction"))

    class Model:
        def with_structured_output(self, schema):
            return self

        def invoke(self, messages):
            return {
                "kind": "read",
                "domain": "feed",
                "action_id": "feed.refresh",
                "arguments": {},
                "confidence": 0.99,
            }

    result = run("帮我处理Feed，备注是‘刷新’", app, model=Model())
    assert result["status"] == "clarification_required" and result["receipts"] == []


@pytest.mark.parametrize(
    "text", ["将Inbox全部用AI生成标签后归档", "把‘资料’用AI生成标签整理到知识库"]
)
def test_explicit_ai_classify_returns_durable_pending_then_real_worker_archives(app, text):
    item = app.state.content.create({"title": "资料", "content": "真实资料"})
    before = time.monotonic()
    result = run(text, app)
    assert time.monotonic() - before < 2 and result["status"] == "pending", result
    batch = result["receipts"][-1]["data"]
    assert batch["job_id"] and batch["counts"]["pending"] == 1
    assert app.state.content.get(item["id"])["status"] == "inbox"
    app.state.inbox.metadata = lambda _item: {
        "title": "AI真实标题",
        "summary": "摘要",
        "tags": ["未匹配"],
    }
    app.state.inbox.start()
    actual = wait_archive(app.state.inbox, batch["job_id"])
    assert actual["status"] == "completed"
    saved = app.state.content.get(item["id"])
    assert (
        saved["status"] == "knowledge" and saved["ai_processed"] and saved["title"] == "AI真实标题"
    )


def test_explicit_ai_import_template_preserves_ai_request_and_returns_pending(app):
    result = run("把‘资料’导入Inbox并用AI生成标签", app)
    assert result["status"] == "pending" and result["model_calls"] == 0
    item = app.state.content.list("inbox")[0]
    with app.state.store.connect() as db:
        assert (
            db.execute("SELECT use_ai FROM inbox_jobs WHERE item_id=?", (item["id"],)).fetchone()[0]
            == 1
        )
