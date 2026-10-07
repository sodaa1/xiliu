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
