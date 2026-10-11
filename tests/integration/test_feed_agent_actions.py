import json
from types import SimpleNamespace

import pytest

from xiliu.api.services.content import ContentService
from xiliu.api.services.feed import FeedService, normalize_aihot
from xiliu.api.store import AppStore
from xiliu.app.dispatch import AppDispatcher
from xiliu.execution.gateway import RunContext
from xiliu.policy.engine import PolicyEngine


@pytest.fixture
def services(tmp_path):
    store = AppStore(tmp_path)
    content = ContentService(store)
    return SimpleNamespace(store=store, content=content, feed=FeedService(store, content))


def dispatch(services, *, local_only=False):
    return AppDispatcher(
        services,
        RunContext(
            "feed-test",
            "feed-session",
            services.store.path.parent,
            policy_engine=PolicyEngine(services.store.path.parent / "policy.json"),
            local_only=local_only,
        ),
    )


def confirmed(dispatcher, action, args):
    pending = dispatcher.execute(action, args)
    assert pending["status"] == "confirmation_required"
    assert dispatcher.approve_confirmation(pending["confirmation_id"], session_id="feed-session")
    return dispatcher.execute(action, args, confirmation_id=pending["confirmation_id"])


def test_agent_feed_crud_replay_and_save_use_persisted_service(services, monkeypatch):
    agent = dispatch(services, local_only=True)
    arguments = {"url": "https://example.org/manual", "title": "Manual"}
    added = agent.execute("feed.add_manual", arguments, request_id="capture")
    assert added["ok"] and added["verification"]["passed"]
    item_id = added["records"][0]["id"]
    assert (
        dispatch(services).execute("feed.add_manual", arguments, request_id="capture")["records"][
            0
        ]["id"]
        == item_id
    )
    edited = agent.execute(
        "feed.update_manual", {"item_id": item_id, "changes": {"title": "Edited", "tags": ["AI"]}}
    )
    assert edited["ok"]
    saved = agent.execute("feed.save_to_inbox", {"item_id": item_id})
    assert saved["ok"]
    assert services.content.get(saved["records"][0]["id"])["source"] == arguments["url"]
    removed = confirmed(agent, "feed.remove_manual", {"item_id": item_id})
    assert removed["ok"] and services.feed.list()["items"] == []
    assert services.feed.list(include_hidden=True)["items"][0]["deleted_at"]
    assert agent.execute("feed.restore_manual", {"item_id": item_id})["ok"]
    restarted = FeedService(services.store, services.content)
    assert restarted.list()["items"][0]["title"] == "Edited"
    with services.store.connect() as db:
        assert db.execute("SELECT COUNT(*) FROM feed_manual_items").fetchone()[0] == 1


def test_agent_feed_policy_and_network_denials_do_not_write(services, monkeypatch):
    policy = services.store.path.parent / "policy.json"
    policy.write_text(
        json.dumps({"profiles": {"interactive": {"feed.write": "allow", "network.read": "deny"}}})
    )
    assert (
        dispatch(services).execute(
            "feed.add_manual", {"url": "https://example.org", "fetch_title": True}
        )["error"]
        == "policy_denied"
    )
    assert (
        dispatch(services, local_only=True).execute(
            "feed.add_manual", {"url": "https://example.org", "fetch_title": True}
        )["error"]
        == "policy_denied"
    )
    assert services.feed.list()["items"] == []
    assert dispatch(services).execute("feed.add_manual", {"url": "https://example.org"})["ok"]
    policy.write_text(json.dumps({"profiles": {"interactive": {"feed.write": "deny"}}}))
    assert (
        dispatch(services).execute("feed.add_manual", {"url": "https://example.org/other"})["error"]
        == "policy_denied"
    )
    assert len(services.feed.list()["items"]) == 1


def test_agent_optional_fetch_patch_verifies_real_title_not_control_flag(services, monkeypatch):
    item = services.feed.add_manual({"url": "https://example.org/story"})
    monkeypatch.setattr(
        services.feed, "_fetch_title", lambda url: ("Fetched", {"fetch_status": "ready"})
    )
    result = dispatch(services).execute(
        "feed.update_manual", {"item_id": item["id"], "changes": {"fetch_title": True}}
    )
    assert services.feed.list()["items"][0]["title"] == "Fetched"
    assert result["ok"] and result["verification"]["passed"]


def test_agent_hide_rejects_unpersisted_receipt(services, monkeypatch):
    story = normalize_aihot([{"title": "News", "url": "https://example.org/news"}])[0]
    with services.store.connect() as db:
        db.execute(
            "UPDATE feed_cache SET items_json=? WHERE source='aihot'", (json.dumps([story]),)
        )
    monkeypatch.setattr(services.feed, "hide_external", lambda item_id: {**story, "hidden": True})
    result = dispatch(services).execute("feed.hide_external", {"item_id": story["id"]})
    assert not result["ok"] and result["verification"]["passed"] is False
    assert services.feed.list()["items"][0]["id"] == story["id"]


def test_agent_remove_rejects_unpersisted_tombstone(services, monkeypatch):
    item = services.feed.add_manual({"url": "https://example.org/story"})
    monkeypatch.setattr(
        services.feed, "remove_manual", lambda item_id: {**item, "deleted_at": "2026-10-10"}
    )
    result = confirmed(dispatch(services), "feed.remove_manual", {"item_id": item["id"]})
    assert not result["ok"] and result["verification"]["passed"] is False
    assert services.feed.list()["items"][0]["id"] == item["id"]


def test_agent_unhide_missing_provider_item_verifies_removed_hidden_record(services, monkeypatch):
    story = normalize_aihot([{"title": "Yesterday", "url": "https://example.org/yesterday"}])[0]
    with services.store.connect() as db:
        db.execute(
            "UPDATE feed_cache SET items_json=? WHERE source='aihot'", (json.dumps([story]),)
        )
    assert dispatch(services).execute("feed.hide_external", {"item_id": story["id"]})["ok"]
    with services.store.connect() as db:
        db.execute("UPDATE feed_cache SET items_json='[]' WHERE source='aihot'")
    result = dispatch(services).execute("feed.unhide_external", {"item_id": story["id"]})
    assert result["ok"]
    with services.store.connect() as db:
        assert db.execute("SELECT COUNT(*) FROM feed_hidden_items").fetchone()[0] == 0
