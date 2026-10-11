from uuid import uuid4

import pytest
from langchain_core.messages import AIMessage
from pydantic import ValidationError

from xiliu.events import FinalEvent
from xiliu.runtime import Runtime
from xiliu.tools.todo import TodoWriteInput


def test_planner_can_complete_its_direct_work_without_code_agent(tmp_path):
    class Model:
        calls = 0

        def bind_tools(self, tools):
            return self

        def invoke(self, messages):
            if "intent router" in messages[0].content:
                return AIMessage(
                    content='{"route":"workflow","reason":"connection","confidence":1}'
                )
            if "Verifier" in messages[0].content:
                return AIMessage(content='{"status":"passed","reason":"Evidence complete"}')
            self.calls += 1
            steps = [
                ("todo_write", {"todos": [{"id": "read", "content": "Read selected source"}]}),
                ("todo_update", {"todo_id": "read", "status": "in_progress"}),
                ("todo_update", {"todo_id": "read", "status": "completed", "note": "Source read"}),
            ]
            if self.calls <= len(steps):
                name, args = steps[self.calls - 1]
                return AIMessage(
                    content="", tool_calls=[{"id": str(self.calls), "name": name, "args": args}]
                )
            return AIMessage(
                content=(
                    '{"summary":"Source read","plan_summary":"Read source",'
                    '"acceptance_criteria":["Source read"],"ready_for_verification":true}'
                )
            )

    runtime = Runtime(Model(), data_dir=tmp_path, checkpoint_mode="off", trace_mode="off")
    try:
        events = list(runtime.stream_session("Read selected connection", str(uuid4()), ""))
    finally:
        runtime.close()
    assert isinstance(events[-1], FinalEvent)
    assert "状态：passed" in events[-1].text
    assert "尝试次数：1/3" in events[-1].text


def test_todo_write_rejects_status_instead_of_silently_ignoring_it():
    with pytest.raises(ValidationError):
        TodoWriteInput.model_validate(
            {"todos": [{"id": "read", "content": "Read source", "status": "completed"}]}
        )
