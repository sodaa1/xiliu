import json

from xiliu.execution.gateway import ExecutionGateway, RunContext
from xiliu.policy.engine import PolicyEngine


def test_local_scope_gateway_rejects_web_without_invoking_it(tmp_path):
    from xiliu.tools.web_search_tool import WebSearchTool

    class Trap(WebSearchTool):
        def _run(self, **kwargs):
            raise AssertionError("network must not execute")

    context = RunContext(
        "r", "s", tmp_path, local_only=True, policy_engine=PolicyEngine(tmp_path / "policy.json")
    )
    raw = ExecutionGateway().wrap_tool(Trap(), context).invoke({"query": "x"})
    assert json.loads(raw)["error"] == "source_scope_denied"


def test_mcp_direct_tool_source_is_evidence_without_subagent():
    from xiliu.execution.evidence import evidence_from_events
    from xiliu.graph.verification import requirements_failure

    event = {
        "event_id": "m1",
        "agent": "planner",
        "tool": "mcp_call",
        "args": {},
        "ok": True,
        "attempt": 1,
        "phase": None,
        "output": json.dumps({"ok": True, "text": "Source: https://example.com/article"}),
    }
    state = {
        "task": "search external sources",
        "supervisor_ok": True,
        "todos": [{"status": "completed"}],
        "agent_results": [],
        "research_notes": [],
        "tool_events": [event],
    }
    assert evidence_from_events([event])[0]["matched"]
    assert requirements_failure(state) is None


def test_negated_network_request_does_not_authorize_external_sources():
    from xiliu.graph.routing import external_scope

    assert not external_scope("仅搜索我的知识库，不要联网")
    assert not external_scope("Search my saved notes without internet access")
    assert external_scope("结合我的资料和最新网络资料")
    assert not external_scope("查我收藏的最新新闻，不要联网")
    assert not external_scope("我收藏的最新新闻在哪里？")


def test_my_ui_bookmarks_are_a_fast_local_task():
    from xiliu.graph.routing import local_scope
    from xiliu.routing import recognize_intent, select_execution

    task = "我的 UI 收藏网站叫什么？"
    assert local_scope(task)
    assert select_execution(recognize_intent(task, model=object())) == "fast_react"
