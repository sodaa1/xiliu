"""Real public adapters, rather than mock graph paths or verifier events."""

import json
from uuid import uuid4

import pytest
from langchain_core.messages import AIMessage

from xiliu.automation.models import AutomationTask
from xiliu.automation.runner import AutomationRunner
from xiliu.automation.store import AutomationStore
from xiliu.core.agent import stream_session_events
from xiliu.core.checkpoint import CheckpointManager
from xiliu.core.session import append_user_turn, load_or_create_session, save_session
from xiliu.events import ErrorEvent, FinalEvent
from xiliu.runtime import Runtime
from xiliu.tools.workspace import create_session_workspace


@pytest.mark.parametrize(
    ("prompt", "expected"), [("查看今天任务", "success"), ("创建待办“后台”", "failed")]
)
def test_automation_runner_uses_verified_graph_and_background_policy(tmp_path, prompt, expected):
    store = AutomationStore(tmp_path)
    store.add(
        AutomationTask(
            id="probe",
            name="Probe",
            prompt=prompt,
            trigger_type="cron",
            schedule={"hour": 9, "minute": 0},
        )
    )
    runtimes = []

    def factory(settings, **kwargs):
        class Model:
            invoked = False

            def bind_tools(self, tools):
                assert [tool.name for tool in tools] == ["app"]
                return self

            def invoke(self, messages):
                if "Verifier" in str(messages[0].content):
                    return AIMessage(content='{"status":"passed","reason":"Read tasks checked"}')
                if not self.invoked:
                    self.invoked = True
                    return AIMessage(
                        content="",
                        tool_calls=[
                            {
                                "id": "automation-action",
                                "name": "app",
                                "args": {
                                    "operation": "execute",
                                    "action_id": "tasks.list"
                                    if expected == "success"
                                    else "tasks.create",
                                    "arguments": {} if expected == "success" else {"title": "后台"},
                                },
                            }
                        ],
                    )
                return AIMessage(
                    content=json.dumps(
                        {
                            "summary": "Tasks read",
                            "plan_summary": "App action",
                            "acceptance_criteria": ["Task receipt"],
                            "ready_for_verification": True,
                        }
                    )
                )

        runtime = Runtime(Model(), data_dir=tmp_path, checkpoint_mode="off", **kwargs)
        runtimes.append(runtime)
        return runtime

    result = AutomationRunner(store, None, runtime_factory=factory).run_once("probe")
    assert result.status == expected
    assert "execution_verifier" in runtimes[0].last_node_path
    assert runtimes[0].last_state["execution_result"]["verified"] is (expected == "success")
    assert result.report_path.is_file()


@pytest.mark.parametrize("command", ["/clear", "/compress"])
def test_cli_control_changes_persisted_history_without_entering_graph(
    tmp_path, monkeypatch, command
):
    session = load_or_create_session(tmp_path)
    append_user_turn(session, "old details to discard")
    save_session(tmp_path, session)

    class Model:
        def invoke(self, messages):
            return AIMessage(content="Compact preserved decisions")

    runtime = Runtime(Model(), data_dir=tmp_path, checkpoint_mode="off", trace_mode="off")
    monkeypatch.setattr("xiliu.config.load_settings", lambda: object())
    monkeypatch.setattr("xiliu.runtime.create_runtime", lambda *a, **k: runtime)
    try:
        events = list(stream_session_events(command, session_workspace=tmp_path))
        assert events[-1]["event"]["text"]
        assert runtime.last_node_path == []
        restored = load_or_create_session(tmp_path)
        assert all(t["content"] != "old details to discard" for t in restored["recent_turns"])
        if command == "/compress":
            assert restored["recent_turns"][-1]["content"] == "Compact preserved decisions"
    finally:
        runtime.close()


@pytest.mark.parametrize("latest_node", ["planner", "verifier", "fast_react", "final"])
def test_old_mode_checkpoint_migrates_without_running_old_executor(tmp_path, latest_node):
    sid = str(uuid4())
    workspace = create_session_workspace(tmp_path, sid)
    runtime = Runtime(object(), data_dir=tmp_path, checkpoint_mode="light", trace_mode="off")
    try:
        inputs, _ = runtime._fresh_inputs("old task", workspace, sid, 1)
        state = dict(inputs)
        state.pop("execution_run_id")
        state.update(
            mode="deep",
            requested_mode="deep",
            intent="task",
            supervisor_ok=True,
            graph_state="passed",
            result="Old saved result",
            attempt=1,
        )
        context = runtime._context(workspace, sid)
        manager = CheckpointManager(context)
        manager.save(state, latest_node=latest_node)
        restored, _ = CheckpointManager.load_resume_inputs(context)
        assert "mode" not in restored and "requested_mode" not in restored
        assert isinstance(restored["intent"], dict)
        assert restored["execution_path"] == "planner"
        assert restored["execution_run_id"].startswith("legacy-")
        events = list(runtime.resume(workspace, max_attempts=1))
        assert not any(isinstance(e, ErrorEvent) for e in events), events
        assert isinstance(events[-1], FinalEvent)
        assert not {"mode_router", "supervisor"} & set(runtime.last_node_path)
    finally:
        runtime.close()
