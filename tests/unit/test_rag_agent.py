import json
from uuid import uuid4

from langchain_core.messages import AIMessage

from xiliu.api.services.content import ContentService
from xiliu.api.store import AppStore
from xiliu.app.actions import AppServices
from xiliu.events import FinalEvent
from xiliu.runtime import Runtime


def test_rag_agent_rewrites_then_returns_only_actual_hit_ids(tmp_path):
    from xiliu.agents.rag_agent import run_rag_agent
    from xiliu.capabilities.agent_registry import AgentRegistry
    from xiliu.execution.gateway import RunContext, active_run
    from xiliu.policy.engine import PolicyEngine

    item = ContentService(AppStore(tmp_path)).create(
        {"content": "Agent Memory durable cognition", "status": "knowledge"}
    )

    class Model:
        calls = 0

        def invoke(self, messages):
            self.calls += 1
            return AIMessage(
                content=json.dumps({"query": "nonexistent" if self.calls == 1 else "cognition"})
            )

    context = RunContext(
        "r",
        "s",
        tmp_path,
        data_dir=tmp_path,
        policy_engine=PolicyEngine(tmp_path / "policy.json"),
        app_services=AppServices.open(tmp_path),
    )
    token = active_run.set(context)
    try:
        result = run_rag_agent(
            {"task": "整理我的知识库文章", "attempt": 1},
            "summarize",
            AgentRegistry(tmp_path).get("rag", "planner"),
            model=Model(),
        )
    finally:
        active_run.reset(token)
    assert result["ok"]
    assert result["hit_ids"] == [item["id"]]
    assert len(result["tool_events"]) == 2
    assert result["answer_supported"]


def test_rag_zero_hits_is_bounded_and_unsupported(tmp_path):
    from xiliu.agents.rag_agent import run_rag_agent
    from xiliu.capabilities.agent_registry import AgentRegistry
    from xiliu.execution.gateway import RunContext, active_run

    class Model:
        def invoke(self, messages):
            return AIMessage(content='{"query":"not found"}')

    token = active_run.set(
        RunContext("r", "s", tmp_path, data_dir=tmp_path, app_services=AppServices.open(tmp_path))
    )
    try:
        result = run_rag_agent(
            {"task": "知识库", "attempt": 1},
            "find",
            AgentRegistry(tmp_path).get("rag", "planner"),
            model=Model(),
            budget=2,
        )
    finally:
        active_run.reset(token)
    assert not result["ok"] and not result["answer_supported"]
    assert len(result["tool_events"]) == 2
    assert result["hit_ids"] == []


def test_fast_checkpoint_resume_preserves_ids_and_does_not_reexecute_tool(tmp_path):
    ContentService(AppStore(tmp_path)).create({"content": "Refero design", "status": "knowledge"})

    class Model:
        calls = 0

        def bind_tools(self, tools):
            return self

        def invoke(self, messages):
            self.calls += 1
            if self.calls == 1:
                return AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "app",
                            "id": "k1",
                            "args": {
                                "operation": "execute",
                                "action_id": "knowledge.search",
                                "arguments": {"query": "Refero"},
                            },
                        }
                    ],
                )
            return AIMessage(content="Refero")

    model = Model()
    runtime = Runtime(model, data_dir=tmp_path, checkpoint_mode="light", trace_mode="full")
    session_id = str(uuid4())
    try:
        events = list(runtime.stream_session("我的收藏 Refero", session_id, ""))
        assert any(isinstance(event, FinalEvent) for event in events)
        resumed = list(runtime.resume(tmp_path / "workspaces" / session_id))
        assert any(isinstance(event, FinalEvent) for event in resumed), resumed
        assert model.calls == 2
    finally:
        runtime.close()
