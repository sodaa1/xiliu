from typing import get_type_hints

from xiliu.app.actions import get_registry
from xiliu.capabilities.manager import CapabilityManager
from xiliu.graph.state import GraphState


def test_state_carries_structured_routing_and_execution_contract():
    fields = get_type_hints(GraphState)
    assert {
        "intent",
        "capability_candidates",
        "tool_events",
        "evidence",
        "execution_result",
        "execution_ids",
        "results",
        "loop_messages",
        "pending_calls",
    } <= fields.keys()


def test_registry_discovers_individual_app_actions_and_other_kinds():
    manager = CapabilityManager()
    action = manager.get("app:tasks.create")
    assert action is not None
    assert action.kind == "app"
    assert action.source_id == "tasks.create"
    assert manager.search("tasks.create", kind="app")[0].id == action.id


def test_app_discovery_does_not_expand_permission():
    manager = CapabilityManager()
    action = manager.get("app:knowledge.folders.delete")
    assert action is not None
    assert action.permission == get_registry()[action.source_id].permission
    assert action.requires_confirmation is True
