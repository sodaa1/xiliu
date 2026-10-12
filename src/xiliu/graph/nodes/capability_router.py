from xiliu.routing import select_execution


def capability_router_node(state):
    path = select_execution(state["intent"])
    return {"execution_path": path, "route_reason": f"{state['intent']['source']}: {path}"}
