import json
from uuid import uuid4

import pytest

from tests.integration.test_semantic_rule_matching import SemanticModel
from xiliu.api.services.conversations import ConversationService
from xiliu.api.services.model_settings import ModelSettingsService
from xiliu.api.store import AppStore
from xiliu.runtime import Runtime


@pytest.mark.parametrize(
    "followup", ["将上一个归类", "把刚才那份资料归档", "前面保存的那条，整理一下"]
)
@pytest.mark.parametrize("compressed", [False, True])
def test_reference_survives_intervening_turns_and_compression(tmp_path, followup, compressed):
    model = SemanticModel(
        dict(
            kind="write",
            domain="inbox",
            action_id="inbox.import_text",
            arguments={"text": "构建个人知识库的灵感"},
        )
    )
    runtime = Runtime(model, data_dir=tmp_path, checkpoint_mode="off", trace_mode="off")
    store = AppStore(tmp_path)
    conversation = store.create()
    cid = conversation["id"]
    service = ConversationService(store, ModelSettingsService(tmp_path / ".env"))
    try:
        request = "把文字「构建个人知识库的灵感」存入 Inbox。"
        list(runtime.stream_session(request, cid, "", include_workspace_history=False))
        item = runtime._app_services.content.list("inbox")[0]
        store.append_message(cid, "user", request)
        saved = store.append_message(
            cid,
            "assistant",
            "资料已提交",
            metadata={"app_receipts": runtime.last_state["app_receipts"]},
        )
        if compressed:
            store.save_summary(
                cid, "用户保存了一条关于知识库的灵感，后续可能需要整理。", saved["seq"]
            )
        store.append_message(cid, "user", "顺便解释一下知识管理")
        store.append_message(cid, "assistant", "知识管理包括收集与整理。")
        model.parsed = dict(
            kind="write",
            domain="inbox",
            action_id="inbox.classify_selected",
            selector=item["id"],
            arguments={"use_ai": False},
        )
        memory = service.build_context(cid)
        assert item["id"] in memory
        list(runtime.stream_session(followup, cid, memory, include_workspace_history=False))
        assert runtime.last_state["execution_result"]["verified"] is True
        assert runtime._app_services.content.get(item["id"])["status"] == "knowledge"
        prompt = "\n".join(str(m.content) for m in model.rule_reads[-1])
        assert "知识管理" in prompt and item["id"] in prompt and "memory" in prompt
        store.clear_context(cid)
        assert item["id"] not in service.build_context(cid)
    finally:
        runtime.close()


def test_all_completes_pending_scope_without_adding_authorization(tmp_path):
    model = SemanticModel(
        dict(
            kind="write",
            domain="inbox",
            action_id="inbox.import_text",
            arguments={"text": "待整理原文"},
        )
    )
    runtime = Runtime(model, data_dir=tmp_path, checkpoint_mode="off", trace_mode="off")
    try:
        list(runtime.stream_session("Inbox 保存「待整理原文」", str(uuid4()), ""))
        model.parsed = dict(
            kind="write", domain="inbox", action_id="inbox.classify_all", scope="all"
        )
        history = "Previous conversation context:\n" + json.dumps(
            {
                "messages": [
                    {"role": "user", "content": "将 inbox 内容归类"},
                    {"role": "assistant", "content": "请选择具体资料，或明确整理全部收件箱。"},
                ]
            },
            ensure_ascii=False,
        )
        list(runtime.stream_session("全部", str(uuid4()), history, include_workspace_history=False))
        assert runtime.last_state["execution_result"]["verified"] is True
        assert not runtime._app_services.content.list("inbox")
        assert runtime.last_state["app_receipts"][-1]["action_id"] == "inbox.classify_all"
    finally:
        runtime.close()


@pytest.mark.parametrize(
    "query", ["不要将上一个归类", "解释怎么把上一个归类", "如果把上一个归类会怎样"]
)
def test_memory_does_not_turn_negative_or_explanatory_followup_into_write(tmp_path, query):
    model = SemanticModel(
        dict(kind="write", domain="inbox", action_id="inbox.classify_all", scope="all")
    )
    runtime = Runtime(model, data_dir=tmp_path, checkpoint_mode="off", trace_mode="off")
    try:
        history = "Previous conversation context:\n" + json.dumps(
            {
                "messages": [
                    {"role": "user", "content": "将 Inbox 全部归类"},
                ]
            },
            ensure_ascii=False,
        )
        list(runtime.stream_session(query, str(uuid4()), history, include_workspace_history=False))
        assert not runtime.last_state.get("app_receipts")
    finally:
        runtime.close()


def test_older_object_selection_and_clear_boundary(tmp_path):
    model = SemanticModel({})
    runtime = Runtime(model, data_dir=tmp_path, checkpoint_mode="off", trace_mode="off")
    store = AppStore(tmp_path)
    cid = store.create()["id"]
    service = ConversationService(store, ModelSettingsService(tmp_path / ".env"))
    ids = []
    try:
        for text in ["语义检索方案", "周末安排"]:
            model.parsed = dict(
                kind="write",
                domain="inbox",
                action_id="inbox.import_text",
                arguments={"text": text},
            )
            query = f"Inbox 保存「{text}」"
            list(
                runtime.stream_session(
                    query, cid, service.build_context(cid), include_workspace_history=False
                )
            )
            receipts = runtime.last_state["app_receipts"]
            ids.append(receipts[-1]["data"]["id"])
            store.append_message(cid, "user", query)
            store.append_message(cid, "assistant", "已保存", metadata={"app_receipts": receipts})
        model.parsed = dict(
            kind="write", domain="inbox", action_id="inbox.classify_selected", selector=ids[0]
        )
        list(
            runtime.stream_session(
                "将前面关于语义检索的那份归类",
                cid,
                service.build_context(cid),
                include_workspace_history=False,
            )
        )
        assert runtime._app_services.content.get(ids[0])["status"] == "knowledge"
        assert runtime._app_services.content.get(ids[1])["status"] == "inbox"
        store.clear_context(cid)
        model.parsed["selector"] = ids[1]
        list(
            runtime.stream_session(
                "将上一个归类", cid, service.build_context(cid), include_workspace_history=False
            )
        )
        assert runtime._app_services.content.get(ids[1])["status"] == "inbox"
        assert not runtime.last_state.get("app_receipts")
    finally:
        runtime.close()
