from xiliu.graph.routing import external_scope, local_scope
from xiliu.routing import select_execution


def capability_router_node(state):
    path = select_execution(state["intent"])
    app_only = path == "app_executor"
    if external_scope(state["task"]) and local_scope(state["task"]):
        path = "planner"
        app_only = False
    if app_only:
        path = "planner"
    return {
        "execution_path": path,
        "tool_scope": "app" if app_only else "all",
        "route_reason": f"{state['intent']['source']}: {path}",
    }
