from xiliu.graph.routing import external_scope
from xiliu.graph.workflow import route_after_verifier

TASK = (
    "调研一下github上关于python相关的最热门的五个项目整理成一份md文件，"
    "存入inbox，再归类入知识库的“优质项目”文件夹，如果没有就创建一个"
)


def test_external_source_is_not_hidden_by_local_destination():
    assert external_scope(TASK)
    assert not external_scope("禁止联网，" + TASK)
    assert not external_scope("查找知识库里我收藏的 GitHub 项目")


def test_mixed_task_retries_after_successful_write():
    state = dict(
        max_attempts=3,
        attempt=1,
        graph_state="failed",
        execution_path="planner",
        tool_scope="all",
        execution_result={"status": "failed"},
        tool_events=[{"ok": True, "tool": "app", "args": {"action_id": "inbox.import_text"}}],
    )
    assert route_after_verifier(state) == "planner"


def test_requested_markdown_requires_written_artifact(tmp_path):
    from xiliu.graph.goal_verification import goal_failure

    assert goal_failure({"task": TASK, "workspace": tmp_path}, []) == (
        "Missing requested Markdown file artifact"
    )


def test_mixed_source_destination_uses_planner():
    from xiliu.graph.nodes.capability_router import capability_router_node

    result = capability_router_node(
        {
            "task": TASK,
            "intent": {
                "intent": "task",
                "domain": "research",
                "action": "search",
                "complexity": "simple",
                "source": "model",
                "preferred_capability": "",
            },
        }
    )
    assert result["execution_path"] == "planner"
    assert result["tool_scope"] == "all"
