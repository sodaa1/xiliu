import time
from threading import Event

import pytest

from xiliu.api.errors import WebError
from xiliu.api.services.content import ContentService
from xiliu.api.services.inbox import InboxService
from xiliu.api.services.knowledge import KnowledgeService
from xiliu.api.store import AppStore
from xiliu.execution.cancellation import TurnCancelled


@pytest.fixture
def services(tmp_path):
    content = ContentService(AppStore(tmp_path))
    knowledge = KnowledgeService(content)
    inbox = InboxService(
        content,
        knowledge,
        metadata=lambda item: {
            "title": "面试资料",
            "summary": "相关资料",
            "tags": ["面试"],
        },
    )
    try:
        yield inbox, content, knowledge
    finally:
        inbox.shutdown()


def queued(services):
    inbox, _, knowledge = services
    assert hasattr(inbox, "queue_archive"), "durable metadata archive queue is missing"
    folder = knowledge.create_folder({"name": "面试"})
    item = inbox.import_item({"text": "https://example.com/interview", "use_ai": True})
    job = inbox.queue_archive(item["id"], folder["id"], item["revision"])
    return item, folder, job


def test_archive_intent_persists_and_replayed_item_revision_has_one_job(services):
    inbox, content, knowledge = services
    item, folder, job = queued(services)
    assert job["status"] == "pending" and job["job_id"]
    assert inbox.queue_archive(item["id"], folder["id"], item["revision"]) == job
    reopened = InboxService(content, knowledge)
    assert reopened.get_archive_job(job["job_id"]) == job
    other = knowledge.create_folder({"name": "其他"})
    with pytest.raises(WebError) as failure:
        inbox.queue_archive(item["id"], other["id"], item["revision"])
    assert failure.value.code == "conflict"
    assert content.get(item["id"])["status"] == "inbox"


def test_successful_metadata_automatically_archives_to_explicit_target(services):
    inbox, content, _ = services
    item, folder, job = queued(services)
    inbox._finish(item, item["revision"], True)
    saved = content.get(item["id"])
    assert saved["tags"] == ["面试"] and saved["processing_status"] == "ready"
    assert saved["status"] == "knowledge" and saved["folder_id"] == folder["id"]
    assert inbox.get_archive_job(job["job_id"])["status"] == "completed"
    assert saved["revision"] == item["revision"] + 1


def test_manual_revision_change_during_metadata_is_preserved_and_job_conflicts(services):
    inbox, content, _ = services
    item, _, job = queued(services)

    def metadata(_item):
        content.update(item["id"], {"title": "用户编辑", "tags": ["人工"]})
        return {"title": "自动标题", "summary": "自动摘要", "tags": ["面试"]}

    inbox.metadata = metadata
    inbox._finish(item, item["revision"], True)
    saved = content.get(item["id"])
    assert saved["title"] == "用户编辑" and saved["tags"] == ["人工"]
    assert saved["status"] == "inbox"
    assert inbox.get_archive_job(job["job_id"])["status"] == "conflict"


def test_deleted_target_during_metadata_fails_safely_without_archiving(services):
    inbox, content, knowledge = services
    item, folder, job = queued(services)
    knowledge.delete_folder(folder["id"])
    inbox._finish(item, item["revision"], True)
    assert inbox.get_archive_job(job["job_id"])["status"] == "failed"
    assert inbox.get_archive_job(job["job_id"])["error"] == "folder_not_found"
    assert content.get(item["id"])["status"] == "inbox"


def test_failed_metadata_never_claims_archival_completed(services):
    inbox, content, _ = services
    item, _, job = queued(services)

    def fail(_item):
        raise RuntimeError("untrusted provider details")

    inbox.metadata = fail
    inbox._finish(item, item["revision"], True)
    actual = inbox.get_archive_job(job["job_id"])
    assert actual["status"] == "failed" and actual["error"] == "metadata_failed"
    assert "untrusted provider" not in str(actual)
    assert content.get(item["id"])["status"] == "inbox"


def test_metadata_cancellation_leaves_explicit_cancelled_archive_status(services):
    inbox, content, _ = services
    item, _, job = queued(services)

    def cancel(_item):
        raise TurnCancelled()

    inbox.metadata = cancel
    inbox._finish(item, item["revision"], True)
    assert inbox.get_archive_job(job["job_id"])["status"] == "cancelled"
    assert content.get(item["id"]) == item


def test_restart_recovers_ready_metadata_without_another_model_call(services):
    inbox, content, knowledge = services
    item, folder, job = queued(services)
    content.update(item["id"], {"processing_status": "ready", "tags": ["面试"]}, internal=True)
    with content.store.connect() as db:
        db.execute("UPDATE inbox_jobs SET state='done' WHERE item_id=?", (item["id"],))
    restarted = InboxService(
        content, knowledge, metadata=lambda item: pytest.fail("ready job must not regenerate")
    )
    try:
        restarted.start()
        deadline = time.monotonic() + 2
        while (
            restarted.get_archive_job(job["job_id"])["status"] in {"pending", "running"}
            and time.monotonic() < deadline
        ):
            Event().wait(0.01)
        assert restarted.get_archive_job(job["job_id"])["status"] == "completed"
        assert content.get(item["id"])["folder_id"] == folder["id"]
    finally:
        restarted.shutdown()


def test_stale_archive_enqueue_does_not_create_a_job(services):
    inbox, content, _ = services
    item, folder, _ = queued(services)
    content.update(item["id"], {"title": "新版本"})
    with pytest.raises(WebError) as failure:
        inbox.queue_archive(item["id"], folder["id"], item["revision"] + 99)
    assert failure.value.code == "conflict"


def test_two_service_workers_do_not_run_metadata_or_archive_twice(services):
    inbox, content, knowledge = services
    item, folder, job = queued(services)
    entered, release = Event(), Event()
    calls = []

    def metadata(_item):
        calls.append(_item["id"])
        entered.set()
        release.wait(2)
        return {"title": "一次处理", "summary": "资料", "tags": ["面试"]}

    inbox.metadata = metadata
    other = InboxService(content, knowledge, metadata=metadata)
    try:
        inbox.start()
        assert entered.wait(1)
        other.start()
        Event().wait(0.1)
        release.set()
        deadline = time.monotonic() + 2
        while (
            inbox.get_archive_job(job["job_id"])["status"] in {"pending", "running"}
            and time.monotonic() < deadline
        ):
            Event().wait(0.01)
        assert inbox.get_archive_job(job["job_id"])["status"] == "completed"
        assert calls == [item["id"]]
        saved = content.get(item["id"])
        assert saved["revision"] == item["revision"] + 1
        assert saved["folder_id"] == folder["id"] and saved["tags"] == ["面试"]
    finally:
        release.set()
        other.shutdown()
        inbox.shutdown()


def test_ready_item_queued_after_metadata_finished_is_archived_by_owned_worker(services):
    inbox, content, knowledge = services
    folder = knowledge.create_folder({"name": "面试"})
    item = inbox.import_item({"text": "https://example.com/interview", "use_ai": True})
    inbox._finish(item, item["revision"], True)
    with content.store.connect() as db:
        db.execute("UPDATE inbox_jobs SET state='done' WHERE item_id=?", (item["id"],))
    job = inbox.queue_archive(item["id"], folder["id"], item["revision"])
    inbox.start()
    deadline = time.monotonic() + 2
    while (
        inbox.get_archive_job(job["job_id"])["status"] in {"pending", "running"}
        and time.monotonic() < deadline
    ):
        Event().wait(0.01)
    assert inbox.get_archive_job(job["job_id"])["status"] == "completed"
    assert content.get(item["id"])["folder_id"] == folder["id"]


def test_archive_commit_and_receipt_survive_interruption_once(services, monkeypatch):
    inbox, content, _ = services
    item, folder, job = queued(services)
    content.update(item["id"], {"processing_status": "ready", "tags": ["面试"]}, internal=True)
    with content.store.connect() as db:
        db.execute(
            "UPDATE inbox_archive_jobs SET status='running' WHERE job_id=?", (job["job_id"],)
        )
        db.execute("UPDATE inbox_jobs SET state='done' WHERE item_id=?", (item["id"],))
    update = content.update

    def interrupt_after_commit(*args, **kwargs):
        result = update(*args, **kwargs)
        if kwargs.get("on_persist"):
            raise SystemExit("interrupted after atomic commit")
        return result

    monkeypatch.setattr(content, "update", interrupt_after_commit)
    with pytest.raises(SystemExit):
        inbox._finish_archives()
    monkeypatch.setattr(content, "update", update)
    inbox.start()
    deadline = time.monotonic() + 2
    while (
        inbox.get_archive_job(job["job_id"])["status"] in {"pending", "running"}
        and time.monotonic() < deadline
    ):
        Event().wait(0.01)
    assert inbox.get_archive_job(job["job_id"])["status"] == "completed"
    assert content.get(item["id"])["revision"] == item["revision"] + 1


def test_dead_process_owner_can_be_reclaimed_before_lease_timeout(services, monkeypatch):
    inbox, content, _ = services
    item, folder, job = queued(services)
    content.update(item["id"], {"processing_status": "ready"}, internal=True)
    with content.store.connect() as db:
        db.execute("UPDATE inbox_jobs SET state='done' WHERE item_id=?", (item["id"],))
        db.execute(
            "INSERT INTO inbox_worker_owner VALUES(1,?,?)", ("1234:dead-token", time.time() + 120)
        )
    monkeypatch.setattr(inbox, "_owner_alive", lambda owner: False, raising=False)
    inbox.start()
    deadline = time.monotonic() + 2
    while (
        inbox.get_archive_job(job["job_id"])["status"] in {"pending", "running"}
        and time.monotonic() < deadline
    ):
        Event().wait(0.01)
    assert inbox.get_archive_job(job["job_id"])["status"] == "completed"
    assert content.get(item["id"])["folder_id"] == folder["id"]


def test_manual_edit_between_archive_snapshot_and_commit_wins(services, monkeypatch):
    inbox, content, _ = services
    item, _, job = queued(services)
    original = content.update

    def edit_before_archive(item_id, changes, **kwargs):
        if changes.get("status") == "knowledge":
            original(item_id, {"title": "最后一刻人工编辑"})
        return original(item_id, changes, **kwargs)

    monkeypatch.setattr(content, "update", edit_before_archive)
    inbox._finish(item, item["revision"], True)
    saved = content.get(item["id"])
    assert saved["title"] == "最后一刻人工编辑" and saved["status"] == "inbox"
    assert inbox.get_archive_job(job["job_id"])["status"] == "conflict"


def test_folder_deleted_between_archive_snapshot_and_commit_fails_safely(services, monkeypatch):
    inbox, content, knowledge = services
    item, folder, job = queued(services)
    original = content.update

    def delete_before_archive(item_id, changes, **kwargs):
        if changes.get("status") == "knowledge":
            knowledge.delete_folder(folder["id"])
        return original(item_id, changes, **kwargs)

    monkeypatch.setattr(content, "update", delete_before_archive)
    inbox._finish(item, item["revision"], True)
    saved = content.get(item["id"])
    actual = inbox.get_archive_job(job["job_id"])
    assert saved["status"] == "inbox" and saved["folder_id"] is None
    assert actual["status"] == "failed" and actual["error"] == "folder_not_found"


def wait_batch(inbox, job_id):
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        batch = inbox.get_archive_job(job_id)
        if batch["status"] not in {"pending", "running"}:
            return batch
        Event().wait(0.01)
    pytest.fail("durable batch did not finish")


def test_failed_batch_retry_resumes_original_archive(services):
    inbox, content, _ = services
    item = content.create({"title": "retry", "content": "material"})
    batch = inbox.queue_archive_batch([item["id"]])
    inbox._archive_status(batch["items"][0]["job_id"], "failed", "metadata_failed")
    with content.store.connect() as db:
        db.execute("UPDATE inbox_jobs SET state='done' WHERE item_id=?", (item["id"],))
    inbox.retry(item["id"])
    assert inbox.get_archive_job(batch["job_id"])["status"] == "pending"
    inbox.start()
    assert wait_batch(inbox, batch["job_id"])["status"] == "completed"
    assert content.get(item["id"])["status"] == "knowledge"


def test_running_archive_cannot_claim_manual_move_as_its_commit(services):
    inbox, content, _ = services
    item = content.create({"title": "manual", "content": "material"})
    batch = inbox.queue_archive_batch([item["id"]])
    job = batch["items"][0]
    inbox._archive_status(job["job_id"], "running")
    with content.store.connect() as db:
        db.execute("UPDATE inbox_jobs SET state='done' WHERE item_id=?", (item["id"],))
    edited = content.update(item["id"], {"status": "knowledge", "title": "人工修改"})
    inbox._finish_archives()
    assert inbox.get_archive_job(job["job_id"])["status"] == "conflict"
    assert content.get(item["id"]) == edited


def test_ai_archive_batch_is_pending_replay_safe_and_restarts_with_rules(services):
    inbox, content, knowledge = services
    assert hasattr(inbox, "queue_archive_batch")
    folder = knowledge.create_folder({"name": "面试", "tags": ["面试"]})
    items = [
        content.create({"title": "资料", "content": "资料"}),
        content.create({"title": "其他", "content": "其他"}),
    ]
    batch = inbox.queue_archive_batch([item["id"] for item in items])
    assert batch["status"] == "pending" and batch["counts"]["pending"] == 2
    assert inbox.queue_archive_batch([item["id"] for item in items])["job_id"] == batch["job_id"]

    def metadata(item):
        return {
            "title": "AI资料",
            "summary": "摘要",
            "tags": ["面试"] if item["id"] == items[0]["id"] else ["其他"],
        }

    resumed = InboxService(content, knowledge, metadata=metadata)
    try:
        resumed.start()
        actual = wait_batch(resumed, batch["job_id"])
        assert actual["status"] == "completed" and actual["counts"]["completed"] == 2
        assert content.get(items[0]["id"])["folder_id"] == folder["id"]
        assert content.get(items[1]["id"])["folder_id"] is None
        assert all(content.get(item["id"])["status"] == "knowledge" for item in items)
        assert all(content.get(item["id"])["ai_processed"] for item in items)
    finally:
        resumed.shutdown()


def test_ai_batch_keeps_item_failure_cancellation_and_manual_conflict(services):
    inbox, content, _ = services
    assert hasattr(inbox, "queue_archive_batch")
    items = [content.create({"title": str(index), "content": str(index)}) for index in range(4)]
    batch = inbox.queue_archive_batch([item["id"] for item in items])

    def metadata(item):
        if item["id"] == items[0]["id"]:
            raise RuntimeError("provider secret")
        if item["id"] == items[1]["id"]:
            raise TurnCancelled()
        if item["id"] == items[2]["id"]:
            content.update(item["id"], {"title": "人工"})
        return {"title": "AI", "summary": "摘要", "tags": ["未匹配"]}

    inbox.metadata = metadata
    inbox.start()
    actual = wait_batch(inbox, batch["job_id"])
    assert actual["status"] == "partial"
    assert (
        actual["counts"]["failed"]
        == actual["counts"]["cancelled"]
        == actual["counts"]["conflict"]
        == 1
    )
    assert actual["counts"]["completed"] == 1 and "provider secret" not in str(actual)
    assert content.get(items[2]["id"])["title"] == "人工"
    assert all(content.get(item["id"])["status"] == "inbox" for item in items[:3])


def test_existing_explicit_archive_job_survives_nullable_target_migration(services):
    inbox, content, knowledge = services
    _, _, job = queued(services)
    assert hasattr(inbox, "queue_archive_batch")
    with content.store.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        db.execute("ALTER TABLE inbox_archive_jobs RENAME TO nullable_jobs")
        db.execute("""CREATE TABLE inbox_archive_jobs(
            job_id TEXT PRIMARY KEY,item_id TEXT NOT NULL,folder_id TEXT NOT NULL,
            revision INTEGER NOT NULL,status TEXT NOT NULL,error TEXT,
            created_at TEXT NOT NULL,updated_at TEXT NOT NULL,UNIQUE(item_id,revision))""")
        db.execute("INSERT INTO inbox_archive_jobs SELECT * FROM nullable_jobs")
        db.execute("DROP TABLE nullable_jobs")
    reopened = InboxService(content, knowledge)
    assert reopened.get_archive_job(job["job_id"]) == job
    with content.store.connect() as db:
        assert (
            next(
                row
                for row in db.execute("PRAGMA table_info(inbox_archive_jobs)")
                if row["name"] == "folder_id"
            )["notnull"]
            == 0
        )


def test_batch_submission_cancellation_rolls_back_partial_queue(services, monkeypatch):
    from xiliu.execution.cancellation import cancel_signal

    inbox, content, _ = services
    items = [content.create({"title": str(index), "content": str(index)}) for index in range(2)]
    signal = Event()
    original = content.get

    def snapshot(item_id):
        result = original(item_id)
        if item_id == items[-1]["id"]:
            signal.set()
        return result

    monkeypatch.setattr(content, "get", snapshot)
    token = cancel_signal.set(signal)
    try:
        with pytest.raises(TurnCancelled):
            inbox.queue_archive_batch([item["id"] for item in items])
    finally:
        cancel_signal.reset(token)
    assert [original(item["id"]) for item in items] == items
    with content.store.connect() as db:
        assert db.execute("SELECT COUNT(*) FROM inbox_archive_batches").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM inbox_archive_jobs").fetchone()[0] == 0


def test_accepted_batch_is_independent_of_later_turn_cancellation(services):
    from xiliu.execution.cancellation import cancel_signal

    inbox, content, _ = services
    item = content.create({"title": "资料", "content": "资料"})
    batch = inbox.queue_archive_batch([item["id"]])
    signal = Event()
    signal.set()
    token = cancel_signal.set(signal)
    try:
        inbox.start()
        actual = wait_batch(inbox, batch["job_id"])
        assert actual["status"] == "completed"
        assert content.get(item["id"])["status"] == "knowledge"
    finally:
        cancel_signal.reset(token)


def test_cancelled_metadata_keeps_exact_card_and_does_not_restart(services):
    inbox, content, knowledge = services
    item = content.create({"title": "原始标题", "content": "原文", "tags": ["原始标签"]})
    batch = inbox.queue_archive_batch([item["id"]])

    def cancelled(_item):
        raise TurnCancelled()

    inbox.metadata = cancelled
    inbox.start()
    assert wait_batch(inbox, batch["job_id"])["status"] == "cancelled"
    inbox.shutdown()
    assert content.get(item["id"]) == item
    resumed = InboxService(
        content, knowledge, metadata=lambda _item: pytest.fail("cancelled metadata restarted")
    )
    try:
        resumed.start()
        resumed.shutdown()
        assert resumed.get_archive_job(batch["job_id"])["status"] == "cancelled"
        assert content.get(item["id"]) == item
    finally:
        resumed.shutdown()
