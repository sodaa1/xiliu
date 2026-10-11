from fastapi.testclient import TestClient

from xiliu.api.app import create_app


def test_offline_import_folder_edit_and_search_api(tmp_path):
    app = create_app(data_dir=tmp_path / "data", env_file=tmp_path / ".env")

    def no_network(_item):
        raise AssertionError("No external request is allowed")

    app.state.inbox.metadata = no_network
    with TestClient(app, base_url="http://127.0.0.1") as client:
        response = client.post("/api/knowledge/folders", json={"name": "Code", "tags": ["Python"]})
        assert response.status_code == 201
        folder = response.json()
        response = client.post(
            "/api/inbox/import", json={"text": "Python source reference", "use_ai": False}
        )
        assert response.status_code == 201
        item = response.json()
        assert item["processing_status"] == "pending"
        app.state.inbox.shutdown()
        saved = client.get("/api/content/" + item["id"]).json()
        assert saved["processing_status"] == "ready" and saved["folder_id"] == folder["id"]
        assert client.get("/api/inbox").json() == []
        assert (
            client.get(f"/api/knowledge/folders/{folder['id']}/items").json()[0]["id"] == item["id"]
        )
        result = client.get(
            "/api/knowledge/search", params={"q": "Python", "mode": "hybrid"}
        ).json()
        assert result["items"][0]["document_id"] == item["id"]
        assert (
            client.get(
                "/api/knowledge/search", params={"q": "Python", "mode": "invalid"}
            ).status_code
            == 422
        )
        response = client.patch(
            "/api/content/" + item["id"], json={"tags": ["Unmatched"], "folder_id": folder["id"]}
        )
        assert response.json()["folder_id"] == folder["id"]
        assert client.delete(f"/api/knowledge/folders/{folder['id']}").status_code == 204
        saved = client.get("/api/content/" + item["id"]).json()
        assert saved["folder_id"] is None and saved["status"] == "knowledge"
