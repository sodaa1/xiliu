from langchain_core.messages import AIMessageChunk, HumanMessage
from langchain_core.outputs import ChatGenerationChunk
from langchain_openai import ChatOpenAI

from xiliu.config import Settings
from xiliu.providers import openai_compatible as provider


def test_official_openai_requests_and_streams_exposed_reasoning_summary(monkeypatch):
    events = []
    monkeypatch.setattr(provider, "get_stream_writer", lambda: events.append)
    monkeypatch.setattr(
        ChatOpenAI,
        "_stream",
        lambda *a, **k: iter(
            [
                ChatGenerationChunk(
                    message=AIMessageChunk(
                        content=[
                            {
                                "type": "reasoning",
                                "summary": [{"type": "summary_text", "text": "先检查数据。"}],
                            }
                        ]
                    )
                )
            ]
        ),
    )
    model = provider.create_chat_model(
        Settings.from_env(
            {"XILIU_PROVIDER": "openai", "XILIU_API_KEY": "fake", "XILIU_MODEL": "gpt-5.6-sol"}
        )
    )
    assert model.use_responses_api is True
    assert model.reasoning["summary"] == "auto"
    list(model._stream([HumanMessage(content="你好")]))
    assert events == [{"type": "reasoning", "stage": "model", "message": "先检查数据。"}]


def test_mimo_retains_reasoning_in_tool_history():
    model = provider.create_chat_model(
        Settings.from_env(
            {
                "XILIU_PROVIDER": "mimo",
                "XILIU_API_KEY": "fake",
                "XILIU_MODEL": "mimo-v2.6-pro",
                "XILIU_BASE_URL": "https://api.xiaomimimo.com/v1",
            }
        )
    )
    chunk = model._convert_chunk_to_generation_chunk(
        {
            "choices": [
                {
                    "delta": {"role": "assistant", "content": "", "reasoning_content": "分析原文"},
                    "finish_reason": None,
                }
            ]
        },
        AIMessageChunk,
        {},
    )
    assert chunk.message.additional_kwargs["reasoning_content"] == "分析原文"
    serialized = model._get_request_payload([HumanMessage(content="测试"), chunk.message])
    assert serialized["messages"][-1]["reasoning_content"] == "分析原文"


def test_custom_openai_compatible_connection_does_not_assume_vendor_parameters(monkeypatch):
    import json

    import httpx

    requests = []

    def respond(request):
        requests.append(json.loads(request.content))
        return httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            content=(
                'data: {"id":"test","object":"chat.completion.chunk","created":1,'
                '"model":"my-local-model","choices":[{"index":0,'
                '"delta":{"role":"assistant","content":"ok"},'
                '"finish_reason":"stop"}]}\n\ndata: [DONE]\n\n'
            ),
        )

    monkeypatch.setattr(
        provider,
        "DefaultHttpxClient",
        lambda **kwargs: httpx.Client(transport=httpx.MockTransport(respond)),
    )
    model = provider.create_chat_model(
        Settings.from_env(
            {
                "XILIU_PROVIDER": "custom",
                "XILIU_API_KEY": "fake",
                "XILIU_MODEL": "my-local-model",
                "XILIU_BASE_URL": "http://127.0.0.1:9999/v1",
            }
        )
    )
    light = provider.lightweight_model(model, routing=True)
    try:
        assert light.invoke([HumanMessage(content="测试")]).content == "ok"
    finally:
        model.root_client.close()
    assert requests[0]["model"] == "my-local-model" and "thinking" not in requests[0]
