import json

from xiliu.api.app import create_app


def test_chat_app_action_without_api_key_fails_without_mutation(tmp_path, monkeypatch):
    monkeypatch.delenv("XILIU_API_KEY", raising=False)
    application = create_app(data_dir=tmp_path, env_file=tmp_path / ".env")
    application.state.chat.runtime_factory = lambda *a, **kw: (_ for _ in ()).throw(
        AssertionError("Supervisor entered")
    )
    cid = application.state.store.create()["id"]
    events = list(application.state.chat.stream_turn(cid, "添加待办「整理面试资料」"))
    assert events[-1]["type"] == "error"
    assert events[-1]["code"] == "model_not_configured"
    assert "设置" in events[-1]["message"]
    assert application.state.tasks.list() == []


def test_local_chat_negation_and_ambiguous_deletion_leave_database_unchanged(tmp_path, monkeypatch):
    monkeypatch.delenv("XILIU_API_KEY", raising=False)
    application = create_app(data_dir=tmp_path, env_file=tmp_path / ".env")
    application.state.tasks.create({"title": "保留"})
    cid = application.state.store.create()["id"]
    for text in ["不要删除待办「保留」", "删除待办"]:
        events = list(application.state.chat.stream_turn(cid, text))
        assert events[-1]["type"] == "error"
        assert events[-1]["code"] == "model_not_configured"
        assert application.state.tasks.list()[0]["title"] == "保留"
        assert "confirmation_id" not in json.dumps(events)
