import json

from fastapi.testclient import TestClient

from xiliu.api.app import create_app


def test_app_http_is_same_service_with_human_confirmation_and_session_binding(tmp_path):
    application = create_app(data_dir=tmp_path, env_file=tmp_path / ".env")
    client = TestClient(application, base_url="http://127.0.0.1")
    first = client.post("/api/conversations").json()["id"]
    other = client.post("/api/conversations").json()["id"]
    payload = {
        "session_id": first,
        "operation": "execute",
        "action_id": "tasks.create",
        "arguments": {"title": "审批保留"},
        "request_id": "create",
    }
    receipt = client.post("/api/app", json=payload).json()
    assert receipt["verification"]["passed"]
    identifier = receipt["records"][0]["id"]
    pending = client.post(
        "/api/app",
        json={
            **payload,
            "request_id": "delete",
            "action_id": "tasks.delete",
            "arguments": {"task_id": identifier},
        },
    ).json()
    token = pending["confirmation_id"]
    denied = client.post("/api/app/confirm", json={"session_id": other, "confirmation_id": token})
    assert denied.status_code == 403 and application.state.tasks.list()
    completed = client.post(
        "/api/app/confirm", json={"session_id": first, "confirmation_id": token}
    ).json()
    assert completed["ok"] and not application.state.tasks.list()
    assert (
        client.post(
            "/api/app/confirm", json={"session_id": first, "confirmation_id": token}
        ).status_code
        == 403
    )
    assert application.state.store.messages(first)[-1]["role"] == "assistant"


def test_app_http_rejects_credentials_unknown_action_and_cross_origin(tmp_path):
    application = create_app(data_dir=tmp_path, env_file=tmp_path / ".env")
    client = TestClient(application, base_url="http://127.0.0.1")
    cid = client.post("/api/conversations").json()["id"]
    body = {
        "session_id": cid,
        "operation": "execute",
        "action_id": "settings.model.update",
        "arguments": {"api_key": "private-value"},
    }
    result = client.post("/api/app", json=body)
    assert "private-value" not in json.dumps(result.json())
    assert result.json()["error"] == "capability_unavailable"
    assert (
        client.post(
            "/api/app", json=body, headers={"Origin": "https://outside.invalid"}
        ).status_code
        == 403
    )
