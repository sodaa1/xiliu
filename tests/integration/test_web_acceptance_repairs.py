import json
from types import SimpleNamespace

from langchain_core.messages import AIMessage, messages_from_dict, messages_to_dict

from xiliu.api.services.content import ContentService
from xiliu.api.services.inbox import InboxService
from xiliu.api.services.knowledge import KnowledgeService
from xiliu.api.store import AppStore
from xiliu.app.actions import _import, get_registry
from xiliu.execution.gateway import active_run
from xiliu.graph.nodes.execution import tool_execute_node
from xiliu.tools.todo import TodoStore


def test_agent_inbox_import_keeps_destination_and_receipt_after_worker(tmp_path):
    content = ContentService(AppStore(tmp_path))
    knowledge = KnowledgeService(content)
    knowledge.create_folder({"name": "Python", "tags": ["Python"]})
    inbox = InboxService(content, knowledge)
    services = SimpleNamespace(content=content, knowledge=knowledge, inbox=inbox)
    args = {"text": "Python original text", "use_ai": False}
    item = _import(services, args, None)
    inbox._finish(item, item["revision"], False)
    current = content.get(item["id"])
    assert current["status"] == "inbox" and current["folder_id"] is None
    assert get_registry()["inbox.import_text"].postcondition(services, args, item)
    edited = content.update(item["id"], {"content": "Human replaced text"})
    assert edited["revision"] != item["revision"]
    assert not get_registry()["inbox.import_text"].postcondition(services, args, item)


def test_rejected_todo_completion_returns_to_model_without_relaxing_transition(
    tmp_path, monkeypatch
):
    from xiliu.graph.nodes import execution

    store = TodoStore(tmp_path)
    store.write([{"id": "db", "content": "Create database"}])
    context = SimpleNamespace(run_id="test", local_only=True)
    call = {
        "id": "complete-db",
        "name": "todo_update",
        "args": {"todo_id": "db", "status": "completed"},
    }
    state = dict(
        workspace=tmp_path,
        task="建立研究数据库",
        execution_path="planner",
        attempt=1,
        intent={},
        selected_tools=["todo_update"],
        pending_calls=[call],
        loop_messages=messages_to_dict([AIMessage(content="", tool_calls=[call])]),
    )
    from xiliu.tools.todo import TodoUpdateTool

    monkeypatch.setattr(
        execution, "available_tools", lambda *_: {"todo_update": TodoUpdateTool(workspace=tmp_path)}
    )
    monkeypatch.setattr(
        execution.ExecutionGateway, "invoke", lambda _, tool, args, __: tool.invoke(args)
    )
    token = active_run.set(context)
    try:
        update = tool_execute_node(state, model=None, memory_manager=None)
    finally:
        active_run.reset(token)
    assert update["loop_complete"] is False
    assert store.read()[0]["status"] == "pending"
    messages = messages_from_dict(update["loop_messages"])
    assert json.loads(messages[-1].content)["error"] == "todo must be in_progress before completed"
    assert update["round_events"][0]["ok"] is False


def test_chat_drains_runtime_before_publishing_final(tmp_path):
    from xiliu.api.services.chat import ChatService
    from xiliu.api.services.conversations import ConversationService
    from xiliu.api.services.model_settings import ModelSettingsService
    from xiliu.events import FinalEvent

    env = tmp_path / ".env"
    env.write_text("XILIU_API_KEY=fake\nXILIU_PROVIDER=deepseek\n")
    store = AppStore(tmp_path / "data")
    finished = []

    class Runtime:
        def stream_session(self, **kwargs):
            yield FinalEvent(text="Done", session_id=kwargs["session_id"])
            finished.append("completed")

    chat = ChatService(
        ConversationService(store, ModelSettingsService(env)),
        runtime_factory=lambda *a, **k: Runtime(),
    )
    for event in chat.stream_turn(store.create()["id"], "Hello"):
        if event["type"] == "final":
            assert finished == ["completed"]
