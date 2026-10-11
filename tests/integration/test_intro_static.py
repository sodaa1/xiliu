from fastapi.testclient import TestClient

from xiliu.api.app import create_app


def test_intro_directory_serves_its_own_index_and_preserves_spa(tmp_path):
    dist = tmp_path / "dist"
    (dist / "intro").mkdir(parents=True)
    (dist / "index.html").write_text("<html>workspace</html>", encoding="utf-8")
    (dist / "intro" / "index.html").write_text("<html>intro landing</html>", encoding="utf-8")
    (dist / "intro" / "favicon.svg").write_text("<svg></svg>", encoding="utf-8")
    with TestClient(
        create_app(data_dir=tmp_path / "data", env_file=tmp_path / ".env", static_dir=dist),
        base_url="http://127.0.0.1",
    ) as client:
        for path in ("/intro", "/intro/", "/intro/index.html"):
            response = client.get(path)
            assert response.status_code == 200
            assert "intro landing" in response.text
            assert response.headers["cache-control"] == "no-cache"
        assert "workspace" in client.get("/today").text
        assert client.get("/intro/favicon.svg").headers["content-type"].startswith("image/svg+xml")
        assert client.get("/intro/missing.js").status_code == 404
        assert client.get("/api/missing").status_code == 404


def test_directory_index_symlink_cannot_escape_static_root(tmp_path):
    dist = tmp_path / "dist"
    (dist / "intro").mkdir(parents=True)
    (dist / "index.html").write_text("<html>workspace</html>", encoding="utf-8")
    outside = tmp_path / "private.html"
    outside.write_text("private sentinel", encoding="utf-8")
    try:
        (dist / "intro" / "index.html").symlink_to(outside)
    except OSError:
        import pytest

        pytest.skip("Windows symlink privilege is unavailable")
    with TestClient(
        create_app(data_dir=tmp_path / "data", env_file=tmp_path / ".env", static_dir=dist),
        base_url="http://127.0.0.1",
    ) as client:
        response = client.get("/intro/")
        assert response.status_code == 404
        assert "private sentinel" not in response.text
