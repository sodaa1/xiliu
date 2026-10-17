from __future__ import annotations

import re
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from threading import Condition
from types import SimpleNamespace

from xiliu.api.app import initialize_services
from xiliu.api.errors import WebError
from xiliu.cloud.config import CloudConfig
from xiliu.cloud.model_settings import CloudModelSettings


@dataclass
class WorkspaceEntry:
    state: SimpleNamespace
    references: int = 0
    touched: float = 0


class WorkspaceRegistry:
    def __init__(self, config: CloudConfig, *, capacity: int = 8):
        self.config, self.capacity = config, capacity
        self.root = config.data_dir / "workspaces"
        self.root.mkdir(parents=True, exist_ok=True)
        self.entries: dict[str, WorkspaceEntry] = {}
        self.condition = Condition()
        self.closed = False

    def directory(self, workspace_id: str):
        if not re.fullmatch(r"[a-f0-9]{32}", workspace_id):
            raise WebError("invalid_workspace", "无效工作区。", 403)
        path = (self.root / workspace_id).resolve()
        if not path.is_relative_to(self.root.resolve()):
            raise WebError("invalid_workspace", "无效工作区。", 403)
        return path

    @staticmethod
    def _close(state):
        automations = getattr(state, "automations", None)
        inbox = getattr(state, "inbox", None)
        worker = getattr(getattr(state, "retrieval", None), "worker", None)
        try:
            if automations is not None:
                automations.shutdown()
        finally:
            try:
                if inbox is not None:
                    inbox.shutdown()
            finally:
                if worker is not None:
                    worker.shutdown()

    @contextmanager
    def acquire(self, workspace_id: str) -> Iterator[SimpleNamespace]:
        with self.condition:
            if self.closed:
                raise WebError("workspace_busy", "工作区正在关闭，请稍后再试。", 503)
            entry = self.entries.get(workspace_id)
            if entry is None:
                if len(self.entries) >= self.capacity:
                    idle = [
                        (key, item) for key, item in self.entries.items() if not item.references
                    ]
                    if not idle:
                        raise WebError("workspace_busy", "工作区繁忙，请稍后再试。", 503)
                    identifier, previous = min(idle, key=lambda pair: pair[1].touched)
                    self._close(previous.state)
                    del self.entries[identifier]
                directory = self.directory(workspace_id)
                models = CloudModelSettings(directory, self.config.master_key, workspace_id)
                state = SimpleNamespace(workspace_id=workspace_id)
                try:
                    initialize_services(state, data_dir=directory, model_settings=models)
                    state.retrieval.worker.start()
                    state.inbox.start()
                except BaseException:
                    if hasattr(state, "inbox"):
                        self._close(state)
                    raise
                entry = WorkspaceEntry(state)
                self.entries[workspace_id] = entry
            entry.references += 1
        try:
            yield entry.state
        finally:
            with self.condition:
                entry.references -= 1
                entry.touched = time.monotonic()
                self.condition.notify_all()

    def close(self):
        with self.condition:
            self.closed = True
            self.condition.wait_for(lambda: all(not e.references for e in self.entries.values()))
            for entry in self.entries.values():
                self._close(entry.state)
            self.entries.clear()
