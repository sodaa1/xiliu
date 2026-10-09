from xiliu.graph.nodes import planner_node


def standard_node(state, **kwargs):
    # Existing executor performs planning and acting in a single bounded ReAct invocation.
    return planner_node(state, **kwargs)
