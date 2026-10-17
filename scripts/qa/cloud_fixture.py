"""Loopback-only disposable browser fixture. Never imported by the production entry point."""

import tempfile
import time
from pathlib import Path

import uvicorn
from cryptography.fernet import Fernet

import xiliu.cloud.workspaces as workspaces
from xiliu.cloud.app import create_cloud_app
from xiliu.cloud.budget import active_budget
from xiliu.cloud.config import CloudConfig
from xiliu.events import FinalEvent, ProgressEvent
from xiliu.execution.cancellation import check_cancelled


class MockRuntime:
    def stream_session(self, task, session_id, **kwargs):
        budget = active_budget.get()
        assert budget is not None
        budget.before_request()
        if "connection-fail" in task:
            raise ConnectionError("disposable fixture connection failure")
        budget.started()
        yield ProgressEvent(stage="chat", message="模拟生成中")
        for _ in range(50 if "slow-response" in task else 1):
            time.sleep(0.1)
            check_cancelled()
        yield FinalEvent(text="模拟模型回复：" + task, session_id=session_id)

    def close(self):
        pass


original = workspaces.initialize_services


def initialize(state, **kwargs):
    original(state, **kwargs)
    state.chat.runtime_factory = lambda *_args, **_kwargs: MockRuntime()


if __name__ == "__main__":
    workspaces.initialize_services = initialize
    with tempfile.TemporaryDirectory(prefix="xiliu-browser-qa-") as directory:
        config = CloudConfig(
            data_dir=Path(directory),
            public_origin="http://127.0.0.1:8767",
            secure_cookies=False,
            master_key=Fernet.generate_key().decode(),
            signup_limit=100,
            login_limit=100,
            trial_api_key="disposable-public-key",
            trial_model="fixture-model",
        )
        app = create_cloud_app(
            config, static_dir=Path(__file__).resolve().parents[2] / "web/dist-cloud"
        )
        uvicorn.run(app, host="127.0.0.1", port=8767, log_level="warning")
