from threading import Event, Thread
from types import SimpleNamespace

import pytest
from cryptography.fernet import Fernet

from xiliu.api.errors import WebError
from xiliu.cloud.config import CloudConfig
from xiliu.cloud.identity import IdentityStore
from xiliu.cloud.jobs import CloudJobCoordinator
from xiliu.cloud.workspaces import WorkspaceRegistry

PASSWORD = "correct horse battery staple"


def components(tmp_path):
    cfg = CloudConfig(
        data_dir=tmp_path,
        public_origin="https://cloud.test",
        master_key=Fernet.generate_key().decode(),
    )
    identity = IdentityStore(tmp_path)
    first = identity.register("alice", PASSWORD)
    second = identity.register("bobby", PASSWORD)
    return cfg, identity, first, second


def test_partial_service_initialization_is_cleaned_without_masking_the_error(tmp_path, monkeypatch):
    cfg, _, a, _ = components(tmp_path)
    registry = WorkspaceRegistry(cfg)
    closed = []

    def broken(state, **_kwargs):
        state.inbox = SimpleNamespace(shutdown=lambda: closed.append(True))
        raise WebError("workspace_failed", "工作区无法初始化。", 503)

    monkeypatch.setattr("xiliu.cloud.workspaces.initialize_services", broken)
    with pytest.raises(WebError) as error, registry.acquire(a["workspace_id"]):
        pass
    assert error.value.code == "workspace_failed" and closed == [True]
    assert not registry.entries


def test_registry_never_evicts_leased_workspace_and_closes_after_release(tmp_path):
    cfg, _, a, b = components(tmp_path)
    registry = WorkspaceRegistry(cfg, capacity=1)
    with registry.acquire(a["workspace_id"]) as state:
        with pytest.raises(WebError) as error, registry.acquire(b["workspace_id"]):
            pass
        assert error.value.status == 503
        finished = Event()
        thread = Thread(target=lambda: (registry.close(), finished.set()))
        thread.start()
        assert not finished.wait(0.05)
        assert state.store.path.exists()
    assert finished.wait(3)
    thread.join()


def test_coordinator_restores_offline_accounts_and_uses_owned_workspace(tmp_path):
    cfg, identity, a, b = components(tmp_path)
    registry = WorkspaceRegistry(cfg)
    identifiers = []
    for account in (a, b):
        with registry.acquire(account["workspace_id"]) as state:
            task = state.automations.create(
                {
                    "name": account["username"],
                    "prompt": "test",
                    "hour": 12,
                    "minute": 0,
                    "timezone": "Asia/Shanghai",
                }
            )
            identifiers.append(task["id"])
    registry.close()
    restored = WorkspaceRegistry(cfg)
    coordinator = CloudJobCoordinator(identity, restored)
    coordinator.start(paused=True)
    try:
        for account, identifier in zip((a, b), identifiers, strict=True):
            assert coordinator.scheduler.get_job(account["workspace_id"] + ":" + identifier)
            with restored.acquire(account["workspace_id"]) as state:
                calls = []
                state.automations.runner.run_once = (
                    lambda task_id, _calls=calls, _state=state, **kwargs: _calls.append(
                        (_state.workspace_id, task_id)
                    )
                )
                coordinator.execute(account["workspace_id"], identifier)
                assert calls == [(account["workspace_id"], identifier)]
    finally:
        coordinator.shutdown()
        restored.close()


def test_pending_index_recovers_without_login_and_one_broken_account_does_not_block_another(
    tmp_path,
):
    cfg, identity, a, b = components(tmp_path)
    registry = WorkspaceRegistry(cfg)
    for account in (a, b):
        with registry.acquire(account["workspace_id"]) as state:
            state.retrieval.worker.shutdown()
            state.content.create(
                {
                    "type": "note",
                    "status": "knowledge",
                    "title": "offline",
                    "content": "PendingCloudRecoveryMarker",
                }
            )
    registry.close()
    (registry.directory(a["workspace_id"]) / "model-settings.enc").write_text(
        "corrupt encrypted configuration", encoding="utf-8"
    )
    restored = WorkspaceRegistry(cfg)
    coordinator = CloudJobCoordinator(identity, restored)
    try:
        coordinator.resume_pending()
        assert not coordinator.pending(restored.directory(b["workspace_id"]))
    finally:
        restored.close()
