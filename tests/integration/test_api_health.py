from fastapi.testclient import TestClient

from xiliu.api.app import create_app


def test_api_boots_without_credentials_and_masks_validation(tmp_path):
    app = create_app(data_dir=tmp_path / "data", env_file=tmp_path / ".env")
    with TestClient(app) as client:
        assert client.get("/api/health").json() == {"status": "ok"}
        assert client.get("/api/settings/model").status_code == 200
        catalog = client.get("/api/models/catalog").json()
        assert "gpt-5.6-terra" in catalog["openai"]["models"]
        assert "deepseek-flash" in catalog["deepseek"]["models"]
        response = client.put(
            "/api/settings/model",
            json={
                "provider": "openai",
                "model": "gpt-5.6-terra",
                "base_url": "file:///secret",
                "api_key": "never-echo-this",
            },
        )
        assert response.status_code == 422
        assert "never-echo-this" not in response.text
        assert response.json()["error"]["code"] == "invalid_request"


def test_settings_routes_keep_existing_key(tmp_path):
    env = tmp_path / ".env"
    env.write_text("XILIU_API_KEY=never-echo-this\nXILIU_MODEL=gpt-5.6-terra\n", encoding="utf-8")
    with TestClient(create_app(data_dir=tmp_path / "data", env_file=env)) as client:
        response = client.put(
            "/api/settings/model",
            json={
                "provider": "openai",
                "model": "gpt-5.6-sol",
                "base_url": "https://api.openai.com/v1",
                "api_key": "",
            },
        )
        assert response.status_code == 200
        assert response.json()["api_key_set"] is True
        assert "never-echo-this" not in response.text
