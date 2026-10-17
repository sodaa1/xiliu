from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from xiliu.app.dispatch import AppDispatcher
from xiliu.cloud.app import create_cloud_app
from xiliu.cloud.config import CloudConfig
from xiliu.cloud.policy import CloudPolicyEngine
from xiliu.execution.gateway import RunContext

ORIGIN = "https://cloud.example"


def test_agent_background_and_http_share_durable_change_metadata(tmp_path):
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
        workspace = session["workspace"]["id"]
        with client.app.state.workspaces.acquire(workspace) as state:
            cid = state.store.create()["id"]
            context = RunContext(
                "agent-run",
                cid,
                state.data_dir,
                data_dir=state.data_dir,
                app_services=state.app_services,
                policy_engine=CloudPolicyEngine(),
            )
            result = AppDispatcher(state.app_services, context).execute(
                "tasks.create", {"title": "Agent task"}, request_id="agent-request"
            )
            assert result["ok"], result
            task = state.automations.create(
                {
                    "name": "daily",
                    "prompt": "test",
                    "hour": 1,
                    "minute": 0,
                    "timezone": "Asia/Shanghai",
                }
            )
            state.automations.runner.run_once = lambda *args, **kwargs: state.tasks.create(
                {"title": "Background task"}
            )
            client.app.state.cloud_jobs.execute(workspace, task["id"])
            assert len([e for e in state.changes.events() if e["entity_type"] == "tasks"]) == 2
            assert any(
                e["entity_type"] == "automations" for e in state.changes.events(domain="automation")
            )
        saved = client.put(
            "/api/settings/model",
            json={
                "provider": "custom",
                "model": "fake",
                "base_url": "https://model.example/v1",
                "api_key": "private-model-key",
            },
        )
        assert saved.status_code == 200
        with client.app.state.workspaces.acquire(workspace) as state:
            events = state.changes.events()
            assert any(e["entity_type"] == "model_settings" for e in events)
            assert "private-model-key" not in str(events)
    with TestClient(create_cloud_app(config), base_url=ORIGIN) as client:
        session = client.post(
            "/api/auth/login",
            headers={"Origin": ORIGIN},
            json={
                "username": "alice",
                "password": "long-enough-password",
            },
        ).json()
        assert session["workspace"]["id"] == workspace
        with client.app.state.workspaces.acquire(workspace) as state:
            assert state.changes.events() == events
