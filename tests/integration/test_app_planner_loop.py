import json
from uuid import uuid4

import pytest
from langchain_core.messages import AIMessage, ToolMessage

from xiliu.runtime import Runtime

ANSWER = "RoPE 通过旋转位置编码表示相对位置。"


class AppPlanModel:
    def __init__(self, omit=False):
        self.omit = omit
        self.round = 0
        self.verifications = 0
        self.bound = []

    def bind_tools(self, tools):
        self.bound.append([tool.name for tool in tools])
        return self

    def invoke(self, messages):
        system = str(messages[0].content)
        if "intent router" in system:
            return AIMessage(
                content=json.dumps(
                    dict(
                        intent="task",
                        domain="knowledge",
                        action="app:match",
                        complexity="simple",
                        preferred_capability="",
                        confidence=1.0,
                    )
                )
            )
        if not self.bound or "actual_execution_receipts" in str(messages[-1].content):
            self.verifications += 1
            failed = self.omit and self.verifications == 1
            return AIMessage(
                content=json.dumps(
                    dict(
                        status="failed" if failed else "passed",
                        reason="Missing card and classification"
                        if failed
                        else "All requested effects verified",
                    )
                )
            )
        self.round += 1
        receipts = [json.loads(m.content) for m in messages if isinstance(m, ToolMessage)]
        actions = {r.get("action_id"): r for r in receipts}
        if "knowledge.folders.ensure" not in actions:
            action, args = "knowledge.folders.ensure", {"name": "模型原理"}
        elif self.omit and self.verifications == 0:
            return self.done()
        elif "inbox.import_text" not in actions:
            assert ANSWER in str(messages)
            action, args = "inbox.import_text", {"text": ANSWER, "use_ai": False}
        elif "inbox.classify_selected" not in actions:
            action, args = (
                "inbox.classify_selected",
                {
                    "item_ids": [actions["inbox.import_text"]["data"]["id"]],
                    "folder_id": actions["knowledge.folders.ensure"]["data"]["id"],
                    "use_ai": False,
                },
            )
        else:
            return self.done()
        return AIMessage(
            content="",
            tool_calls=[
                dict(
                    id=f"step-{self.round}",
                    name="app",
                    args=dict(operation="execute", action_id=action, arguments=args),
                )
            ],
        )

    def done(self):
        return AIMessage(
            content=json.dumps(
                dict(
                    summary="已保存卡片到模型原理",
                    plan_summary="创建卡片、确保文件夹、归类",
                    acceptance_criteria=["卡片内容等于回答", "卡片属于模型原理文件夹"],
                    ready_for_verification=True,
                )
            )
        )


@pytest.mark.parametrize("omit", [False, True])
def test_app_plan_uses_real_receipts_and_completes_all_effects(tmp_path, omit):
    model = AppPlanModel(omit)
    runtime = Runtime(model, data_dir=tmp_path, checkpoint_mode="off", trace_mode="off")
    history = "Previous conversation context:\n" + json.dumps(
        {"messages": [{"role": "assistant", "content": ANSWER}]}, ensure_ascii=False
    )
    try:
        list(
            runtime.stream_session(
                "将回答存成一个卡片，在知识库创建一个名为“模型原理”的文件夹放进去",
                str(uuid4()),
                history,
            )
        )
        state = runtime.last_state
        assert state["execution_path"] == "planner"
        assert state["tool_scope"] == "app"
        assert state["execution_result"]["verified"] is True
        assert all(names == ["app"] for names in model.bound)
        assert runtime.last_node_path.count("tool_execute") == 3
        folders = runtime._app_services.knowledge.list_folders()
        cards = runtime._app_services.content.list("knowledge")
        assert len(folders) == 1 and len(cards) == 1
        assert cards[0]["content"] == ANSWER
        assert cards[0]["folder_id"] == folders[0]["id"]
        assert model.verifications == (2 if omit else 1)
    finally:
        runtime.close()


@pytest.mark.parametrize(
    "tool,args",
    [
        ("web_search", {"query": "not authorized"}),
        ("file_write", {"path": "escape.txt", "content": "not authorized"}),
        ("mcp_call", {"capability_id": "mcp:test:write", "arguments": {}}),
        ("app", {"operation": "execute", "action_id": "capabilities.skills", "arguments": {}}),
    ],
)
def test_app_scope_rejects_tools_outside_catalog(tmp_path, tool, args):
    class Model:
        def bind_tools(self, tools):
            assert [t.name for t in tools] == ["app"]
            return self

        def invoke(self, messages):
            return AIMessage(content="", tool_calls=[dict(id="blocked", name=tool, args=args)])

    runtime = Runtime(Model(), data_dir=tmp_path, checkpoint_mode="off", trace_mode="off")
    try:
        list(runtime.stream_session("创建待办“阅读论文”", str(uuid4()), "", max_attempts=1))
        assert runtime.last_state["execution_result"]["verified"] is False
        assert not runtime._app_services.tasks.list()
        assert not (runtime.last_state["workspace"] / "escape.txt").exists()
        assert runtime.last_state["tool_events"][0]["ok"] is False
    finally:
        runtime.close()


def test_app_plan_confirmation_stops_before_later_steps(tmp_path):
    class Model:
        def bind_tools(self, tools):
            return self

        def invoke(self, messages):
            return AIMessage(
                content="",
                tool_calls=[
                    dict(
                        id="confirm",
                        name="app",
                        args=dict(
                            operation="execute",
                            action_id="automations.create",
                            arguments={
                                "name": "晨报",
                                "prompt": "总结待办",
                                "hour": 9,
                                "minute": 0,
                            },
                        ),
                    ),
                    dict(
                        id="later",
                        name="app",
                        args=dict(
                            operation="execute",
                            action_id="tasks.create",
                            arguments={"title": "不应创建"},
                        ),
                    ),
                ],
            )

    runtime = Runtime(Model(), data_dir=tmp_path, checkpoint_mode="off", trace_mode="off")
    try:
        list(runtime.stream_session("创建自动任务“晨报”，每天九点总结待办", str(uuid4()), ""))
        assert runtime.last_state["execution_result"]["status"] == "confirmation_required"
        assert len(runtime.last_state["app_receipts"]) == 1
        assert not runtime._app_services.tasks.list()
        assert not runtime._app_services.automations.list()
    finally:
        runtime.close()


def test_app_plan_background_policy_still_blocks_writes(tmp_path):
    model = AppPlanModel()
    runtime = Runtime(
        model,
        data_dir=tmp_path,
        checkpoint_mode="off",
        trace_mode="off",
        actor_type="automation",
        policy_profile="background",
        approval_mode="deny",
    )
    try:
        list(runtime.stream_session("知识库创建“模型原理”文件夹", str(uuid4()), "", max_attempts=1))
        assert not runtime._app_services.knowledge.list_folders()
        assert runtime.last_state["execution_result"]["verified"] is False
        assert runtime.last_state["tool_events"][0]["ok"] is False
    finally:
        runtime.close()


def test_app_plan_clarification_keeps_pending_domain(tmp_path):
    class Model:
        def bind_tools(self, tools):
            return self

        def invoke(self, messages):
            return AIMessage(
                content=json.dumps(
                    dict(
                        summary="每天几点运行？",
                        plan_summary="等待时间",
                        acceptance_criteria=[],
                        ready_for_verification=False,
                    )
                )
            )

    runtime = Runtime(Model(), data_dir=tmp_path, checkpoint_mode="off", trace_mode="off")
    try:
        list(runtime.stream_session("创建自动任务“晨报”", str(uuid4()), ""))
        result = runtime.last_state["execution_result"]
        assert result["status"] == "clarification_required"
        assert result["semantic_decision"]["domain"] == "automations"
        assert not runtime._app_services.automations.list()
    finally:
        runtime.close()
