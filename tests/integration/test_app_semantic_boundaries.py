"""AppIntent contracts retained for checkpoint compatibility and planner boundaries."""

from uuid import uuid4

import pytest

from tests.integration.test_semantic_rule_matching import SemanticModel
from xiliu.api.app import create_app
from xiliu.runtime import Runtime


def run(tmp_path, parsed, query, setup=None, model=None, *, planner=False):
    """Exercise checkpoint-compatible semantic contracts, or the current planner graph."""
    application = create_app(data_dir=tmp_path, env_file=tmp_path / ".env")
    if setup:
        setup(application.state)
    model = model or SemanticModel(parsed)
    runtime = Runtime(
        model,
        data_dir=tmp_path,
        app_services=application.state.app_services,
        checkpoint_mode="off",
        trace_mode="off",
    )
    try:
        if planner:
            list(runtime.stream_session(query, str(uuid4()), ""))
            state = runtime.last_state
        else:
            from xiliu.app.executor import execute_app_request
            from xiliu.execution.gateway import active_run
            from xiliu.runtime import _activate_run_context

            with _activate_run_context(runtime._context(tmp_path, str(uuid4()))):
                outcome = execute_app_request(
                    query, application.state.app_services, active_run.get(), model=model
                )
            assert outcome is not None
            # The compatibility adapter reports actual dispatcher receipts. Verify
            # those outcomes without involving the new planner's different protocol.
            state = {
                "result": outcome["text"],
                "app_receipts": outcome["receipts"],
                "execution_result": {
                    **outcome,
                    "verified": outcome["status"] == "completed"
                    and all(r["verification"]["passed"] for r in outcome["receipts"]),
                },
            }
        return state, application.state, model
    finally:
        runtime.close()


@pytest.mark.parametrize(
    "query", ["目前待办有哪些", "列出待办事项", "全部待办给我看看", "待办清单有什么"]
)
def test_collection_read_is_not_a_bulk_write(tmp_path, query):
    state, app, _ = run(
        tmp_path,
        dict(kind="read", domain="tasks", action_id="tasks.list", scope="all", confidence=0.75),
        query,
        lambda app: app.tasks.create({"title": "阅读论文"}),
    )
    assert state["execution_result"]["verified"] is True
    assert state["app_receipts"][-1]["action_id"] == "tasks.list"
    assert state["result"] == "阅读论文"
    assert len(app.tasks.list()) == 1
    assert state["execution_result"]["semantic_decision"]["scope"] == "all"


def test_registry_domain_wins_over_redundant_model_domain(tmp_path):
    state, _, _ = run(
        tmp_path, dict(kind="read", domain="inbox", action_id="tasks.list"), "目前待办有哪些"
    )
    assert state["execution_result"]["verified"] is True


def test_relative_date_reaches_model_and_normalized_name_is_accepted(tmp_path):
    state, app, model = run(
        tmp_path,
        dict(
            kind="write",
            domain="tasks",
            action_id="tasks.create",
            arguments={"title": "阅读论文", "due_at": "2026-10-13T09:00:00+08:00"},
        ),
        "明天上午九点提醒我读一下论文，加到待办",
    )
    assert state["execution_result"]["verified"] is True
    assert app.tasks.list()[0]["due_at"] == "2026-10-13T09:00:00+08:00"
    assert len(model.rule_reads) == 1
    assert "current_time" in str(model.rule_reads[0])


def test_unsupported_bulk_write_stays_blocked_with_relevant_reason(tmp_path):
    state, app, _ = run(
        tmp_path,
        dict(kind="write", domain="tasks", action_id="tasks.delete", scope="all"),
        "删除全部待办",
        lambda app: app.tasks.create({"title": "保留"}),
    )
    assert len(app.tasks.list()) == 1
    assert not state["execution_result"]["verified"]
    assert "Inbox" not in state["result"] and "收件箱" not in state["result"]
    assert state["execution_result"]["reason_code"] == "unsupported_bulk_write"


def test_collection_write_uses_declared_capability_not_specific_phrase(tmp_path):
    state, app, _ = run(
        tmp_path,
        dict(kind="write", domain="inbox", action_id="inbox.classify_all", scope="all"),
        "把 Inbox 里剩下的统一归类",
    )
    assert state["execution_result"]["verified"] is True
    assert state["app_receipts"][-1]["action_id"] == "inbox.classify_all"


def test_write_uses_registry_domain_and_not_self_reported_confidence(tmp_path):
    state, app, _ = run(
        tmp_path,
        dict(
            kind="write",
            domain="inbox",
            action_id="tasks.create",
            confidence=0.5,
            arguments={"title": "阅读论文"},
        ),
        "新建待办，提醒我读一下论文",
    )
    assert state["execution_result"]["verified"] is True
    assert app.tasks.list()[0]["title"] == "阅读论文"


@pytest.mark.parametrize("due", ["tomorrow", "2026-10-13T09:00:00", "2026-10-13"])
def test_invalid_or_timezone_free_dates_do_not_write(tmp_path, due):
    state, app, _ = run(
        tmp_path,
        dict(
            kind="write",
            domain="tasks",
            action_id="tasks.create",
            arguments={"title": "阅读论文", "due_at": due},
        ),
        "明天上午九点加个阅读论文的待办",
    )
    assert not state["execution_result"]["verified"]
    assert app.tasks.list() == []


@pytest.mark.parametrize("planner", [False, True], ids=["checkpoint-adapter", "planner"])
def test_model_call_itself_does_not_authorize_ai(tmp_path, planner):
    state, app, _ = run(
        tmp_path,
        dict(
            kind="write",
            domain="inbox",
            action_id="inbox.classify_all",
            scope="all",
            arguments={"use_ai": True},
        ),
        "把 Inbox 里剩下的统一归类",
        setup=lambda app: app.content.create({"content": "保留原文", "status": "inbox"}),
        planner=planner,
    )
    assert not state["execution_result"]["verified"]
    assert len(app.content.list("inbox")) == 1
    assert not app.content.list("knowledge")
    if planner:
        assert state["app_receipts"]
        assert all(
            not receipt["ok"]
            and receipt["error"] == "ai_metadata_not_authorized"
            and receipt["retryable"] is False
            for receipt in state["app_receipts"]
        )
    else:
        assert not state.get("app_receipts")


@pytest.mark.parametrize("valid", [True, False])
def test_semantic_object_resolution_checks_actual_database_candidates(tmp_path, valid):
    from xiliu.app.selection import ObjectSelection

    ids = []

    def setup(app):
        ids.append(app.tasks.create({"title": "阅读论文"})["id"])

    class SelectingModel(SemanticModel):
        def with_structured_output(self, schema, **kwargs):
            if schema is ObjectSelection:
                return SemanticModel(
                    {"ids": [ids[0] if valid else "invented"]}
                ).with_structured_output(schema)
            return super().with_structured_output(schema, **kwargs)

    parsed = dict(kind="write", domain="tasks", action_id="tasks.complete", selector="论文相关那项")
    state, app, _ = run(
        tmp_path, parsed, "把与读文章有关的那个待办标记完成", setup, SelectingModel(parsed)
    )
    assert bool(state["execution_result"]["verified"]) is valid
    assert app.tasks.list()[0]["completed"] is valid
