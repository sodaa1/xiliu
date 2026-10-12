import json
from threading import Event
from time import monotonic
from uuid import uuid4

import pytest

from xiliu.api.app import create_app
from xiliu.execution.gateway import ExecutionGateway, RunContext, active_run
from xiliu.policy.engine import PolicyEngine
from xiliu.routing import recognize_intent, select_execution
from xiliu.tools.app import build_app_tool

URL = "https://github.com/CHENG-LIANG1/real-company-interview-ai-coding-projects"
TASK = (
    f"{URL} 在知识库创建一个叫面试的文件夹把这个链接放进去，"
    "只放链接不用克隆，先放入inbox生成标签再放入知识库"
)


def test_exact_folder_import_request_uses_write_workflow():
    assert select_execution(recognize_intent(TASK, model=object())) == "app_executor"


@pytest.fixture
def application(tmp_path):
    env = tmp_path / ".env"
    env.write_text("XILIU_API_KEY=fake\nXILIU_MODEL=deepseek-v4-flash\n")
    app = create_app(data_dir=tmp_path / "data", env_file=env)
    app.state.inbox.metadata = lambda item: {
        "title": "公司面试项目",
        "summary": "面试编程资料",
        "tags": ["面试", "Python"],
    }
    try:
        yield app
    finally:
        app.state.inbox.shutdown()


def execute(app, action_id, arguments, *, context=None):
    context = context or RunContext(
        "test",
        "test",
        app.state.store.path.parent,
        app_services=app.state.app_services,
        policy_engine=PolicyEngine(app.state.store.path.parent / "policy.json"),
    )
    token = active_run.set(context)
    try:
        return json.loads(
            ExecutionGateway().invoke(
                build_app_tool(),
                {
                    "operation": "execute",
                    "action_id": action_id,
                    "arguments": arguments,
                },
                context,
            )
        )
    finally:
        active_run.reset(token)


def complete_archive(application, job_id):
    application.state.inbox.start()
    deadline = monotonic() + 3
    while monotonic() < deadline:
        actual = application.state.inbox.get_archive_job(job_id)
        if actual["status"] not in {"pending", "running"}:
            return actual
        Event().wait(0.01)
    pytest.fail("metadata archive job did not finish")


def test_folder_tool_reuses_existing_folder_and_is_registered_as_write(application):
    from xiliu.app.actions import get_registry

    first = execute(application, "knowledge.folders.ensure", {"name": "面试"})
    second = execute(application, "knowledge.folders.ensure", {"name": "面试"})
    assert first["ok"] and second["ok"]
    assert first["records"][0]["id"] == second["records"][0]["id"]
    assert len(application.state.knowledge.list_folders()) == 1
    assert get_registry()["knowledge.folders.ensure"].permission == "knowledge.write"


def test_target_folder_waits_for_inbox_tags_and_preserves_link_only(application):
    folder = application.state.knowledge.create_folder({"name": "面试"})
    item = application.state.inbox.import_item({"text": URL, "use_ai": True})
    assert item["status"] == "inbox"
    result = execute(
        application,
        "inbox.classify_selected",
        {
            "item_ids": [item["id"]],
            "folder_id": folder["id"],
            "use_ai": True,
        },
    )
    assert result["ok"]
    assert result["data"]["status"] == "pending"
    assert complete_archive(application, result["data"]["job_id"])["status"] == "completed"
    saved = application.state.content.get(item["id"])
    assert saved["status"] == "knowledge" and saved["folder_id"] == folder["id"]
    assert saved["tags"] == ["面试", "Python"]
    assert saved["processing_status"] == "ready"
    assert saved["source"] == saved["content"] == URL
    assert saved["type"] == "link" and saved["filename"] is None


def test_invalid_target_folder_does_not_move_card(application):
    item = application.state.inbox.import_item({"text": URL, "use_ai": False})
    result = execute(
        application,
        "inbox.classify_selected",
        {
            "item_ids": [item["id"]],
            "folder_id": str(uuid4()),
        },
    )
    assert not result["ok"] and result["error"] == "folder_not_found"
    assert application.state.content.get(item["id"])["status"] == "inbox"


def test_manual_edit_during_metadata_is_not_overwritten_by_target_move(application):
    requested = application.state.knowledge.create_folder({"name": "面试"})
    other = application.state.knowledge.create_folder({"name": "人工选择"})

    def metadata(item):
        application.state.content.update(
            item["id"], {"status": "knowledge", "folder_id": other["id"], "tags": ["人工"]}
        )
        return {"title": "自动标题", "summary": "自动摘要", "tags": ["面试"]}

    application.state.inbox.metadata = metadata
    item = application.state.inbox.import_item({"text": URL})
    result = execute(
        application,
        "inbox.classify_selected",
        {
            "item_ids": [item["id"]],
            "folder_id": requested["id"],
            "use_ai": True,
        },
    )
    assert result["ok"] and result["data"]["status"] == "pending"
    assert complete_archive(application, result["data"]["job_id"])["status"] == "conflict"
    saved = application.state.content.get(item["id"])
    assert saved["folder_id"] == other["id"] and saved["tags"] == ["人工"]


def test_verification_rejects_knowledge_card_without_requested_folder(application, monkeypatch):
    folder = application.state.knowledge.create_folder({"name": "面试"})
    item = application.state.content.create(
        {"type": "link", "source": URL, "content": URL, "status": "knowledge", "title": "link"}
    )
    monkeypatch.setattr(application.state.content, "update", lambda *args, **kwargs: item)
    result = execute(
        application,
        "inbox.move",
        {
            "item_id": item["id"],
            "folder_id": folder["id"],
            "expected_revision": item["revision"],
        },
    )
    assert not result["ok"] and not result["verification"]["passed"]
    assert application.state.content.get(item["id"])["folder_id"] is None


def test_exact_request_through_fast_creates_folder_and_real_link_card(application):
    from xiliu.app.fast import run_app_fast

    context = RunContext(
        "fast",
        "test",
        application.state.store.path.parent,
        app_services=application.state.app_services,
        policy_engine=PolicyEngine(application.state.store.path.parent / "policy.json"),
    )

    class ForbiddenModel:
        def invoke(self, *args, **kwargs):
            pytest.fail("Explicit local folder workflow must not call Planner")

    result = run_app_fast(TASK, application.state.app_services, context, model=ForbiddenModel())
    assert result is not None and result["status"] == "completed"
    assert result["model_calls"] == 0
    assert result["receipts"] and all(r["verification"]["passed"] for r in result["receipts"])
    folder = application.state.knowledge.list_folders()[0]
    cards = application.state.knowledge.folder_items(folder["id"])
    assert folder["name"] == "面试" and len(cards) == 1
    assert cards[0]["source"] == cards[0]["content"] == URL
    assert cards[0]["type"] == "link" and cards[0]["filename"] is None
    assert cards[0]["processing_status"] == "ready"


@pytest.mark.parametrize("task", ["查看我创建的知识库文件夹", "查找我放入知识库的资料"])
def test_historical_app_actions_remain_readonly(task):
    assert select_execution(recognize_intent(task, model=object())) == "app_executor"


def test_python_url_is_not_a_request_to_write_code():
    route = recognize_intent("https://github.com/python/cpython 放入知识库", model=object())
    assert select_execution(route) == "app_executor"


def test_cancelled_metadata_wait_does_not_start_worker(application):
    from threading import Event

    from xiliu.execution.cancellation import TurnCancelled, cancel_signal

    item = application.state.inbox.import_item({"text": URL})
    signal = Event()
    signal.set()
    token = cancel_signal.set(signal)
    try:
        with pytest.raises(TurnCancelled):
            application.state.inbox.wait_for_metadata(item["id"])
        assert application.state.inbox._thread is None
    finally:
        cancel_signal.reset(token)


def test_wait_timeout_is_bounded(application, monkeypatch):
    from xiliu.api.errors import WebError

    item = application.state.inbox.import_item({"text": URL})
    monkeypatch.setattr(application.state.inbox, "start", lambda: None)
    with pytest.raises(WebError) as error:
        application.state.inbox.wait_for_metadata(item["id"], timeout=0)
    assert error.value.code == "inbox_processing_timeout"


def test_folder_creation_is_rejected_by_write_policy(application):
    policy_file = application.state.store.path.parent / "deny.json"
    policy_file.write_text('{"profiles":{"interactive":{"knowledge.write":"deny"}}}')
    context = RunContext(
        "test",
        "test",
        application.state.store.path.parent,
        app_services=application.state.app_services,
        policy_engine=PolicyEngine(policy_file),
    )
    result = execute(application, "knowledge.folders.ensure", {"name": "面试"}, context=context)
    assert not result["ok"] and result["error"] == "policy_denied"
    assert application.state.knowledge.list_folders() == []


def test_folder_only_action_verifies_database(application):
    from xiliu.graph.verification import _app_action_failure

    result = execute(application, "knowledge.folders.ensure", {"name": "面试"})
    assert result["ok"] and application.state.knowledge.list_folders()[0]["name"] == "面试"
    assert (
        _app_action_failure(
            {
                "task": "在知识库创建一个叫面试的文件夹",
                "tool_events": [
                    {
                        "tool": "app",
                        "ok": True,
                        "args": {
                            "operation": "execute",
                            "action_id": "knowledge.folders.ensure",
                            "arguments": {"name": "面试"},
                        },
                        "output": json.dumps(result),
                    }
                ],
            }
        )
        is None
    )
