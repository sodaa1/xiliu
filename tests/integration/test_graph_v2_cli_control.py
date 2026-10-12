from xiliu.core.agent import stream_session_events
from xiliu.core.session import load_or_create_session


def test_cli_clear_does_not_require_a_configured_model(tmp_path, monkeypatch):
    def forbidden():
        raise AssertionError("Clearing context must not load model settings")

    monkeypatch.setattr("xiliu.config.load_settings", forbidden)
    events = list(stream_session_events("/clear", session_workspace=tmp_path))
    assert events[-1]["event"]["text"]
    assert load_or_create_session(tmp_path)["recent_turns"][-1]["role"] == "assistant"
