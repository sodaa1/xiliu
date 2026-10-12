import json
from uuid import uuid4

from langchain_core.messages import AIMessage

from xiliu.events import ErrorEvent, FinalEvent, VerifierEvent
from xiliu.graph.workflow import build_workflow
from xiliu.runtime import Runtime

NODES = {
    "intent_router",
    "capability_router",
    "chat_responder",
    "app_executor",
    "fast_react",
    "planner",
    "capability_discovery",
    "tool_execute",
    "state_collect",
    "execution_verifier",
    "clarification",
    "final",
}


def test_only_one_graph_registers_all_twelve_real_nodes():
    graph = build_workflow(object(), None).get_graph()
    assert set(graph.nodes) - {"__start__", "__end__"} == NODES
    edges = {(edge.source, edge.target) for edge in graph.edges}
    expected = {
        ("intent_router", "capability_router"),
        ("app_executor", "tool_execute"),
        ("tool_execute", "state_collect"),
        ("state_collect", "execution_verifier"),
        ("execution_verifier", "fast_react"),
        ("execution_verifier", "planner"),
        ("clarification", "final"),
        ("final", "__end__"),
        ("intent_router", "__end__"),
        ("chat_responder", "final"),
        ("fast_react", "capability_discovery"),
        ("planner", "capability_discovery"),
        ("capability_discovery", "tool_execute"),
        ("capability_discovery", "execution_verifier"),
        ("state_collect", "capability_discovery"),
        ("execution_verifier", "final"),
        ("execution_verifier", "clarification"),
    } | {("__start__", node) for node in NODES} | {
        ("capability_router", node) for node in {
            "chat_responder", "app_executor", "fast_react", "planner", "clarification"
        }
    }
    assert edges == expected


class LocalModel:
    def invoke(self, messages):
        raise AssertionError("Direct registered actions need no model call")


def test_direct_action_runs_inside_graph_and_verifies_persisted_receipt(tmp_path):
    runtime = Runtime(LocalModel(), data_dir=tmp_path, checkpoint_mode="off", trace_mode="full")
    try:
        events = list(runtime.stream_session("创建待办“论文提交”", str(uuid4()), ""))
        assert not any(isinstance(event, ErrorEvent) for event in events)
        assert any(isinstance(event, VerifierEvent) and event.passed for event in events)
        assert isinstance(events[-1], FinalEvent)
        assert [t["title"] for t in runtime._app_services.tasks.list()] == ["论文提交"]
        assert runtime.last_state["execution_path"] == "app_executor"
        assert runtime.last_node_path == [
            "intent_router",
            "capability_router",
            "app_executor",
            "tool_execute",
            "state_collect",
            "execution_verifier",
            "final",
        ]
        receipt = runtime.last_state["app_receipts"][-1]
        assert receipt["verification"]["passed"] is True
        assert runtime.last_state["tool_events"][-1]["args"]["action_id"] == "tasks.create"
        assert runtime.last_state["execution_ids"]
    finally:
        runtime.close()


def test_fast_model_tools_execute_in_graph_nodes_with_actual_file_effect(tmp_path):
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
                            "id": "write",
                            "name": "file_write",
                            "args": {"path": "report.txt", "content": "real output"},
                        }
                    ],
                )
            return AIMessage(content="Saved the report")

    runtime = Runtime(Model(), data_dir=tmp_path, checkpoint_mode="off", trace_mode="off")
    sid = str(uuid4())
    try:
        events = list(runtime.stream_session("帮我查找并整理一个文件", sid, ""))
        assert not any(isinstance(event, ErrorEvent) for event in events)
        assert isinstance(events[-1], FinalEvent)
        assert (runtime.last_state["workspace"] / "report.txt").read_text() == "real output"
        assert runtime.last_node_path.count("tool_execute") == 1
        assert runtime.last_node_path.count("capability_discovery") == 2
        assert runtime.last_state["execution_result"]["status"] == "completed"
        assert runtime.last_state["tool_events"][0]["tool"] == "file_write"
    finally:
        runtime.close()


def test_confirmation_never_becomes_success_or_retries(tmp_path):
    runtime = Runtime(LocalModel(), data_dir=tmp_path, checkpoint_mode="off", trace_mode="off")
    try:
        folder = runtime._context(tmp_path).owner._app_services.knowledge.create_folder(
            {"name": "AI"}
        )
        events = list(runtime.stream_session("删除知识库文件夹“AI”", str(uuid4()), ""))
        assert isinstance(events[-1], FinalEvent)
        assert any(isinstance(e, VerifierEvent) and not e.passed for e in events)
        assert runtime.last_state["execution_result"]["status"] == "confirmation_required"
        assert runtime.last_node_path.count("tool_execute") == 1
        assert runtime._app_services.knowledge.get_folder(folder["id"])["name"] == "AI"
        assert json.loads(runtime.last_state["tool_events"][-1]["output"])["ok"] is False
    finally:
        runtime.close()
