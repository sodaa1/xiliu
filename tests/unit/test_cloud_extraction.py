from types import SimpleNamespace

from xiliu.cloud.extraction import extract_cloud_text


def test_cloud_parser_isolated_and_bounded(monkeypatch):
    observed = {}

    def run(argv, **kwargs):
        observed.update(argv=argv, **kwargs)
        return SimpleNamespace(returncode=0, stdout=b'["hello",null]')

    monkeypatch.setattr("xiliu.cloud.extraction.subprocess.run", run)
    assert extract_cloud_text("notes.txt", b"hello") == ("hello", None)
    assert observed["timeout"] == 12
    assert observed["input"] == b"hello"
    assert "shell" not in observed


def test_cloud_parser_failure_preserves_original(monkeypatch):
    def run(*args, **kwargs):
        raise TimeoutError()

    monkeypatch.setattr("xiliu.cloud.extraction.subprocess.run", run)
    text, error = extract_cloud_text("large.pdf", b"%PDF")
    assert not text and "原件" in error
