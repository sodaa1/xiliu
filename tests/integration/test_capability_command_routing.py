import pytest

from xiliu.api.app import create_app
from xiliu.app.intent import resolve_intent
from xiliu.events import FinalEvent
from xiliu.graph.nodes import intent_router_node
from xiliu.graph.routing import app_action, local_scope, mode_router_node


@pytest.fixture
def command_app(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text("XILIU_API_KEY=fixture-only\nXILIU_MODEL=deepseek-v4-flash\n")
    app = create_app(data_dir=tmp_path / "data", env_file=env)
    def entries():
        return [{"name": "probe", "description": "Controlled capability"}]
    monkeypatch.setattr(app.state.commands, "skills", entries)
    monkeypatch.setattr(app.state.commands, "mcp", entries)
    try:
        yield app
    finally:
        app.state.inbox.shutdown()
        app.state.retrieval.worker.shutdown()
        app.state.automations.shutdown()


@pytest.mark.parametrize("command", ["mcp", "skill"])
def test_explicit_capability_command_reaches_runtime_instead_of_app_fast(command_app, command):
    app = command_app
    calls = []

    class Runtime:
        def stream_session(self, **kwargs):
            calls.append(kwargs)
            yield FinalEvent(text="Capability workflow", session_id=kwargs["session_id"])

    app.state.chat.runtime_factory = lambda *args, **kwargs: Runtime()
    cid = app.state.store.create()["id"]
    events = list(app.state.chat.stream_turn(cid, f"/{command} probe 列出知识库资料"))
    assert len(calls) == 1
    assert events[-1]["text"] == "Capability workflow"
    assert not events[-1]["metadata"].get("app_receipts")


@pytest.mark.parametrize("command", ["mcp", "skill"])
def test_expanded_capability_command_remains_a_workflow_through_graph(command_app, command):
    app = command_app
    cid = app.state.store.create()["id"]
    task = app.state.commands.resolve(cid, f"/{command} probe 创建待办“探针”").task
    assert task is not None
    assert resolve_intent(task) is None
    assert not app_action(task)
    assert not local_scope(task)
    state = {"task": task, "requested_mode": "fast"}
    assert mode_router_node(state)["mode"] == "standard"
    assert intent_router_node({"task": task}, model=object())["intent_route"] == "workflow"
