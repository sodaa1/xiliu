from __future__ import annotations

import base64
import binascii
import json
import os
import shutil
import sqlite3
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit
from uuid import UUID, uuid4

from xiliu.api.errors import WebError
from xiliu.api.store import AppStore, now
from xiliu.tools.workspace import atomic_write_utf8

MAX_UPLOAD_BYTES = 20 * 1024 * 1024
_EDITABLE = {"status", "title", "content", "summary", "source", "tags", "folder_id"}
_COLUMNS = (
    "id",
    "type",
    "status",
    "title",
    "content",
    "summary",
    "source",
    "tags_json",
    "created_at",
    "updated_at",
    "filename",
    "folder_id",
    "ai_processed",
    "processing_status",
    "processing_error",
    "revision",
)


def _invalid(message: str) -> WebError:
    return WebError("invalid_content", message, 422)


def _text(value: Any, field: str, limit: int, *, nonblank: bool = False) -> str:
    if not isinstance(value, str) or len(value) > limit or "\x00" in value:
        raise _invalid(f"{field} 必须是有效文本，且不能超过 {limit} 个字符。")
    if nonblank and not value.strip():
        raise _invalid(f"{field} 不能为空。")
    return value


def _filename(value: Any) -> str:
    name = _text(value, "filename", 255, nonblank=True)
    stem = name.split(".")[0].upper()
    reserved = {"CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$"}
    reserved |= {f"{prefix}{i}" for prefix in ("COM", "LPT") for i in range(1, 10)}
    if (
        name in {".", ".."}
        or name.endswith((".", " "))
        or any(char in '<>:"/\\|?*' or ord(char) < 32 for char in name)
        or stem in reserved
    ):
        raise _invalid("文件名不能包含路径或系统保留字符。")
    return name


def _render(item: dict[str, Any]) -> str:
    fields = (
        "id",
        "type",
        "status",
        "title",
        "source",
        "created_at",
        "updated_at",
        "tags",
        "filename",
        "folder_id",
        "ai_processed",
        "processing_status",
        "processing_error",
        "revision",
    )
    metadata = "\n".join(f"{key}: {json.dumps(item[key], ensure_ascii=False)}" for key in fields)
    metadata += f"\ncontent_length: {len(item['content'])}\nsummary_length: {len(item['summary'])}"
    return (
        f"---\n{metadata}\n---\n\n# {item['title']}\n\n"
        f"## Content\n\n{item['content']}\n\n## Summary\n\n{item['summary']}\n"
    )


class ContentService:
    """Portable Markdown and retained attachments with a shared SQLite search index."""

    def __init__(self, store: AppStore):
        self.store = store
        self.root = store.path.parent.resolve() / "content"
        if self.root.resolve() != self.root:
            raise WebError("invalid_content_storage", "内容目录不能是符号链接。", 500)
        self.root.mkdir(parents=True, exist_ok=True)
        self.knowledge: Any = None
        with store.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS content_items (
                    id TEXT PRIMARY KEY,
                    type TEXT NOT NULL CHECK(type IN ('note','link','file')),
                    status TEXT NOT NULL CHECK(status IN ('inbox','knowledge')),
                    title TEXT NOT NULL, content TEXT NOT NULL, summary TEXT NOT NULL,
                    source TEXT NOT NULL, tags_json TEXT NOT NULL,
                    created_at TEXT NOT NULL, updated_at TEXT NOT NULL, filename TEXT
                );
                CREATE INDEX IF NOT EXISTS content_status_updated
                    ON content_items(status, updated_at DESC);
                CREATE TABLE IF NOT EXISTS content_dedup (
                    key TEXT PRIMARY KEY, content_id TEXT NOT NULL
                );
                CREATE VIRTUAL TABLE IF NOT EXISTS content_fts USING fts5(
                    id UNINDEXED, title, content, summary, source, tags, filename,
                    tokenize='trigram'
                );
            """)

        with store.connect() as db:
            columns = {row[1] for row in db.execute("PRAGMA table_info(content_items)")}
            additions = {
                "folder_id": "TEXT",
                "ai_processed": "INTEGER NOT NULL DEFAULT 0",
                "processing_status": "TEXT NOT NULL DEFAULT 'ready'",
                "processing_error": "TEXT",
                "revision": "INTEGER NOT NULL DEFAULT 0",
            }
            if set(additions) - columns:
                backup = store.path.with_suffix(".pre-knowledge.sqlite3")
                if not backup.exists():
                    with sqlite3.connect(backup) as destination:
                        db.backup(destination)
            db.execute("BEGIN IMMEDIATE")
            for column, declaration in additions.items():
                if column not in columns:
                    db.execute(f"ALTER TABLE content_items ADD COLUMN {column} {declaration}")
            for statement in (
                "CREATE TABLE IF NOT EXISTS content_migrations(version INTEGER PRIMARY KEY)",
                "CREATE TABLE IF NOT EXISTS tags(id TEXT PRIMARY KEY,name TEXT NOT NULL, "
                "normalized_name TEXT NOT NULL UNIQUE)",
                "CREATE TABLE IF NOT EXISTS document_tags(document_id TEXT NOT NULL, "
                "tag_id TEXT NOT NULL, PRIMARY KEY(document_id,tag_id))",
                "INSERT OR IGNORE INTO content_migrations VALUES(1)",
            ):
                db.execute(statement)
            for row in db.execute("SELECT id,tags_json FROM content_items").fetchall():
                self._sync_tags(db, row["id"], json.loads(row["tags_json"]))
        with store.connect() as db:
            empty = not db.execute("SELECT 1 FROM content_items LIMIT 1").fetchone()
        if empty and next(self.root.glob("*/item.md"), None) is not None:
            self.rebuild_index()
        from xiliu.rag.ingestion import migrate

        migrate(store)

    @staticmethod
    def _sync_tags(db: sqlite3.Connection, item_id: str, tags: list[str]) -> None:
        db.execute("DELETE FROM document_tags WHERE document_id=?", (item_id,))
        for tag in tags:
            normalized = tag.strip().casefold()
            db.execute("INSERT OR IGNORE INTO tags VALUES(?,?,?)", (str(uuid4()), tag, normalized))
            tag_id = db.execute(
                "SELECT id FROM tags WHERE normalized_name=?", (normalized,)
            ).fetchone()[0]
            db.execute("INSERT OR IGNORE INTO document_tags VALUES(?,?)", (item_id, tag_id))

    def _directory(self, item_id: str) -> Path:
        try:
            if str(UUID(item_id)) != item_id:
                raise ValueError("noncanonical UUID")
        except (ValueError, TypeError, AttributeError):
            raise WebError("content_not_found", "内容不存在。", 404) from None
        directory = self.root / item_id
        if self.root.resolve() != self.root or directory.resolve() != directory:
            raise WebError("invalid_content_storage", "内容路径无效。", 500)
        return directory

    def _get(self, db: sqlite3.Connection, item_id: str) -> dict[str, Any]:
        self._directory(item_id)
        row = db.execute("SELECT * FROM content_items WHERE id=?", (item_id,)).fetchone()
        if row is None:
            raise WebError("content_not_found", "内容不存在。", 404)
        item = dict(row)
        item["tags"] = json.loads(item.pop("tags_json"))
        item["ai_processed"] = bool(item["ai_processed"])
        return item

    @staticmethod
    def _validate(item: dict[str, Any]) -> dict[str, Any]:
        if item["type"] not in ("note", "link", "file"):
            raise _invalid("type 必须是 note、link 或 file。")
        if item["status"] not in ("inbox", "knowledge"):
            raise _invalid("status 必须是 inbox 或 knowledge。")
        item["title"] = _text(item["title"], "title", 500, nonblank=True).strip()
        item["content"] = _text(
            item["content"], "content", 1_000_000, nonblank=item["type"] == "note"
        )
        item["summary"] = _text(item["summary"], "summary", 100_000)
        item["source"] = _text(item["source"], "source", 2048).strip()
        if item["type"] == "link":
            try:
                url = urlsplit(item["source"])
                valid = (
                    url.scheme in {"http", "https"}
                    and bool(url.hostname)
                    and not url.username
                    and not url.password
                    and not any(char.isspace() for char in item["source"])
                )
                _ = url.port  # Validate malformed/out-of-range ports as well.
            except ValueError:
                valid = False
            if not valid:
                raise _invalid("链接必须是有效的 http 或 https 地址。")
        tags = item["tags"]
        if not isinstance(tags, list) or len(tags) > 50:
            raise _invalid("tags 必须是最多包含 50 个标签的列表。")
        unique = {}
        for tag in tags:
            value = _text(tag, "tag", 100, nonblank=True).strip()
            unique.setdefault(value.casefold(), value)
        item["tags"] = list(unique.values())
        folder = item.get("folder_id")
        if folder is not None:
            _text(folder, "folder_id", 100, nonblank=True)
        if item.get("processing_status", "ready") not in {"pending", "ready", "failed"}:
            raise _invalid("无效处理状态。")
        return item

    @staticmethod
    def _values(item: dict[str, Any]) -> tuple[Any, ...]:
        return tuple(
            json.dumps(item["tags"], ensure_ascii=False) if key == "tags_json" else item[key]
            for key in _COLUMNS
        )

    @contextmanager
    def _transaction(
        self, restore: Callable[[], None], *, enforce_storage: bool = True
    ) -> Iterator[sqlite3.Connection]:
        with self.store.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            guard = getattr(self, "storage_guard", None) if enforce_storage else None
            previous = guard(measure=True) if guard is not None else None
            try:
                yield db
                if guard is not None:
                    guard(previous=previous)
                # Commit here so failed commits restore files before releasing the write lock.
                db.commit()
            except BaseException:
                restore()
                raise

    @staticmethod
    def _index(db: sqlite3.Connection, item: dict[str, Any]) -> None:
        ContentService._sync_tags(db, item["id"], item["tags"])
        db.execute("DELETE FROM content_fts WHERE id=?", (item["id"],))
        db.execute(
            "INSERT INTO content_fts(id,title,content,summary,source,tags,filename) "
            "VALUES(?,?,?,?,?,?,?)",
            (
                item["id"],
                item["title"],
                item["content"],
                item["summary"],
                item["source"],
                " ".join(item["tags"]),
                item["filename"] or "",
            ),
        )
        if db.execute("SELECT 1 FROM sqlite_master WHERE name='rag_index_jobs'").fetchone():
            from xiliu.rag.ingestion import enqueue, remove_chunks

            remove_chunks(db, item["id"])
            enqueue(db, item)

    def create(self, payload: dict[str, Any], *, dedupe_key: str | None = None) -> dict[str, Any]:
        if dedupe_key is not None:
            dedupe_key = _text(dedupe_key, "dedupe_key", 500, nonblank=True)
        if not isinstance(payload, dict) or set(payload) - (
            _EDITABLE | {"type", "filename", "data_base64"}
        ):
            raise _invalid("存在不支持的内容字段。")
        kind = payload.get("type", "note")
        filename = _filename(payload.get("filename")) if kind == "file" else None
        data: bytes | None = None
        if kind == "file":
            encoded = payload.get("data_base64")
            if not isinstance(encoded, str):
                raise _invalid("文件必须提供 data_base64。")
            if len(encoded) > 4 * ((MAX_UPLOAD_BYTES + 2) // 3):
                raise WebError("content_file_too_large", "文件不能超过 20 MiB。", 413)
            try:
                data = base64.b64decode(encoded, validate=True)
            except (ValueError, binascii.Error):
                raise _invalid("data_base64 不是有效的 Base64 文件。") from None
            if len(data) > MAX_UPLOAD_BYTES:
                raise WebError("content_file_too_large", "文件不能超过 20 MiB。", 413)
        elif "filename" in payload or "data_base64" in payload:
            raise _invalid("只有 file 类型可以包含附件。")
        timestamp = now()
        default_title = filename or payload.get("source") or "未命名笔记"
        item = self._validate(
            {
                "id": str(uuid4()),
                "type": kind,
                "status": payload.get("status", "inbox"),
                "title": payload.get("title", default_title),
                "content": payload.get("content", ""),
                "summary": payload.get("summary", ""),
                "source": payload.get("source", ""),
                "tags": payload.get("tags", []),
                "created_at": timestamp,
                "updated_at": timestamp,
                "filename": filename,
                "folder_id": payload.get("folder_id"),
                "ai_processed": False,
                "processing_status": "ready",
                "processing_error": None,
                "revision": 0,
            }
        )
        directory = self._directory(item["id"])
        created = False

        def restore() -> None:
            if created:
                shutil.rmtree(directory)

        with self._transaction(restore) as db:
            if dedupe_key is not None:
                mapping = db.execute(
                    "SELECT content_id FROM content_dedup WHERE key=?", (dedupe_key,)
                ).fetchone()
                if mapping is not None:
                    existing = db.execute(
                        "SELECT id FROM content_items WHERE id=?", (mapping["content_id"],)
                    ).fetchone()
                    if existing is not None:
                        return self._get(db, existing["id"])
                    db.execute("DELETE FROM content_dedup WHERE key=?", (dedupe_key,))
            if item["folder_id"] is not None:
                if self.knowledge is None:
                    raise _invalid("请先创建知识文件夹。")
                self.knowledge.get_folder(item["folder_id"], db=db)
            directory.mkdir()
            created = True
            if data is not None:
                with self._attachment(directory, filename).open("xb") as stream:
                    stream.write(data)
                    stream.flush()
                    os.fsync(stream.fileno())
            atomic_write_utf8(directory / "item.md", _render(item))
            columns = ",".join(_COLUMNS)
            placeholders = ",".join("?" for _ in _COLUMNS)
            db.execute(
                f"INSERT INTO content_items({columns}) VALUES({placeholders})",
                self._values(item),
            )
            self._index(db, item)
            if dedupe_key is not None:
                db.execute(
                    "INSERT INTO content_dedup(key,content_id) VALUES(?,?)",
                    (dedupe_key, item["id"]),
                )
        return item

    def list(self, status: str = "inbox", q: str = "", tag: str = "") -> list[dict[str, Any]]:
        if status not in ("inbox", "knowledge"):
            raise _invalid("status 必须是 inbox 或 knowledge。")
        q = _text(q, "q", 1000).strip()
        tag = _text(tag, "tag", 100).strip()
        clauses, params = ["status=?"], [status]
        long_terms = []
        for term in q.split():
            if len(term) >= 3:
                # Quote every term: operators, wildcards and quotes are always literal input.
                long_terms.append('"' + term.replace('"', '""') + '"')
            else:
                # Trigram FTS cannot match <3 characters, including short Chinese words.
                clauses.append(
                    "(title || char(10) || content || char(10) || summary || char(10) || "
                    "source || char(10) || tags_json || char(10) || COALESCE(filename,'')) "
                    "LIKE ? ESCAPE '|'"
                )
                params.append(
                    "%" + term.replace("|", "||").replace("%", "|%").replace("_", "|_") + "%"
                )
        if long_terms:
            clauses.append("id IN (SELECT id FROM content_fts WHERE content_fts MATCH ?)")
            params.append(" AND ".join(long_terms))
        if tag:
            clauses.append("EXISTS (SELECT 1 FROM json_each(tags_json) WHERE value=?)")
            params.append(tag)
        with self.store.connect() as db:
            rows = db.execute(
                "SELECT * FROM content_items WHERE "
                + " AND ".join(clauses)
                + " ORDER BY updated_at DESC, id",
                params,
            )
            items = []
            for row in rows:
                item = dict(row)
                item["tags"] = json.loads(item.pop("tags_json"))
                item["ai_processed"] = bool(item["ai_processed"])
                items.append(item)
            return items

    def get(self, item_id: str) -> dict[str, Any]:
        with self.store.connect() as db:
            return self._get(db, item_id)

    def update(
        self,
        item_id: str,
        changes: dict[str, Any],
        *,
        expected_revision: int | None = None,
        internal: bool = False,
        advance_revision: bool = False,
        on_persist: Callable[[sqlite3.Connection], Any] | None = None,
    ) -> dict[str, Any]:
        if on_persist is not None and not internal:
            raise _invalid("提交回调仅允许内部业务调用。")
        allowed = _EDITABLE | (
            {"ai_processed", "processing_status", "processing_error"} if internal else set()
        )
        if not isinstance(changes, dict) or set(changes) - allowed:
            raise _invalid("存在不支持的更新字段。")
        markdown = self._directory(item_id) / "item.md"
        before = None
        written = False

        def restore() -> None:
            if written:
                if before is None:
                    markdown.unlink(missing_ok=True)
                else:
                    atomic_write_utf8(markdown, before)

        with self._transaction(restore) as db:
            previous = self._get(db, item_id)
            if expected_revision is not None and previous["revision"] != expected_revision:
                return previous
            if not changes:
                return previous
            changes = dict(changes)
            if self.knowledge is not None:
                if "folder_id" in changes:
                    if changes["folder_id"] is not None:
                        self.knowledge.get_folder(changes["folder_id"], db=db)
                        changes.setdefault("status", "knowledge")
                elif "tags" in changes:
                    changes["folder_id"] = self.knowledge.classify(changes["tags"], db=db)
                    if changes["folder_id"]:
                        changes.setdefault("status", "knowledge")
            if changes.get("status") == "inbox":
                changes["folder_id"] = None
            item = self._validate(
                {
                    **previous,
                    **changes,
                    "updated_at": now(),
                    "revision": previous["revision"]
                    + (1 if not internal or advance_revision else 0),
                }
            )
            if markdown.resolve() != markdown:
                raise WebError("invalid_content_storage", "内容文件路径无效。", 500)
            before = markdown.read_text(encoding="utf-8") if markdown.exists() else None
            atomic_write_utf8(markdown, _render(item))
            written = True
            assignments = ",".join(f"{column}=?" for column in _COLUMNS[1:])
            db.execute(
                f"UPDATE content_items SET {assignments} WHERE id=?",
                (*self._values(item)[1:], item_id),
            )
            self._index(db, item)
            if (
                any(key in changes for key in ("content", "title", "summary", "tags", "status"))
                and db.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name='knowledge_vectors'"
                ).fetchone()
            ):
                db.execute("DELETE FROM knowledge_vectors WHERE document_id=?", (item_id,))
            if on_persist is not None:
                on_persist(db)
        return item

    def delete(self, item_id: str) -> None:
        directory = self._directory(item_id)
        trash = self.root / f".deleted-{uuid4()}"
        moved = False

        def restore() -> None:
            if moved:
                trash.rename(directory)

        with self._transaction(restore, enforce_storage=False) as db:
            self._get(db, item_id)
            if directory.exists():
                directory.rename(trash)
                moved = True
            db.execute("DELETE FROM content_fts WHERE id=?", (item_id,))
            db.execute("DELETE FROM document_tags WHERE document_id=?", (item_id,))
            for table in ("content_embeddings", "knowledge_vectors", "inbox_jobs"):
                if db.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
                ).fetchone():
                    columns = {r[1] for r in db.execute(f"PRAGMA table_info({table})")}
                    key = "document_id" if "document_id" in columns else "item_id"
                    if key in columns:
                        db.execute(f"DELETE FROM {table} WHERE {key}=?", (item_id,))
            db.execute("DELETE FROM content_items WHERE id=?", (item_id,))
            from xiliu.rag.ingestion import remove_chunks

            remove_chunks(db, item_id)
            db.execute("DELETE FROM rag_chunk_vectors WHERE document_id=?", (item_id,))
            db.execute("UPDATE rag_index_jobs SET state='deleted' WHERE document_id=?", (item_id,))
        if moved:
            shutil.rmtree(trash)

    @staticmethod
    def _attachment(directory: Path, filename: str | None) -> Path:
        # Keep the user-facing name as metadata; use a fixed disk name to avoid item.md collisions.
        return directory / ("original" + Path(filename or "").suffix)

    def original(self, item_id: str) -> Path:
        item = self.get(item_id)
        if item["type"] != "file":
            raise WebError("content_original_not_found", "该内容没有原附件。", 404)
        path = self._attachment(self._directory(item_id), item["filename"])
        if path.resolve() != path or not path.is_file():
            raise WebError("content_original_not_found", "原附件不存在。", 404)
        return path

    def rebuild_index(self) -> int:
        """Recover portable Markdown into SQLite; never overwrite originals from stale rows."""
        recovered = []
        for path in self.root.glob("*/item.md"):
            try:
                self._directory(path.parent.name)
            except WebError:
                continue
            if path.resolve() != path:
                raise WebError("invalid_content_storage", "内容文件路径无效。", 500)
            try:
                raw = path.read_text(encoding="utf-8")
                if not raw.startswith("---\n"):
                    raise ValueError("invalid frontmatter")
                header, body = raw[4:].split("\n---\n", 1)
                item = {
                    key: json.loads(value.strip())
                    for key, value in (line.split(":", 1) for line in header.splitlines())
                }
                self._directory(item["id"])
                if path.parent.name != item["id"]:
                    continue
                prefix = f"\n# {item['title']}\n\n## Content\n\n"
                if not body.startswith(prefix):
                    raise ValueError("invalid content heading")
                section = body[len(prefix) :]
                content_length = item.pop("content_length", None)
                summary_length = item.pop("summary_length", None)
                if content_length is not None and summary_length is not None:
                    if type(content_length) is not int or type(summary_length) is not int:
                        raise ValueError("invalid section lengths")
                    content_body = section[:content_length]
                    remaining = section[content_length:]
                    separator = "\n\n## Summary\n\n"
                    if not remaining.startswith(separator):
                        raise ValueError("invalid section boundary")
                    summary = remaining[len(separator) :].removesuffix("\n")
                    if len(content_body) != content_length or len(summary) != summary_length:
                        raise ValueError("invalid section lengths")
                else:
                    content_body, summary = section.rsplit("\n\n## Summary\n\n", 1)
                    summary = summary.removesuffix("\n")
                item.update(content=content_body, summary=summary)
                for key, value in {
                    "folder_id": None,
                    "ai_processed": False,
                    "processing_status": "ready",
                    "processing_error": None,
                    "revision": 0,
                }.items():
                    item.setdefault(key, value)
                recovered.append(self._validate(item))
            except (ValueError, KeyError, TypeError, WebError):
                raise WebError(
                    "invalid_content_markdown",
                    "Markdown 元数据损坏，索引重建已停止；原件与现有索引均已保留。",
                    422,
                ) from None
        with self.store.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("DELETE FROM content_fts")
            db.execute("DELETE FROM document_tags")
            db.execute("DELETE FROM content_items")
            for item in recovered:
                columns = ",".join(_COLUMNS)
                placeholders = ",".join("?" for _ in _COLUMNS)
                db.execute(
                    f"INSERT INTO content_items({columns}) VALUES({placeholders})",
                    self._values(item),
                )
                self._index(db, item)
        return len(recovered)
