import json

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from xiliu.cloud.app import create_cloud_app
from xiliu.cloud.budget import active_budget
from xiliu.cloud.config import CloudConfig
from xiliu.events import FinalEvent
from xiliu.execution.cancellation import TurnCancelled

ORIGIN = "https://cloud.example"


def test_trial_chat_uses_ephemeral_model_counts_once_and_replays(tmp_path):
    config = CloudConfig(
        data_dir=tmp_path,
        public_origin=ORIGIN,
        master_key=Fernet.generate_key().decode(),
        trial_api_key="operator-secret",
        trial_model="test-model",
        trial_base_url="https://model.example/v1",
    )
    calls = []

    class Runtime:
        def stream_session(self, **kwargs):
            active_budget.get().before_request()
            active_budget.get().started()
            yield FinalEvent(text="hello", session_id=kwargs["session_id"])

        def close(self):
            pass

    def factory(settings, **kwargs):
        calls.append(settings)
        return Runtime()

    with TestClient(create_cloud_app(config), base_url=ORIGIN) as client:
        session = client.post(
            "/api/auth/register",
            headers={"Origin": ORIGIN},
            json={
                "username": "alice",
                "password": "long-enough-password",
            },
        ).json()
        client.headers.update({"Origin": ORIGIN, "X-CSRF-Token": session["csrf_token"]})
        assert session["trial"] == {"enabled": True, "limit": 5, "remaining": 5}
        cid = client.post("/api/conversations").json()["id"]
        with client.app.state.workspaces.acquire(session["workspace"]["id"]) as state:
            state.chat.runtime_factory = factory
        body = {"text": "hello", "source": "trial", "request_id": "request-0001"}
        first = client.post(f"/api/conversations/{cid}/chat", json=body)
        events = [json.loads(line) for line in first.text.splitlines()]
        assert any(event.get("text") == "hello" for event in events), first.text
        assert "operator-secret" not in first.text
        assert client.get("/api/auth/session").json()["trial"]["remaining"] == 4
        assert client.post(f"/api/conversations/{cid}/chat", json=body).status_code == 200
        assert len(calls) == 1
        assert calls[0].api_key.get_secret_value() == "operator-secret"
        assert client.get("/api/settings/model").json()["api_key_set"] is False
        for number in range(2, 6):
            body["request_id"] = f"request-{number:04}"
            client.post(f"/api/conversations/{cid}/chat", json=body)
        body["request_id"] = "request-0006"
        exhausted = client.post(f"/api/conversations/{cid}/chat", json=body)
        assert "trial_exhausted" in exhausted.text
        assert len(calls) == 5
        saved = client.put(
            "/api/settings/model",
            json={
                "provider": "custom",
                "model": "own-model",
                "base_url": "https://own.example/v1",
                "api_key": "user-secret",
            },
        )
        assert saved.status_code == 200, saved.text
        own = client.post(
            f"/api/conversations/{cid}/chat",
            json={
                "text": "my api",
                "source": "own",
                "request_id": "own-request-1",
            },
        )
        assert "hello" in own.text
        assert calls[-1].api_key.get_secret_value() == "user-secret"
        assert client.get("/api/auth/session").json()["trial"]["remaining"] == 0


def test_unconfigured_trial_returns_unavailable_without_deduction(tmp_path):
    config = CloudConfig(
        data_dir=tmp_path, public_origin=ORIGIN, master_key=Fernet.generate_key().decode()
    )
    with TestClient(create_cloud_app(config), base_url=ORIGIN) as client:
        session = client.post(
            "/api/auth/register",
            headers={"Origin": ORIGIN},
            json={
                "username": "alice",
                "password": "long-enough-password",
            },
        ).json()
        client.headers.update({"Origin": ORIGIN, "X-CSRF-Token": session["csrf_token"]})
        cid = client.post("/api/conversations").json()["id"]
        response = client.post(
            f"/api/conversations/{cid}/chat",
            json={
                "text": "hello",
                "source": "trial",
                "request_id": "request-0001",
            },
        )
        assert "trial_unavailable" in response.text
        assert client.get("/api/auth/session").json()["trial"]["remaining"] == 5


@pytest.mark.parametrize("mode,remaining", [("connection", 5), ("timeout", 4), ("stop", 4)])
def test_connection_refund_but_started_timeout_and_stop_count(tmp_path, mode, remaining):
    config = CloudConfig(
        data_dir=tmp_path,
        public_origin=ORIGIN,
        master_key=Fernet.generate_key().decode(),
        trial_api_key="operator-secret",
        trial_model="test-model",
    )

    class Runtime:
        def stream_session(self, **kwargs):
            active_budget.get().before_request()
            if mode == "connection":
                raise ConnectionError("operator-secret")
            active_budget.get().started()
            if mode == "timeout":
                raise TimeoutError("operator-secret")
            raise TurnCancelled()
            yield  # Keep the same lazy generator interface as the real runtime.

        def close(self):
            pass

    with TestClient(create_cloud_app(config), base_url=ORIGIN) as client:
        session = client.post(
            "/api/auth/register",
            headers={"Origin": ORIGIN},
            json={
                "username": "alice",
                "password": "long-enough-password",
            },
        ).json()
        client.headers.update({"Origin": ORIGIN, "X-CSRF-Token": session["csrf_token"]})
        cid = client.post("/api/conversations").json()["id"]
        with client.app.state.workspaces.acquire(session["workspace"]["id"]) as state:
            state.chat.runtime_factory = lambda *args, **kwargs: Runtime()
        response = client.post(
            f"/api/conversations/{cid}/chat",
            json={
                "text": "hello",
                "source": "trial",
                "request_id": "request-0001",
            },
        )
        assert "operator-secret" not in response.text
        assert client.get("/api/auth/session").json()["trial"]["remaining"] == remaining
