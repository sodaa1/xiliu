from __future__ import annotations

import json
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

            columns = {row["name"] for row in db.execute("PRAGMA table_info(tasks)")}
            if "scope" not in columns:
                db.execute("ALTER TABLE tasks ADD COLUMN scope TEXT NOT NULL DEFAULT 'day'")
            if "parent_id" not in columns:
                db.execute("ALTER TABLE tasks ADD COLUMN parent_id TEXT")
            metadata_columns = {
                "status": "TEXT NOT NULL DEFAULT 'not_started'",
                "completed_at": "TEXT",
                "starts_at": "TEXT",
                "description": "TEXT NOT NULL DEFAULT ''",
                "category": "TEXT NOT NULL DEFAULT ''",
                "priority": "TEXT NOT NULL DEFAULT 'normal'",
                "tags": "TEXT NOT NULL DEFAULT '[]'",
                "reminder_minutes": "INTEGER",
            }
            for name, definition in metadata_columns.items():
                if name not in columns:
                    db.execute(f"ALTER TABLE tasks ADD COLUMN {name} {definition}")
            if "status" not in columns:
                db.execute("UPDATE tasks SET status='completed' WHERE completed=1")

    @staticmethod
    def _validate(payload: dict[str, Any]) -> dict[str, Any]:
        if set(payload) - {
            "title",
            "completed",
            "due_at",
            "scope",
            "parent_id",
            "status",
            "completed_at",
            "starts_at",
            "description",
            "category",
            "priority",
            "tags",
            "reminder_minutes",
        }:
            raise WebError("invalid_task", "任务字段无效。")
        changes = dict(payload)
        if "title" in changes:
            title = changes["title"]
            if not isinstance(title, str) or not title.strip() or len(title) > 500:
                raise WebError("invalid_task", "请输入 1–500 字的任务名称。")
            changes["title"] = title.strip()
        if "completed" in changes and type(changes["completed"]) is not bool:
            raise WebError("invalid_task", "任务完成状态无效。")
        if "status" in changes and changes["status"] not in (
            "not_started",
            "in_progress",
            "completed",
        ):
            raise WebError("invalid_task", "任务状态无效。")
        if "priority" in changes and changes["priority"] not in (
            "normal",
            "important",
            "urgent",
            "low",
        ):
            raise WebError("invalid_task", "任务优先级无效。")
        for field, limit in (("description", 500), ("category", 32)):
            if field in changes:
                value = changes[field]
                if not isinstance(value, str) or len(value) > limit:
                    raise WebError("invalid_task", "任务描述或分类无效。")
                changes[field] = value.strip()
        if "tags" in changes:
            tags = changes["tags"]
            if not isinstance(tags, list) or any(
                not isinstance(tag, str) or not tag.strip() or len(tag.strip()) > 32 for tag in tags
            ):
                raise WebError("invalid_task", "任务标签必须为 1–32 字的文本。")
            changes["tags"] = list(dict.fromkeys(tag.strip() for tag in tags))
            if len(changes["tags"]) > 10:
                raise WebError("invalid_task", "任务标签最多 10 个。")
        reminder = changes.get("reminder_minutes")
        if reminder is not None and (
            type(reminder) is not int or reminder not in (0, 5, 15, 30, 60, 1440)
        ):
            raise WebError("invalid_task", "任务提醒时间无效。")
        if "scope" in changes and changes["scope"] not in ("goal", "week", "day"):
            raise WebError("invalid_task", "计划类型无效。")
        if (
            "parent_id" in changes
            and changes["parent_id"] is not None
            and (not isinstance(changes["parent_id"], str) or not changes["parent_id"])
        ):
            raise WebError("invalid_task", "上级计划无效。")
        for field in ("due_at", "starts_at", "completed_at"):
            value = changes.get(field)
            if value is not None:
                try:
                    if not isinstance(value, str):
                        raise ValueError
                    changes[field] = datetime.fromisoformat(value).isoformat()
                except ValueError:
                    raise WebError("invalid_task", "任务日期必须为 ISO 格式。") from None
        return changes

    @staticmethod
    def _validate_state(changes: dict[str, Any], current: dict[str, Any]) -> None:
        if (
            "status" in changes
            and "completed" in changes
            and (changes["status"] == "completed") != changes["completed"]
        ):
            raise WebError("invalid_task", "任务状态与完成标记冲突。")
        if "status" in changes:
            changes["completed"] = changes["status"] == "completed"
        elif "completed" in changes:
            changes["status"] = "completed" if changes["completed"] else "not_started"
        state = {**current, **changes}
        completed = state.get("status", "not_started") == "completed"
        if not completed:
            if changes.get("completed_at") is not None:
                raise WebError("invalid_task", "未完成任务不能设置完成时间。")
            if current.get("completed_at") is not None:
                changes["completed_at"] = None
        elif not current.get("completed", False) and changes.get("completed_at") is None:
            changes["completed_at"] = now()
        starts, due = state.get("starts_at"), state.get("due_at")
        if starts is not None and due is not None:
            start_time, due_time = datetime.fromisoformat(starts), datetime.fromisoformat(due)
            # A floating local endpoint shares the explicit endpoint's timezone.
            if start_time.tzinfo is None and due_time.tzinfo is not None:
                start_time = start_time.replace(tzinfo=due_time.tzinfo)
            elif due_time.tzinfo is None and start_time.tzinfo is not None:
                due_time = due_time.replace(tzinfo=start_time.tzinfo)
            if start_time > due_time:
                raise WebError("invalid_task", "任务开始时间不能晚于结束时间。")
        if state.get("reminder_minutes") is not None and starts is None and due is None:
            raise WebError("invalid_task", "请先设置任务日期，再添加提醒。")

    @staticmethod
    def _get(db: Any, task_id: str) -> dict[str, Any]:
        row = db.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        if row is None:
            raise WebError("task_not_found", "任务不存在。", 404)
        task = dict(row)
        task["completed"] = bool(task["completed"])
        task["tags"] = json.loads(task["tags"])
        return task

    @classmethod
    def _validate_parent(cls, db: Any, task_id: str, scope: str, parent_id: str | None) -> None:
        rank = {"goal": 0, "week": 1, "day": 2}
        if parent_id:
            parent = cls._get(db, parent_id)
            if parent_id == task_id or rank[parent["scope"]] >= rank[scope]:
                raise WebError("invalid_task", "上级计划必须是更长期的目标或计划。")
        for child in db.execute("SELECT scope FROM tasks WHERE parent_id=?", (task_id,)):
            if rank[child["scope"]] <= rank[scope]:
                raise WebError("invalid_task", "请先调整子计划，再修改计划类型。")

    def list(self) -> list[dict[str, Any]]:
        with self.store.connect() as db:
            ids = db.execute("SELECT id FROM tasks ORDER BY completed, created_at DESC, id")
            return [self._get(db, row["id"]) for row in ids]

    def create(self, payload: dict[str, Any]) -> dict[str, Any]:
        values = self._validate(payload)
        if "title" not in values:
            raise WebError("invalid_task", "请输入任务名称。")
        self._validate_state(values, {})
        task_id, timestamp = str(uuid4()), now()
        with self.store.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            self._validate_parent(db, task_id, values.get("scope", "day"), values.get("parent_id"))
            db.execute(
                "INSERT INTO "
                "tasks(id,title,completed,due_at,created_at,updated_at,scope,parent_id,"
                "status,completed_at,starts_at,description,category,priority,"
                "tags,reminder_minutes) "
                "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    task_id,
                    values["title"],
                    values.get("completed", False),
                    values.get("due_at"),
                    timestamp,
                    timestamp,
                    values.get("scope", "day"),
                    values.get("parent_id"),
                    values.get("status", "not_started"),
                    values.get("completed_at"),
                    values.get("starts_at"),
                    values.get("description", ""),
                    values.get("category", ""),
                    values.get("priority", "normal"),
                    json.dumps(values.get("tags", []), ensure_ascii=False),
                    values.get("reminder_minutes"),
                ),
            )
            return self._get(db, task_id)

    def update(self, task_id: str, changes: dict[str, Any]) -> dict[str, Any]:
        changes = self._validate(changes)
        with self.store.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            current = self._get(db, task_id)
            self._validate_state(changes, current)
            self._validate_parent(
                db,
                task_id,
                changes.get("scope", current["scope"]),
                changes.get("parent_id", current["parent_id"]),
            )
            if changes:
                if "tags" in changes:
                    changes["tags"] = json.dumps(changes["tags"], ensure_ascii=False)
                changes["updated_at"] = now()
                assignments = ", ".join(f"{key}=?" for key in changes)
                db.execute(
                    f"UPDATE tasks SET {assignments} WHERE id=?", (*changes.values(), task_id)
                )
            return self._get(db, task_id)

    def delete(self, task_id: str) -> None:
        with self.store.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            self._get(db, task_id)
            db.execute(
                "UPDATE tasks SET parent_id=NULL, updated_at=? WHERE parent_id=?", (now(), task_id)
            )
            db.execute("DELETE FROM tasks WHERE id=?", (task_id,))
