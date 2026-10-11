import json

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from xiliu.graph.memory import HistorySummaryStore, MemoryLimits, MemoryManager, summarize_messages


class SummaryModel:
    def __init__(self):
        self.payloads = []

    def invoke(self, messages):
        self.payloads.append(json.loads(messages[1].content))
        return AIMessage(content="Decisions preserved")


def test_public_summary_preserves_previous_context_and_message_roles():
    model = SummaryModel()
    result = summarize_messages(
        model,
        [HumanMessage(content="Question"), AIMessage(content="Answer")],
        {"context_summary": "Previous decisions"},
    )
    assert result == "Decisions preserved"
    assert model.payloads[0]["previous_context_summary"] == "Previous decisions"
    assert [m["role"] for m in model.payloads[0]["messages"]] == ["human", "ai"]


def test_automatic_compression_still_writes_history_and_events(tmp_path):
    class Preferences:
        def read(self):
            return []

    model = SummaryModel()
    memory = MemoryManager(
        tmp_path,
        Preferences(),
        MemoryLimits(200, 0.8, 50),
        model_name="test",
        token_counter=lambda messages, model: sum(len(str(m.content)) for m in messages),
    )
    messages = [
        SystemMessage(content="rules"),
        HumanMessage(content="task"),
        HumanMessage(content="Older facts " * 30),
        AIMessage(content="Recent"),
    ]
    state = {"context_summary": "Earlier summary", "attempt": 1}
    result = memory.prepare_planner_messages(messages, state, model=model)
    assert "Older facts" not in str([message.content for message in result])
    assert HistorySummaryStore(tmp_path).read() == "Decisions preserved"
    assert state["context_summary"] == "Decisions preserved"
    assert (
        state["compression_events"][0]["before_tokens"]
        > state["compression_events"][0]["after_tokens"]
    )
    assert model.payloads[0]["previous_context_summary"] == "Earlier summary"


def test_automatic_compression_failure_keeps_original_messages(tmp_path):
    class Preferences:
        def read(self):
            return []

    class BrokenModel:
        def invoke(self, messages):
            raise TimeoutError()

    memory = MemoryManager(
        tmp_path,
        Preferences(),
        MemoryLimits(100, 0.8, 20),
        model_name="test",
        token_counter=lambda messages, model: sum(len(str(m.content)) for m in messages),
    )
    messages = [
        SystemMessage(content="rules"),
        HumanMessage(content="task"),
        AIMessage(content="Facts " * 40),
    ]
    state = {"context_summary": "Keep me"}
    assert memory.prepare_planner_messages(messages, state, model=BrokenModel()) == messages
    assert state == {"context_summary": "Keep me"}


def test_web_memory_ignores_prior_workspace_history_but_keeps_new_notes(tmp_path):
    class Preferences:
        def read(self):
            return []

    HistorySummaryStore(tmp_path).write("OLD_HISTORY_MARKER")
    notepad = tmp_path / "NOTEPAD.md"
    notepad.write_text("OLD_NOTEPAD_MARKER\n")
    memory = MemoryManager(
        tmp_path,
        Preferences(),
        MemoryLimits(200, 0.8, 50),
        model_name="test",
        include_workspace_history=False,
    )
    state = {"context_summary": "Database context"}
    first = memory.assemble(state, current_node="planner")
    assert first["history"]["history_summary"] == ""
    assert first["history"]["notepad_summary"] == ""
    assert first["history"]["context_summary"] == "Database context"
    notepad.write_text("OLD_NOTEPAD_MARKER\nNew turn finding\n")
    later = memory.assemble(state, current_node="verifier")
    assert later["history"]["notepad_summary"] == "New turn finding\n"
    assert HistorySummaryStore(tmp_path).read() == "OLD_HISTORY_MARKER"


def test_default_memory_still_restores_workspace_for_cli(tmp_path):
    class Preferences:
        def read(self):
            return []

    HistorySummaryStore(tmp_path).write("Saved summary")
    (tmp_path / "NOTEPAD.md").write_text("Saved findings")
    memory = MemoryManager(tmp_path, Preferences(), MemoryLimits(200, 0.8, 50), model_name="test")
    history = memory.assemble({}, current_node="planner")["history"]
    assert history["history_summary"] == "Saved summary"
    assert history["notepad_summary"] == "Saved findings"
