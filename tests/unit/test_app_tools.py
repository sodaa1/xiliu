import json
from contextvars import copy_context
from threading import Event, Thread
from time import monotonic

import pytest

from xiliu.api.app import create_app
from xiliu.events import FinalEvent
from xiliu.execution.gateway import ExecutionGateway, RunContext, active_run
from xiliu.policy.engine import PolicyEngine
from xiliu.tools.app import build_app_tool


def execute(app, action_id, arguments, session_id="test"):
    context = RunContext(
        "test",
        session_id,
        app.state.store.path.parent,
        policy_engine=PolicyEngine(app.state.store.path.parent / "policy.json"),
        app_services=app.state.app_services,
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


def test_chat_without_credentials_cannot_import_or_archive_links(tmp_path, monkeypatch):
    monkeypatch.delenv("XILIU_API_KEY", raising=False)
    app = create_app(data_dir=tmp_path / "data", env_file=tmp_path / ".env")
    app.state.chat.runtime_factory = lambda *args, **kwargs: pytest.fail("Configured runtime used")
    cid = app.state.store.create()["id"]
    for text in [
        "将 https://example.com/a 加入 Inbox，只保存链接",
        "将Inbox里面内容分类归入知识库",
    ]:
        events = list(app.state.chat.stream_turn(cid, text))
        assert events[-1]["type"] == "error"
        assert events[-1]["code"] == "model_not_configured"
        assert "设置" in events[-1]["message"]
    assert app.state.content.list("inbox") == []
    assert app.state.content.list("knowledge") == []


def test_chat_can_import_separate_links_and_save_real_knowledge_cards(tmp_path):
    from langchain_core.messages import AIMessage

    from xiliu.runtime import Runtime

    env_file = tmp_path / ".env"
    env_file.write_text("XILIU_API_KEY=fake\nXILIU_MODEL=deepseek-v4-flash\n")
    app = create_app(data_dir=tmp_path / "data", env_file=env_file)
    app.state.inbox._invoke = lambda *args, **kwargs: pytest.fail("Unexpected metadata AI")
    urls = (
        "https://www.reactbits.dev/micro/prompt-bar?radius=3",
        "https://uiverse.io/JohnnyCSilva/jolly-elephant-67",
    )
    models, runtimes = [], []
    actions = [("inbox.import_url", {"url": url, "use_ai": False}) for url in urls]

    class ChatModel:
        def __init__(self, action, arguments):
            self.action, self.arguments = action, arguments
            self.bound = []
            self.executed = False

        def bind_tools(self, tools):
            self.bound.append([tool.name for tool in tools])
            return self

        def invoke(self, messages):
            system = str(messages[0].content)
            if "intent router" in system:
                return AIMessage(
                    content=json.dumps(
                        dict(
                            intent="task",
                            domain="inbox",
                            action="app:match",
                            complexity="simple",
                            preferred_capability="",
                            confidence=1.0,
                        )
                    )
                )
            if "actual_execution_receipts" in str(messages[-1].content):
                return AIMessage(
                    content=json.dumps(dict(status="passed", reason="Actual receipts verified"))
                )
            if not self.executed:
                self.executed = True
                return AIMessage(
                    content="",
                    tool_calls=[
                        dict(
                            id="app-action",
                            name="app",
                            args=dict(
                                operation="execute", action_id=self.action, arguments=self.arguments
                            ),
                        )
                    ],
                )
            return AIMessage(
                content=json.dumps(
                    dict(
                        summary="已保存并核对卡片",
                        plan_summary="执行并核对请求",
                        acceptance_criteria=["请求的卡片已持久化"],
                        ready_for_verification=True,
                    )
                )
            )

    def runtime_factory(settings, **kwargs):
        model = ChatModel(*actions.pop(0))
        models.append(model)
        runtime = Runtime(
            model, data_dir=settings.data_dir, checkpoint_mode="off", trace_mode="off", **kwargs
        )
        runtimes.append(runtime)
        return runtime

    app.state.chat.runtime_factory = runtime_factory
    cid = app.state.store.create()["id"]
    imported = []
    for url in urls:
        events = list(app.state.chat.stream_turn(cid, f"将 {url} 加入 Inbox，只保存链接"))
        assert events[-1]["type"] == "final", events
        metadata = events[-1]["metadata"]
        assert metadata["execution_path"] == "planner"
        assert metadata["model_calls"] > 0
        assert metadata["app_receipts"] and all(
            r["verification"]["passed"] for r in metadata["app_receipts"]
        )
        imported.append(
            next(item for item in app.state.content.list("inbox") if item["source"] == url)["id"]
        )
    actions.append(("inbox.classify_selected", {"item_ids": imported, "use_ai": False}))
    events = list(app.state.chat.stream_turn(cid, "将Inbox里面内容分类归入知识库"))
    assert events[-1]["type"] == "final", events
    metadata = events[-1]["metadata"]
    assert metadata["model_calls"] > 0
    assert metadata["execution_result"]["verified"]
    assert metadata["app_receipts"] and all(
        r["verification"]["passed"] for r in metadata["app_receipts"]
    )
    assert [receipt["action_id"] for receipt in metadata["app_receipts"]] == [
        "inbox.classify_selected"
    ]
    assert len(metadata["app_receipts"][0]["records"]) == 2
    cards = app.state.content.list("knowledge")
    assert {item["source"] for item in cards} == set(urls)
    assert {item["id"] for item in cards} == set(imported)
    assert app.state.content.list("inbox") == []
    assert all(model.bound and all(names == ["app"] for names in model.bound) for model in models)
    assert all("execution_verifier" in runtime.last_node_path for runtime in runtimes)


def test_cancelled_turn_never_persists_late_answer_and_other_chat_can_finish(tmp_path):
    app = create_app(data_dir=tmp_path / "data", env_file=tmp_path / ".env")
    (tmp_path / ".env").write_text("XILIU_API_KEY=fake\nXILIU_MODEL=deepseek-v4-flash\n")
    entered, release = Event(), Event()
    cid = app.state.store.create()["id"]
    other = app.state.store.create()["id"]

    class Runtime:
        def stream_session(self, **kwargs):
            if kwargs["session_id"] == cid:
                entered.set()
                assert release.wait(5)
            yield FinalEvent(text="Late answer", session_id=kwargs["session_id"])

    app.state.chat.runtime_factory = lambda *args, **kwargs: Runtime()
    events = []
    worker = Thread(target=lambda: events.extend(app.state.chat.stream_turn(cid, "Wait")))
    worker.start()
    assert entered.wait(5)
    try:
        assert app.state.chat.cancel(cid)["stopping"] is True
        assert list(app.state.chat.stream_turn(other, "Hello"))[-1]["text"] == "Late answer"
    finally:
        release.set()
        worker.join(5)
    assert events[-1]["metadata"]["cancelled"] is True
    assert "Late answer" not in [m["content"] for m in app.state.store.messages(cid)]
    with app.state.chat.reserve(cid):
        pass


def test_cancel_signal_blocks_tool_side_effects_in_copied_graph_context(tmp_path):
    from langchain_core.tools import tool

    from xiliu.execution.cancellation import cancel_signal
    from xiliu.execution.gateway import ExecutionGateway, RunContext

    @tool
    def write_marker() -> str:
        """Write a marker for this test."""
        (tmp_path / "marker").write_text("bad")
        return "ok"

    signal = Event()
    token = cancel_signal.set(signal)
    try:
        copied = copy_context()
        signal.set()
        import pytest

        with pytest.raises(Exception, match="cancelled"):
            copied.run(
                ExecutionGateway().invoke,
                write_marker,
                {},
                RunContext(run_id="test", session_id="test", workspace=tmp_path),
            )
        assert not (tmp_path / "marker").exists()
    finally:
        cancel_signal.reset(token)


@pytest.mark.parametrize("cancel_before_submit", [False, True])
def test_cancel_during_classification_prevents_late_card_updates(
    tmp_path, cancel_before_submit, monkeypatch
):
    from xiliu.execution.cancellation import TurnCancelled, cancel_signal

    app = create_app(data_dir=tmp_path / "data", env_file=tmp_path / ".env")
    (tmp_path / ".env").write_text("XILIU_API_KEY=fake\nXILIU_MODEL=deepseek-v4-flash\n")
    cards = [
        app.state.content.create(
            {"type": "note", "status": "inbox", "title": title, "content": title}
        )
        for title in ("First", "Second")
    ]
    signal = Event()
    original = app.state.content.get

    def cancel_during_snapshot(item_id):
        result = original(item_id)
        signal.set()
        return result

    if cancel_before_submit:
        signal.set()
    else:
        monkeypatch.setattr(app.state.content, "get", cancel_during_snapshot)
    token = cancel_signal.set(signal)
    try:
        with pytest.raises(TurnCancelled):
            execute(
                app,
                "inbox.classify_selected",
                {
                    "item_ids": [item["id"] for item in cards],
                    "use_ai": True,
                },
            )
    finally:
        cancel_signal.reset(token)
    assert [original(item["id"]) for item in cards] == cards
    with app.state.store.connect() as db:
        assert db.execute("SELECT COUNT(*) FROM inbox_archive_batches").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM inbox_archive_jobs").fetchone()[0] == 0
    assert app.state.inbox._thread is None


def test_agent_classification_preserves_manual_move_during_model_request(tmp_path):
    app = create_app(data_dir=tmp_path / "data", env_file=tmp_path / ".env")
    card = app.state.content.create(
        {
            "type": "note",
            "status": "knowledge",
            "title": "Manual move",
            "content": "Keep me",
        }
    )

    def classify(_item):
        app.state.content.update(card["id"], {"status": "inbox"})
        return {"title": "AI", "summary": "摘要", "tags": []}

    app.state.inbox.metadata = classify
    result = execute(app, "inbox.classify_selected", {"item_ids": [card["id"]], "use_ai": True})
    assert result["ok"] and result["data"]["status"] == "pending"
    try:
        app.state.inbox.start()
        deadline = monotonic() + 3
        while (
            app.state.inbox.get_archive_job(result["data"]["job_id"])["status"]
            in {"pending", "running"}
            and monotonic() < deadline
        ):
            Event().wait(0.01)
        actual = app.state.inbox.get_archive_job(result["data"]["job_id"])
        assert actual["status"] == "conflict" and actual["counts"]["conflict"] == 1
        assert app.state.content.get(card["id"])["status"] == "inbox"
    finally:
        app.state.inbox.shutdown()


def test_real_fast_local_classification_verifies_two_persisted_cards(tmp_path):
    from xiliu.app.fast import run_app_fast

    app = create_app(data_dir=tmp_path / "data", env_file=tmp_path / ".env")
    for url in ("https://example.com/a", "https://example.com/b"):
        assert execute(app, "inbox.import_url", {"url": url})["ok"]
    context = RunContext(
        "fast",
        "test",
        app.state.store.path.parent,
        app_services=app.state.app_services,
        policy_engine=PolicyEngine(app.state.store.path.parent / "policy.json"),
    )

    class ForbiddenModel:
        def invoke(self, *args, **kwargs):
            pytest.fail("Local classification must not invoke a planning model")

    result = run_app_fast(
        "将Inbox里面内容分类归入知识库", app.state.app_services, context, model=ForbiddenModel()
    )
    assert result is not None and result["status"] == "completed"
    assert result["model_calls"] == 0
    assert result["receipts"] and all(r["verification"]["passed"] for r in result["receipts"])
    assert len(app.state.content.list("knowledge")) == 2
    assert app.state.content.list("inbox") == []


def test_cancelled_turn_does_not_execute_pending_unified_app_import(tmp_path):
    app = create_app(data_dir=tmp_path / "data", env_file=tmp_path / ".env")
    (tmp_path / ".env").write_text("XILIU_API_KEY=fake\nXILIU_MODEL=deepseek-v4-flash\n")
    entered, release = Event(), Event()

    class Runtime:
        def stream_session(self, **kwargs):
            entered.set()
            assert release.wait(5)
            execute(
                app, "inbox.import_url", {"url": "https://example.com/late"}, kwargs["session_id"]
            )
            yield FinalEvent(text="Late import", session_id=kwargs["session_id"])

    app.state.chat.runtime_factory = lambda *args, **kwargs: Runtime()
    cid = app.state.store.create()["id"]
    events = []
    worker = Thread(
        target=lambda: events.extend(app.state.chat.stream_turn(cid, "继续执行之前的请求"))
    )
    worker.start()
    assert entered.wait(5)
    try:
        app.state.chat.cancel(cid)
    finally:
        release.set()
        worker.join(5)
    assert events[-1]["metadata"]["cancelled"]
    assert not app.state.content.list("inbox")
    assert not app.state.content.list("knowledge")


def test_personal_plan_actions_preserve_scope_and_parent_relationship(tmp_path):
    app = create_app(data_dir=tmp_path / "data", env_file=tmp_path / ".env")
    goal = execute(app, "tasks.create", {"title": "Long goal", "scope": "goal"})
    assert goal["ok"], goal
    week = execute(
        app,
        "tasks.create",
        {"title": "Week plan", "scope": "week", "parent_id": goal["data"]["id"]},
    )
    assert week["ok"], week
    assert week["data"]["scope"] == "week"
    day = execute(app, "tasks.create", {"title": "Daily step", "parent_id": week["data"]["id"]})
    assert day["ok"], day
    assert (
        next(item for item in app.state.tasks.list() if item["id"] == day["data"]["id"])[
            "parent_id"
        ]
        == week["data"]["id"]
    )
