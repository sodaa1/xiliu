from typing import Any, cast

from langchain_core.messages import AIMessage, AIMessageChunk
from pydantic import SecretStr

from xiliu.config import Settings
from xiliu.graph.workflow import build_entry_workflow
from xiliu.providers.openai_compatible import create_chat_model


def test_chat_prompt_contains_selected_model_and_streams_progress():
    seen = []

    class Model:
        def invoke(self, messages):
            seen.append(messages[0].content)
            if len(seen) == 1:
                return AIMessage(content='{"route":"chat","reason":"identity","confidence":1}')
            return AIMessage(content="I am deepseek-v4-pro")

    graph = cast(Any, build_entry_workflow(Model(), model_name="deepseek-v4-pro"))
    events = list(graph.stream({"task": "你是哪个模型"}, stream_mode=["custom", "updates"]))
    assert "deepseek-v4-pro" in seen[-1]
    assert any(mode == "custom" and event["stage"] == "chat" for mode, event in events)


def test_deepseek_stream_retains_reasoning_and_light_requests_use_lower_effort():
    model = create_chat_model(
        Settings.from_env(
            {
                "XILIU_API_KEY": "fake",
                "XILIU_MODEL": "deepseek-v4-flash",
                "XILIU_PROVIDER": "deepseek",
                "XILIU_BASE_URL": "https://api.deepseek.com",
            }
        )
    )
    chunk = model._convert_chunk_to_generation_chunk(
        {
            "choices": [
                {
                    "delta": {"role": "assistant", "content": "", "reasoning_content": "Thought"},
                    "finish_reason": None,
                }
            ]
        },
        AIMessageChunk,
        {},
    )
    assert chunk is not None
    assert chunk.message.additional_kwargs["reasoning_content"] == "Thought"
    from xiliu.providers.openai_compatible import lightweight_model

    assert lightweight_model(model, routing=True).kwargs["extra_body"] == {
        "thinking": {"type": "disabled"},
    }
    assert lightweight_model(model).kwargs["reasoning_effort"] == "low"


def test_deepseek_runtime_streams_real_sse_reasoning_and_model_identity(tmp_path):
    import json
    from uuid import uuid4

    import httpx

    from xiliu.events import FinalEvent, ProgressEvent
    from xiliu.providers.openai_compatible import DeepSeekChatOpenAI
    from xiliu.runtime import Runtime

    requests = []

    def respond(request):
        body = json.loads(request.content)
        requests.append(body)
        if len(requests) == 1:
            delta = {"content": '{"route":"chat","reason":"identity","confidence":1}'}
            parts = [delta]
        else:
            parts = [
                {"reasoning_content": "Identify the selected model."},
                {"content": "The model is deepseek-v4-flash."},
            ]
        chunks = [
            {
                "id": "test",
                "object": "chat.completion.chunk",
                "choices": [
                    {"index": 0, "delta": {"role": "assistant", **part}, "finish_reason": None}
                ],
            }
            for part in parts
        ]
        return httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            content=(
                "".join("data: " + json.dumps(chunk) + "\n\n" for chunk in chunks)
                + "data: [DONE]\n\n"
            ),
        )

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        model = DeepSeekChatOpenAI(
            api_key=SecretStr("fake"),
            model="deepseek-v4-flash",
            streaming=True,
            http_client=client,
            base_url="https://example.test/v1",
        )
        runtime = Runtime(model, model_name="deepseek-v4-flash", data_dir=tmp_path)
        try:
            events = list(runtime.stream_session("Which model are you?", str(uuid4()), ""))
        finally:
            runtime.close()
    assert any(
        isinstance(event, ProgressEvent)
        and event.event_type == "reasoning"
        and event.message == "Identify the selected model."
        for event in events
    )
    assert isinstance(events[-1], FinalEvent)
    assert events[-1].text == "The model is deepseek-v4-flash."
    assert requests[0]["thinking"] == {"type": "disabled"}
    assert requests[1]["reasoning_effort"] == "low"
    assert "deepseek-v4-flash" in requests[1]["messages"][0]["content"]


def test_cli_chat_progress_does_not_mark_history_as_workflow(tmp_path, monkeypatch):
    from xiliu.core.agent import stream_session_events
    from xiliu.core.session import load_or_create_session
    from xiliu.runtime import Runtime

    class Model:
        def invoke(self, messages):
            if "intent router" in messages[0].content:
                return AIMessage(content='{"route":"chat","reason":"greeting","confidence":1}')
            return AIMessage(content="Hello")

    monkeypatch.setattr("xiliu.config.load_settings", lambda: None)
    monkeypatch.setattr(
        "xiliu.runtime.create_runtime", lambda *args, **kwargs: Runtime(Model(), data_dir=tmp_path)
    )
    list(stream_session_events("Hello", session_workspace=tmp_path))
    session = load_or_create_session(tmp_path)
    assert session["recent_turns"][-1]["route"] == "chat"
