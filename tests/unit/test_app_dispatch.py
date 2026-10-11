import json
from types import SimpleNamespace

import pytest

from xiliu.api.app import create_app
from xiliu.execution.gateway import RunContext
from xiliu.policy.engine import PolicyEngine


@pytest.fixture
def services(tmp_path):
    env = tmp_path / ".env"
    env.write_text("XILIU_API_KEY=fake\n")
    app = create_app(data_dir=tmp_path / "data", env_file=env)
    try:
        yield SimpleNamespace(**app.state._state)
    finally:
        app.state.inbox.shutdown()


def dispatcher(services, **kwargs):
    from xiliu.app.dispatch import AppDispatcher

    context = RunContext(
        "test",
        "session-a",
        services.store.path.parent,
        policy_engine=PolicyEngine(services.store.path.parent / "policy.json"),
    )
    return AppDispatcher(services, context, **kwargs)


def test_registry_has_all_domains_and_one_tool(services):
    from xiliu.app.actions import get_registry
    from xiliu.tools.app import build_app_tool

    registry = get_registry()
    assert {
        "inbox",
        "knowledge",
        "tasks",
        "feed",
        "automations",
        "conversations",
        "preferences",
        "settings",
        "today",
        "capabilities",
    } <= {s.domain for s in registry.values()}
    for identifier, spec in registry.items():
        assert identifier == spec.id and callable(spec.handler) and callable(spec.postcondition)
        assert spec.args_schema.model_json_schema()["additionalProperties"] is False
    assert build_app_tool(services).name == "app"


def test_task_write_is_persisted_and_request_replay_is_durable(services):
    first = dispatcher(services).execute("tasks.create", {"title": "真实待办"}, request_id="same")
    replay = dispatcher(services).execute("tasks.create", {"title": "真实待办"}, request_id="same")
    assert first["ok"] and first["verification"]["passed"]
    assert first["records"][0]["id"] == replay["records"][0]["id"]
    assert len(services.tasks.list()) == 1
    conflict = dispatcher(services).execute(
        "tasks.create", {"title": "变更内容"}, request_id="same"
    )
    assert conflict["error"] == "conflict" and len(services.tasks.list()) == 1


def test_unknown_action_and_unknown_arguments_do_not_write(services):
    assert dispatcher(services).execute("made.up", {})["error"] == "capability_unavailable"
    result = dispatcher(services).execute("tasks.create", {"title": "x", "api_key": "sensitive"})
    assert result["error"] == "invalid_arguments"
    assert "sensitive" not in json.dumps(result)
    assert not services.tasks.list()


def test_ai_classify_verifies_durable_batch_identity_and_request_replay(services, monkeypatch):
    services.inbox.shutdown()
    item = services.content.create({"title": "AI 批次", "content": "真实内容"})
    dispatch = dispatcher(services)
    args = {"item_ids": [item["id"]], "use_ai": True}
    first = dispatch.execute("inbox.classify_selected", args, request_id="ai-batch")
    assert first["ok"] and first["status"] == "pending"
    assert services.content.get(item["id"])["status"] == "inbox"
    actual = services.inbox.get_archive_job(first["data"]["job_id"])
    assert actual["items"][0]["item_id"] == item["id"]
    assert actual["counts"]["pending"] == 1
    replay = dispatch.execute("inbox.classify_selected", args, request_id="ai-batch")
    assert replay == first
    original = services.inbox.queue_archive_batch

    def wrong_identity(*args, **kwargs):
        result = original(*args, **kwargs)
        result["items"][0]["revision"] += 1
        return result

    monkeypatch.setattr(services.inbox, "queue_archive_batch", wrong_identity)
    corrupt = dispatch.execute("inbox.classify_selected", args)
    assert not corrupt["ok"] and corrupt["error"] == "postcondition_failed"


def test_noop_preferences_reset_cannot_claim_restored_defaults(services, monkeypatch):
    current = services.preferences.update({"theme": "dark"}, expected_revision=0)
    monkeypatch.setattr(services.preferences, "reset", lambda **kwargs: current)
    result = dispatcher(services).execute(
        "preferences.reset", {"expected_revision": current["revision"]}
    )
    assert not result["ok"] and result["error"] == "postcondition_failed"
    assert services.preferences.get()["preferences"]["theme"] == "dark"


def test_policy_and_rag_scope_reject_writes(services):
    policy = services.store.path.parent / "policy.json"
    policy.write_text('{"profiles":{"interactive":{"tasks.write":"deny"}}}')
    assert dispatcher(services).execute("tasks.create", {"title": "x"})["error"] == "policy_denied"
    assert (
        dispatcher(services, allowed_actions={"knowledge.search", "knowledge.get"}).execute(
            "inbox.import_url", {"url": "https://example.com"}
        )["error"]
        == "policy_denied"
    )
    assert not services.tasks.list()


def test_delete_confirmation_cannot_be_approved_by_model_or_other_session(services):
    task = services.tasks.create({"title": "保留"})
    dispatch = dispatcher(services)
    args = {"task_id": task["id"]}
    pending = dispatch.execute("tasks.delete", args)
    assert pending["status"] == "confirmation_required" and services.tasks.list()
    forged = dispatch.execute("tasks.delete", args, confirmation_id=pending["confirmation_id"])
    assert forged["status"] == "confirmation_required" and services.tasks.list()
    dispatch.approve_confirmation(pending["confirmation_id"], session_id="session-a")
    result = dispatch.execute("tasks.delete", args, confirmation_id=pending["confirmation_id"])
    assert result["ok"] and not services.tasks.list()
    assert (
        dispatch.execute("tasks.delete", args, confirmation_id=pending["confirmation_id"])["ok"]
        is False
    )


def test_bulk_inbox_archival_uses_local_rules_and_handles_empty(services):
    dispatch = dispatcher(services)
    assert dispatch.execute("inbox.classify_all", {})["counts"]["total"] == 0
    folder = services.knowledge.create_folder({"name": "面试", "tags": ["面试"]})
    item = services.content.create(
        {"type": "note", "title": "资料", "content": "资料", "tags": ["面试"]}
    )
    services.inbox.classifier = lambda *a: pytest.fail("Local Fast must not call metadata model")
    result = dispatch.execute("inbox.classify_all", {})
    assert result["ok"] and result["counts"]["succeeded"] == 1
    saved = services.content.get(item["id"])
    assert saved["status"] == "knowledge" and saved["folder_id"] == folder["id"]


def test_sensitive_model_settings_action_is_restricted(services):
    result = dispatcher(services).execute("settings.model.update", {"api_key": "do-not-echo"})
    assert not result["ok"] and "do-not-echo" not in json.dumps(result)


def test_catalog_describe_are_bounded_and_role_filtered(services):
    dispatch = dispatcher(services, allowed_actions={"knowledge.search", "knowledge.get"})
    assert len(dispatch.catalog()["actions"]) == 2
    assert dispatch.describe("tasks.create")["error"] == "policy_denied"


def test_unrelated_request_does_not_wait_for_slow_service(services):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event

    entered, release = Event(), Event()
    original = services.tasks.create

    def slow(payload):
        if payload["title"] == "slow":
            entered.set()
            assert release.wait(5)
        return original(payload)

    services.tasks.create = slow
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(
            dispatcher(services).execute, "tasks.create", {"title": "slow"}, request_id="slow"
        )
        assert entered.wait(2)
        second = pool.submit(
            dispatcher(services).execute,
            "tasks.create",
            {"title": "independent"},
            request_id="other",
        )
        try:
            assert second.result(timeout=1)["ok"]
        finally:
            release.set()
        assert first.result(timeout=5)["ok"]
    assert len(services.tasks.list()) == 2


def test_request_receipt_rechecks_optional_network_permission(services):
    dispatch = dispatcher(services)
    services.feed._fetch_title = lambda url: ("source", {})
    # A replay must not bypass a permission revoked after the first execution.
    first = dispatch.execute(
        "feed.add_manual",
        {"title": "source", "url": "https://example.com", "fetch_title": True},
        request_id="network",
    )
    assert first["ok"]
    (services.store.path.parent / "policy.json").write_text(
        '{"profiles":{"interactive":{"feed.write":"allow","network.read":"deny"}}}'
    )
    assert dispatcher(services).get_receipt("network")["error"] == "policy_denied"


def test_conversation_history_reads_messages_not_conversation_ids(services):
    conversation = services.store.create()
    services.store.append_message(conversation["id"], role="user", content="hello")
    result = dispatcher(services).execute("conversations.messages", {"cid": conversation["id"]})
    assert result["ok"] and result["data"][0]["content"] == "hello"


def test_noop_service_cannot_claim_requested_task_completion(services):
    task = services.tasks.create({"title": "unfinished"})
    services.tasks.update = lambda task_id, changes: task
    result = dispatcher(services).execute("tasks.complete", {"task_id": task["id"]})
    assert result["error"] == "postcondition_failed"
    assert not result["verification"]["passed"]


def test_ai_metadata_requires_network_permission_before_queueing(services):
    (services.store.path.parent / "policy.json").write_text(
        '{"profiles":{"interactive":{"knowledge.write":"allow","network.read":"deny"}}}'
    )
    result = dispatcher(services).execute(
        "inbox.import_url", {"url": "https://example.com", "use_ai": True}
    )
    assert result["error"] == "policy_denied"
    assert not services.content.list("inbox")


@pytest.mark.parametrize(
    "action,args",
    [
        ("feed.add_manual", {"url": "https://Example.COM#section", "summary": "  padded  "}),
        (
            "knowledge.folders.create",
            {"name": "fixture", "summary": "  padded  ", "tags": ["Z", "a"]},
        ),
    ],
)
def test_write_verification_matches_service_normalization(services, action, args):
    result = dispatcher(services).execute(action, args)
    assert result["ok"] and result["data"]["summary"] == "padded"


def test_conversation_title_preserves_existing_service_whitespace(services):
    conversation = services.store.create()
    result = dispatcher(services).execute(
        "conversations.update", {"cid": conversation["id"], "title": "  padded  "}
    )
    assert result["ok"] and result["data"]["title"] == "  padded  "


def test_bulk_service_cannot_claim_success_in_a_different_folder(services):
    target = services.knowledge.create_folder({"name": "target"})
    other = services.knowledge.create_folder({"name": "other"})
    item = services.content.create({"content": "source"})
    original = services.inbox.classify_batch

    def wrong(ids, **kwargs):
        return original(ids, **{**kwargs, "folder_id": other["id"]})

    services.inbox.classify_batch = wrong
    result = dispatcher(services).execute(
        "inbox.classify_selected", {"item_ids": [item["id"]], "folder_id": target["id"]}
    )
    assert not result["ok"] and result["counts"]["failed"] == 1


def test_cli_trusted_human_handler_can_confirm_once(services):
    from dataclasses import replace

    from xiliu.core.approval import ApprovalDecision

    task = services.tasks.create({"title": "human approved"})
    dispatch = dispatcher(services)
    prompts = []

    def human(request):
        prompts.append(request)
        assert request.tool_name == "app" and task["id"] in request.command
        return ApprovalDecision(True)

    dispatch.context = replace(dispatch.context, approval_handler=human)
    result = dispatch.execute("tasks.delete", {"task_id": task["id"]}, request_id="human")
    assert result["ok"] and not services.tasks.list() and len(prompts) == 1
    assert dispatch.execute("tasks.delete", {"task_id": task["id"]}, request_id="human") == result
    assert len(prompts) == 1
