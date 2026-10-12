import json

import pytest

from tests.integration.test_app_semantic_boundaries import run
from tests.integration.test_semantic_rule_matching import SemanticModel
from xiliu.api.services.conversations import ConversationService
from xiliu.api.services.model_settings import ModelSettingsService
from xiliu.api.store import AppStore
from xiliu.app.memory import conversation_data, provenance
from xiliu.routing import recognize_intent

REQUEST = (
    "创建自动任务「AI晨报」：每天早上九点对昨天的待办事项创建了什么，"
    "完成了什么，还剩什么没有完成进行总结"
)
PROMPT = "对昨天的待办事项创建了什么，完成了什么，还剩什么没有完成进行总结"


def test_one_request_prepares_atomic_automation_and_keeps_confirmation(tmp_path):
    state, app, _ = run(
        tmp_path,
        dict(
            kind="write",
            domain="automations",
            action_id="automations.create",
            arguments={"name": "AI晨报", "prompt": PROMPT, "hour": 9, "minute": 0},
        ),
        REQUEST,
    )
    assert state["execution_result"]["status"] == "confirmation_required"
    receipt = state["app_receipts"][-1]
    assert receipt["action_id"] == "automations.create"
    assert receipt["arguments"]["hour"] == 9
    assert receipt["arguments"]["prompt"] == PROMPT
    assert app.automations.list() == []
    assert app.tasks.list() == []


def pending_context(tmp_path, compressed=False):
    store = AppStore(tmp_path)
    cid = store.create()["id"]
    store.append_message(cid, "user", "创建自动任务「AI晨报」")
    reply = store.append_message(
        cid,
        "assistant",
        "每天几点运行、需要总结什么？",
        metadata={
            "execution_result": {
                "status": "clarification_required",
                "semantic_decision": {
                    "kind": "clarify",
                    "domain": "automations",
                    "action_id": None,
                },
            },
        },
    )
    if compressed:
        store.save_summary(cid, "正在补充自动任务参数。", reply["seq"])
    store.append_message(cid, "user", "顺便说说什么是知识管理")
    store.append_message(cid, "assistant", "知识管理是组织和使用知识。")
    service = ConversationService(store, ModelSettingsService(tmp_path / ".env"))
    return store, cid, service


@pytest.mark.parametrize("compressed", [False, True])
def test_pending_request_is_explicit_memory_until_clear(tmp_path, compressed):
    store, cid, service = pending_context(tmp_path, compressed)
    context = service.build_context(cid)
    pending = conversation_data(context)["pending_requests"]
    assert pending[-1]["domain"] == "automations"
    assert pending[-1]["user_request"] == "创建自动任务「AI晨报」"
    assert "AI晨报" in provenance(context, "每天早上九点总结昨天待办")[0]
    store.clear_context(cid)
    assert not conversation_data(service.build_context(cid)).get("pending_requests")


def test_followup_rule_cannot_override_pending_domain_before_model(tmp_path):
    _, cid, service = pending_context(tmp_path)
    from langchain_core.messages import AIMessage

    class RoutingModel(SemanticModel):
        def invoke(self, messages):
            assert "pending_requests" in str(messages)
            return AIMessage(
                content=json.dumps(
                    dict(
                        intent="task",
                        domain="automations",
                        action="app:match",
                        complexity="simple",
                        confidence=1,
                    )
                )
            )

    parsed = recognize_intent(
        "每天早上九点对昨天的待办事项创建了什么，完成了什么进行总结",
        context=service.build_context(cid),
        model=RoutingModel({}),
    )
    assert parsed["domain"] == "automations"
    assert parsed["source"] == "llm"


def test_confirmed_creation_clears_pending_but_read_does_not(tmp_path):
    store, cid, service = pending_context(tmp_path)
    store.append_message(cid, "user", "列出自动任务")
    store.append_message(
        cid,
        "assistant",
        "没有自动任务",
        metadata={
            "execution_result": {
                "status": "completed",
                "verified": True,
                "semantic_decision": {"kind": "read", "domain": "automations"},
            },
        },
    )
    assert conversation_data(service.build_context(cid))["pending_requests"]
    store.append_message(
        cid,
        "assistant",
        "已确认创建",
        metadata={
            "app_receipts": [
                {
                    "ok": True,
                    "action_id": "automations.create",
                    "verification": {"passed": True},
                    "records": [{"id": "test", "name": "AI晨报"}],
                }
            ]
        },
    )
    assert not conversation_data(service.build_context(cid))["pending_requests"]
