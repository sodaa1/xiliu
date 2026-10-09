from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from xiliu.api.errors import WebError


def now() -> str:
    return datetime.now(UTC).isoformat()


class AppStore:
    """Web history only; Runtime checkpoints and TUI sessions remain separate."""

    def __init__(self, data_dir: Path):
        self.path = data_dir / "app.sqlite3"
        data_dir.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY, title TEXT NOT NULL, model_override TEXT,
                    context_cutoff_seq INTEGER NOT NULL DEFAULT 0,
                    compressed_through_seq INTEGER NOT NULL DEFAULT 0,
                    context_summary TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL, updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY, conversation_id TEXT NOT NULL,
                    seq INTEGER NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('user','assistant','event')),
                    content TEXT NOT NULL, route TEXT, created_at TEXT NOT NULL,
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    UNIQUE(conversation_id, seq),
                    FOREIGN KEY(conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
                );
            """)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        db = sqlite3.connect(self.path, timeout=30)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA busy_timeout=30000")
        db.execute("PRAGMA foreign_keys=ON")
        try:
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def _get(db: sqlite3.Connection, cid: str) -> dict[str, Any]:
        row = db.execute("SELECT * FROM conversations WHERE id=?", (cid,)).fetchone()
        if row is None:
            raise WebError("conversation_not_found", "对话不存在。", 404)
        return dict(row)

    def create(self) -> dict[str, Any]:
        cid, timestamp = str(uuid4()), now()
        with self.connect() as db:
            db.execute(
                "INSERT INTO conversations(id,title,created_at,updated_at) VALUES(?,?,?,?)",
                (cid, "New Chat", timestamp, timestamp),
            )
            return self._get(db, cid)

    def list(self) -> list[dict[str, Any]]:
        with self.connect() as db:
            return [
                dict(row)
                for row in db.execute("SELECT * FROM conversations ORDER BY updated_at DESC, id")
            ]

    def get(self, cid: str) -> dict[str, Any]:
        with self.connect() as db:
            return self._get(db, cid)

    def update(self, cid: str, **changes: Any) -> dict[str, Any]:
        if set(changes) - {"title", "model_override"}:
            raise ValueError("unsupported conversation update")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            self._get(db, cid)
            if changes:
                keys = [*changes, "updated_at"]
                assignments = ", ".join(f"{key}=?" for key in keys)
                db.execute(
                    f"UPDATE conversations SET {assignments} WHERE id=?",
                    (*changes.values(), now(), cid),
                )
            return self._get(db, cid)

    def delete(self, cid: str) -> None:
        with self.connect() as db:
            self._get(db, cid)
            db.execute("DELETE FROM conversations WHERE id=?", (cid,))

    def messages(self, cid: str) -> list[dict[str, Any]]:
        with self.connect() as db:
            self._get(db, cid)
            return [
                dict(row)
                for row in db.execute(
                    "SELECT * FROM messages WHERE conversation_id=? ORDER BY seq", (cid,)
                )
            ]

    def append_message(
        self,
        cid: str,
        role: str,
        content: str,
        *,
        route: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if role not in {"user", "assistant", "event"}:
            raise ValueError("invalid message role")
        mid, timestamp = str(uuid4()), now()
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            self._get(db, cid)
            seq = db.execute(
                "SELECT COALESCE(MAX(seq),0)+1 FROM messages WHERE conversation_id=?", (cid,)
            ).fetchone()[0]
            db.execute(
                "INSERT INTO messages VALUES(?,?,?,?,?,?,?,?)",
                (
                    mid,
                    cid,
                    seq,
                    role,
                    content,
                    route,
                    timestamp,
                    json.dumps(metadata or {}, ensure_ascii=False),
                ),
            )
            db.execute("UPDATE conversations SET updated_at=? WHERE id=?", (timestamp, cid))
            return dict(db.execute("SELECT * FROM messages WHERE id=?", (mid,)).fetchone())

    def clear_context(self, cid: str) -> None:
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            self._get(db, cid)
            seq = db.execute(
                "SELECT COALESCE(MAX(seq),0) FROM messages WHERE conversation_id=?", (cid,)
            ).fetchone()[0]
            db.execute(
                """UPDATE conversations SET context_cutoff_seq=?,
                        compressed_through_seq=?, context_summary='', updated_at=? WHERE id=?""",
                (seq, seq, now(), cid),
            )

    def clear_messages(self, cid: str) -> None:
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            self._get(db, cid)
            db.execute("DELETE FROM messages WHERE conversation_id=?", (cid,))
            db.execute(
                """UPDATE conversations SET context_cutoff_seq=0,
                        compressed_through_seq=0, context_summary='', updated_at=? WHERE id=?""",
                (now(), cid),
            )

    def save_summary(self, cid: str, summary: str, through_seq: int) -> None:
        with self.connect() as db:
            self._get(db, cid)
            db.execute(
                """UPDATE conversations SET context_summary=?, compressed_through_seq=?,
                        updated_at=? WHERE id=?""",
                (summary, through_seq, now(), cid),
            )
