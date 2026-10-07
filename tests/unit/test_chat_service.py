from threading import Event, Thread

from xiliu.api.services.chat import ChatService
from xiliu.api.services.conversations import ConversationService
from xiliu.api.services.model_settings import ModelSettingsService
from xiliu.api.store import AppStore
from xiliu.events import ErrorEvent, FinalEvent, ProgressEvent


def setup_services(tmp_path, factory):
    env = tmp_path / ".env"
    env.write_text("XILIU_API_KEY=private-key\nXILIU_MODEL=deepseek-flash\n")
    store = AppStore(tmp_path / "data")
    conversations = ConversationService(store, ModelSettingsService(env))
    return store, ChatService(conversations, runtime_factory=factory)


def test_runtime_session_context_model_and_final_persisted(tmp_path):
    calls = []

    class FakeRuntime:
        def stream_session(self, **kwargs):
            calls.append(kwargs)
            yield ProgressEvent(stage="planner", message="Working")
            yield FinalEvent(text="Real adapter answer", session_id=kwargs["session_id"])

    def factory(settings, **kwargs):
        assert kwargs == {"approval_mode": "deny"}
        assert settings.model == "deepseek-v4-pro"
        return FakeRuntime()

    store, chat = setup_services(tmp_path, factory)
    conversation = store.create()
    store.update(conversation["id"], model_override="deepseek-v4-pro")
    store.append_message(conversation["id"], "user", "Earlier context")
    events = list(chat.stream_turn(conversation["id"], "New question"))
    assert calls[0]["task"] == "New question"
    assert calls[0]["session_id"] == conversation["id"]
    assert calls[0]["include_workspace_history"] is False
    assert "Earlier context" in calls[0]["context_summary"]
    assert "New question" not in calls[0]["context_summary"]
    assert events[-1]["type"] == "final"
    assert store.messages(conversation["id"])[-1]["content"] == "Real adapter answer"
    assert store.get(conversation["id"])["title"] == "New question"


def test_error_event_does_not_persist_success(tmp_path):
    class FakeRuntime:
        def stream_session(self, **kwargs):
            yield ErrorEvent(code="authentication", message="Provider authentication failed")

    store, chat = setup_services(tmp_path, lambda *args, **kwargs: FakeRuntime())
    conversation = store.create()
    events = list(chat.stream_turn(conversation["id"], "Hello"))
    assert events[-1]["code"] == "provider_authentication_failed"
    assert [m["role"] for m in store.messages(conversation["id"])] == ["user"]


def test_unexpected_failure_is_secret_free(tmp_path):
    def factory(*args, **kwargs):
        raise RuntimeError("private-key")

    store, chat = setup_services(tmp_path, factory)
    events = list(chat.stream_turn(store.create()["id"], "Hello"))
    assert events[-1]["code"] == "provider_error"
    assert "private-key" not in repr(events)


def test_concurrent_turn_rejected_without_second_user_message(tmp_path):
    entered, release = Event(), Event()

    class FakeRuntime:
        def stream_session(self, **kwargs):
            entered.set()
            assert release.wait(5)
            yield FinalEvent(text="Done", session_id=kwargs["session_id"])

    store, chat = setup_services(tmp_path, lambda *args, **kwargs: FakeRuntime())
    cid = store.create()["id"]
    worker = Thread(target=lambda: list(chat.stream_turn(cid, "First")))
    worker.start()
    assert entered.wait(5)
    try:
        assert list(chat.stream_turn(cid, "Second"))[-1]["code"] == "conversation_busy"
    finally:
        release.set()
        worker.join(5)
    assert [m["content"] for m in store.messages(cid)] == ["First", "Done"]


def test_real_runtime_chat_graph_uses_shared_session(tmp_path):
    from uuid import uuid4

    from langchain_core.messages import AIMessage

    from xiliu.runtime import Runtime

    class ChatModel:
        def __init__(self):
            self.calls = 0

        def invoke(self, messages):
            self.calls += 1
            if self.calls == 1:
                return AIMessage(content='{"route":"chat","reason":"Greeting","confidence":0.99}')
            return AIMessage(content="Hello from the real xiliu Runtime")

    model = ChatModel()
    runtime = Runtime(model, data_dir=tmp_path / "data", approval_mode="deny")
    cid = str(uuid4())
    try:
        events = list(
            runtime.stream_session(
                task="Hello", session_id=cid, context_summary="Previous greeting"
            )
        )
    finally:
        runtime.close()
    assert events[-1] == FinalEvent(text="Hello from the real xiliu Runtime", session_id=cid)
    assert model.calls == 2
    assert (tmp_path / "data" / "workspaces" / cid).is_dir()


def test_real_runtime_workflow_turn_excludes_old_workspace_memory(tmp_path):
    from uuid import uuid4

    from langchain_core.messages import AIMessage

    from xiliu.graph.memory import HistorySummaryStore
    from xiliu.runtime import Runtime
    from xiliu.tools.workspace import create_session_workspace

    class WorkflowModel:
        def invoke(self, messages):
            return AIMessage(content='{"route":"workflow","reason":"Task","confidence":0.99}')

    class InspectingRuntime(Runtime):
        def _run(self, inputs, memory_manager, context, **kwargs):
            for memory in (
                inputs["memory"],
                memory_manager.assemble(inputs, current_node="planner"),
            ):
                assert memory["history"]["history_summary"] == ""
                assert memory["history"]["notepad_summary"] == ""
                assert memory["history"]["context_summary"] == "SQLite context"
            yield FinalEvent(text="Workflow isolated", session_id=inputs["session_id"])

    cid = str(uuid4())
    runtime = InspectingRuntime(WorkflowModel(), data_dir=tmp_path / "data", approval_mode="deny")
    workspace = create_session_workspace(tmp_path / "data", cid)
    HistorySummaryStore(workspace).write("OLD_HISTORY_MARKER")
    (workspace / "NOTEPAD.md").write_text("OLD_NOTEPAD_MARKER")
    try:
        events = list(
            runtime.stream_session("Task", cid, "SQLite context", include_workspace_history=False)
        )
    finally:
        runtime.close()
    assert events[-1] == FinalEvent(text="Workflow isolated", session_id=cid)


def test_closing_turn_releases_runtime_and_conversation_reservation(tmp_path):
    closed = []

    class FakeRuntime:
        def stream_session(self, **kwargs):
            try:
                yield ProgressEvent(stage="planner", message="Working")
                yield FinalEvent(text="Done", session_id=kwargs["session_id"])
            finally:
                closed.append("events")

        def close(self):
            closed.append("runtime")

    store, chat = setup_services(tmp_path, lambda *args, **kwargs: FakeRuntime())
    cid = store.create()["id"]
    turn = chat.stream_turn(cid, "Hello")
    next(turn)
    next(turn)
    turn.close()
    assert closed == ["events", "runtime"]
    with chat.reserve(cid):
        pass
