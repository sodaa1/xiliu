import re
import tempfile
from pathlib import Path
from urllib.parse import urljoin

from fastapi.testclient import TestClient

from xiliu.api.app import create_app

with tempfile.TemporaryDirectory(prefix="xiliu-intro-") as folder:
    state = Path(folder)
    with TestClient(
        create_app(data_dir=state / "data", env_file=state / ".env", static_dir=Path(__file__).resolve().parents[4] / "web/dist"),
        base_url="http://127.0.0.1",
    ) as client:
        for url in ("/intro", "/intro/", "/intro/index.html"):
            response = client.get(url)
            assert response.status_code == 200
            assert "信息有归处" in response.text
            assert response.headers["cache-control"] == "no-cache"
        for asset in re.findall(r'(?:src|href)="([^\"]+)"', response.text):
            asset = urljoin("/intro/", asset)
            result = client.get(asset)
            assert result.status_code == 200, asset
            assert "text/html" not in result.headers.get("content-type", ""), asset
        assert "信息有归处" not in client.get("/today").text
        assert client.get("/api/health").json() == {"status": "ok"}
        assert client.get("/intro/not-found.js").status_code == 404
print("Built intro directory routes, all JS/CSS/icon assets, SPA and health: passed")
