from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from xiliu.cloud.app import create_cloud_app
from xiliu.cloud.config import CloudConfig
from xiliu.cloud.limits import check_storage

ORIGIN = "https://cloud.example"


def test_cloud_limits_and_extensions_leave_existing_data_intact(tmp_path):
    config = CloudConfig(
        data_dir=tmp_path, public_origin=ORIGIN, master_key=Fernet.generate_key().decode()
    )
    with TestClient(create_cloud_app(config), base_url=ORIGIN) as client:
        response = client.post(
            "/api/auth/register",
            headers={"Origin": ORIGIN},
            json={
                "username": "alice",
                "password": "long-enough-password",
            },
        )
        session = response.json()
        client.headers.update({"Origin": ORIGIN, "X-CSRF-Token": session["csrf_token"]})
        assert client.get("/api/capabilities/mcp").json() == []
        assert client.get("/api/capabilities/skills").json() == []
        assert client.put("/api/appearance/models/live2d", json={}).status_code == 403
        oversized = client.put("/api/models", content=b"x" * (1024 * 1024 + 1))
        assert oversized.status_code == 413
        assert oversized.json()["error"]["code"] == "request_too_large"
        payload = {"type": "note", "status": "inbox", "title": "preserved", "content": "hi"}
        original = client.post("/api/content", json=payload)
        assert original.status_code == 201
        with client.app.state.workspaces.acquire(session["workspace"]["id"]) as state:
            state.content.storage_guard = lambda **kwargs: check_storage(
                state.data_dir, limit=1, **kwargs
            )
        failed = client.post("/api/content", json={**payload, "title": "too much"})
        assert failed.status_code == 413
        notes = client.get("/api/content").json()
        assert [item["id"] for item in notes] == [original.json()["id"]]
        assert client.delete("/api/content/" + original.json()["id"]).status_code == 204


def test_cloud_runtime_forces_policy_for_chat_and_background(tmp_path, monkeypatch):
    import xiliu.runtime as runtime_module
    from xiliu.cloud.model_settings import CloudRuntimeSettings

    monkeypatch.setattr(runtime_module, "create_chat_model", lambda settings: object())
    (tmp_path / "policy.json").write_text("invalid user policy")
    (tmp_path / "hooks.json").write_text("invalid user hooks")
    settings = CloudRuntimeSettings(api_key="test", model="test", data_dir=tmp_path)
    for profile in ("interactive", "background"):
        runtime = runtime_module.create_runtime(settings, policy_profile=profile)
        try:
            assert runtime._policy_profile == "cloud"
            assert (
                runtime._policy_engine.evaluate(
                    actor="agent",
                    source="builtin",
                    capability_id="builtin:command",
                    permission="process.execute.safe",
                    arguments={},
                    profile="interactive",
                ).effect
                == "deny"
            )
            assert runtime._capabilities.skill_registry is None
            assert runtime._capabilities.mcp_manager is None
            assert runtime._hook_engine.hooks == []
        finally:
            runtime.close()
