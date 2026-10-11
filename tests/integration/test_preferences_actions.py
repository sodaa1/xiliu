"""Preference persistence, migration and compare-and-set safety contracts."""

import importlib
import importlib.util
import json
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from xiliu.api.errors import WebError
from xiliu.api.store import AppStore


def dispatcher(tmp_path):
    from xiliu.app.dispatch import AppDispatcher
    from xiliu.execution.gateway import RunContext
    from xiliu.policy.engine import PolicyEngine

    prefs = service(tmp_path)
    services = SimpleNamespace(store=prefs.store, preferences=prefs)
    context = RunContext(
        "prefs", "prefs-session", tmp_path, policy_engine=PolicyEngine(tmp_path / "policy.json")
    )
    return AppDispatcher(services, context)


def service(tmp_path):
    name = "xiliu.api.services.preferences"
    assert importlib.util.find_spec(name) is not None, "shared PreferencesService is missing"
    return importlib.import_module(name).PreferencesService(AppStore(tmp_path))


def test_partial_updates_persist_across_restart_without_resetting_profile(tmp_path):
    prefs = service(tmp_path)
    first = prefs.update({"displayName": "溪流", "email": "me@example.com", "theme": "dark"})
    second = prefs.update({"density": "compact"}, expected_revision=first["revision"])
    reopened = service(tmp_path).get()
    assert reopened == second
    assert reopened["preferences"]["displayName"] == "溪流"
    assert reopened["preferences"]["email"] == "me@example.com"
    assert reopened["preferences"]["theme"] == "dark"
    assert reopened["preferences"]["density"] == "compact"
    assert reopened["initialized"] is True


def test_stale_window_cannot_overwrite_agent_update(tmp_path):
    prefs = service(tmp_path)
    first = prefs.update({"displayName": "Original"}, expected_revision=0)
    agent = prefs.update({"displayName": "Agent edit"}, expected_revision=first["revision"])
    with pytest.raises(WebError) as failure:
        prefs.update(
            {"displayName": "Stale edit", "theme": "dark"}, expected_revision=first["revision"]
        )
    assert failure.value.code == "conflict"
    assert failure.value.status == 409
    assert prefs.get() == agent


def test_concurrent_revision_writes_have_one_winner(tmp_path):
    prefs = service(tmp_path)
    first = prefs.update({"theme": "light"})

    def write(theme):
        try:
            return prefs.update({"theme": theme}, expected_revision=first["revision"])
        except WebError as error:
            return error.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(write, ["dark", "system"]))
    assert outcomes.count("conflict") == 1
    winner = next(item for item in outcomes if isinstance(item, dict))
    assert prefs.get() == winner


@pytest.mark.parametrize(
    "payload",
    [
        {"api_key": "secret"},
        {"provider": "untrusted"},
        {"model": "other"},
        {"base_url": "http://untrusted"},
        {"theme": "invalid"},
        {"reducedMotion": "true"},
        {"bio": "x" * 301},
        {"avatar": "file:///C:/private.png"},
        {"avatar": "https://untrusted/avatar.png"},
        {"avatar": "data:image/svg+xml;base64,PHN2Zz4="},
    ],
)
def test_invalid_or_sensitive_patch_is_atomic(tmp_path, payload):
    prefs = service(tmp_path)
    before = prefs.update({"displayName": "Keep me"})
    with pytest.raises(WebError) as failure:
        prefs.update({"displayName": "Must not persist", **payload})
    assert failure.value.code == "invalid_arguments"
    assert prefs.get() == before
    assert "secret" not in failure.value.message


def test_legacy_desktop_migration_is_once_only_and_preserves_supported_values(tmp_path):
    legacy = {
        "displayName": "Desktop name",
        "theme": "dark",
        "fontSize": "large",
        "avatar": "data:image/png;base64,aGVsbG8=",
        "api_key": "never migrate",
    }
    (tmp_path / "preferences.json").write_text(json.dumps(legacy), encoding="utf-8")
    prefs = service(tmp_path)
    migrated = prefs.get()
    assert migrated["preferences"]["displayName"] == "Desktop name"
    assert migrated["preferences"]["avatar"] == legacy["avatar"]
    assert migrated["preferences"]["theme"] == "dark"
    assert "api_key" not in migrated["preferences"]
    prefs.update({"theme": "light"})
    assert service(tmp_path).get()["preferences"]["theme"] == "light"


def test_reset_restores_appearance_and_preserves_personal_data(tmp_path):
    prefs = service(tmp_path)
    prefs.update({"displayName": "Keep", "bio": "My notes", "theme": "dark", "fontSize": "large"})
    result = prefs.reset()
    assert result["preferences"]["displayName"] == "Keep"
    assert result["preferences"]["bio"] == "My notes"
    assert result["preferences"]["theme"] == "light"
    assert result["preferences"]["fontSize"] == "small"


def test_corrupt_legacy_file_does_not_prevent_browser_migration(tmp_path):
    (tmp_path / "preferences.json").write_text("{broken", encoding="utf-8")
    prefs = service(tmp_path)
    assert prefs.get()["initialized"] is False
    migrated = prefs.update({"displayName": "Browser name"}, expected_revision=0)
    assert migrated["preferences"]["displayName"] == "Browser name"


def test_http_requires_revision_and_returns_conflict_without_side_effect(tmp_path):
    from xiliu.api.app import create_app

    app = create_app(data_dir=tmp_path, env_file=tmp_path / ".env")
    client = TestClient(app, base_url="http://localhost")
    initial = client.get("/api/settings/preferences")
    assert initial.status_code == 200
    assert initial.json()["initialized"] is False
    missing = client.put("/api/settings/preferences", json={"changes": {"theme": "dark"}})
    assert missing.status_code == 422
    saved = client.put(
        "/api/settings/preferences", json={"changes": {"theme": "dark"}, "expected_revision": 0}
    )
    assert saved.status_code == 200
    stale = client.put(
        "/api/settings/preferences", json={"changes": {"theme": "light"}, "expected_revision": 0}
    )
    assert stale.status_code == 409
    assert client.get("/api/settings/preferences").json()["preferences"]["theme"] == "dark"


def test_agent_patch_and_http_read_share_persisted_preferences(tmp_path):
    from xiliu.api.app import create_app

    dispatch = dispatcher(tmp_path)
    updated = dispatch.execute(
        "preferences.update",
        {
            "changes": {"displayName": "Agent name", "theme": "dark"},
            "expected_revision": 0,
        },
        request_id="profile-update",
    )
    assert updated["ok"] and updated["verification"]["passed"]
    client = TestClient(
        create_app(data_dir=tmp_path, env_file=tmp_path / ".env"), base_url="http://localhost"
    )
    persisted = client.get("/api/settings/preferences").json()
    assert persisted["preferences"]["displayName"] == "Agent name"
    assert persisted["preferences"]["theme"] == "dark"
    replay = dispatcher(tmp_path).execute(
        "preferences.update",
        {
            "changes": {"displayName": "Agent name", "theme": "dark"},
            "expected_revision": 0,
        },
        request_id="profile-update",
    )
    assert replay == updated
    assert client.get("/api/settings/preferences").json()["revision"] == persisted["revision"]


def test_agent_revision_conflict_and_permission_denial_leave_preferences_intact(tmp_path):
    dispatch = dispatcher(tmp_path)
    before = dispatch.services.preferences.update({"theme": "dark"}, expected_revision=0)
    stale = dispatch.execute(
        "preferences.update",
        {
            "changes": {"theme": "light"},
            "expected_revision": 0,
        },
    )
    assert stale["error"] == "conflict"
    (tmp_path / "policy.json").write_text(
        '{"profiles":{"interactive":{"preferences.write":"deny"}}}', encoding="utf-8"
    )
    denied = dispatcher(tmp_path).execute(
        "preferences.update",
        {
            "changes": {"theme": "light"},
            "expected_revision": before["revision"],
        },
    )
    assert denied["error"] == "policy_denied"
    assert service(tmp_path).get() == before


@pytest.mark.parametrize(
    "changes",
    [
        {"avatar": "file:///C:/private.png"},
        {"avatar": "data:image/png;base64,aGVsbG8="},
        {"api_key": "never echo"},
        {"model": "other"},
        {"base_url": "http://untrusted"},
    ],
)
def test_agent_avatar_and_credentials_are_restricted_without_mutation(tmp_path, changes):
    dispatch = dispatcher(tmp_path)
    before = dispatch.services.preferences.get()
    result = dispatch.execute("preferences.update", {"changes": changes, "expected_revision": 0})
    assert not result["ok"] and result["error"] == "invalid_arguments"
    assert "never echo" not in json.dumps(result)
    assert dispatch.services.preferences.get() == before
