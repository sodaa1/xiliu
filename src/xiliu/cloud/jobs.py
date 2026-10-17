from __future__ import annotations

import json
import logging
import sqlite3
import time

from apscheduler.schedulers.background import BackgroundScheduler

from xiliu.api.errors import WebError
from xiliu.automation.scheduler import AutomationScheduler
from xiliu.automation.store import AutomationStore

logger = logging.getLogger(__name__)


class CloudJobCoordinator:
    """A bounded scheduler routes all accounts' durable jobs through workspace leases."""

    def __init__(self, identity, registry):
        self.identity, self.registry = identity, registry
        self.scheduler = BackgroundScheduler(
            job_defaults={"max_instances": 1},
            executors={"default": {"type": "threadpool", "max_workers": 2}},
        )
        self.fingerprints: dict[str, str] = {}
        self.stopping = False

    def synchronize(self):
        jobs = {}
        for workspace in self.identity.workspaces():
            store = AutomationStore(self.registry.directory(workspace))
            for task in store.list(enabled_only=True):
                jobs[workspace + ":" + task.id] = (workspace, task)
        for identifier in self.fingerprints.keys() - jobs.keys():
            if self.scheduler.get_job(identifier):
                self.scheduler.remove_job(identifier)
        for identifier, (workspace, task) in jobs.items():
            fingerprint = json.dumps(task.model_dump(mode="json"), sort_keys=True)
            if self.fingerprints.get(identifier) != fingerprint:
                self.scheduler.add_job(
                    self.execute,
                    trigger=AutomationScheduler._trigger(task),
                    args=[workspace, task.id],
                    id=identifier,
                    replace_existing=True,
                    coalesce=True,
                    misfire_grace_time=60,
                )
        self.fingerprints = {
            key: json.dumps(task.model_dump(mode="json"), sort_keys=True)
            for key, (_, task) in jobs.items()
        }

    def execute(self, workspace: str, identifier: str):
        if self.stopping:
            return
        with self.registry.acquire(workspace) as state:
            task = state.automations.store.get(identifier)
            if task and task.enabled:
                state.automations.runner.run_once(
                    identifier, scheduled_for=AutomationScheduler._slot(task)
                )

    @staticmethod
    def pending(directory) -> bool:
        path = directory / "app.sqlite3"
        if not path.exists():
            return False
        # All names are fixed server-owned tables, never request input.
        checks = {
            "inbox_jobs": "state IN ('pending','running')",
            "inbox_archive_jobs": "status IN ('pending','running')",
            "rag_index_jobs": "state IN ('pending','partial','indexing') AND attempts<3",
        }
        with sqlite3.connect(path) as db:
            tables = {
                row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")
            }
            return any(
                db.execute(f"SELECT 1 FROM {name} WHERE {condition} LIMIT 1").fetchone()
                for name, condition in checks.items()
                if name in tables
            )

    def resume_pending(self):
        for workspace in self.identity.workspaces():
            if self.stopping:
                return
            try:
                directory = self.registry.directory(workspace)
                if not self.pending(directory):
                    continue
                with self.registry.acquire(workspace):
                    deadline = time.monotonic() + 2
                    while (
                        not self.stopping
                        and self.pending(directory)
                        and time.monotonic() < deadline
                    ):
                        time.sleep(0.05)
            except (WebError, OSError, ValueError, sqlite3.DatabaseError):
                logger.error("Cloud workspace background recovery unavailable")

    def _tick(self):
        if self.stopping:
            return
        try:
            self.synchronize()
            self.resume_pending()
        except Exception:
            # Never log provider responses, keys, prompts or arbitrary exception text.
            logger.error("Cloud background reconciliation failed")

    def start(self, *, paused=False):
        self.stopping = False
        self.scheduler.start(paused=True)
        try:
            self.synchronize()
            self.scheduler.add_job(
                self._tick,
                "interval",
                seconds=10,
                id="cloud:reconcile",
                coalesce=True,
                max_instances=1,
            )
            if not paused:
                self.scheduler.resume()
        except BaseException:
            self.scheduler.shutdown(wait=True)
            raise

    def shutdown(self):
        self.stopping = True
        if self.scheduler.running:
            self.scheduler.shutdown(wait=True)
