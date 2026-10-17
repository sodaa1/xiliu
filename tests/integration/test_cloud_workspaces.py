from concurrent.futures import ThreadPoolExecutor

from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from xiliu.cloud.app import create_cloud_app
from xiliu.cloud.config import CloudConfig

ORIGIN = "https://cloud.example.test"
PASSWORD = "correct horse battery staple"


def test_streaming_owner_thread_holds_an_independent_workspace_lease(tmp_path):
    cfg = CloudConfig(
        data_dir=tmp_path, public_origin=ORIGIN, master_key=Fernet.generate_key().decode()
    )
    app = create_cloud_app(cfg)
    observed = []
    with TestClient(app, base_url=ORIGIN) as client:
        session = register(client, "alice")
        workspace = session["workspace"]["id"]
        cid = client.post("/api/conversations").json()["id"]
        with app.state.workspaces.acquire(workspace) as state:

            def stream(*_args, **_kwargs):
                observed.append(app.state.workspaces.entries[workspace].references)
                yield {"type": "final", "text": "isolated reply"}

            state.chat.stream_turn = stream
        response = client.post(f"/api/conversations/{cid}/chat", json={"text": "test"})
        assert response.status_code == 200 and "isolated reply" in response.text
        assert observed and observed[0] >= 2


def register(client, name):
    response = client.post(
        "/api/auth/register",
        json={"username": name, "password": PASSWORD},
        headers={"Origin": ORIGIN},
    )
    assert response.status_code == 201, response.text
    client.headers.update({"Origin": ORIGIN, "X-CSRF-Token": response.json()["csrf_token"]})
    return response.json()


def test_two_accounts_isolate_business_objects_and_restart(tmp_path):
    cfg = CloudConfig(
        data_dir=tmp_path / "data", public_origin=ORIGIN, master_key=Fernet.generate_key().decode()
    )
    with TestClient(create_cloud_app(cfg), base_url=ORIGIN) as a:
        assert a.get("/api/content").status_code == 401
        a_session = register(a, "alice")
        b = TestClient(a.app, base_url=ORIGIN)
        register(b, "bobby")

        def populate(client, label):
            note = client.post(
                "/api/content",
                json={"type": "note", "status": "inbox", "title": label, "content": label},
            )
            assert note.status_code == 201, note.text
            task = client.post("/api/tasks", json={"title": label})
            assert task.status_code == 201, task.text
            chat = client.post("/api/conversations")
            assert chat.status_code == 201
            return note.json()["id"], task.json()["id"], chat.json()["id"]

        with ThreadPoolExecutor(max_workers=2) as pool:
            a_ids, b_ids = list(
                pool.map(lambda pair: populate(*pair), [(a, "Alice private"), (b, "Bob private")])
            )
        for client, own, other in ((a, a_ids, b_ids), (b, b_ids, a_ids)):
            assert (
                own[0] in client.get("/api/content").text
                and other[0] not in client.get("/api/content").text
            )
            assert client.get("/api/content/" + other[0]).status_code == 404
            assert client.delete("/api/tasks/" + other[1]).status_code == 404
            assert client.post("/api/conversations/" + other[2] + "/stop").status_code == 404
            assert (
                client.patch("/api/conversations/" + other[2], json={"title": "stolen"}).status_code
                == 404
            )
    with TestClient(create_cloud_app(cfg), base_url=ORIGIN) as restarted:
        response = restarted.post(
            "/api/auth/login",
            json={"username": "alice", "password": PASSWORD},
            headers={"Origin": ORIGIN},
        )
        assert response.status_code == 200
        assert response.json()["workspace"] == a_session["workspace"]
        assert "Alice private" in restarted.get("/api/content").text
        assert "Bob private" not in restarted.get("/api/content").text
