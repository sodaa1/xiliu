"""Real AppTool/Gateway cases for actions previously covered only through UI/Service tests."""

import json
from dataclasses import replace
from types import SimpleNamespace

import pytest

from xiliu.api.app import create_app
from xiliu.app.actions import get_registry
from xiliu.app.dispatch import AppDispatcher
from xiliu.execution.gateway import ExecutionGateway, RunContext, active_run
from xiliu.policy.engine import DEFAULT_PROFILES, PolicyEngine
from xiliu.tools.app import build_app_tool


@pytest.fixture
def app_context(tmp_path):
    env = tmp_path / ".env"
    env.write_text("XILIU_PROVIDER=deepseek\nXILIU_MODEL=deepseek-v4-flash\n", encoding="utf-8")
    app = create_app(data_dir=tmp_path / "data", env_file=env)
    session = app.state.store.create()["id"]
    events = []
    context = RunContext(
        "coverage",
        session,
        tmp_path,
        data_dir=tmp_path / "data",
        policy_engine=PolicyEngine(tmp_path / "data/policy.json"),
        app_services=app.state.app_services,
        event_sink=events.append,
    )
    try:
        yield app, context, events
    finally:
        app.state.inbox.shutdown()
        app.state.retrieval.worker.shutdown()
        app.state.automations.shutdown()


def invoke(app_context, action, arguments=None, *, confirm=False):
    app, context, events = app_context
    call = {"operation": "execute", "action_id": action, "arguments": arguments or {}}
    tool = build_app_tool(app.state.app_services)
    gateway = ExecutionGateway()
    receipt = json.loads(gateway.invoke(tool, call, context))
    assert active_run.get() is None
    if confirm:
        assert receipt["status"] == "confirmation_required"
        assert AppDispatcher(app.state.app_services, context).approve_confirmation(
            receipt["confirmation_id"], session_id=context.session_id
        )
        call["confirmation_id"] = receipt["confirmation_id"]
        receipt = json.loads(gateway.invoke(tool, call, context))
    assert any(event.get("tool_name") == "app" for event in events)
    return receipt


@pytest.mark.parametrize(
    "action",
    [
        "today.read",
        "settings.model.read",
        "settings.data.read",
        "capabilities.skills",
        "capabilities.mcp",
        "settings.models.catalog",
        "capabilities.commands",
    ],
)
def test_gateway_metadata_and_today_actions_read_real_services_without_credentials(
    app_context, action
):
    app, _, _ = app_context
    task = app.state.tasks.create({"title": "stored task"})
    receipt = invoke(app_context, action)
    assert receipt["ok"] and receipt["verification"]["passed"]
    data = receipt["data"]
    if action == "today.read":
        assert data["tasks"][0]["id"] == task["id"] and data["inbox_count"] == 0
    elif action == "settings.model.read":
        assert data == {
            "provider": "deepseek",
            "model": "deepseek-v4-flash",
            "base_url": "https://api.deepseek.com",
            "api_key_set": False,
        }
    elif action == "settings.data.read":
        assert data["content_count"] == 0 and data["data_dir"] == str(app.state.data_dir)
    elif action == "settings.models.catalog":
        assert "deepseek-v4-flash" in data["deepseek"]["models"]
    elif action == "capabilities.commands":
        assert any(command["name"] == "clear" for command in data)
    else:
        assert isinstance(data, list)
    assert app.state.tasks.list() == [task]
    assert not app.state.content.list("inbox")


def test_gateway_content_create_and_inbox_get_persist_exact_note(app_context):
    app, _, _ = app_context
    result = invoke(
        app_context,
        "content.create",
        {
            "title": "precise note",
            "content": " actual text ",
            "summary": " exact summary ",
            "type": "note",
        },
    )
    assert result["ok"] and result["verification"]["passed"]
    item = result["data"]
    assert app.state.content.get(item["id"])["content"] == " actual text "
    assert (app.state.content.root / item["id"] / "item.md").exists()
    read = invoke(app_context, "inbox.get", {"item_id": item["id"]})
    assert read["ok"] and read["data"] == app.state.content.get(item["id"])


def test_gateway_knowledge_items_folder_reads_update_and_move_share_sqlite(app_context):
    app, _, _ = app_context
    folder = app.state.knowledge.create_folder({"name": "target", "tags": ["matching"]})
    item = app.state.content.create(
        {"content": "source", "title": "source", "status": "knowledge", "folder_id": folder["id"]}
    )
    listed = invoke(app_context, "knowledge.items.list")
    assert listed["ok"] and listed["data"][0]["id"] == item["id"]
    read = invoke(app_context, "knowledge.items.get", {"item_id": item["id"]})
    assert read["ok"] and read["data"] == app.state.content.get(item["id"])
    folder_read = invoke(app_context, "knowledge.folders.get", {"folder_id": folder["id"]})
    assert folder_read["ok"] and folder_read["data"] == app.state.knowledge.get_folder(folder["id"])
    folder_items = invoke(app_context, "knowledge.folders.items", {"folder_id": folder["id"]})
    assert folder_items["ok"] and folder_items["data"][0]["id"] == item["id"]
    changed = invoke(
        app_context,
        "knowledge.items.update",
        {
            "item_id": item["id"],
            "expected_revision": item["revision"],
            "changes": {"title": "edited", "content": "new body"},
        },
    )
    assert changed["ok"] and app.state.content.get(item["id"])["content"] == "new body"
    stale = invoke(
        app_context,
        "knowledge.items.update",
        {
            "item_id": item["id"],
            "expected_revision": item["revision"],
            "changes": {"title": "stale"},
        },
    )
    assert not stale["ok"] and stale["error"] in {"conflict", "postcondition_failed"}
    assert app.state.content.get(item["id"])["title"] == "edited"
    moved = invoke(
        app_context,
        "content.move_to_inbox",
        {"item_id": item["id"], "expected_revision": changed["data"]["revision"]},
    )
    assert moved["ok"] and app.state.content.get(item["id"])["status"] == "inbox"
    assert app.state.content.get(item["id"])["folder_id"] is None


@pytest.mark.parametrize(
    "action,status", [("inbox.delete", "inbox"), ("knowledge.items.delete", "knowledge")]
)
def test_gateway_content_delete_requires_human_approval_and_removes_real_files(
    app_context, action, status
):
    app, _, _ = app_context
    item = app.state.content.create({"content": "delete fixture", "status": status})
    receipt = invoke(app_context, action, {"item_id": item["id"]})
    assert receipt["status"] == "confirmation_required"
    assert app.state.content.get(item["id"])["content"] == "delete fixture"
    deleted = invoke(app_context, action, {"item_id": item["id"]}, confirm=True)
    assert deleted["ok"] and deleted["verification"]["passed"]
    assert all(
        record["id"] != item["id"]
        for state in ("inbox", "knowledge")
        for record in app.state.content.list(state)
    )
    assert not (app.state.content.root / item["id"]).exists()


def test_gateway_conversation_model_change_matches_persisted_override(app_context):
    app, context, _ = app_context
    result = invoke(
        app_context,
        "conversations.model",
        {"cid": context.session_id, "model": "deepseek-v4-flash"},
    )
    assert result["ok"] and result["verification"]["passed"]
    assert app.state.store.get(context.session_id)["model_override"] == "deepseek-v4-flash"
    invalid = invoke(
        app_context, "conversations.model", {"cid": context.session_id, "model": "fabricated-model"}
    )
    assert (
        not invalid["ok"]
        and app.state.store.get(context.session_id)["model_override"] == "deepseek-v4-flash"
    )


@pytest.mark.parametrize(
    "action,args",
    [("inbox.import_file", {"attachment_id": "not-granted"}), ("conversations.stop", {})],
)
def test_gateway_restricted_actions_cannot_be_enabled_by_agent(app_context, action, args):
    app, context, _ = app_context
    before = app.state.store.messages(context.session_id)
    if action == "conversations.stop":
        args = {"cid": context.session_id}
    result = invoke(app_context, action, args)
    assert not result["ok"] and result["error"] == "capability_unavailable"
    assert app.state.store.messages(context.session_id) == before
    assert not app.state.content.list("inbox")


@pytest.mark.parametrize("action", sorted(get_registry()))
def test_every_action_gateway_honors_its_exact_denied_permission(app_context, action):
    app, context, _ = app_context
    spec = get_registry()[action]
    policy = context.data_dir / "policy.json"
    policy.write_text(
        json.dumps({"profiles": {"interactive": {spec.permission: "deny"}}}), encoding="utf-8"
    )
    denied_context = replace(context, policy_engine=PolicyEngine(policy))
    tool = build_app_tool(app.state.app_services)
    arguments = {"operation": "execute", "action_id": action, "arguments": {}}
    assert ExecutionGateway._policy_target(tool, arguments, denied_context)[2] == spec.permission
    result = json.loads(ExecutionGateway().invoke(tool, arguments, denied_context))
    assert not result["ok"] and result["error"] == "policy_denied"
    assert not app.state.content.list("inbox") and not app.state.tasks.list()
    assert len(app.state.store.list()) == 1


def test_all_registry_actions_background_catalog_follows_scope_and_never_grants_writes(app_context):
    app, context, _ = app_context
    background = replace(context, actor_type="background", policy_profile="background")
    result = json.loads(
        ExecutionGateway().invoke(
            build_app_tool(app.state.app_services), {"operation": "catalog"}, background
        )
    )
    enabled = {row["action_id"] for row in result["actions"]}
    expected = {
        name
        for name, spec in get_registry().items()
        if spec.agent_availability == "enabled"
        and DEFAULT_PROFILES["background"].get(spec.permission) == "allow"
    }
    assert enabled == expected
    assert not any(get_registry()[name].side_effect == "write" for name in enabled)
    rag = build_app_tool(
        app.state.app_services, allowed_actions={"knowledge.search", "knowledge.get"}
    )
    narrowed = json.loads(ExecutionGateway().invoke(rag, {"operation": "catalog"}, background))
    assert {row["action_id"] for row in narrowed["actions"]} == {
        "knowledge.search",
        "knowledge.get",
    }


def test_restricted_file_handler_explicitly_rejects_missing_attachment_protocol(app_context):
    from xiliu.api.errors import WebError

    app, context, _ = app_context
    spec = get_registry()["inbox.import_file"]
    with pytest.raises(WebError) as caught:
        spec.handler(app.state.app_services, {"attachment_id": "not-granted"}, context)
    assert caught.value.code == "capability_unavailable"
    assert not app.state.content.list("inbox")


def test_gateway_automation_lifecycle_real_store_and_bound_human_confirmations(app_context):
    app, _, _ = app_context
    created = invoke(
        app_context,
        "automations.create",
        {
            "name": "coverage automation",
            "prompt": "read local tasks",
            "hour": 9,
            "minute": 15,
        },
        confirm=True,
    )
    assert created["ok"] and created["verification"]["passed"]
    identifier = created["data"]["id"]
    listed = invoke(app_context, "automations.list")
    assert listed["ok"] and any(row["id"] == identifier for row in listed["data"])
    runs = invoke(app_context, "automations.runs", {"task_id": identifier})
    assert runs["ok"] and runs["data"] == app.state.automations.runs(identifier)
    changed = invoke(
        app_context,
        "automations.toggle",
        {
            "task_id": identifier,
            "enabled": False,
        },
        confirm=True,
    )
    assert changed["ok"] and not app.state.automations.list()[0]["enabled"]
    deleted = invoke(app_context, "automations.delete", {"task_id": identifier}, confirm=True)
    assert deleted["ok"] and not app.state.automations.list()


def test_gateway_remaining_conversation_and_task_crud_matches_persisted_records(app_context):
    app, _, _ = app_context
    created = invoke(app_context, "conversations.create")
    assert created["ok"]
    identifier = created["data"]["id"]
    listed = invoke(app_context, "conversations.list")
    assert listed["ok"] and any(row["id"] == identifier for row in listed["data"])
    read = invoke(app_context, "conversations.get", {"cid": identifier})
    assert read["ok"] and read["data"] == app.state.conversations.get(identifier)
    denied = invoke(app_context, "conversations.delete", {"cid": identifier})
    assert denied["error"] == "capability_unavailable"
    assert app.state.store.get(identifier)
    task = app.state.tasks.create({"title": "original"})
    updated = invoke(
        app_context,
        "tasks.update",
        {
            "task_id": task["id"],
            "changes": {"title": "exact updated"},
        },
    )
    assert updated["ok"] and app.state.tasks.list()[0]["title"] == "exact updated"


def test_gateway_remaining_inbox_folder_preferences_actions_use_actual_services(app_context):
    app, _, _ = app_context
    imported = invoke(app_context, "inbox.import_text", {"text": "local fixture", "use_ai": False})
    assert imported["ok"]
    item = imported["data"]
    assert app.state.content.get(item["id"])["content"] == "local fixture"
    listed = invoke(app_context, "inbox.list")
    assert listed["ok"] and listed["data"][0]["id"] == item["id"]
    updated = invoke(
        app_context,
        "inbox.update",
        {
            "item_id": item["id"],
            "expected_revision": item["revision"],
            "changes": {"title": "manual title"},
        },
    )
    assert updated["ok"] and app.state.content.get(item["id"])["title"] == "manual title"
    folder = app.state.knowledge.create_folder({"name": "folder"})
    folders = invoke(app_context, "knowledge.folders.list")
    assert folders["ok"] and folders["data"][0]["id"] == folder["id"]
    edited = invoke(
        app_context,
        "knowledge.folders.update",
        {
            "folder_id": folder["id"],
            "changes": {"name": "edited folder"},
        },
    )
    assert edited["ok"] and app.state.knowledge.get_folder(folder["id"])["name"] == "edited folder"
    moved = invoke(
        app_context,
        "inbox.move",
        {
            "item_id": item["id"],
            "folder_id": folder["id"],
            "expected_revision": updated["data"]["revision"],
        },
    )
    assert moved["ok"] and app.state.content.get(item["id"])["folder_id"] == folder["id"]
    document = invoke(app_context, "knowledge.get", {"document_id": item["id"]})
    assert document["ok"] and document["data"]["matched"]
    assert document["data"]["document"]["content"] == "local fixture"
    deleted = invoke(
        app_context, "knowledge.folders.delete", {"folder_id": folder["id"]}, confirm=True
    )
    assert deleted["ok"] and not app.state.knowledge.list_folders()
    assert app.state.content.get(item["id"])["folder_id"] is None
    prefs = invoke(app_context, "preferences.get")
    assert prefs["ok"] and prefs["data"]["revision"] == app.state.preferences.get()["revision"]
    assert "avatar" not in prefs["data"]["preferences"]
    changed = app.state.preferences.update(
        {"theme": "dark"}, expected_revision=prefs["data"]["revision"]
    )
    reset = invoke(app_context, "preferences.reset", {"expected_revision": changed["revision"]})
    assert reset["ok"], reset
    assert reset["data"]["revision"] == app.state.preferences.get()["revision"]
    assert reset["data"]["preferences"]["theme"] == "light"


def test_gateway_feed_refresh_real_cache_and_inbox_retry_queue_without_external_models(
    app_context, monkeypatch
):
    app, _, _ = app_context
    monkeypatch.setattr(app.state.feed, "_fetch_aihot", lambda: [])
    monkeypatch.setattr(app.state.feed, "_fetch_github", lambda: [])
    refreshed = invoke(app_context, "feed.refresh")
    assert refreshed["ok"] and refreshed["verification"]["passed"]
    assert refreshed["data"] == app.state.feed.list()
    app.state.inbox.shutdown()
    item = app.state.inbox.import_item({"text": "retry fixture", "use_ai": False})
    with app.state.store.connect() as db:
        db.execute("UPDATE inbox_jobs SET state='failed' WHERE item_id=?", (item["id"],))
    retried = invoke(app_context, "inbox.retry", {"item_id": item["id"]})
    assert retried["ok"] and app.state.content.get(item["id"])["processing_status"] == "pending"
    with app.state.store.connect() as db:
        job = db.execute(
            "SELECT state, use_ai FROM inbox_jobs WHERE item_id=?", (item["id"],)
        ).fetchone()
    assert job["state"] == "pending" and job["use_ai"] == 1


@pytest.mark.parametrize("action", sorted(get_registry()))
def test_every_action_background_scope_rejects_writes_before_arguments(app_context, action):
    app, context, _ = app_context
    spec = get_registry()[action]
    background = replace(context, actor_type="background", policy_profile="background")
    result = json.loads(
        ExecutionGateway().invoke(
            build_app_tool(app.state.app_services),
            {"operation": "execute", "action_id": action, "arguments": {}},
            background,
        )
    )
    if DEFAULT_PROFILES["background"].get(spec.permission) != "allow":
        assert not result["ok"] and result["error"] == "policy_denied"
    elif spec.agent_availability == "restricted":
        assert not result["ok"] and result["error"] == "capability_unavailable"
    else:
        assert result.get("error") != "policy_denied"
    assert not app.state.content.list("inbox") and not app.state.tasks.list()
    assert len(app.state.store.list()) == 1


def test_gateway_remaining_read_edit_delete_chains_have_real_readback(app_context):
    app, context, _ = app_context
    renamed = invoke(
        app_context,
        "conversations.update",
        {
            "cid": context.session_id,
            "title": "exact conversation",
        },
    )
    assert (
        renamed["ok"] and app.state.store.get(context.session_id)["title"] == "exact conversation"
    )
    app.state.store.append_message(context.session_id, "user", "stored message")
    messages = invoke(app_context, "conversations.messages", {"cid": context.session_id})
    assert messages["ok"] and messages["data"] == app.state.store.messages(context.session_id)
    folder = invoke(app_context, "knowledge.folders.create", {"name": "readback folder"})
    assert (
        folder["ok"]
        and app.state.knowledge.get_folder(folder["data"]["id"])["name"] == "readback folder"
    )
    item = app.state.inbox.import_item({"text": "durable queued note", "use_ai": False})
    job = app.state.inbox.queue_archive(item["id"], folder["data"]["id"], item["revision"])
    read = invoke(app_context, "inbox.archive_job", {"job_id": job["job_id"]})
    assert read["ok"] and read["data"]["item_id"] == item["id"]
    assert app.state.inbox.get_archive_job(job["job_id"])["job_id"] == read["data"]["job_id"]
    prefs = app.state.preferences.get()
    changed = invoke(
        app_context,
        "preferences.update",
        {
            "changes": {"displayName": "actual name"},
            "expected_revision": prefs["revision"],
        },
    )
    assert (
        changed["ok"] and app.state.preferences.get()["preferences"]["displayName"] == "actual name"
    )
    task = app.state.tasks.create({"title": "delete actual task"})
    deleted = invoke(app_context, "tasks.delete", {"task_id": task["id"]}, confirm=True)
    assert deleted["ok"] and not app.state.tasks.list()


def test_gateway_feed_visibility_restore_and_save_chains_share_actual_database(app_context):
    from xiliu.api.services.feed import normalize_aihot

    app, _, _ = app_context
    manual = app.state.feed.add_manual(
        {"title": "actual story", "url": "https://example.org/story"}
    )
    saved = invoke(app_context, "feed.save_to_inbox", {"item_id": manual["id"]})
    assert saved["ok"] and app.state.content.get(saved["data"]["id"])["source"] == manual["url"]
    removed = invoke(app_context, "feed.remove_manual", {"item_id": manual["id"]}, confirm=True)
    assert removed["ok"] and not app.state.feed.list()["items"]
    restored = invoke(app_context, "feed.restore_manual", {"item_id": manual["id"]})
    assert restored["ok"] and app.state.feed.list()["items"][0]["id"] == manual["id"]
    story = normalize_aihot([{"title": "external fixture", "url": "https://example.org/external"}])[
        0
    ]
    with app.state.store.connect() as db:
        db.execute(
            "UPDATE feed_cache SET items_json=? WHERE source='aihot'", (json.dumps([story]),)
        )
    hidden = invoke(app_context, "feed.hide_external", {"item_id": story["id"]})
    assert hidden["ok"] and story["id"] not in {row["id"] for row in app.state.feed.list()["items"]}
    unhidden = invoke(app_context, "feed.unhide_external", {"item_id": story["id"]})
    assert unhidden["ok"] and story["id"] in {row["id"] for row in app.state.feed.list()["items"]}


def test_gateway_feed_summarize_uses_stored_metadata_without_mutating_the_feed(
    app_context, monkeypatch
):
    app, _, _ = app_context
    monkeypatch.setenv("XILIU_PROVIDER", "deepseek")
    monkeypatch.setenv("XILIU_MODEL", "deepseek-v4-flash")
    monkeypatch.setenv("XILIU_API_KEY", "disposable-test-key")
    item = app.state.feed.add_manual(
        {
            "title": "Stored story",
            "url": "https://example.org/stored-story",
            "summary": "Original short summary",
            "tags": ["research"],
        }
    )
    before = app.state.feed.list()
    calls = []
    options = []
    summary = "A detailed interpretation based only on the stored story metadata."

    class FakeModel:
        max_retries = 0
        request_timeout = 0
        streaming = True

        def __init__(self):
            self.root_client = SimpleNamespace(with_options=self.with_options)

        def with_options(self, **kwargs):
            options.append(kwargs)
            return SimpleNamespace(chat=SimpleNamespace(completions=object()))

        def invoke(self, messages):
            calls.append(messages)
            assert self.max_retries == 0 and self.request_timeout == 45
            assert self.streaming is False
            return SimpleNamespace(content=f"  {summary}  ")

    def create_model(settings):
        assert settings.provider == "deepseek"
        assert settings.model == "deepseek-v4-flash"
        return FakeModel()

    monkeypatch.setattr("xiliu.providers.openai_compatible.create_chat_model", create_model)
    result = invoke(app_context, "feed.summarize", {"item_id": item["id"]})

    assert result["ok"] and result["verification"]["passed"], result
    assert result["data"] == {"summary": summary}
    assert len(calls) == 1 and len(calls[0]) == 2
    assert calls[0][0].type == "system"
    assert calls[0][1].type == "human"
    assert json.loads(calls[0][1].content) == {
        "title": item["title"],
        "summary": item["summary"],
        "tags": item["tags"],
        "url": item["url"],
    }
    assert options == [{"max_retries": 0, "timeout": 45}]
    assert app.state.feed.list() == before
    assert not app.state.content.list("inbox")
