from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from xiliu.cloud.auth import create_auth_app
from xiliu.cloud.config import CloudConfig

ORIGIN = "https://cloud.example.test"
PASSWORD = "correct horse battery staple"


def config(tmp_path, **changes):
    return CloudConfig(
        data_dir=tmp_path,
        public_origin=ORIGIN,
        master_key=Fernet.generate_key().decode(),
        **changes,
    )


def test_auth_cookie_csrf_origin_and_no_secret_echo(tmp_path):
    app = create_auth_app(config(tmp_path))
    with TestClient(app, base_url=ORIGIN) as client:
        assert client.get("/api/auth/session").status_code == 401
        credentials = {"username": "alice", "password": PASSWORD}
        assert client.post("/api/auth/register", json=credentials).status_code == 403
        assert (
            client.post(
                "/api/auth/register", json=credentials, headers={"Origin": "https://evil.test"}
            ).status_code
            == 403
        )
        response = client.post("/api/auth/register", json=credentials, headers={"Origin": ORIGIN})
        assert response.status_code == 201
        cookie = response.headers["set-cookie"].lower()
        assert "httponly" in cookie and "secure" in cookie and "samesite=lax" in cookie
        session = client.get("/api/auth/session").json()
        assert session["user"]["username"] == "alice"
        assert session["workspace"]["id"]
        assert session["trial"] == {"enabled": False, "limit": 5, "remaining": 5}
        assert PASSWORD not in response.text and "password_hash" not in response.text
        assert client.post("/api/auth/logout", headers={"Origin": ORIGIN}).status_code == 403
        assert (
            client.post(
                "/api/auth/logout",
                headers={"Origin": ORIGIN, "X-CSRF-Token": session["csrf_token"]},
            ).status_code
            == 204
        )
        assert client.get("/api/auth/session").status_code == 401
        assert client.get("/api/cloud/bootstrap").json()["guest_url"] == "/demo/#/today"


def test_login_errors_limits_and_validation_never_echo_inputs(tmp_path):
    app = create_auth_app(config(tmp_path, login_limit=2))
    with TestClient(app, base_url=ORIGIN) as client:
        headers = {"Origin": ORIGIN}
        for _ in range(2):
            response = client.post(
                "/api/auth/login",
                json={"username": "missing", "password": PASSWORD},
                headers=headers,
            )
            assert response.status_code == 401 and PASSWORD not in response.text
        assert (
            client.post(
                "/api/auth/login",
                json={"username": "missing", "password": PASSWORD},
                headers=headers,
            ).status_code
            == 429
        )
        response = client.post(
            "/api/auth/register",
            json={"username": "alice", "password": PASSWORD, "unexpected": "secret-input"},
            headers=headers,
        )
        assert response.status_code == 422 and "secret-input" not in response.text


def test_host_is_checked_and_password_reset_invalidates_browser(tmp_path):
    app = create_auth_app(config(tmp_path))
    with TestClient(app, base_url=ORIGIN) as client:
        assert client.get("/api/cloud/bootstrap", headers={"Host": "evil.test"}).status_code == 400
        client.post(
            "/api/auth/register",
            json={"username": "alice", "password": PASSWORD},
            headers={"Origin": ORIGIN},
        )
        app.state.identity.reset_password("alice", "replacement strong password")
        assert client.get("/api/auth/session").status_code == 401
