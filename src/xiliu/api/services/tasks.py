from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from xiliu.api.errors import WebError
from xiliu.api.store import AppStore, now


class TaskService:
    def __init__(self, store: AppStore):
        self.store = store
        with store.connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY, title TEXT NOT NULL,
                completed INTEGER NOT NULL DEFAULT 0, due_at TEXT,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            )""")

    @staticmethod
    def _validate(payload: dict[str, Any]) -> dict[str, Any]:
        if set(payload) - {"title", "completed", "due_at"}:
            raise WebError("invalid_task", "任务字段无效。")
        changes = dict(payload)
        if "title" in changes:
            title = changes["title"]
            if not isinstance(title, str) or not title.strip() or len(title) > 500:
                raise WebError("invalid_task", "请输入 1–500 字的任务名称。")
            changes["title"] = title.strip()
        if "completed" in changes and type(changes["completed"]) is not bool:
            raise WebError("invalid_task", "任务完成状态无效。")
        due = changes.get("due_at")
        if due is not None:
            try:
                if not isinstance(due, str):
                    raise ValueError
                changes["due_at"] = datetime.fromisoformat(due).isoformat()
            except ValueError:
                raise WebError("invalid_task", "任务日期必须为 ISO 格式。") from None
        return changes

    @staticmethod
    def _get(db: Any, task_id: str) -> dict[str, Any]:
        row = db.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        if row is None:
            raise WebError("task_not_found", "任务不存在。", 404)
        task = dict(row)
        task["completed"] = bool(task["completed"])
        return task

    def list(self) -> list[dict[str, Any]]:
        with self.store.connect() as db:
            ids = db.execute("SELECT id FROM tasks ORDER BY completed, created_at DESC, id")
            return [self._get(db, row["id"]) for row in ids]

    def create(self, payload: dict[str, Any]) -> dict[str, Any]:
        values = self._validate(payload)
        if "title" not in values:
            raise WebError("invalid_task", "请输入任务名称。")
        task_id, timestamp = str(uuid4()), now()
        with self.store.connect() as db:
            db.execute(
                "INSERT INTO tasks VALUES(?,?,?,?,?,?)",
                (
                    task_id,
                    values["title"],
                    values.get("completed", False),
                    values.get("due_at"),
                    timestamp,
                    timestamp,
                ),
            )
            return self._get(db, task_id)

    def update(self, task_id: str, changes: dict[str, Any]) -> dict[str, Any]:
        changes = self._validate(changes)
        with self.store.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            self._get(db, task_id)
            if changes:
                changes["updated_at"] = now()
                assignments = ", ".join(f"{key}=?" for key in changes)
                db.execute(
                    f"UPDATE tasks SET {assignments} WHERE id=?", (*changes.values(), task_id)
                )
            return self._get(db, task_id)

    def delete(self, task_id: str) -> None:
        with self.store.connect() as db:
            self._get(db, task_id)
            db.execute("DELETE FROM tasks WHERE id=?", (task_id,))
