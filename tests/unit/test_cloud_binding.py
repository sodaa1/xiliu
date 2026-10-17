import asyncio
from contextlib import contextmanager
from threading import Event
from types import SimpleNamespace

import pytest

from xiliu.cloud.app import WorkspaceBinding


@pytest.mark.asyncio
async def test_cancel_during_workspace_initialization_releases_lease():
    entered, proceed = Event(), Event()
    active = []

    class Registry:
        @contextmanager
        def acquire(self, identifier):
            entered.set()
            proceed.wait(2)
            active.append(identifier)
            try:
                yield object()
            finally:
                active.remove(identifier)

    async def app(scope, receive, send):
        pytest.fail("cancelled request must not dispatch")

    middleware = WorkspaceBinding(
        app,
        registry=Registry(),
        identity=SimpleNamespace(session=lambda token: {"workspace_id": "alice"}),
    )
    task = asyncio.create_task(
        middleware(
            {
                "type": "http",
                "method": "GET",
                "path": "/api/content",
                "headers": [],
            },
            None,
            None,
        )
    )
    await asyncio.to_thread(entered.wait, 2)
    task.cancel()
    proceed.set()
    with pytest.raises(asyncio.CancelledError):
        await task
    await asyncio.sleep(0.05)
    assert active == []
    assert not middleware.slots.counts
