from __future__ import annotations

import json
import sqlite3
from typing import Any
from uuid import uuid4

from xiliu.api.errors import WebError
from xiliu.api.services.content import _COLUMNS, ContentService, _invalid, _render, _text
from xiliu.api.store import now
from xiliu.tools.workspace import atomic_write_utf8


class KnowledgeService:
    def __init__(self, content: ContentService):
        self.content = content
        self.store = content.store
        self.snapshot = content.root.parent / "knowledge-folders.json"
        with self.store.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS knowledge_folders(id TEXT PRIMARY KEY,name TEXT NOT NULL,
                    summary TEXT NOT NULL,priority INTEGER NOT NULL,
                    created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS folder_tags(folder_id TEXT NOT NULL,tag_id TEXT NOT NULL,
                    PRIMARY KEY(folder_id,tag_id));
            """)
            if (
                not db.execute("SELECT 1 FROM knowledge_folders LIMIT 1").fetchone()
                and self.snapshot.exists()
            ):
                for folder in json.loads(self.snapshot.read_text(encoding="utf-8")):
                    self._save(db, folder)
        content.knowledge = self

    def _save(self, db: sqlite3.Connection, folder: dict[str, Any]) -> None:
        db.execute(
            "INSERT OR REPLACE INTO knowledge_folders VALUES(?,?,?,?,?,?)",
            tuple(
                folder[key]
                for key in ("id", "name", "summary", "priority", "created_at", "updated_at")
            ),
        )
        db.execute("DELETE FROM folder_tags WHERE folder_id=?", (folder["id"],))
        for tag in folder["tags"]:
            db.execute(
                "INSERT OR IGNORE INTO tags VALUES(?,?,?)", (str(uuid4()), tag, tag.casefold())
            )
            tag_id = db.execute(
                "SELECT id FROM tags WHERE normalized_name=?", (tag.casefold(),)
            ).fetchone()[0]
            db.execute("INSERT OR IGNORE INTO folder_tags VALUES(?,?)", (folder["id"], tag_id))

    def _folders(self, db: sqlite3.Connection) -> list[dict[str, Any]]:
        result = []
        for row in db.execute(
            "SELECT * FROM knowledge_folders ORDER BY priority DESC,id"
        ).fetchall():
            folder = dict(row)
            folder["tags"] = [
                r[0]
                for r in db.execute(
                    "SELECT t.name FROM tags t JOIN folder_tags f ON t.id=f.tag_id "
                    "WHERE f.folder_id=? ORDER BY t.normalized_name",
                    (folder["id"],),
                )
            ]
            folder["item_count"] = db.execute(
                "SELECT count(*) FROM content_items WHERE status='knowledge' AND folder_id=?",
                (folder["id"],),
            ).fetchone()[0]
            result.append(folder)
        return result

    def list_folders(self) -> list[dict[str, Any]]:
        with self.store.connect() as db:
            return self._folders(db)

    def get_folder(self, folder_id: str, *, db: sqlite3.Connection | None = None) -> dict[str, Any]:
        if db is None:
            with self.store.connect() as connection:
                return self.get_folder(folder_id, db=connection)
        for folder in self._folders(db):
            if folder["id"] == folder_id:
                return folder
        raise WebError("folder_not_found", "文件夹不存在。", 404)

    def _mutate(self, operation):
        before = self.snapshot.read_text(encoding="utf-8") if self.snapshot.exists() else None

        def restore():
            if before is None:
                self.snapshot.unlink(missing_ok=True)
            else:
                atomic_write_utf8(self.snapshot, before)

        with self.content._transaction(restore) as db:
            result = operation(db)
            atomic_write_utf8(
                self.snapshot, json.dumps(self._folders(db), ensure_ascii=False, indent=2)
            )
            return result

    @staticmethod
    def _validate(payload: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, dict) or set(payload) - {"name", "summary", "tags", "priority"}:
            raise _invalid("存在不支持的文件夹字段。")
        name = _text(payload.get("name", ""), "name", 200, nonblank=True).strip()
        summary = _text(payload.get("summary", ""), "summary", 2000).strip()
        tags = payload.get("tags", [])
        if not isinstance(tags, list) or len(tags) > 50:
            raise _invalid("文件夹最多包含 50 个标签。")
        unique = {}
        for value in tags:
            tag = _text(value, "tag", 100, nonblank=True).strip()
            unique.setdefault(tag.casefold(), tag)
        priority = payload.get("priority", 0)
        if type(priority) is not int or not -10000 <= priority <= 10000:
            raise _invalid("priority 必须是 -10000 到 10000 的整数。")
        return {
            "name": name,
            "summary": summary,
            "tags": list(unique.values()),
            "priority": priority,
        }

    def create_folder(self, payload: dict[str, Any]) -> dict[str, Any]:
        timestamp = now()
        folder = {
            **self._validate(payload),
            "id": str(uuid4()),
            "created_at": timestamp,
            "updated_at": timestamp,
        }

        def operation(db):
            self._save(db, folder)
            return self.get_folder(folder["id"], db=db)

        return self._mutate(operation)

    def update_folder(self, folder_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, dict) or set(payload) - {"name", "summary", "tags", "priority"}:
            raise _invalid("存在不支持的文件夹字段。")

        def operation(db):
            previous = self.get_folder(folder_id, db=db)
            values = {key: previous[key] for key in ("name", "summary", "tags", "priority")}
            folder = {**previous, **self._validate({**values, **payload}), "updated_at": now()}
            self._save(db, folder)
            return self.get_folder(folder_id, db=db)

        return self._mutate(operation)

    def delete_folder(self, folder_id: str) -> None:
        snapshots = {}
        before = self.snapshot.read_text(encoding="utf-8") if self.snapshot.exists() else None

        def restore():
            for path, source in snapshots.items():
                atomic_write_utf8(path, source)
            if before is None:
                self.snapshot.unlink(missing_ok=True)
            else:
                atomic_write_utf8(self.snapshot, before)

        with self.content._transaction(restore) as db:
            self.get_folder(folder_id, db=db)
            ids = [
                row[0]
                for row in db.execute(
                    "SELECT id FROM content_items WHERE folder_id=?", (folder_id,)
                )
            ]
            for item_id in ids:
                item = self.content._get(db, item_id)
                path = self.content._directory(item_id) / "item.md"
                snapshots[path] = path.read_text(encoding="utf-8")
                item.update(folder_id=None, revision=item["revision"] + 1, updated_at=now())
                atomic_write_utf8(path, _render(item))
                assignments = ",".join(f"{column}=?" for column in _COLUMNS[1:])
                db.execute(
                    f"UPDATE content_items SET {assignments} WHERE id=?",
                    (*self.content._values(item)[1:], item_id),
                )
            db.execute("DELETE FROM folder_tags WHERE folder_id=?", (folder_id,))
            db.execute("DELETE FROM knowledge_folders WHERE id=?", (folder_id,))
            atomic_write_utf8(
                self.snapshot, json.dumps(self._folders(db), ensure_ascii=False, indent=2)
            )

    def folder_items(
        self, folder_id: str | None, q: str = "", tag: str = ""
    ) -> list[dict[str, Any]]:
        if folder_id not in (None, "unclassified"):
            self.get_folder(folder_id)
        target = None if folder_id == "unclassified" else folder_id
        return [
            item for item in self.content.list("knowledge", q, tag) if item["folder_id"] == target
        ]

    def classify(self, tags: list[str], *, db: sqlite3.Connection | None = None) -> str | None:
        if db is None:
            with self.store.connect() as connection:
                return self.classify(tags, db=connection)
        normalized = {tag.strip().casefold() for tag in tags if isinstance(tag, str)}
        scored = [
            (len(normalized & {tag.casefold() for tag in f["tags"]}), f["priority"], f["id"])
            for f in self._folders(db)
        ]
        scored.sort(key=lambda entry: (-entry[0], -entry[1], entry[2]))
        return scored[0][2] if scored and scored[0][0] > 0 else None

    def fallback_tags(self, text: str) -> list[str]:
        lowered = text.casefold()
        unique = {
            tag.casefold(): tag
            for folder in self.list_folders()
            for tag in folder["tags"]
            if tag.casefold() in lowered
        }
        return list(unique.values())[:50]
