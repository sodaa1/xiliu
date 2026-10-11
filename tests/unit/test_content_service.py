from __future__ import annotations

import base64
from concurrent.futures import ThreadPoolExecutor

import pytest

from xiliu.api.errors import WebError
from xiliu.api.store import AppStore


@pytest.fixture
def service(tmp_path):
    from xiliu.api.services.content import ContentService

    return ContentService(AppStore(tmp_path))


def test_creates_note_link_and_file_with_portable_markdown(service):
    note = service.create({"title": "笔记", "content": "# Markdown 正文", "tags": ["学习"]})
    link = service.create({"type": "link", "source": "https://example.com/article"})
    data = b"\x00original attachment\xff"
    file = service.create(
        {"type": "file", "filename": "参考.pdf", "data_base64": base64.b64encode(data).decode()}
    )
    assert note["type"] == "note" and note["status"] == "inbox"
    assert link["source"] == "https://example.com/article"
    assert file["filename"] == "参考.pdf"
    assert service.original(file["id"]).read_bytes() == data
    markdown = (service.store.path.parent / "content" / note["id"] / "item.md").read_text(
        encoding="utf-8"
    )
    assert "# Markdown 正文" in markdown and "学习" in markdown and "status:" in markdown


def test_move_and_edits_update_search_without_moving_original(service):
    item = service.create(
        {
            "type": "file",
            "filename": "notes.txt",
            "data_base64": base64.b64encode(b"unchanged").decode(),
            "content": "机器学习的 Markdown records",
            "tags": ["研究"],
        }
    )
    path = service.original(item["id"])
    changed = service.update(item["id"], {"status": "knowledge", "summary": "检索摘要"})
    assert changed["created_at"] == item["created_at"]
    assert service.list() == []
    assert service.original(item["id"]) == path and path.read_bytes() == b"unchanged"
    assert service.list(status="knowledge", q="机器学习", tag="研究")[0]["id"] == item["id"]
    assert service.list(status="knowledge", q="摘要")[0]["id"] == item["id"]
    assert service.list(status="knowledge", q="Markdown")[0]["id"] == item["id"]
    assert service.list(status="knowledge", q='" OR * -') == []
    assert service.list(status="knowledge", tag="不存在") == []
    service.update(item["id"], {"content": "替换正文", "summary": "", "tags": ["新标签"]})
    assert service.list(status="knowledge", q="机器学习") == []
    assert service.list(status="knowledge", q="替换", tag="新标签")[0]["id"] == item["id"]
    markdown = path.parent.joinpath("item.md").read_text(encoding="utf-8")
    assert 'status: "knowledge"' in markdown and "替换正文" in markdown


def test_rejects_invalid_files_and_invalid_content_without_partial_items(service):
    invalid = [
        {"content": " "},
        {"title": " ", "content": "valid"},
        {"type": "link", "source": "javascript:alert(1)"},
        {"type": "link", "source": "https://"},
        {"type": "file", "filename": "../escape.txt", "data_base64": "YQ=="},
        {"type": "file", "filename": "C:\\escape.txt", "data_base64": "YQ=="},
        {"type": "file", "filename": "CON.txt", "data_base64": "YQ=="},
        {"type": "file", "filename": "a.txt", "data_base64": "!bad!"},
        {"type": "file", "filename": "a.txt", "data_base64": "A" * (28_000_000)},
        {"content": "valid", "tags": "string"},
    ]
    for payload in invalid:
        with pytest.raises(WebError) as error:
            service.create(payload)
        assert error.value.status in {413, 422}
    assert service.list() == []
    assert not list((service.store.path.parent / "content").glob("*/item.md"))


def test_missing_ids_and_delete_are_safe(service):
    item = service.create({"content": "retained until deleted"})
    with pytest.raises(WebError) as error:
        service.original(item["id"])
    assert error.value.status == 404
    for item_id in ("../../outside", "00000000-0000-0000-0000-000000000000"):
        for action in (service.get, service.delete, service.original):
            with pytest.raises(WebError) as error:
                action(item_id)
            assert error.value.status == 404
    service.delete(item["id"])
    assert not (service.store.path.parent / "content" / item["id"]).exists()
    assert service.list(q="retained") == []
    with pytest.raises(WebError):
        service.update(item["id"], {"title": "missing"})


def test_failed_markdown_update_keeps_database_and_file_consistent(service, monkeypatch):
    item = service.create({"content": "original note"})
    markdown = service.store.path.parent / "content" / item["id"] / "item.md"
    before = markdown.read_text(encoding="utf-8")

    def fail_write(*args):
        raise OSError("disk unavailable")

    monkeypatch.setattr("xiliu.api.services.content.atomic_write_utf8", fail_write)
    with pytest.raises(OSError, match="disk unavailable"):
        service.update(item["id"], {"content": "replacement"})
    assert service.get(item["id"])["content"] == "original note"
    assert markdown.read_text(encoding="utf-8") == before
    monkeypatch.undo()

    def fail_index(*args):
        raise RuntimeError("index unavailable")

    monkeypatch.setattr(service, "_index", fail_index)
    with pytest.raises(RuntimeError, match="index unavailable"):
        service.update(item["id"], {"content": "replacement"})
    assert service.get(item["id"])["content"] == "original note"
    assert markdown.read_text(encoding="utf-8") == before


def test_concurrent_instances_keep_independent_edits(service):
    from xiliu.api.services.content import ContentService

    item = service.create({"content": "concurrent content"})
    other = ContentService(service.store)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(service.update, item["id"], {"title": "edited title"}),
            pool.submit(other.update, item["id"], {"tags": ["edited tag"]}),
        ]
        for future in futures:
            future.result()
    saved = service.get(item["id"])
    assert saved["title"] == "edited title" and saved["tags"] == ["edited tag"]
    markdown = (service.store.path.parent / "content" / item["id"] / "item.md").read_text(
        encoding="utf-8"
    )
    assert "edited title" in markdown and "edited tag" in markdown


def test_deduplicates_concurrent_creates_and_recreates_after_delete(service):
    from xiliu.api.services.content import ContentService

    other = ContentService(service.store)
    payload = {"type": "link", "source": "https://example.com/feed", "title": "Feed item"}
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(instance.create, payload, dedupe_key="feed:shared")
            for instance in (service, other)
        ]
        items = [future.result() for future in futures]
    assert items[0]["id"] == items[1]["id"]
    assert len(service.list()) == 1
    service.delete(items[0]["id"])
    replacement = other.create(payload, dedupe_key="feed:shared")
    assert replacement["id"] != items[0]["id"]
    assert service.create(payload, dedupe_key="feed:shared")["id"] == replacement["id"]
    assert len(service.list()) == 1
