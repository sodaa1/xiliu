import base64

from fastapi.testclient import TestClient

from xiliu.api.app import create_app
from xiliu.automation.store import AutomationStore


def test_content_capture_move_search_download_and_task_today(tmp_path):
    app = create_app(data_dir=tmp_path / "data", env_file=tmp_path / ".env")
    with TestClient(app, base_url="http://127.0.0.1") as client:
        note = client.post(
            "/api/content",
            json={
                "type": "note",
                "title": "知识笔记",
                "content": "息流中文检索示例",
                "tags": ["学习"],
            },
        ).json()
        assert note["status"] == "inbox"
        response = client.patch(f"/api/content/{note['id']}", json={"status": "knowledge"})
        assert response.status_code == 200
        found = client.get("/api/content", params={"status": "knowledge", "q": "中文"}).json()
        assert any(item["id"] == note["id"] for item in found)
        attachment = client.post(
            "/api/content",
            json={
                "type": "file",
                "title": "Original",
                "filename": "reference.txt",
                "data_base64": base64.b64encode(b"Original bytes").decode(),
            },
        ).json()
        original = client.get(f"/api/content/{attachment['id']}/original")
        assert original.content == b"Original bytes"
        task = client.post("/api/tasks", json={"title": "Read saved note"}).json()
        assert client.patch(f"/api/tasks/{task['id']}", json={"completed": True}).status_code == 200
        today = client.get("/api/today").json()
        assert today["inbox_count"] == 1
        assert today["tasks"][0]["completed"] is True
        assert client.delete(f"/api/tasks/{task['id']}").status_code == 204


def test_automation_endpoints_use_existing_store_and_validation(tmp_path):
    data = tmp_path / "data"
    app = create_app(data_dir=data, env_file=tmp_path / ".env")
    with TestClient(app, base_url="http://127.0.0.1") as client:
        definition = {
            "name": "Daily brief",
            "prompt": "Prepare a brief",
            "hour": 2,
            "minute": 17,
            "timezone": "Asia/Shanghai",
        }
        response = client.post("/api/automations", json=definition)
        assert response.status_code == 201
        task = response.json()
        assert AutomationStore(data).get(task["id"]) is not None
        assert (
            client.patch(f"/api/automations/{task['id']}", json={"enabled": False}).status_code
            == 200
        )
        persisted = AutomationStore(data).get(task["id"])
        assert persisted is not None and persisted.enabled is False
        assert client.get(f"/api/automations/{task['id']}/runs").json() == []
        assert client.post("/api/automations", json={**definition, "hour": 25}).status_code == 422
        assert client.delete(f"/api/automations/{task['id']}").status_code == 204


def test_web_scheduler_does_not_take_existing_owner_lease(tmp_path):
    data = tmp_path / "data"
    automations = AutomationStore(data)
    assert automations.acquire_owner("external-owner")
    app = create_app(data_dir=data, env_file=tmp_path / ".env")
    with TestClient(app, base_url="http://127.0.0.1") as client:
        assert client.get("/api/health").status_code == 200
        assert client.get("/api/settings/data").json()["scheduler_active"] is False
        assert not automations.acquire_owner("competing-owner")
