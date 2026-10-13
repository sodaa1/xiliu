from fastapi.testclient import TestClient

from xiliu.api.app import create_app


def test_api_boots_without_credentials_and_masks_validation(tmp_path):
    app = create_app(data_dir=tmp_path / "data", env_file=tmp_path / ".env")
    with TestClient(app, base_url="http://127.0.0.1") as client:
        assert client.get("/api/health").json() == {"status": "ok"}
        assert client.get("/api/settings/model").status_code == 200
        catalog = client.get("/api/models/catalog").json()
        assert "gpt-5.6-terra" in catalog["openai"]["models"]
        assert "deepseek-v4-flash" in catalog["deepseek"]["models"]
        assert "deepseek-flash" not in catalog["deepseek"]["models"]
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
    with TestClient(
        create_app(data_dir=tmp_path / "data", env_file=env), base_url="http://127.0.0.1"
    ) as client:
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


def test_spa_deep_links_and_unknown_api_do_not_return_html(tmp_path):
    from click import unstyle
    from typer.testing import CliRunner

    from xiliu.cli import app as cli_app

    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<html>xiliu preview</html>")
    with TestClient(
        create_app(data_dir=tmp_path / "data", env_file=tmp_path / ".env", static_dir=dist),
        base_url="http://127.0.0.1",
    ) as client:
        assert client.get("/assistant").status_code == 200
        assert "xiliu preview" in client.get("/settings").text
        assert client.get("/api/missing").status_code == 404
        assert client.get("/missing.js").status_code == 404
    result = CliRunner().invoke(cli_app, ["web", "--help"], color=True)
    assert result.exit_code == 0
    assert "--open" in unstyle(result.stdout)


def test_foreign_host_cannot_read_private_local_api(tmp_path):
    app = create_app(data_dir=tmp_path / "data", env_file=tmp_path / ".env")
    with TestClient(app, base_url="http://127.0.0.1") as client:
        client.post("/api/conversations")
        response = client.get(
            "/api/conversations",
            headers={"host": "attacker.example:8765", "origin": "http://attacker.example:8765"},
        )
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "invalid_host"
        assert client.get("/api/health", headers={"host": "127.0.0.1:8765"}).status_code == 200
