import json

from xiliu.graph.verification import requirements_failure


def test_local_document_id_satisfies_research_without_search_agent():
    state = {
        "task": "搜索我的本地知识库 Refero",
        "supervisor_ok": True,
        "todos": [{"status": "completed"}],
        "agent_results": [],
        "research_notes": [],
        "tool_events": [
            {
                "event_id": "local-1",
                "agent": "planner",
                "tool": "app",
                "ok": True,
                "args": {"action_id": "knowledge.search", "operation": "execute"},
                "attempt": 1,
                "phase": None,
                "output": json.dumps(
                    {
                        "ok": True,
                        "data": {
                            "matched": True,
                            "hits": [{"document_id": "doc-1", "title": "Refero", "snippet": "UI"}],
                        },
                    }
                ),
            }
        ],
    }
    assert requirements_failure(state) is None


def test_events_and_evidence_are_idempotent_and_empty_hits_are_not_matches():
    from xiliu.execution.evidence import evidence_from_events, merge_events_by_id

    event = {
        "event_id": "q1",
        "tool": "app",
        "agent": "fast",
        "ok": True,
        "args": {"action_id": "knowledge.search", "operation": "execute"},
        "output": json.dumps({"ok": True, "data": {"matched": False, "hits": []}}),
    }
    assert len(merge_events_by_id([event], [event])) == 1
    evidence = evidence_from_events([event])
    assert evidence[0]["tool_ok"] is True
    assert evidence[0]["matched"] is False
    assert evidence[0]["source_id"] is None
