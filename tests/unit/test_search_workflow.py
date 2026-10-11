import json
from uuid import uuid4

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import StructuredTool
from tavily.errors import (
    BadRequestError,
    ForbiddenError,
    InvalidAPIKeyError,
    MissingAPIKeyError,
    TavilyKeylessLimitError,
    UsageLimitExceededError,
)
from tavily.errors import TimeoutError as TavilyTimeoutError

from xiliu.runtime import Runtime


class ToolModel:
    def __init__(self, name, arguments, *, repeat=False):
        self.name = name
        self.arguments = arguments
        self.repeat = repeat
        self.calls = 0
        self.tools = []

    def bind_tools(self, tools):
        self.tools = [tool.name for tool in tools]
        return self

    def invoke(self, messages):
        self.calls += 1
        if self.repeat or self.calls == 1:
            return AIMessage(
                content="",
                tool_calls=[{"id": str(self.calls), "name": self.name, "args": self.arguments}],
            )
        return AIMessage(content="Beijing is 17 C.")


class Memory:
    def assemble(self, *args, **kwargs):
        return {}


@pytest.fixture
def search_sdk(monkeypatch):
    requests = []
    keyed_clients = []
    response = {
        "answer": "Beijing is 17 C.",
        "results": [{"title": "Weather", "url": "https://example.com/weather", "content": "17 C"}],
    }

    class Client:
        def __init__(self, **kwargs):
            keyed_clients.append(bool(kwargs.get("api_key")))

        def search(self, **kwargs):
            requests.append(kwargs)
            return response

    monkeypatch.setattr("xiliu.tools.web_search_tool.TavilyClient", Client)
    return requests, response, keyed_clients


@pytest.mark.parametrize(
    "task",
    [
        "北京今天的天气怎么样？",
        "查询北京实时天气",
        "北京天气怎么样？",
        "北京天气如何",
        "北京天气",
        "上海气温",
        "What is the weather in Beijing today?",
        "Weather in Shanghai",
    ],
)
def test_current_weather_uses_fast_web_search(task, tmp_path, search_sdk):
    from xiliu.events import FinalEvent
    from xiliu.graph.routing import external_scope, mode_router_node

    assert external_scope(task)
    assert mode_router_node({"task": task})["mode"] == "fast"
    model = ToolModel("web_search", {"query": task})
    runtime = Runtime(model, data_dir=tmp_path, checkpoint_mode="off", trace_mode="off")
    try:
        events = list(runtime.stream_session(task, str(uuid4()), ""))
    finally:
        runtime.close()
    assert isinstance(events[-1], FinalEvent)
    assert "17 C" in events[-1].text
    assert "https://example.com/weather" in events[-1].text
    assert model.tools == ["app", "web_search"]
    assert len(search_sdk[0]) == 1


@pytest.mark.parametrize(
    "task",
    [
        "北京今天的天气怎么样？不要联网",
        "Beijing weather today without internet access",
        "查我的知识库里北京今天的天气笔记",
        "Find my saved notes about today's weather in Beijing",
        "什么是天气？",
        "解释天气变化的原理",
        "What does weather mean?",
        "Explain why weather changes",
        "你喜欢什么天气？",
        "解释天气",
        "Translate weather in Chinese",
        "What does weather in Chinese mean?",
    ],
)
def test_weather_routing_preserves_local_and_conceptual_questions(task):
    from xiliu.graph.routing import external_scope

    assert not external_scope(task)


def test_permanent_search_failure_stops_parent_and_verifier(tmp_path, monkeypatch):
    from xiliu.agents.react import run_react
    from xiliu.graph.workflow import route_after_verifier
    from xiliu.tools.subagent_tools import CallSearchAgentTool, SupervisorContext

    class LimitedClient:
        def __init__(self, **kwargs):
            pass

        def search(self, **kwargs):
            raise UsageLimitExceededError("offline usage limit")

    monkeypatch.setattr("xiliu.tools.web_search_tool.TavilyClient", LimitedClient)
    child = ToolModel("web_search", {"query": "Beijing weather"}, repeat=True)
    monkeypatch.setattr("xiliu.agents.search_agent.create_agent_model", lambda: child)
    parent = ToolModel("call_search_agent", {"instruction": "Find Beijing weather"}, repeat=True)
    state = {
        "task": "Beijing weather today",
        "workspace": tmp_path,
        "attempt": 1,
        "max_attempts": 3,
        "graph_state": "failed",
        "tool_events": [],
        "agent_results": [],
        "research_notes": [],
    }
    context = SupervisorContext(state, Memory())
    result = run_react(
        parent,
        [CallSearchAgentTool(context=context)],
        [HumanMessage(content=state["task"])],
        agent="planner",
        attempt=1,
    )
    state["tool_events"].extend(result["tool_events"])
    assert not result["ok"]
    assert result["retryable"] is False
    assert json.loads(result["tool_events"][-1]["output"])["retryable"] is False
    assert len(state["agent_results"]) == 1
    assert child.calls == parent.calls == 1
    assert route_after_verifier(state) == "final"


def test_empty_mcp_discovery_uses_one_audited_web_fallback(tmp_path, monkeypatch, search_sdk):
    from xiliu.agents.search_agent import run_search_agent
    from xiliu.capabilities.manager import CapabilityManager
    from xiliu.execution.gateway import RunContext, active_run

    model = ToolModel("capability_search", {"query": "weather", "kind": "mcp"}, repeat=True)
    monkeypatch.setattr("xiliu.agents.search_agent.create_agent_model", lambda: model)
    token = active_run.set(
        RunContext("run", "session", tmp_path, capability_manager=CapabilityManager())
    )
    emitted = []
    try:
        result = run_search_agent(
            {"task": "Beijing weather today"}, "Find weather", writer=emitted.append
        )
    finally:
        active_run.reset(token)
    assert result["ok"]
    assert result["sources"] == ["https://example.com/weather"]
    assert [event["tool"] for event in result["tool_events"]] == ["capability_search", "web_search"]
    assert model.calls == 1
    assert len(search_sdk[0]) == 1
    assert any(event["type"] == "search_results" for event in emitted)


@pytest.mark.parametrize(
    "task",
    ["Beijing weather today without internet access", "查我的知识库里北京今天的天气笔记"],
)
def test_empty_mcp_discovery_does_not_force_network_outside_scope(
    task, tmp_path, monkeypatch, search_sdk
):
    from xiliu.agents.search_agent import run_search_agent
    from xiliu.capabilities.manager import CapabilityManager
    from xiliu.execution.gateway import RunContext, active_run

    model = ToolModel("capability_search", {"query": "weather", "kind": "mcp"}, repeat=True)
    monkeypatch.setattr("xiliu.agents.search_agent.create_agent_model", lambda: model)
    token = active_run.set(
        RunContext("run", "session", tmp_path, capability_manager=CapabilityManager())
    )
    try:
        result = run_search_agent({"task": task}, "Find weather")
    finally:
        active_run.reset(token)
    assert search_sdk[0] == []
    assert not result["ok"]
    assert result["sources"] == []
    assert [event["tool"] for event in result["tool_events"]] == ["capability_search"]
    assert model.calls == 1


def test_web_fallback_respects_gateway_denial(tmp_path, monkeypatch, search_sdk):
    from xiliu.agents.search_agent import run_search_agent
    from xiliu.capabilities.manager import CapabilityManager
    from xiliu.execution.gateway import RunContext, active_run
    from xiliu.policy.engine import Decision, PolicyEngine

    class DenySearch(PolicyEngine):
        def evaluate(self, **kwargs):
            if kwargs["capability_id"] == "builtin:web_search":
                return Decision("deny", "offline denied search")
            return super().evaluate(**kwargs)

    model = ToolModel("capability_search", {"query": "weather", "kind": "mcp"}, repeat=True)
    monkeypatch.setattr("xiliu.agents.search_agent.create_agent_model", lambda: model)
    token = active_run.set(
        RunContext(
            "run",
            "session",
            tmp_path,
            capability_manager=CapabilityManager(),
            policy_engine=DenySearch(tmp_path / "policy.json"),
        )
    )
    try:
        result = run_search_agent({"task": "Beijing weather today"}, "Find weather")
    finally:
        active_run.reset(token)
    assert not result["ok"]
    assert result["retryable"] is False
    assert result["sources"] == []
    assert json.loads(result["tool_events"][-1]["output"])["error"] == "policy_denied"
    assert search_sdk[0] == []


def test_empty_web_fallback_does_not_fabricate_sources_or_retry(tmp_path, monkeypatch, search_sdk):
    from xiliu.agents.search_agent import run_search_agent
    from xiliu.capabilities.manager import CapabilityManager
    from xiliu.execution.gateway import RunContext, active_run

    search_sdk[1]["results"] = []
    model = ToolModel("capability_search", {"query": "weather", "kind": "mcp"}, repeat=True)
    monkeypatch.setattr("xiliu.agents.search_agent.create_agent_model", lambda: model)
    token = active_run.set(
        RunContext("run", "session", tmp_path, capability_manager=CapabilityManager())
    )
    try:
        result = run_search_agent({"task": "Beijing weather today"}, "Find weather")
    finally:
        active_run.reset(token)
    assert not result["ok"]
    assert result["sources"] == []
    assert result["retryable"] is False
    assert len(search_sdk[0]) == 1


def test_empty_mcp_fallback_preserves_transient_error(tmp_path, monkeypatch):
    from xiliu.agents.search_agent import run_search_agent
    from xiliu.capabilities.manager import CapabilityManager
    from xiliu.execution.gateway import RunContext, active_run

    class Client:
        def __init__(self, **kwargs):
            pass

        def search(self, **kwargs):
            raise ConnectionError("offline")

    monkeypatch.setattr("xiliu.tools.web_search_tool.TavilyClient", Client)
    model = ToolModel("capability_search", {"query": "weather", "kind": "mcp"}, repeat=True)
    monkeypatch.setattr("xiliu.agents.search_agent.create_agent_model", lambda: model)
    token = active_run.set(
        RunContext("run", "session", tmp_path, capability_manager=CapabilityManager())
    )
    try:
        result = run_search_agent({"task": "Beijing weather today"}, "Find weather")
    finally:
        active_run.reset(token)
    assert not result["ok"]
    assert result["retryable"] is True
    assert result["error"] == "search failed"
    assert result["sources"] == []
    assert [event["tool"] for event in result["tool_events"]] == ["capability_search", "web_search"]
    assert model.calls == 1


def test_existing_search_sources_survive_model_loop_limit(monkeypatch, search_sdk):
    from xiliu.agents.search_agent import run_search_agent

    model = ToolModel("web_search", {"query": "Beijing weather"}, repeat=True)
    monkeypatch.setattr("xiliu.agents.search_agent.create_agent_model", lambda: model)
    result = run_search_agent({"task": "Beijing weather today"}, "Find weather", max_loops=1)
    assert result["ok"]
    assert result["sources"] == ["https://example.com/weather"]
    assert "17 C" in result["summary"]


def test_keyless_search_can_return_sources(search_sdk):
    from xiliu.tools.web_search_tool import WebSearchTool, search_api_key

    token = search_api_key.set(None)
    try:
        result = json.loads(WebSearchTool().invoke({"query": "Beijing weather"}))
    finally:
        search_api_key.reset(token)
    assert result["ok"]
    assert result["results"][0]["url"] == "https://example.com/weather"
    assert search_sdk[2] == [False]


@pytest.mark.parametrize(
    ("failure", "error"),
    [
        (MissingAPIKeyError(), "invalid TAVILY_API_KEY"),
        (InvalidAPIKeyError("internal details"), "invalid TAVILY_API_KEY"),
        (TavilyKeylessLimitError("internal details", code="limit"), "Tavily usage limit exceeded"),
        (ForbiddenError("internal details"), "Tavily request forbidden"),
        (BadRequestError("internal details"), "Tavily rejected search request"),
    ],
)
def test_search_permanent_errors_are_readable_and_not_retried(failure, error, monkeypatch):
    from xiliu.agents.react import run_react
    from xiliu.tools.web_search_tool import WebSearchTool

    class Client:
        def __init__(self, **kwargs):
            pass

        def search(self, **kwargs):
            raise failure

    monkeypatch.setattr("xiliu.tools.web_search_tool.TavilyClient", Client)
    model = ToolModel("web_search", {"query": "Beijing weather"}, repeat=True)
    result = run_react(model, [WebSearchTool()], [], agent="search_agent", attempt=1)
    assert result["retryable"] is False
    assert result["summary"] == error
    assert model.calls == 1
    assert "internal details" not in repr(result)


@pytest.mark.parametrize(
    ("failure", "error"),
    [(ConnectionError("offline"), "search failed"), (TavilyTimeoutError(1), "search timed out")],
)
def test_fast_search_stops_at_first_transient_failure(failure, error, tmp_path, monkeypatch):
    from xiliu.events import FinalEvent

    requests = []

    class Client:
        def __init__(self, **kwargs):
            pass

        def search(self, **kwargs):
            requests.append(kwargs)
            raise failure

    monkeypatch.setattr("xiliu.tools.web_search_tool.TavilyClient", Client)
    model = ToolModel("web_search", {"query": "Beijing weather"}, repeat=True)
    runtime = Runtime(model, data_dir=tmp_path, checkpoint_mode="off", trace_mode="off")
    try:
        events = list(runtime.stream_session("Beijing weather today", str(uuid4()), ""))
    finally:
        runtime.close()
    assert isinstance(events[-1], FinalEvent)
    assert error in events[-1].text
    assert len(requests) == model.calls == 1


@pytest.mark.parametrize("delegate", ["call_search_agent", "agent_call"])
def test_transient_search_retries_only_with_outer_attempt_budget(delegate, tmp_path, monkeypatch):
    from xiliu.events import FinalEvent

    requests = []

    class Client:
        def __init__(self, **kwargs):
            pass

        def search(self, **kwargs):
            requests.append(kwargs)
            raise ConnectionError("offline")

    monkeypatch.setattr("xiliu.tools.web_search_tool.TavilyClient", Client)
    child = ToolModel("web_search", {"query": "Beijing weather"}, repeat=True)
    arguments = {"instruction": "Find weather"}
    if delegate == "agent_call":
        arguments["agent_id"] = "research"
    parent = ToolModel(delegate, arguments, repeat=True)
    runtime = Runtime(
        parent,
        agent_model_factory=lambda: child,
        data_dir=tmp_path,
        checkpoint_mode="off",
        trace_mode="off",
    )
    try:
        events = list(
            runtime.stream_session("Beijing weather today", str(uuid4()), "", mode="standard")
        )
    finally:
        runtime.close()
    assert isinstance(events[-1], FinalEvent)
    assert "3/3" in events[-1].text
    assert "search failed" in events[-1].text
    assert len(requests) == child.calls == parent.calls == 3


def test_new_agent_call_propagates_permanent_search_failure(tmp_path, monkeypatch):
    from xiliu.agents.react import run_react
    from xiliu.agents.runtime import AgentCallTool
    from xiliu.execution.gateway import RunContext, active_run
    from xiliu.graph.workflow import route_after_verifier

    class LimitedClient:
        def __init__(self, **kwargs):
            pass

        def search(self, **kwargs):
            raise UsageLimitExceededError("offline usage limit")

    monkeypatch.setattr("xiliu.tools.web_search_tool.TavilyClient", LimitedClient)
    child = ToolModel("web_search", {"query": "Beijing weather"}, repeat=True)
    monkeypatch.setattr("xiliu.agents.runtime.create_agent_model", lambda: child)
    parent = ToolModel(
        "agent_call", {"agent_id": "research", "instruction": "Find weather"}, repeat=True
    )
    state = {
        "task": "Beijing weather today",
        "workspace": tmp_path,
        "mode": "standard",
        "attempt": 1,
        "max_attempts": 3,
        "graph_state": "failed",
    }
    token = active_run.set(RunContext("run", "session", tmp_path, data_dir=tmp_path))
    try:
        result = run_react(parent, [AgentCallTool(state=state)], [], agent="planner", attempt=1)
    finally:
        active_run.reset(token)
    state["tool_events"] = result["tool_events"]
    output = json.loads(result["tool_events"][-1]["output"])
    assert output["retryable"] is False
    assert output["error"] == "Tavily usage limit exceeded"
    assert result["retryable"] is False
    assert parent.calls == child.calls == 1
    assert route_after_verifier(state) == "final"


def test_cancelled_new_agent_call_does_not_discover_or_invoke(tmp_path, monkeypatch):
    from threading import Event

    from xiliu.agents.runtime import call_agent
    from xiliu.execution.cancellation import TurnCancelled, cancel_signal

    def unexpected_registry(*args, **kwargs):
        raise AssertionError("cancelled invocation must not discover agents")

    monkeypatch.setattr("xiliu.agents.runtime.AgentRegistry", unexpected_registry)
    signal = Event()
    signal.set()
    token = cancel_signal.set(signal)
    try:
        with pytest.raises(TurnCancelled):
            call_agent({"workspace": tmp_path}, "research", "Find weather")
    finally:
        cancel_signal.reset(token)


@pytest.mark.parametrize("boundary", ["tool", "search", "delegate"])
def test_cancellation_escapes_search_boundaries(boundary, tmp_path, monkeypatch):
    from xiliu.agents.react import run_react
    from xiliu.agents.search_agent import run_search_agent
    from xiliu.execution.cancellation import TurnCancelled
    from xiliu.tools.subagent_tools import SupervisorContext

    def cancelled(query: str = "") -> str:
        """Simulate cancellation at an external boundary."""
        raise TurnCancelled()

    with pytest.raises(TurnCancelled):
        if boundary == "tool":
            tool = StructuredTool.from_function(cancelled, name="web_search")
            run_react(
                ToolModel("web_search", {"query": "weather"}),
                [tool],
                [],
                agent="search_agent",
                attempt=1,
            )
        elif boundary == "search":
            monkeypatch.setattr("xiliu.agents.search_agent.create_agent_model", cancelled)
            run_search_agent({"task": "weather"}, "Find weather")
        else:
            monkeypatch.setattr(
                "xiliu.tools.subagent_tools.run_search_agent", lambda *a, **kw: cancelled()
            )
            state = {
                "workspace": tmp_path,
                "attempt": 1,
                "agent_results": [],
                "tool_events": [],
                "research_notes": [],
            }
            SupervisorContext(state, Memory()).delegate("search_agent", "Find weather")
