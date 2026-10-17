import httpx
import pytest
from openai import AuthenticationError

from xiliu.api.errors import WebError
from xiliu.cloud.budget import CloudCallBudget, active_budget
from xiliu.cloud.model_settings import CloudRuntimeSettings
from xiliu.providers.openai_compatible import create_chat_model


@pytest.mark.parametrize("status,started", [(200, True), (401, False)])
def test_actual_provider_marks_generation_only_after_received_chunk(monkeypatch, status, started):
    dispatched, generations = [], []

    def response(request):
        data = (
            'data: {"id":"test","object":"chat.completion.chunk","created":1,'
            '"model":"fake","choices":[{"index":0,"delta":{"content":"hi"},'
            '"finish_reason":"stop"}]}\n\ndata: [DONE]\n\n'
        )
        return httpx.Response(
            status,
            text=data if status == 200 else "{}",
            headers={"content-type": "text/event-stream"},
        )

    sync = httpx.Client(transport=httpx.MockTransport(response))
    asynchronous = httpx.AsyncClient(transport=httpx.MockTransport(response))
    monkeypatch.setattr("xiliu.cloud.network.cloud_http_clients", lambda: (sync, asynchronous))
    model = create_chat_model(
        CloudRuntimeSettings(
            api_key="fake",
            model="fake",
            base_url="https://model.example/v1",
        )
    )
    budget = CloudCallBudget(
        on_dispatch=lambda: dispatched.append(True),
        on_start=lambda: generations.append(True),
        maximum_calls=1,
    )
    token = active_budget.set(budget)
    try:
        if status == 200:
            assert model.invoke("hello").content == "hi"
        else:
            with pytest.raises(AuthenticationError):
                model.invoke("hello")
        assert bool(generations) is started
        assert len(dispatched) == 1
        with pytest.raises(WebError):
            model.invoke("another")
        assert len(dispatched) == 1
    finally:
        active_budget.reset(token)
        sync.close()
