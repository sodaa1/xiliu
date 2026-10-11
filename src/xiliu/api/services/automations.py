from __future__ import annotations

from pathlib import Path
from threading import RLock
from typing import Any
from uuid import uuid4

from pydantic import ValidationError

from xiliu.api.errors import WebError
from xiliu.api.services.model_settings import ModelSettingsService
from xiliu.automation.models import AutomationTask
from xiliu.automation.runner import AutomationRunner
from xiliu.automation.scheduler import AutomationScheduler
from xiliu.automation.store import AutomationStore
from xiliu.runtime import create_runtime


class AutomationService:
    def __init__(self, data_dir: Path, model_settings: ModelSettingsService):
        self.store = AutomationStore(data_dir)
        self.model_settings = model_settings
        self.runner = AutomationRunner(self.store, None, runtime_factory=self._runtime)
        self.scheduler = AutomationScheduler(self.store, self.runner)
        self.scheduler_active = False
        self.scheduler_error: str | None = None
        self._lock = RLock()
        self._stopping = False
        self._shutdown_requested = False
        self.app_services: Any = None

    def _runtime(self, _settings: Any, **kwargs: Any):
        # Resolve credentials only when a persisted task actually runs.
        settings = self.model_settings.runtime_settings().model_copy(
            update={"data_dir": self.store.data_dir}
        )
        return create_runtime(settings, app_services=self.app_services, **kwargs)

    def list(self) -> list[dict[str, Any]]:
        return [task.model_dump(mode="json") for task in self.store.list()]

    def _get(self, task_id: str) -> AutomationTask:
        task = self.store.get(task_id)
        if task is None:
            raise WebError("automation_not_found", "自动任务不存在。", 404)
        return task

    def create(self, payload: dict[str, Any]) -> dict[str, Any]:
        if set(payload) - {"name", "prompt", "hour", "minute", "timezone"}:
            raise WebError("invalid_automation", "自动任务字段无效。")
        try:
            task = AutomationTask(
                id="daily-" + uuid4().hex,
                name=payload.get("name", "").strip(),
                prompt=payload.get("prompt", "").strip(),
                trigger_type="cron",
                schedule={"hour": payload.get("hour"), "minute": payload.get("minute")},
                timezone=payload.get("timezone", "Asia/Shanghai"),
            )
        except (ValidationError, AttributeError):
            raise WebError(
                "invalid_automation", "请输入名称、提示词和有效的每日运行时间。"
            ) from None
        self.store.add(task)
        self._sync_owned()
        return task.model_dump(mode="json")

    def toggle(self, task_id: str, enabled: bool) -> dict[str, Any]:
        if type(enabled) is not bool:
            raise WebError("invalid_automation", "自动任务启停状态无效。")
        if not self.store.set_enabled(task_id, enabled):
            self._get(task_id)
        self._sync_owned()
        return self._get(task_id).model_dump(mode="json")

    def delete(self, task_id: str) -> None:
        if not self.store.remove(task_id):
            self._get(task_id)
        self._sync_owned()

    def runs(self, task_id: str) -> list[dict[str, Any]]:
        self._get(task_id)
        # Existing Store has no list-runs method; reuse its connection and database.
        with self.store._connect() as db:
            rows = db.execute(
                "SELECT run_id, automation_id, scheduled_for, status, started_at, finished_at "
                "FROM automation_runs WHERE automation_id=? ORDER BY started_at DESC LIMIT 30",
                (task_id,),
            ).fetchall()
        return [
            {
                **dict(row),
                "error": "自动任务运行失败，请检查模型或连接设置。"
                if row["status"] == "failed"
                else None,
                "result_preview": "运行成功，结果已保存。" if row["status"] == "success" else "",
            }
            for row in rows
        ]

    def start(self) -> None:
        with self._lock:
            if self._stopping:
                return
            self._shutdown_requested = False
            if self.scheduler_active:
                return
            try:
                self.scheduler.start()
            except Exception:
                # A live CLI scheduler remains the owner; CRUD still works.
                self.scheduler_error = "自动任务调度暂不可用。"
                if self.scheduler._started:
                    self.scheduler.shutdown()
                    self.scheduler = AutomationScheduler(self.store, self.runner)
                return
            self.scheduler_active = True
            self.scheduler_error = None

    def _sync_owned(self) -> None:
        if self.scheduler_active:
            self.sync()

    def sync(self) -> None:
        with self._lock:
            if self._stopping:
                # Keep the lease while shutdown drains running jobs; add no new work.
                if self.scheduler_active:
                    try:
                        self.store.acquire_owner(self.scheduler.instance_id)
                    except Exception:
                        self.scheduler_error = "自动任务停止期间续租暂不可用。"
                return
            if self._shutdown_requested:
                return
            if not self.scheduler_active:
                self.start()
                return
            try:
                if not self.store.acquire_owner(self.scheduler.instance_id):
                    self.scheduler.shutdown()
                    self.scheduler_active = False
                    self.scheduler = AutomationScheduler(self.store, self.runner)
                    return
                self.scheduler.sync_jobs()
                self.scheduler_error = None
            except Exception:
                # Preserve the heartbeat loop across a temporary SQLite/job failure.
                self.scheduler_error = "自动任务同步暂不可用。"

    def shutdown(self) -> None:
        with self._lock:
            self._shutdown_requested = True
            if self._stopping:
                return
            self._stopping = True
            scheduler = self.scheduler
        try:
            # Release the service lock so the lifespan heartbeat can renew ownership.
            scheduler.shutdown(wait=True)
        finally:
            with self._lock:
                self.scheduler_active = False
                self.scheduler = AutomationScheduler(self.store, self.runner)
                self._stopping = False
