from datetime import UTC, datetime, timedelta
from threading import Event
from types import SimpleNamespace

import pytest
from apscheduler.events import EVENT_JOB_REMOVED

from xiliu.automation.models import AutomationTask
from xiliu.automation.scheduler import AutomationScheduler
from xiliu.automation.store import AutomationStore


@pytest.mark.parametrize("operation", ["disable", "delete"])
def test_finished_date_task_does_not_block_new_jobs(tmp_path, operation):
    store = AutomationStore(tmp_path)
    task = AutomationTask(
        id="one-shot",
        name="One shot",
        prompt="Check",
        trigger_type="date",
        schedule={"at": (datetime.now(UTC) - timedelta(seconds=1)).isoformat()},
    )
    store.add(task)
    scheduler = AutomationScheduler(store, SimpleNamespace(run_once=lambda *args, **kwargs: None))
    removed = Event()
    scheduler._scheduler.add_listener(
        lambda event: removed.set() if event.job_id == task.id else None,
        EVENT_JOB_REMOVED,
    )
    scheduler.start()
    try:
        assert removed.wait(5), "The one-shot job was not removed after execution"
        assert scheduler.get_job(task.id) is None
        if operation == "disable":
            store.set_enabled(task.id, False)
        else:
            store.remove(task.id)
        store.add(
            AutomationTask(
                id="new-daily",
                name="New daily",
                prompt="Check",
                trigger_type="cron",
                schedule={"hour": 9, "minute": 0},
            )
        )

        scheduler.sync_jobs()
        scheduler.sync_jobs()

        assert scheduler.get_job("new-daily") is not None
        assert scheduler.get_job(task.id) is None
    finally:
        scheduler.shutdown(wait=True)
