import json

import pytest
from langchain_core.messages import AIMessage

from xiliu.api.services.chat import ChatService
from xiliu.api.services.commands import CommandService
from xiliu.api.services.conversations import ConversationService
from xiliu.api.services.model_settings import ModelSettingsService
from xiliu.api.store import AppStore
from xiliu.events import FinalEvent


def setup(tmp_path):
    env = tmp_path / ".env"
    env.write_text("XILIU_API_KEY=fake\nXILIU_MODEL=deepseek-flash\n")
    data = tmp_path / "data"
    skill = data / "skills" / "example"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        "---\nname: example\ndescription: Test a real skill registry\n---\nInstructions"
    )
    mcp = data / "mcp" / "aihot"
    mcp.mkdir(parents=True)
    (mcp / "mcp.json").write_text(
        json.dumps(
            {
                "servers": {
                    "aihot": {
                        "enabled": True,
                        "trust": "explicit",
                        "transport": "http",
                        "url": "https://example.com/mcp",
                        "permissions": ["network.read"],
                        "tool_allowlist": [],
                    }
                }
            }
        )
    )
    conversations = ConversationService(AppStore(data), ModelSettingsService(env))
    commands = CommandService(conversations)
    chat = ChatService(conversations)
    chat.commands = commands
    cid = conversations.store.create()["id"]
    return conversations, commands, chat, cid


def test_clear_removes_visible_messages_and_old_context(tmp_path):
    conversations, commands, chat, cid = setup(tmp_path)
    conversations.store.append_message(cid, "user", "Old facts")
    conversations.store.append_message(cid, "assistant", "Old answer")
    result = list(chat.stream_turn(cid, "/clear"))
    assert result[-1]["role"] == "event"
    assert result[-1]["text"] == "已清除对话内容"
    assert result[-1]["reset_messages"] is True
    assert len(conversations.store.messages(cid)) == 1
    assert conversations.build_context(cid) == ""
    conversations.store.append_message(cid, "user", "Fresh facts")
    assert "Old facts" not in conversations.build_context(cid)
    assert "Fresh facts" in conversations.build_context(cid)


def test_compress_uses_shared_summary_and_preserves_prior_summary(tmp_path, monkeypatch):
    conversations, commands, chat, cid = setup(tmp_path)
    store = conversations.store
    store.append_message(cid, "user", "old")
    store.save_summary(cid, "Previous durable summary", 1)
    store.append_message(cid, "assistant", "New response")
    received = []

    class SummaryModel:
        def invoke(self, messages):
            received.append(json.loads(messages[1].content))
            return AIMessage(content="Combined faithful summary")

    monkeypatch.setattr(
        "xiliu.api.services.commands.create_chat_model", lambda settings: SummaryModel()
    )
    result = list(chat.stream_turn(cid, "/compress"))
    assert result[-1]["text"] == "Context compressed"
    assert received[0]["previous_context_summary"] == "Previous durable summary"
    assert [m["content"] for m in received[0]["messages"]] == ["New response"]
    conversation = store.get(cid)
    assert conversation["context_summary"] == "Combined faithful summary"
    assert conversation["compressed_through_seq"] == 3
    assert len(store.messages(cid)) == 4
    assert "Combined faithful summary" in conversations.build_context(cid)
    assert "New response" not in conversations.build_context(cid)
    list(chat.stream_turn(cid, "/compress"))
    assert len(received) == 1  # no paid resummary when there is no fresh content


def test_failed_compression_does_not_replace_existing_summary(tmp_path, monkeypatch):
    conversations, commands, chat, cid = setup(tmp_path)
    conversations.store.save_summary(cid, "Must survive", 0)
    conversations.store.append_message(cid, "user", "Fresh facts")

    class BrokenModel:
        def invoke(self, messages):
            raise TimeoutError("sensitive-key")

    monkeypatch.setattr(
        "xiliu.api.services.commands.create_chat_model", lambda settings: BrokenModel()
    )
    result = list(chat.stream_turn(cid, "/compress"))
    assert result[-1]["code"] == "provider_timeout"
    assert "sensitive-key" not in repr(result)
    assert conversations.store.get(cid)["context_summary"] == "Must survive"
    assert conversations.store.get(cid)["compressed_through_seq"] == 0


@pytest.mark.parametrize(
    "text,code",
    [
        ("/unknown", "invalid_command"),
        ("/clear extra", "invalid_command"),
        ("/skill missing", "skill_not_found"),
        ("/mcp missing", "mcp_not_found"),
        ("/skill", "invalid_command"),
    ],
)
def test_command_errors_are_stable(tmp_path, text, code):
    conversations, commands, chat, cid = setup(tmp_path)
    result = list(chat.stream_turn(cid, text))
    assert result[-1]["code"] == code
    assert len(conversations.store.messages(cid)) == 1


@pytest.mark.parametrize("kind,name", [("skill", "example"), ("mcp", "aihot")])
def test_capability_instruction_is_routed_through_runtime(tmp_path, kind, name):
    conversations, commands, chat, cid = setup(tmp_path)
    tasks = []

    class FakeRuntime:
        def stream_session(self, **kwargs):
            tasks.append(kwargs["task"])
            yield FinalEvent(text="Handled by Runtime", session_id=kwargs["session_id"])

    chat.runtime_factory = lambda *args, **kwargs: FakeRuntime()
    result = list(chat.stream_turn(cid, f"/{kind} {name} Explain this"))
    assert result[-1]["text"] == "Handled by Runtime"
    assert name in tasks[0] and "Explain this" in tasks[0]
    assert ("skill_load" if kind == "skill" else "mcp_call") in tasks[0]
    assert "capability_search" in tasks[0] if kind == "mcp" else "skill:example" in tasks[0]


@pytest.mark.parametrize("text", ["/skill example", "/mcp aihot"])
def test_metadata_only_does_not_start_runtime(tmp_path, text):
    conversations, commands, chat, cid = setup(tmp_path)

    def forbidden(*args, **kwargs):
        raise AssertionError("Runtime must not run for metadata")

    chat.runtime_factory = forbidden
    result = list(chat.stream_turn(cid, text))
    assert result[-1]["type"] == "final"
    assert text in result[-1]["text"]
