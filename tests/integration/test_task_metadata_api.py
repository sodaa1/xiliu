from fastapi.testclient import TestClient

from xiliu.api.app import create_app


def test_task_metadata_api_preserves_patch_omissions_and_status_only_creation(tmp_path):
    app = create_app(data_dir=tmp_path / "data", env_file=tmp_path / ".env")
    with TestClient(app, base_url="http://127.0.0.1") as client:
        response = client.post(
            "/api/tasks",
            json={
                "title": "Finished",
                "status": "completed",
                "category": "工作",
                "description": "Read chapter",
                "priority": "urgent",
                "tags": ["study"],
                "starts_at": "2026-10-18T09:00:00",
                "due_at": "2026-10-18T10:00:00",
                "reminder_minutes": 5,
            },
        )
        assert response.status_code == 201
        task = response.json()
        assert task["status"] == "completed" and task["completed"] is True
        assert task["completed_at"] is not None
        response = client.patch(f"/api/tasks/{task['id']}", json={"title": "Renamed"})
        assert response.status_code == 200
        assert response.json()["description"] == "Read chapter"
        assert response.json()["completed_at"] == task["completed_at"]
        for invalid in (
            {"status": "unknown"},
            {"priority": "unknown"},
            {"status": "completed", "completed": False},
            {"starts_at": "2026-10-20"},
            {"tags": [1]},
            {"description": None},
            {"reminder_minutes": True},
        ):
            assert client.patch(f"/api/tasks/{task['id']}", json=invalid).status_code in (400, 422)
        restored = client.patch(f"/api/tasks/{task['id']}", json={"completed": False}).json()
        assert restored["status"] == "not_started" and restored["completed_at"] is None
