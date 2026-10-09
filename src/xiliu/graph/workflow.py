from __future__ import annotations

from functools import partial
from typing import Any, Literal

from langgraph.graph import END, START, StateGraph

from xiliu.agents.react import payload
from xiliu.graph.modes.deep import supervisor_node
from xiliu.graph.modes.fast import fast_react_node
from xiliu.graph.nodes import (
    chat_responder_node,
    final_node,
    intent_route_fn,
    intent_router_node,
    planner_node,
    verifier_node,
)
from xiliu.graph.routing import mode_route, mode_router_node
from xiliu.graph.state import GraphState


def route_entry(state: GraphState) -> str:
    node = state.get("resume_node", "planner")
    if node not in {"planner", "verifier", "final"}:
        raise ValueError("invalid resume node")
    return (
        "mode_router"
        if node == "planner" and not state.get("attempt")
        else (mode_route(state) if node == "planner" else node)
    )


def route_after_verifier(state: GraphState) -> Literal["planner", "supervisor", "final"]:
    if state["max_attempts"] < 1:
        raise ValueError("max_attempts must be at least 1")
    if state["graph_state"] == "passed" or state["attempt"] >= state["max_attempts"]:
        return "final"
    events = state.get("tool_events", [])
    if (
        events
        and not events[-1].get("ok")
        and payload(events[-1].get("output", "")).get("retryable") is False
    ):
        return "final"
    return "supervisor" if state.get("mode") == "deep" else "planner"


def build_entry_workflow(model: Any, *, model_name: str = "unknown-model"):
    """Build the intent-routing graph that precedes the main workflow."""
    graph = StateGraph(GraphState)
    graph.add_node("intent_router", partial(intent_router_node, model=model))
    graph.add_node(
        "chat_responder", partial(chat_responder_node, model=model, model_name=model_name)
    )
    graph.add_edge(START, "intent_router")
    graph.add_conditional_edges(
        "intent_router",
        intent_route_fn,
        {"chat_responder": "chat_responder", "planner": END},
    )
    graph.add_edge("chat_responder", END)
    return graph.compile()


def build_workflow(model: Any, memory_manager: Any, checkpointer: Any | None = None):
    graph = StateGraph(GraphState)
    graph.add_node("mode_router", mode_router_node)
    graph.add_node(
        "fast_react", partial(fast_react_node, model=model, memory_manager=memory_manager)
    )
    graph.add_node(
        "supervisor", partial(supervisor_node, model=model, memory_manager=memory_manager)
    )
    graph.add_node("planner", partial(planner_node, model=model, memory_manager=memory_manager))
    graph.add_node("verifier", partial(verifier_node, model=model, memory_manager=memory_manager))
    graph.add_node("final", partial(final_node, memory_manager=memory_manager))
    graph.add_conditional_edges(
        START,
        route_entry,
        {
            name: name
            for name in ("mode_router", "fast_react", "supervisor", "planner", "verifier", "final")
        },
    )
    graph.add_conditional_edges(
        "mode_router", mode_route, {name: name for name in ("fast_react", "planner", "supervisor")}
    )
    graph.add_edge("fast_react", "final")
    graph.add_edge("supervisor", "verifier")
    graph.add_edge("planner", "verifier")
    graph.add_conditional_edges(
        "verifier",
        route_after_verifier,
        {"planner": "planner", "supervisor": "supervisor", "final": "final"},
    )
    graph.add_edge("final", END)
    return graph.compile(checkpointer=checkpointer)


build_complex_workflow = build_workflow
