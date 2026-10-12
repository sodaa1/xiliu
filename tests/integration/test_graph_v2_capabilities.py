"""Registry candidates are metadata; all execution still crosses Gateway policy."""

import json
from types import SimpleNamespace
from uuid import uuid4

import pytest
from langchain_core.messages import AIMessage

from xiliu.events import ErrorEvent, FinalEvent
from xiliu.runtime import Runtime


class ParentModel:
    def __init__(self, calls):
        self.calls = iter(calls)

    def bind_tools(self, tools):
        return self

    def invoke(self, messages):
        if "Verifier" in str(messages[0].content):
            self.verifier_input = json.loads(messages[-1].content)
            return AIMessage(content='{"status":"passed","reason":"Actual evidence supplied"}')
        call = next(self.calls, None)
        if call:
            return AIMessage(content="", tool_calls=[{**call, "id": str(uuid4())}])
        return AIMessage(
            content=json.dumps(
                {
                    "summary": "Completed using actual sources",
                    "plan_summary": "Discover and execute",
                    "acceptance_criteria": ["Real receipt and sources"],
                    "ready_for_verification": True,
                }
            )
        )


@pytest.mark.parametrize("denied", [False, True])
def test_mcp_discovery_schema_allowlist_and_policy_are_preserved(tmp_path, denied):
    root = tmp_path / "mcp/probe"
    root.mkdir(parents=True)
    (root / "mcp.json").write_text(
        json.dumps(
            {
                "servers": {
                    "probe": {
                        "enabled": True,
                        "trust": "explicit",
                        "transport": "http",
                        "url": "https://example.test/mcp",
                        "permissions": ["network.read"],
                        "tool_allowlist": ["lookup"],
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    model = ParentModel(
        [
            {"name": "capability_search", "args": {"query": "", "kind": "mcp"}},
            {
                "name": "mcp_call",
                "args": {"capability_id": "mcp:probe:lookup", "arguments": {"query": "Agent"}},
            },
        ]
    )
    runtime = Runtime(model, data_dir=tmp_path, checkpoint_mode="off", trace_mode="full")
    actual_calls = []

    class Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def list_tools(self):
            schema = {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            }
            return SimpleNamespace(
                tools=[SimpleNamespace(name="lookup", description="Probe", input_schema=schema)]
            )

        async def call_tool(self, name, arguments):
            actual_calls.append((name, arguments))
            return SimpleNamespace(
                content=[SimpleNamespace(type="text", text="Source: https://example.test/paper")],
                is_error=False,
                structured_content=None,
            )

    runtime._mcp_manager._client_factory = lambda target: Client()
    if denied:
        # Copy the profile instead of mutating process-wide DEFAULT_PROFILES.
        runtime._policy_engine.profiles = {
            "interactive": {
                **runtime._policy_engine.profiles["interactive"],
                "network.read": "deny",
            }
        }
    try:
        events = list(
            runtime.stream_session("/mcp probe 查询可用能力", str(uuid4()), "", max_attempts=1)
        )
        assert not any(isinstance(e, ErrorEvent) for e in events), events
        assert isinstance(events[-1], FinalEvent)
        assert runtime.last_state["execution_path"] == "planner"
        assert runtime.last_state["execution_result"]["verified"] is (not denied)
        assert actual_calls == ([] if denied else [("lookup", {"query": "Agent"})])
        if not denied:
            assert {e["tool"] for e in model.verifier_input["actual_execution_receipts"]} == {
                "capability_search",
                "mcp_call",
            }
            assert any(
                e.get("source_uri") == "https://example.test/paper"
                for e in runtime.last_state["evidence"]
            )
            assert runtime._capabilities.get("mcp:probe:lookup") is not None
        else:
            assert runtime.last_state["tool_events"][-1]["ok"] is False
    finally:
        runtime.close()


def test_subagent_keeps_local_rag_sources_and_child_receipts_in_parent_state(tmp_path):
    class Child:
        def invoke(self, messages):
            if "Only rewrite" in messages[0].content:
                return AIMessage(content='{"query":"Agent"}')
            hits = json.loads(messages[-1].content)["hits"]
            return AIMessage(
                content=json.dumps(
                    {
                        "summary": "Compared the two real papers",
                        "citations": [h["document_id"] for h in hits],
                    }
                )
            )

    parent = ParentModel(
        [
            {
                "name": "agent_call",
                "args": {"agent_id": "rag", "instruction": "比较两篇 Agent 文档", "budget": 3},
            }
        ]
    )
    runtime = Runtime(
        parent,
        agent_model_factory=lambda: Child(),
        data_dir=tmp_path,
        checkpoint_mode="off",
        trace_mode="full",
    )
    try:
        services = runtime._context(tmp_path).owner._app_services
        items = [
            services.content.create(
                {"title": f"Agent {i}", "content": f"Evidence {i}", "status": "knowledge"}
            )
            for i in (1, 2)
        ]
        events = list(runtime.stream_session("比较两个知识文档", str(uuid4()), "", max_attempts=1))
        assert not any(isinstance(e, ErrorEvent) for e in events), events
        assert isinstance(events[-1], FinalEvent)
        state = runtime.last_state
        assert state["execution_result"]["verified"] is True
        assert any(
            e["agent"] == "subagent:rag" for e in parent.verifier_input["actual_execution_receipts"]
        )
        result = state["agent_results"][-1]
        assert result["agent_id"] == "rag" and result["answer_supported"] is True
        assert set(result["hit_ids"]) == {item["id"] for item in items}
        assert any(e["agent"] == "subagent:rag" and e["ok"] for e in state["tool_events"])
        assert set(result["evidence_ids"]) <= set(state["execution_ids"])
    finally:
        runtime.close()
