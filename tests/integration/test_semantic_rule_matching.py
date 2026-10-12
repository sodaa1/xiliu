import json
from uuid import uuid4

import pytest
from langchain_core.messages import AIMessage

from xiliu.events import FinalEvent
from xiliu.runtime import Runtime


class SemanticModel:
    def __init__(self, parsed):
        self.parsed = parsed
        self.rule_reads = []

    def with_structured_output(self, schema, **kwargs):
        outer = self

        class Parser:
            def invoke(self, messages):
                outer.rule_reads.append(messages)
                return schema.model_validate(outer.parsed)

        return Parser()

    def invoke(self, messages):
        return AIMessage(
            content=json.dumps(
                {
                    "intent": "task",
                    "domain": "inbox",
                    "action": "app:match",
                    "complexity": "simple",
                    "confidence": 1,
                }
            )
        )


PHRASES = [
    "把文字「构建个人知识库的灵感」存入 Inbox。",
    "请在收件箱记下「构建个人知识库的灵感」。",
    "Inbox 帮我收着这段文字：「构建个人知识库的灵感」。",
    "把「构建个人知识库的灵感」留在收件箱。",
    "收件箱里帮我记一笔：「构建个人知识库的灵感」。",
    "将「构建个人知识库的灵感」保存到 Inbox。",
    "往 Inbox 里放一段文字：「构建个人知识库的灵感」。",
    "把「构建个人知识库的灵感」收录进收件箱。",
]


@pytest.mark.parametrize("query", PHRASES)
def test_direct_action_reads_complete_rules_once_and_persists_original_text(tmp_path, query):
    model = SemanticModel(
        dict(
            kind="write",
            domain="inbox",
            action_id="inbox.import_text",
            arguments={"text": "构建个人知识库的灵感"},
        )
    )
    runtime = Runtime(model, data_dir=tmp_path, checkpoint_mode="off", trace_mode="off")
    try:
        events = list(runtime.stream_session(query, str(uuid4()), ""))
        assert isinstance(events[-1], FinalEvent)
        assert runtime.last_state["execution_result"]["verified"] is True
        items = runtime._app_services.content.list("inbox")
        assert len(items) == 1 and items[0]["content"] == "构建个人知识库的灵感"
        assert len(model.rule_reads) == 1
        prompt = "\n".join(str(m.content) for m in model.rule_reads[0])
        assert query in prompt
        assert "schema" in prompt and "inbox.import_text" in prompt and "语义匹配" in prompt
        assert runtime.last_node_path.count("tool_execute") == 1
    finally:
        runtime.close()


def test_model_cannot_use_missing_action_or_invent_user_content(tmp_path):
    for parsed in (
        dict(kind="write", domain="inbox", action_id="unknown.tool", arguments={"text": "原文"}),
        dict(
            kind="write",
            domain="inbox",
            action_id="inbox.import_text",
            arguments={"text": "模型虚构的内容"},
        ),
    ):
        runtime = Runtime(
            SemanticModel(parsed), data_dir=tmp_path, checkpoint_mode="off", trace_mode="off"
        )
        try:
            list(runtime.stream_session("Inbox 记下「原文」", str(uuid4()), ""))
            assert runtime._app_services.content.list("inbox") == []
            assert runtime.last_state["execution_result"]["verified"] is False
        finally:
            runtime.close()


@pytest.mark.parametrize(
    "query",
    [
        "不要把「原文」保存到 Inbox",
        "解释怎么保存「原文」到 Inbox",
        "如果我把「原文」存到收件箱会怎样",
    ],
)
def test_negative_and_explanatory_requests_never_write(tmp_path, query):
    runtime = Runtime(
        SemanticModel(
            dict(
                kind="write",
                domain="inbox",
                action_id="inbox.import_text",
                arguments={"text": "原文"},
            )
        ),
        data_dir=tmp_path,
        checkpoint_mode="off",
        trace_mode="off",
    )
    try:
        list(runtime.stream_session(query, str(uuid4()), ""))
        assert runtime._app_services.content.list("inbox") == []
    finally:
        runtime.close()
