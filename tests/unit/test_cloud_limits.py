from contextlib import ExitStack

import pytest

from xiliu.api.errors import WebError
from xiliu.cloud.limits import BodyLimit, RequestSlots


def test_slots_bound_per_account_and_release_on_failure():
    slots = RequestSlots()
    with ExitStack() as stack:
        for _ in range(8):
            stack.enter_context(slots.acquire("alice"))
        with pytest.raises(WebError), slots.acquire("alice"):
            pytest.fail("ninth request must not run")
        with slots.acquire("bob"):
            pass
    assert not slots.counts


@pytest.mark.asyncio
async def test_streamed_body_cannot_bypass_limit_without_content_length(monkeypatch):
    import xiliu.cloud.limits as limits

    monkeypatch.setattr(limits, "MAX_BODY", 5)
    sent = []
    chunks = iter([b"abc", b"def"])

    async def receive():
        return {"type": "http.request", "body": next(chunks), "more_body": True}

    async def send(message):
        sent.append(message)

    async def app(scope, receive, send):
        pytest.fail("oversized body reached the application")

    await BodyLimit(app)({"type": "http", "method": "POST", "path": "/api/models"}, receive, send)
    assert sent[0]["status"] == 413
