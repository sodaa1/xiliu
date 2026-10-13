import json
import sqlite3
from uuid import uuid4

from langchain_core.messages import AIMessage

from xiliu.events import ErrorEvent, FinalEvent, ProgressEvent, VerifierEvent
from xiliu.runtime import Runtime


class ScriptModel:
    def __init__(self, calls):
        self.calls = iter(calls)

    def bind_tools(self, tools):
        return self

    def invoke(self, messages):
        if "Verifier" in str(messages[0].content):
            return AIMessage(content='{"status":"passed","reason":"Model says done"}')
        call = next(self.calls, None)
        if call:
            return AIMessage(content="", tool_calls=[{"id": str(uuid4()), **call}])
        return AIMessage(
            content=json.dumps(
                {
                    "summary": "Model says done",
                    "plan_summary": "Plan",
                    "acceptance_criteria": ["Completed goal"],
                    "ready_for_verification": True,
                }
            )
        )


def test_requested_skill_cannot_be_replaced_by_unrelated_app_tool(tmp_path):
    model = ScriptModel(
        [
            {
                "name": "app",
                "args": {
                    "operation": "execute",
                    "action_id": "tasks.create",
                    "arguments": {"title": "not authorized as skill"},
                },
            }
        ]
    )
    runtime = Runtime(model, data_dir=tmp_path, checkpoint_mode="off", trace_mode="off")
    try:
        events = list(
            runtime.stream_session(
                "/skill missing 创建知识整理流程", str(uuid4()), "", max_attempts=1
            )
        )
        assert isinstance(events[-1], FinalEvent)
        assert runtime._app_services.tasks.list() == []
        assert runtime.last_state["execution_result"]["verified"] is False
        assert runtime.last_state["tool_events"][0]["ok"] is False
    finally:
        runtime.close()


def test_background_app_write_denial_is_not_replanned_or_persisted(tmp_path):
    runtime = Runtime(
        ScriptModel(
            [
                {
                    "name": "app",
                    "args": {
                        "operation": "execute",
                        "action_id": "tasks.create",
                        "arguments": {"title": "后台不能写"},
                    },
                }
            ]
        ),
        data_dir=tmp_path,
        checkpoint_mode="off",
        trace_mode="off",
        actor_type="automation",
        policy_profile="background",
        approval_mode="deny",
    )
    try:
        events = list(runtime.stream("创建待办“后台不能写”", str(uuid4())))
        assert isinstance(events[-1], FinalEvent)
        assert runtime._app_services.tasks.list() == []
        assert any(isinstance(e, VerifierEvent) and not e.passed for e in events)
        assert runtime.last_node_path.count("tool_execute") == 1
        assert runtime.last_state["execution_result"]["verified"] is False
    finally:
        runtime.close()


def test_todo_or_list_receipt_cannot_prove_automation_was_created(tmp_path):
    model = ScriptModel(
        [
            {
                "name": "app",
                "args": {"operation": "execute", "action_id": "automations.list", "arguments": {}},
            }
        ]
    )
    runtime = Runtime(model, data_dir=tmp_path, checkpoint_mode="off", trace_mode="off")
    try:
        events = list(runtime.stream_session("创建每日AI简报", str(uuid4()), "", max_attempts=1))
        assert isinstance(events[-1], FinalEvent)
        assert any(isinstance(e, VerifierEvent) and not e.passed for e in events)
        assert runtime.last_state["execution_result"]["verified"] is False
    finally:
        runtime.close()


def test_archive_goal_cannot_pass_with_search_receipts_only(tmp_path):
    model = ScriptModel(
        [
            {
                "name": "app",
                "args": {
                    "operation": "execute",
                    "action_id": "knowledge.search",
                    "arguments": {"query": "AI"},
                },
            }
        ]
    )
    runtime = Runtime(model, data_dir=tmp_path, checkpoint_mode="off", trace_mode="off")
    try:
        events = list(runtime.stream_session("把AI文章归档", str(uuid4()), "", max_attempts=1))
        assert isinstance(events[-1], FinalEvent)
        assert runtime.last_state["execution_result"]["verified"] is False
        assert any(isinstance(e, VerifierEvent) and not e.passed for e in events)
    finally:
        runtime.close()


def test_interruption_after_app_execution_resumes_collection_without_repeating_write(tmp_path):
    runtime = Runtime(
        ScriptModel(
            [
                {
                    "name": "app",
                    "args": {
                        "operation": "execute",
                        "action_id": "tasks.create",
                        "arguments": {"title": "只写一次"},
                    },
                }
            ]
        ),
        data_dir=tmp_path,
        checkpoint_mode="light",
        trace_mode="off",
    )
    sid = str(uuid4())
    events = runtime.stream_session("创建待办“只写一次”", sid, "")
    try:
        for _event in events:
            if runtime.last_node_path and runtime.last_node_path[-1] == "tool_execute":
                break
        events.close()
        assert len(runtime._app_services.tasks.list()) == 1
        resumed = list(runtime.resume(tmp_path / "workspaces" / sid))
        assert not any(isinstance(e, ErrorEvent) for e in resumed), resumed
        assert isinstance(resumed[-1], FinalEvent)
        assert runtime.last_node_path[0] == "state_collect"
        assert "tool_execute" not in runtime.last_node_path
        assert len(runtime._app_services.tasks.list()) == 1
        assert len(runtime.last_state["execution_ids"]) == 1
    finally:
        events.close()
        runtime.close()


def test_runtime_clear_is_control_without_agent_graph(tmp_path):
    runtime = Runtime(object(), data_dir=tmp_path, checkpoint_mode="off", trace_mode="off")
    try:
        events = list(runtime.stream_session("/clear", str(uuid4()), "old context"))
        assert isinstance(events[-1], FinalEvent)
        assert runtime.last_node_path == []
        assert not runtime.last_state.get("tool_events")
    finally:
        runtime.close()


def test_stop_on_streamed_receipt_resumes_without_duplicate_app_write(tmp_path):
    runtime = Runtime(
        ScriptModel(
            [
                {
                    "name": "app",
                    "args": {
                        "operation": "execute",
                        "action_id": "tasks.create",
                        "arguments": {"title": "回执时停止"},
                    },
                }
            ]
        ),
        data_dir=tmp_path,
        checkpoint_mode="light",
        trace_mode="off",
    )
    sid = str(uuid4())
    stream = runtime.stream_session("创建待办“回执时停止”", sid, "")
    try:
        for event in stream:
            if isinstance(event, ProgressEvent) and event.event_type == "tool_result":
                break
        stream.close()
        assert len(runtime._app_services.tasks.list()) == 1
        restored = list(runtime.resume(tmp_path / "workspaces" / sid))
        assert not any(isinstance(e, ErrorEvent) for e in restored), restored
        assert isinstance(restored[-1], FinalEvent)
        assert len(runtime._app_services.tasks.list()) == 1
        assert runtime.last_state["execution_result"]["verified"] is True
    finally:
        stream.close()
        runtime.close()


def test_fast_read_cannot_prove_requested_file_move(tmp_path):
    from xiliu.tools.workspace import create_session_workspace

    sid = str(uuid4())
    workspace = create_session_workspace(tmp_path, sid)
    (workspace / "paper.txt").write_text("paper", encoding="utf-8")
    runtime = Runtime(
        ScriptModel([{"name": "file_read", "args": {"path": "paper.txt"}}]),
        data_dir=tmp_path,
        checkpoint_mode="off",
        trace_mode="off",
    )
    try:
        events = list(
            runtime.stream_session("帮我移动桌面的论文文件到Research", sid, "", max_attempts=1)
        )
        assert isinstance(events[-1], FinalEvent)
        assert runtime.last_state["execution_result"]["verified"] is False
        assert (workspace / "paper.txt").read_text() == "paper"
    finally:
        runtime.close()


def test_successful_app_write_then_model_failure_does_not_repeat_mutation(tmp_path):
    class Model(ScriptModel):
        def invoke(self, messages):
            if getattr(self, "written", False):
                raise ValueError("transient model failure after a write")
            self.written = True
            return AIMessage(
                content="",
                tool_calls=[
                    {
                        "id": str(uuid4()),
                        "name": "app",
                        "args": {
                            "operation": "execute",
                            "action_id": "tasks.create",
                            "arguments": {"title": "once"},
                        },
                    }
                ],
            )

    runtime = Runtime(Model([]), data_dir=tmp_path, checkpoint_mode="off", trace_mode="off")
    try:
        events = list(
            runtime.stream_session("创建一个待办后生成报告", str(uuid4()), "", max_attempts=3)
        )
        assert isinstance(events[-1], FinalEvent)
        assert (
            sum(
                e["ok"]
                for e in runtime.last_state["tool_events"]
                if e["args"].get("action_id") == "tasks.create"
            )
            == 1
        )
        assert len(runtime._app_services.tasks.list()) == 1
        assert runtime.last_state["execution_result"]["verified"] is False
    finally:
        runtime.close()


def test_existing_database_cannot_prove_new_database_creation(tmp_path):
    from xiliu.tools.workspace import create_session_workspace

    sid = str(uuid4())
    workspace = create_session_workspace(tmp_path, sid)
    with sqlite3.connect(workspace / "unrelated.db") as db:
        db.execute("CREATE TABLE old_cache(id INTEGER)")
    runtime = Runtime(
        ScriptModel(
            [
                {
                    "name": "app",
                    "args": {
                        "operation": "execute",
                        "action_id": "knowledge.search",
                        "arguments": {"query": "Agent"},
                    },
                }
            ]
        ),
        data_dir=tmp_path,
        checkpoint_mode="off",
        trace_mode="off",
    )
    try:
        runtime._context(workspace).owner._app_services.content.create(
            {"title": "Agent", "content": "Local evidence", "status": "knowledge"}
        )
        events = list(runtime.stream_session("建立研究数据库", sid, "", max_attempts=1))
        assert isinstance(events[-1], FinalEvent)
        assert runtime.last_state["execution_result"]["verified"] is False
        assert "actual persisted" in runtime.last_state["verification"]
        assert not (workspace / "research.db").exists()
    finally:
        runtime.close()


def test_batch_receipt_checks_only_objects_not_superseded_by_later_writes(tmp_path):
    runtime = Runtime(object(), data_dir=tmp_path, checkpoint_mode="off", trace_mode="off")
    try:
        services = runtime._context(tmp_path).owner._app_services
        first, second = [
            services.content.create({"title": title, "status": "inbox", "content": "Agent"})
            for title in ("A", "B")
        ]

        class BatchModel(ScriptModel):
            def invoke(self, messages):
                response = super().invoke(messages)
                for call in response.tool_calls:
                    if call["args"].get("action_id") == "knowledge.items.update":
                        receipt = json.loads(messages[-1].content)
                        record = next(r for r in receipt["data"]["items"] if r["id"] == first["id"])
                        call["args"]["arguments"]["expected_revision"] = record["revision"]
                return response

        runtime._model = BatchModel(
            [
                {
                    "name": "app",
                    "args": {
                        "operation": "execute",
                        "action_id": "inbox.classify_selected",
                        "arguments": {"item_ids": [first["id"], second["id"]], "use_ai": False},
                    },
                },
                {
                    "name": "app",
                    "args": {
                        "operation": "execute",
                        "action_id": "knowledge.items.update",
                        "arguments": {
                            "item_id": first["id"],
                            "expected_revision": 2,
                            "changes": {"title": "Updated A"},
                        },
                    },
                },
            ]
        )
        events = list(
            runtime.stream_session(
                "批量归档 Inbox 然后更新 A 标题", str(uuid4()), "", max_attempts=1
            )
        )
        assert isinstance(events[-1], FinalEvent)
        assert all(e["ok"] for e in runtime.last_state["tool_events"]), [
            json.loads(e["output"]).get("error") for e in runtime.last_state["tool_events"]
        ]
        assert runtime.last_state["execution_result"]["verified"] is True, runtime.last_state[
            "tool_events"
        ]
        assert services.content.get(first["id"])["title"] == "Updated A"
        assert services.content.get(first["id"])["status"] == "knowledge"
        assert services.content.get(second["id"])["status"] == "knowledge"
    finally:
        runtime.close()
