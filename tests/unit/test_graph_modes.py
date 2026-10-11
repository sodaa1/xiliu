import json
from uuid import uuid4

from langchain_core.messages import AIMessage

from xiliu.api.services.content import ContentService
from xiliu.api.store import AppStore
from xiliu.events import FinalEvent
from xiliu.runtime import Runtime


def test_fast_local_query_has_no_todo_subagent_verifier_or_web(tmp_path):
    item = ContentService(AppStore(tmp_path)).create(
        {"title": "Refero UI", "content": "UI design library", "status": "knowledge"}
    )

    class Model:
        calls = 0
        names = []

        def bind_tools(self, tools):
            self.names = [t.name for t in tools]
            return self

        def invoke(self, messages):
            if "intent router" in messages[0].content:
                return AIMessage(content='{"route":"chat","reason":"bad guess","confidence":1}')
            assert "Verifier" not in messages[0].content
            self.calls += 1
            if self.calls == 1:
                return AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "id": "find",
                            "name": "app",
                            "args": {
                                "operation": "execute",
                                "action_id": "knowledge.search",
                                "arguments": {"query": "Refero"},
                            },
                        }
                    ],
                )
            result = json.loads(messages[-1].content)
            assert result["data"]["hits"][0]["document_id"] == item["id"]
            return AIMessage(content="你收藏的网站是 Refero。")

    model = Model()
    runtime = Runtime(model, data_dir=tmp_path, checkpoint_mode="off", trace_mode="off")
    try:
        events = list(runtime.stream_session("我收藏的 Refero UI 网站叫什么？", str(uuid4()), ""))
    finally:
        runtime.close()
    assert isinstance(events[-1], FinalEvent)
    assert "Refero" in events[-1].text and "failed" not in events[-1].text
    assert model.calls == 2
    assert not {"todo_write", "call_search_agent", "web_search"} & set(model.names)


def test_mode_routing_respects_explicit_and_local_scope():
    from xiliu.graph.routing import mode_router_node

    assert mode_router_node({"task": "查我的知识库"})["mode"] == "fast"
    assert mode_router_node({"task": "比较多篇文章并解释分歧"})["mode"] == "deep"
    assert mode_router_node({"task": "你好", "requested_mode": "standard"})["mode"] == "standard"


def test_non_retryable_tool_failure_exits_without_replanning():
    from xiliu.graph.workflow import route_after_verifier

    assert (
        route_after_verifier(
            {
                "max_attempts": 3,
                "attempt": 1,
                "graph_state": "failed",
                "tool_events": [
                    {
                        "ok": False,
                        "output": '{"ok":false,"retryable":false,"error":"policy_denied"}',
                    }
                ],
            }
        )
        == "final"
    )
