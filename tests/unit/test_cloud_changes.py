import sqlite3

import pytest
from cryptography.fernet import Fernet

from xiliu.cloud.changes import ChangeJournal
from xiliu.cloud.model_settings import CloudModelSettings


def test_committed_changes_deletions_and_restart(tmp_path):
    path = tmp_path / "app.sqlite3"
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE tasks(id TEXT PRIMARY KEY,title TEXT)")
    journal = ChangeJournal(tmp_path, "workspace-a")
    journal.install()
    with sqlite3.connect(path) as db:
        db.execute("INSERT INTO tasks VALUES('task-a','private text')")
        db.execute("UPDATE tasks SET title='updated' WHERE id='task-a'")
        db.execute("DELETE FROM tasks WHERE id='task-a'")
    events = journal.events()
    assert [event["version"] for event in events] == [1, 2, 3]
    assert [event["deleted"] for event in events] == [False, False, True]
    assert all(event["workspace_id"] == "workspace-a" for event in events)
    assert "private text" not in str(events)
    assert ChangeJournal(tmp_path, "workspace-a").events() == events
    with pytest.raises(RuntimeError), sqlite3.connect(path) as db:
        db.execute("INSERT INTO tasks VALUES('rolled-back','never committed')")
        raise RuntimeError()
    assert journal.events() == events
    with pytest.raises(ValueError):
        ChangeJournal(tmp_path, "workspace-b").install()


def test_existing_data_and_composite_keys(tmp_path):
    with sqlite3.connect(tmp_path / "app.sqlite3") as db:
        db.execute(
            "CREATE TABLE document_tags(document_id TEXT,tag_id TEXT,"
            "PRIMARY KEY(document_id,tag_id))"
        )
        db.execute("INSERT INTO document_tags VALUES('doc','tag')")
    journal = ChangeJournal(tmp_path, "workspace-a")
    journal.install()
    before = journal.events()
    assert len(before) == 1
    journal.install()
    assert journal.events() == before
    with sqlite3.connect(tmp_path / "app.sqlite3") as db:
        db.execute("DELETE FROM document_tags")
    assert journal.events()[-1]["entity_id"] == '["doc","tag"]'
    assert journal.events()[-1]["deleted"] is True


def test_failed_model_version_write_restores_ciphertext(tmp_path):
    settings = CloudModelSettings(tmp_path, Fernet.generate_key().decode(), "workspace-a")
    settings._write_values({"XILIU_API_KEY": "old-secret"})
    previous = settings.env_file.read_bytes()

    def fail():
        raise RuntimeError("journal unavailable")

    settings.on_changed = fail
    with pytest.raises(RuntimeError):
        settings._write_values({"XILIU_API_KEY": "new-secret"})
    assert settings.env_file.read_bytes() == previous
    assert settings.values()["XILIU_API_KEY"] == "old-secret"
