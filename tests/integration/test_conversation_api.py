import json

from fastapi.testclient import TestClient

from xiliu.api.app import create_app
from xiliu.events import FinalEvent


def test_conversation_api_and_ndjson_contract(tmp_path):
    env = tmp_path / ".env"
    env.write_text("XILIU_API_KEY=fake\nXILIU_MODEL=deepseek-flash\n")
    app = create_app(data_dir=tmp_path / "data", env_file=env)

    class FakeRuntime:
        def stream_session(self, **kwargs):
            yield FinalEvent(text="你好\nSecond line", session_id=kwargs["session_id"])

    app.state.chat.runtime_factory = lambda *args, **kwargs: FakeRuntime()
    with TestClient(app, base_url="http://127.0.0.1") as client:
        assert (
            client.get("/api/conversations/missing").json()["error"]["code"]
            == "conversation_not_found"
        )
        cid = client.post("/api/conversations").json()["id"]
        response = client.patch(f"/api/conversations/{cid}", json={"model_override": "gpt-5.6-sol"})
        assert response.status_code == 400
        assert (
            client.patch(
                f"/api/conversations/{cid}", json={"model_override": "deepseek-v4-pro"}
            ).status_code
            == 200
        )
        response = client.post(f"/api/conversations/{cid}/chat", json={"text": "Hello"})
        assert response.headers["content-type"].startswith("application/x-ndjson")
        events = [json.loads(line) for line in response.text.splitlines()]
        assert events[-1]["text"] == "你好\nSecond line"
        assert (
            client.get(f"/api/conversations/{cid}/messages").json()[-1]["content"]
            == "你好\nSecond line"
        )
        assert client.delete(f"/api/conversations/{cid}").status_code == 204
        assert client.get("/api/conversations").json() == []


def test_command_catalog_metadata_and_clear_route(tmp_path):
    app = create_app(data_dir=tmp_path / "data", env_file=tmp_path / ".env")
    with TestClient(app, base_url="http://127.0.0.1") as client:
        assert [entry["name"] for entry in client.get("/api/commands").json()] == [
            "clear",
            "compress",
            "skill",
            "mcp",
        ]
        assert client.get("/api/capabilities/skills").json() == []
        assert client.get("/api/capabilities/mcp").json() == []
        cid = client.post("/api/conversations").json()["id"]
        response = client.post(f"/api/conversations/{cid}/chat", json={"text": "/clear"})
        events = [json.loads(line) for line in response.text.splitlines()]
        assert events[-1]["text"] == "已清除对话内容"
        messages = client.get(f"/api/conversations/{cid}/messages").json()
        assert [message["role"] for message in messages] == ["event"]


def test_real_runtime_stream_survives_fastapi_worker_contexts(tmp_path):
    from langchain_core.messages import AIMessage

    from xiliu.runtime import Runtime

    env = tmp_path / ".env"
    env.write_text("XILIU_API_KEY=fake\nXILIU_MODEL=deepseek-v4-flash\n")
    app = create_app(data_dir=tmp_path / "data", env_file=env)

    class Model:
        def invoke(self, messages):
            if "intent router" in messages[0].content:
                return AIMessage(content='{"route":"chat","reason":"greeting","confidence":1}')
            return AIMessage(content="Completed through the real Runtime")

    app.state.chat.runtime_factory = lambda settings, **kwargs: Runtime(
        Model(), model_name=settings.model, data_dir=settings.data_dir
    )
    with TestClient(app, base_url="http://127.0.0.1") as client:
        cid = client.post("/api/conversations").json()["id"]
        response = client.post(f"/api/conversations/{cid}/chat", json={"text": "Hello"})
        events = [json.loads(line) for line in response.text.splitlines()]
        assert events[-1]["type"] == "final"
        assert events[-1]["text"] == "Completed through the real Runtime"
