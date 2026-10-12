from functools import partial

from langgraph.graph import END, START, StateGraph

from xiliu.agents.react import payload
from xiliu.graph import nodes
from xiliu.graph.state import GraphState

NODE_NAMES = (
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
)


def route_entry(state):
    node = state.get("resume_node", "intent_router")
    if node == "verifier":
        node = "execution_verifier"
    if node not in NODE_NAMES:
        raise ValueError("invalid resume node")
    return node


def route_after_verifier(state):
    if state["max_attempts"] < 1:
        raise ValueError("max_attempts must be at least 1")
    status = state.get("execution_result", {}).get("status")
    if status == "clarification_required":
        return "clarification"
    if status == "confirmation_required":
        return "final"
    if state["graph_state"] == "passed" or state["attempt"] >= state["max_attempts"]:
        return "final"
    events = state.get("tool_events", [])
    if (
        events
        and not events[-1].get("ok")
        and payload(events[-1].get("output", "")).get("retryable") is False
    ):
        return "final"
    if state.get("execution_path") == "app_executor":
        return "clarification"
    if state.get("tool_scope") == "app":
        return "planner"
    # Planner retries retain messages and receipts, including successful writes.
    return "fast_react" if state.get("execution_path") == "fast_react" else "planner"


def after_discovery(state):
    return "tool_execute" if state.get("pending_calls") else "execution_verifier"


def after_collect(state):
    return "execution_verifier" if state.get("loop_complete") else "capability_discovery"


def build_workflow(
    model, memory_manager, checkpointer=None, *, model_name="unknown-model", embedding_matcher=None
):
    """The only conversational Agent graph. All adapters use this builder."""
    graph = StateGraph(GraphState)
    graph.add_node(
        "intent_router",
        partial(nodes.intent_router_node, model=model, embedding_matcher=embedding_matcher),
    )
    graph.add_node("capability_router", nodes.capability_router_node)
    graph.add_node(
        "chat_responder", partial(nodes.chat_responder_node, model=model, model_name=model_name)
    )
    graph.add_node("app_executor", nodes.app_executor_node)
    for name in (
        "fast_react",
        "planner",
        "capability_discovery",
        "tool_execute",
        "execution_verifier",
    ):
        graph.add_node(
            name,
            partial(getattr(nodes, name + "_node"), model=model, memory_manager=memory_manager),
        )
    graph.add_node(
        "state_collect", partial(nodes.state_collect_node, memory_manager=memory_manager)
    )
    graph.add_node("clarification", nodes.clarification_node)
    graph.add_node("final", partial(nodes.final_node, memory_manager=memory_manager))
    graph.add_conditional_edges(START, route_entry, {name: name for name in NODE_NAMES})
    graph.add_conditional_edges(
        "intent_router",
        lambda s: END if s.get("command") else "capability_router",
        {END: END, "capability_router": "capability_router"},
    )
    graph.add_conditional_edges(
        "capability_router",
        lambda s: s["execution_path"],
        {
            name: name
            for name in ("chat_responder", "app_executor", "fast_react", "planner", "clarification")
        },
    )
    graph.add_edge("chat_responder", "final")
    graph.add_edge("app_executor", "tool_execute")
    graph.add_edge("fast_react", "capability_discovery")
    graph.add_edge("planner", "capability_discovery")
    graph.add_conditional_edges(
        "capability_discovery",
        after_discovery,
        {name: name for name in ("tool_execute", "execution_verifier")},
    )
    graph.add_edge("tool_execute", "state_collect")
    graph.add_conditional_edges(
        "state_collect",
        after_collect,
        {name: name for name in ("capability_discovery", "execution_verifier")},
    )
    graph.add_conditional_edges(
        "execution_verifier",
        route_after_verifier,
        {name: name for name in ("final", "fast_react", "planner", "clarification")},
    )
    graph.add_edge("clarification", "final")
    graph.add_edge("final", END)
    return graph.compile(checkpointer=checkpointer)


def build_entry_workflow(model, *, model_name="unknown-model"):
    """Compatibility alias; returns the same twelve-node graph, never a separate entry graph."""
    return build_workflow(model, None, model_name=model_name)
