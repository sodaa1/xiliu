from __future__ import annotations

import time
from collections.abc import Callable
from contextvars import ContextVar
from dataclasses import dataclass, field
from threading import Lock

from xiliu.api.errors import WebError


@dataclass
class CloudCallBudget:
    on_dispatch: Callable[[], None] = lambda: None
    on_start: Callable[[], None] = lambda: None
    maximum_calls: int = 8
    seconds: int = 60
    calls: int = 0
    has_started: bool = False
    began: float = field(default_factory=time.monotonic)
    _lock: Lock = field(default_factory=Lock, repr=False)

    def before_request(self):
        with self._lock:
            if self.calls >= self.maximum_calls or time.monotonic() - self.began >= self.seconds:
                raise WebError("model_budget", "本次模型调用已达上限，请缩小任务后重试。", 429)
            self.calls += 1
            self.on_dispatch()

    def started(self):
        with self._lock:
            if not self.has_started:
                self.on_start()
                self.has_started = True


active_budget: ContextVar[CloudCallBudget | None] = ContextVar("cloud_call_budget", default=None)
