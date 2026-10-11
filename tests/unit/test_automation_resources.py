from xiliu.automation.models import AutomationTask
from xiliu.automation.runner import AutomationRunner
from xiliu.automation.store import AutomationStore
from xiliu.events import FinalEvent, VerifierEvent


def test_automation_runtime_releases_resources_after_success(tmp_path):
    store = AutomationStore(tmp_path)
    store.add(
        AutomationTask(
            id="daily-check",
            name="Daily",
            prompt="Check",
            trigger_type="cron",
            schedule={"hour": 9, "minute": 0},
        )
    )
    closed = []

    class Runtime:
        last_trace_id = "trace"

        def stream(self, task, session_id):
            yield VerifierEvent(passed=True, reason="Verified", attempt=1)
            yield FinalEvent(text="Done", session_id=session_id)

        def close(self):
            closed.append(True)

    result = AutomationRunner(
        store, None, runtime_factory=lambda *args, **kwargs: Runtime()
    ).run_once("daily-check")
    assert result.status == "success"
    assert closed == [True]
