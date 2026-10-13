import json
from uuid import uuid4

import pytest
from langchain_core.messages import AIMessage, ToolMessage

from xiliu.api.app import create_app
from xiliu.runtime import Runtime


def test_real_runtime_factory_accepts_shared_app_services(tmp_path, monkeypatch):
    import xiliu.runtime as module
    from xiliu.config import Settings

    shared = object()
    monkeypatch.setattr(module, "create_chat_model", lambda settings: object())
    runtime = module.create_runtime(
        Settings(api_key="fake", model="fake", data_dir=tmp_path), app_services=shared
    )
    assert runtime._app_services is shared
    runtime.close()


def test_cli_registered_local_action_uses_planner_and_real_receipt(tmp_path):
    application = create_app(data_dir=tmp_path, env_file=tmp_path / ".env")

    class Model:
        calls = 0

        def bind_tools(self, tools):
            assert [tool.name for tool in tools] == ["app"]
            return self

        def invoke(self, messages):
            self.calls += 1
            if "Verifier" in str(messages[0].content):
                return AIMessage(content='{"status":"passed","reason":"Task persisted"}')
            if self.calls == 1:
                return AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "id": "cli-create",
                            "name": "app",
                            "args": {
                                "operation": "execute",
                                "action_id": "tasks.create",
                                "arguments": {"title": "CLI本地任务"},
                            },
                        }
                    ],
                )
            return AIMessage(
                content=json.dumps(
                    {
                        "summary": "Task created",
                        "plan_summary": "Create task",
                        "acceptance_criteria": ["Task persisted"],
                        "ready_for_verification": True,
                    }
                )
            )

    runtime = Runtime(
        Model(),
        data_dir=tmp_path,
        app_services=application.state.app_services,
        checkpoint_mode="off",
        trace_mode="off",
    )
    try:
        events = list(runtime.stream_session("添加待办‘CLI本地任务’", str(uuid4()), ""))
        assert application.state.tasks.list()[0]["title"] == "CLI本地任务"
        assert runtime.last_state["execution_path"] == "planner"
        assert runtime.last_state["tool_scope"] == "app"
        assert runtime._model.calls > 0
        assert runtime.last_state["app_receipts"][-1]["verification"]["passed"]
        assert events[-1].text
    finally:
        runtime.close()


def test_app_fast_uses_shared_gateway_hooks_and_audit(tmp_path):
    from xiliu.app.fast import run_app_fast
    from xiliu.execution.gateway import RunContext
    from xiliu.policy.engine import PolicyEngine

    application = create_app(data_dir=tmp_path, env_file=tmp_path / ".env")
    events = []

    class Hooks:
        def before(self, **kwargs):
            assert kwargs["tool_name"] == "app"
            assert kwargs["arguments"]["action_id"] == "tasks.create"
            return [], True

    context = RunContext(
        "fast-hooks",
        "session",
        tmp_path,
        app_services=application.state.app_services,
        policy_engine=PolicyEngine(tmp_path / "policy.json"),
        hook_engine=Hooks(),
        event_sink=events.append,
    )
    result = run_app_fast("添加待办‘受控任务’", application.state.app_services, context)
    assert result["status"] == "failed" and result["receipts"][0]["error"] == "hook_blocked"
    assert not application.state.tasks.list()
    assert events[-1]["capability_id"] == "builtin:app:tasks.create"
    assert events[-1]["decision"] == "deny" and not events[-1]["success"]


@pytest.mark.parametrize(
    "task", ["我的收藏 Refero", "比较多篇我的收藏 Refero", "我的收藏 Refero 生成报告"]
)
def test_fast_and_planner_bind_one_business_tool_and_share_services(tmp_path, task):
    application = create_app(data_dir=tmp_path, env_file=tmp_path / ".env")
    item = application.state.content.create(
        {"content": "Refero local source", "status": "knowledge"}
    )

    class Model:
        bound = []
        invoked = False

        def bind_tools(self, tools):
            self.bound.append({tool.name for tool in tools})
            return self

        def invoke(self, messages):
            if "Verifier" in messages[0].content:
                return AIMessage(content='{"status":"passed","reason":"Read verified"}')
            if not self.invoked:
                from xiliu.execution.gateway import active_run

                assert active_run.get().app_services is application.state.app_services
                self.invoked = True
                return AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "id": "read",
                            "name": "app",
                            "args": {
                                "operation": "execute",
                                "action_id": "knowledge.search",
                                "arguments": {"query": "Refero"},
                            },
                        }
                    ],
                )
            receipts = [
                json.loads(message.content)
                for message in messages
                if isinstance(message, ToolMessage)
            ]
            assert receipts and receipts[-1]["verification"]["passed"]
            assert receipts[-1]["data"]["hits"][0]["document_id"] == item["id"]
            return AIMessage(
                content=json.dumps(
                    {
                        "summary": "Refero",
                        "plan_summary": "Local source",
                        "acceptance_criteria": ["Actual record"],
                        "ready_for_verification": True,
                    }
                )
            )

    model = Model()
    runtime = Runtime(
        model,
        data_dir=tmp_path,
        app_services=application.state.app_services,
        checkpoint_mode="off",
        trace_mode="off",
    )
    try:
        list(runtime.stream_session(task, str(uuid4()), ""))
    finally:
        runtime.close()
    assert model.bound
    for names in model.bound:
        assert "app" in names
        assert not names & {
            "knowledge_search",
            "knowledge_get",
            "inbox_import",
            "inbox_list",
            "knowledge_folders",
            "knowledge_folder_create",
            "inbox_classify",
            "automation_manage",
        }


def test_background_uses_same_services_but_cannot_write(tmp_path):
    from xiliu.app.dispatch import AppDispatcher
    from xiliu.execution.gateway import RunContext
    from xiliu.policy.engine import PolicyEngine

    app = create_app(data_dir=tmp_path, env_file=tmp_path / ".env")
    context = RunContext(
        "background",
        "background",
        tmp_path,
        app_services=app.state.app_services,
        actor_type="automation",
        policy_profile="background",
        policy_engine=PolicyEngine(tmp_path / "policy.json"),
    )
    dispatch = AppDispatcher(app.state.app_services, context)
    assert dispatch.execute("tasks.list", {})["ok"]
    for action, args in [
        ("tasks.create", {"title": "must not persist"}),
        ("inbox.import_url", {"url": "https://example.com"}),
        ("feed.add_manual", {"url": "https://example.com"}),
        ("preferences.update", {"changes": {"theme": "dark"}, "expected_revision": 0}),
    ]:
        assert dispatch.execute(action, args)["error"] == "policy_denied"
    assert not app.state.tasks.list() and not app.state.content.list("inbox")
