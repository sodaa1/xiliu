from pathlib import Path
from threading import Event

from xiliu.api.services.content import ContentService
from xiliu.api.store import AppStore


def test_folder_rules_migration_and_markdown_recovery(tmp_path: Path):
    from xiliu.api.services.knowledge import KnowledgeService

    content = ContentService(AppStore(tmp_path))
    old = content.create({"content": "Python reference", "tags": ["Python"], "status": "knowledge"})
    knowledge = KnowledgeService(content)
    first = knowledge.create_folder({"name": "Low", "tags": ["python"], "priority": 1})
    best = knowledge.create_folder({"name": "High", "tags": ["PYTHON"], "priority": 2})
    assert knowledge.classify(["Python", "python"]) == best["id"]
    assert knowledge.classify(["Other"]) is None
    assert content.get(old["id"])["folder_id"] is None
    item = content.update(old["id"], {"tags": ["PYTHON"]})
    assert item["folder_id"] == best["id"]
    content.rebuild_index()
    assert content.get(old["id"])["folder_id"] == best["id"]
    knowledge.delete_folder(best["id"])
    assert content.get(old["id"])["status"] == "knowledge"
    assert content.get(old["id"])["folder_id"] is None
    assert knowledge.list_folders()[0]["id"] == first["id"]


def test_background_failure_and_revision_guard(tmp_path: Path):
    from xiliu.api.services.inbox import InboxService
    from xiliu.api.services.knowledge import KnowledgeService

    content = ContentService(AppStore(tmp_path))
    knowledge = KnowledgeService(content)
    knowledge.create_folder({"name": "Python", "tags": ["Python"]})
    entered, release = Event(), Event()

    def metadata(_item):
        entered.set()
        release.wait(5)
        return {"title": "AI title", "summary": "AI summary", "tags": ["Python"]}

    inbox = InboxService(content, knowledge, metadata=metadata)
    item = inbox.import_item({"text": "Python source"})
    assert item["processing_status"] == "pending"
    inbox.start()
    assert entered.wait(5)
    content.update(item["id"], {"title": "Human title"})
    release.set()
    inbox.shutdown()
    assert content.get(item["id"])["title"] == "Human title"
    assert content.get(item["id"])["processing_status"] == "ready"

    def fail(_item):
        raise RuntimeError("secret credential")

    inbox = InboxService(content, knowledge, metadata=fail)
    second = inbox.import_item({"text": "Python retained"})
    inbox.start()
    inbox.shutdown()
    result = content.get(second["id"])
    assert result["processing_status"] == "failed"
    assert result["content"] == "Python retained"
    assert result["folder_id"] is not None
    assert "secret" not in result["processing_error"]


def test_durable_jobs_resume_and_batch_aligns_ids(tmp_path: Path):
    from xiliu.api.services.inbox import InboxService
    from xiliu.api.services.knowledge import KnowledgeService

    content = ContentService(AppStore(tmp_path))
    knowledge = KnowledgeService(content)
    folder = knowledge.create_folder({"name": "Code", "tags": ["Python"]})
    inbox = InboxService(
        content, knowledge, metadata=lambda _: (_ for _ in ()).throw(AssertionError("AI disabled"))
    )
    item = inbox.import_item({"text": "Python persisted", "use_ai": False})
    resumed = InboxService(
        content, knowledge, metadata=lambda _: (_ for _ in ()).throw(AssertionError("AI disabled"))
    )
    resumed.start()
    resumed.shutdown()
    assert content.get(item["id"])["folder_id"] == folder["id"]
    assert content.get(item["id"])["ai_processed"] is False
    second = content.create({"content": "Unrelated", "tags": ["Other"]})
    calls = []

    def batch(system, payload):
        calls.append(payload)
        return {
            "items": [
                {"document_id": second["id"], "tags": ["unknown"], "folder_id": folder["id"]},
                {"document_id": item["id"], "tags": ["Python"], "folder_id": folder["id"]},
            ]
        }

    resumed._invoke = batch
    result = resumed.classify_batch([item["id"], second["id"]])["items"]
    assert [entry["id"] for entry in result] == [item["id"], second["id"]]
    assert result[0]["folder_id"] == folder["id"]
    assert result[1]["folder_id"] is None and result[1]["processing_status"] == "failed"
    assert len(calls) == 1


def test_old_schema_migrates_and_deleted_index_recovers_originals(tmp_path: Path):
    import base64
    import json
    from uuid import uuid4

    from xiliu.api.services.knowledge import KnowledgeService

    store = AppStore(tmp_path)
    item_id = str(uuid4())
    with store.connect() as db:
        db.execute("""CREATE TABLE content_items(id TEXT PRIMARY KEY,type TEXT,status TEXT,
            title TEXT,content TEXT,summary TEXT,source TEXT,tags_json TEXT,
            created_at TEXT,updated_at TEXT,filename TEXT)""")
        db.execute(
            "INSERT INTO content_items VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (
                item_id,
                "note",
                "knowledge",
                "Legacy",
                "Legacy body",
                "",
                "",
                json.dumps(["Python"]),
                "old",
                "old",
                None,
            ),
        )
        db.execute("CREATE TABLE content_dedup(key TEXT PRIMARY KEY,content_id TEXT)")
        db.execute("INSERT INTO content_dedup VALUES(?,?)", ("feed:legacy", item_id))
    content = ContentService(store)
    assert content.get(item_id)["tags"] == ["Python"]
    assert content.get(item_id)["folder_id"] is None
    assert store.path.with_suffix(".pre-knowledge.sqlite3").exists()
    duplicate = content.create({"content": "unused"}, dedupe_key="feed:legacy")
    assert duplicate["id"] == item_id
    # Give the old item portable metadata without silently reclassifying it.
    content.update(item_id, {"summary": "Portable"})
    knowledge = KnowledgeService(content)
    folder = knowledge.create_folder({"name": "Code", "tags": ["Python"]})
    attachment = content.create(
        {
            "type": "file",
            "filename": "original.txt",
            "data_base64": base64.b64encode(b"original").decode(),
            "content": "Portable file",
            "status": "knowledge",
            "folder_id": folder["id"],
        }
    )
    store.path.unlink()
    recovered = ContentService(AppStore(tmp_path))
    rules = KnowledgeService(recovered)
    assert recovered.get(item_id)["content"] == "Legacy body"
    assert recovered.original(attachment["id"]).read_bytes() == b"original"
    assert rules.list_folders()[0]["id"] == folder["id"]
    assert rules.folder_items(folder["id"])[0]["id"] == attachment["id"]


def test_extract_docx_and_binary_boundaries():
    from io import BytesIO
    from zipfile import ZipFile

    from xiliu.api.services.extract_text import extract_text

    stream = BytesIO()
    with ZipFile(stream, "w") as archive:
        archive.writestr(
            "word/document.xml",
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:p><w:r><w:t>中文正文</w:t></w:r></w:p></w:document>',
        )
    assert extract_text("notes.docx", stream.getvalue()) == ("中文正文", None)
    assert extract_text("notes.txt", "编码文本".encode("gb18030")) == ("编码文本", None)
    text, error = extract_text("binary.txt", b"\x00\x01\x02binary")
    assert text == "" and error
    text, error = extract_text("scanned.pdf", b"not a pdf")
    assert text == "" and error


def test_rebuild_invalid_markdown_never_drops_existing_content(tmp_path):
    import pytest

    from xiliu.api.errors import WebError

    content = ContentService(AppStore(tmp_path))
    item = content.create({"content": "Retain indexed content"})
    (content.root / item["id"] / "item.md").write_text("broken frontmatter", encoding="utf-8")
    with pytest.raises(WebError):
        content.rebuild_index()
    assert content.get(item["id"])["content"] == "Retain indexed content"


def test_deleted_sqlite_pending_recovery_preserves_ai_opt_out(tmp_path):
    from xiliu.api.services.inbox import InboxService
    from xiliu.api.services.knowledge import KnowledgeService

    content = ContentService(AppStore(tmp_path))
    knowledge = KnowledgeService(content)
    knowledge.create_folder({"name": "Code", "tags": ["Python"]})
    inbox = InboxService(content, knowledge)
    item = inbox.import_item({"text": "Python resume", "use_ai": False})
    content.store.path.unlink()
    recovered = ContentService(AppStore(tmp_path))
    calls = []

    def metadata(_item):
        calls.append(_item)
        return {"title": "AI", "summary": "AI", "tags": ["Python"]}

    resumed = InboxService(recovered, KnowledgeService(recovered), metadata=metadata)
    resumed.start()
    resumed.shutdown()
    assert calls == []
    assert recovered.get(item["id"])["processing_status"] == "ready"
    assert recovered.get(item["id"])["ai_processed"] is False


def test_markdown_recovery_preserves_embedded_section_markers(tmp_path):
    content = ContentService(AppStore(tmp_path))
    item = content.create(
        {
            "title": "Title\n\n## Content\n\ninside title",
            "content": "Body\n\n## Summary\n\ninside body",
            "summary": "Summary\n\n## Summary\n\ninside summary",
        }
    )
    content.rebuild_index()
    recovered = content.get(item["id"])
    assert recovered["content"] == item["content"]
    assert recovered["summary"] == item["summary"]
