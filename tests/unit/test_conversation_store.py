from concurrent.futures import ThreadPoolExecutor

import pytest

from xiliu.api.errors import WebError
from xiliu.api.services.conversations import ConversationService
from xiliu.api.services.model_settings import ModelSettingsService
from xiliu.api.store import AppStore


def test_durable_crud_and_cascade(tmp_path):
    store = AppStore(tmp_path)
    chat = store.create()
    assert store.list()[0]["title"] == "New Chat"
    store.update(chat["id"], title="Research", model_override="gpt-5.6-sol")
    store.append_message(chat["id"], "user", "Hello")
    assert AppStore(tmp_path).get(chat["id"])["model_override"] == "gpt-5.6-sol"
    assert store.messages(chat["id"])[0]["content"] == "Hello"
    store.delete(chat["id"])
    assert store.list() == []
    with store.connect() as db:
        assert db.execute("SELECT count(*) FROM messages").fetchone()[0] == 0
    with pytest.raises(WebError) as error:
        store.get(chat["id"])
    assert error.value.code == "conversation_not_found"


def test_message_seq_is_atomic_across_connections(tmp_path):
    store = AppStore(tmp_path)
    chat = store.create()
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(
            pool.map(
                lambda i: AppStore(tmp_path).append_message(chat["id"], "user", str(i)), range(12)
            )
        )
    assert [m["seq"] for m in store.messages(chat["id"])] == list(range(1, 13))


def test_context_ignores_events_and_cleared_history(tmp_path):
    store = AppStore(tmp_path)
    settings = ModelSettingsService(tmp_path / ".env")
    service = ConversationService(store, settings)
    chat = store.create()
    store.append_message(chat["id"], "user", "OLD PRIVATE CONTEXT")
    store.append_message(chat["id"], "assistant", "OLD ANSWER")
    store.clear_context(chat["id"])
    store.append_message(chat["id"], "event", "Context cleared")
    store.append_message(chat["id"], "user", "Fresh question")
    context = service.build_context(chat["id"])
    assert "OLD" not in context
    assert "Context cleared" not in context
    assert "Fresh question" in context
    assert len(store.messages(chat["id"])) == 4


def test_invalid_override_reset_when_provider_changes(tmp_path):
    env = tmp_path / ".env"
    env.write_text("XILIU_PROVIDER=deepseek\nXILIU_MODEL=deepseek-flash\n")
    store = AppStore(tmp_path)
    service = ConversationService(store, ModelSettingsService(env))
    chat = store.create()
    store.update(chat["id"], model_override="gpt-5.6-sol")
    assert service.get(chat["id"])["model_override"] is None
    assert store.get(chat["id"])["model_override"] is None
