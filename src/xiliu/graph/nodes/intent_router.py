from xiliu.graph.nodes.common import _writer
from xiliu.routing import recognize_intent


def intent_router_node(state, *, model, embedding_matcher=None):
    writer = _writer()
    if writer:
        writer({"type": "progress", "stage": "routing", "message": "正在识别问题类型…"})
    structured = recognize_intent(
        state["task"],
        model=model,
        context=state.get("context_summary", ""),
        embedding_matcher=embedding_matcher,
    )
    return {
        "intent": structured,
        "intent_route": "chat" if structured["intent"] == "chat" else "workflow",
        "intent_confidence": structured["confidence"],
        "command": structured["action"] if structured["intent"] == "control" else "",
    }
