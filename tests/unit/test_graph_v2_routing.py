import pytest
from langchain_core.messages import AIMessage

from xiliu.routing import recognize_intent, select_execution


class NoModel:
    def invoke(self, messages):
        raise AssertionError("Deterministic intent must not invoke a model")


@pytest.mark.parametrize(
    "task,want",
    [
        ("/clear", "control"),
        ("/compress", "control"),
        ("/skill 创建知识整理流程", "planner"),
        ("/mcp 查询可用能力", "planner"),
        ("解释什么是RAG", "chat_responder"),
        ("创建待办“提交论文”", "app_executor"),
        ("帮我移动桌面的论文文件到Research", "fast_react"),
        ("分析知识库论文并生成报告", "planner"),
        ("删除它", "clarification"),
        ("删除所有数据", "clarification"),
        ("查询今天AI新闻", "fast_react"),
        ("只使用本地知识库回答", "clarification"),
    ],
)
def test_rules_choose_safe_path_without_model(task, want):
    intent = recognize_intent(task, model=NoModel())
    assert select_execution(intent) == want
    assert set(intent) == {
        "intent",
        "domain",
        "action",
        "complexity",
        "source",
        "preferred_capability",
        "confidence",
    }


def test_capability_command_preserves_preference_and_does_not_become_app():
    intent = recognize_intent("/skill probe 创建待办“提交论文”", model=NoModel())
    assert intent["preferred_capability"] == "skill:probe"
    assert select_execution(intent) == "planner"


def test_bad_classifier_output_cannot_authorize_action():
    class Model:
        def invoke(self, messages):
            return AIMessage(content='{"action":"tasks.delete","confidence":2}')

    intent = recognize_intent("some unspecified thing", model=Model())
    assert select_execution(intent) == "clarification"


def test_embedding_is_consulted_before_llm():
    intent = recognize_intent(
        "unrecognized synonym",
        model=NoModel(),
        embedding_matcher=lambda task: {
            "intent": "task",
            "domain": "workspace",
            "action": "",
            "complexity": "bounded",
            "source": "embedding",
            "preferred_capability": "",
            "confidence": 0.92,
        },
    )
    assert select_execution(intent) == "fast_react"
    assert intent["source"] == "embedding"


@pytest.mark.parametrize("action", ["web.search", "search", "查询热点新闻"])
def test_non_app_action_does_not_route_to_app_executor(action):
    import json

    class Model:
        def invoke(self, messages):
            return AIMessage(
                content=json.dumps(
                    {
                        "intent": "task",
                        "domain": "network",
                        "action": action,
                        "complexity": "simple",
                        "preferred_capability": "",
                        "confidence": 0.9,
                    }
                )
            )

    structured = recognize_intent("昨天openai有什么热点新闻吗", model=Model())
    assert select_execution(structured) == "fast_react"


def test_valid_low_confidence_request_reaches_tool_capable_model():
    class Model:
        def invoke(self, messages):
            return AIMessage(
                content='{"intent":"task","domain":"network","action":"",'
                '"complexity":"simple","confidence":0.4}'
            )

    assert (
        select_execution(recognize_intent("昨天openai有什么热点新闻吗", model=Model()))
        == "fast_react"
    )
