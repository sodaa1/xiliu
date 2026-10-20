from datetime import UTC, datetime

import pytest

from xiliu.api.errors import WebError
from xiliu.api.services.tasks import TaskService
from xiliu.api.store import AppStore


def test_goal_week_day_hierarchy_is_durable_and_delete_detaches_children(tmp_path):
    store = AppStore(tmp_path)
    tasks = TaskService(store)
    goal = tasks.create({"title": "Learn Japanese", "scope": "goal"})
    week = tasks.create({"title": "Chapter one", "scope": "week", "parent_id": goal["id"]})
    day = tasks.create({"title": "Ten words", "parent_id": week["id"]})
    assert day["scope"] == "day"
    assert TaskService(store).list()[0]["parent_id"] == week["id"]
    with pytest.raises(WebError):
        tasks.update(goal["id"], {"parent_id": day["id"]})
    with pytest.raises(WebError):
        tasks.update(week["id"], {"scope": "day"})
    tasks.delete(week["id"])
    assert next(t for t in tasks.list() if t["id"] == day["id"])["parent_id"] is None


def test_old_tasks_migrate_without_losing_title_completion_or_date(tmp_path):
    store = AppStore(tmp_path)
    with store.connect() as db:
        db.execute(
            "CREATE TABLE tasks (id TEXT PRIMARY KEY,title TEXT,completed "
            "INTEGER,due_at TEXT,created_at TEXT,updated_at TEXT)"
        )
        db.execute("INSERT INTO tasks VALUES('legacy','Keep me',1,'2026-10-15','a','a')")
    tasks = TaskService(store)
    assert tasks.list()[0] == {
        "id": "legacy",
        "title": "Keep me",
        "completed": True,
        "due_at": "2026-10-15",
        "created_at": "a",
        "updated_at": "a",
        "scope": "day",
        "parent_id": None,
        "status": "completed",
        "completed_at": None,
        "starts_at": None,
        "description": "",
        "category": "",
        "priority": "normal",
        "tags": [],
        "reminder_minutes": None,
    }
    assert tasks.create({"title": "Existing client"})["scope"] == "day"


def test_invalid_scope_and_missing_parent_are_rejected(tmp_path):
    tasks = TaskService(AppStore(tmp_path))
    with pytest.raises(WebError):
        tasks.create({"title": "Bad", "scope": "unknown"})
    with pytest.raises(WebError):
        tasks.create({"title": "Bad", "parent_id": "missing"})


def test_task_metadata_and_interval_survive_reload_and_partial_update(tmp_path):
    store = AppStore(tmp_path)
    tasks = TaskService(store)
    task = tasks.create(
        {
            "title": " Write proposal ",
            "status": "in_progress",
            "description": "Outline milestones",
            "category": "工作",
            "priority": "important",
            "tags": [" planning ", "writing", "planning"],
            "starts_at": "2026-10-18T09:00:00+08:00",
            "due_at": "2026-10-18T10:00:00+08:00",
            "reminder_minutes": 15,
        }
    )
    assert task["title"] == "Write proposal"
    assert task["completed"] is False
    assert task["completed_at"] is None
    assert task["tags"] == ["planning", "writing"]
    assert TaskService(store).list()[0] == task
    updated = tasks.update(task["id"], {"title": "Updated"})
    for field in (
        "status",
        "description",
        "category",
        "priority",
        "tags",
        "starts_at",
        "due_at",
        "reminder_minutes",
    ):
        assert updated[field] == task[field]
    cleared = tasks.update(
        task["id"], {"starts_at": None, "due_at": None, "reminder_minutes": None, "tags": []}
    )
    assert cleared["starts_at"] is None and cleared["due_at"] is None
    assert cleared["tags"] == []


def test_completion_transitions_capture_actual_time_and_legacy_bool_works(tmp_path):
    tasks = TaskService(AppStore(tmp_path))
    task = tasks.create({"title": "Future plan", "due_at": "2027-10-18"})
    before = datetime.now(UTC)
    done = tasks.update(task["id"], {"status": "completed"})
    after = datetime.now(UTC)
    assert done["completed"] is True
    assert before <= datetime.fromisoformat(done["completed_at"]) <= after
    renamed = tasks.update(task["id"], {"description": "keep timestamp"})
    assert renamed["completed_at"] == done["completed_at"]
    restored = tasks.update(task["id"], {"completed": False})
    assert restored["status"] == "not_started" and restored["completed_at"] is None
    explicit = tasks.update(
        task["id"], {"completed": True, "completed_at": "2026-10-17T16:00:00+08:00"}
    )
    assert explicit["status"] == "completed"
    assert explicit["completed_at"] == "2026-10-17T16:00:00+08:00"
    assert tasks.create({"title": "Done", "status": "completed"})["completed_at"] is not None


@pytest.mark.parametrize(
    "metadata",
    [
        {"status": "unknown"},
        {"priority": "unknown"},
        {"description": "x" * 501},
        {"description": None},
        {"category": "x" * 33},
        {"category": None},
        {"tags": "tag"},
        {"tags": [1]},
        {"tags": [""]},
        {"tags": ["x" * 33]},
        {"tags": [str(i) for i in range(11)]},
        {"reminder_minutes": 10},
        {"reminder_minutes": True},
        {"reminder_minutes": 15},
        {"starts_at": "not a date"},
        {"completed_at": "not a date"},
        {"starts_at": "2026-10-19", "due_at": "2026-10-18"},
        {"status": "completed", "completed": False},
        {"status": "in_progress", "completed": True},
        {"completed_at": "2026-10-17T16:00:00+08:00"},
    ],
)
def test_invalid_metadata_is_rejected(tmp_path, metadata):
    tasks = TaskService(AppStore(tmp_path))
    with pytest.raises(WebError):
        tasks.create({"title": "Invalid", **metadata})


def test_interval_validation_uses_existing_values_and_handles_mixed_timezones(tmp_path):
    tasks = TaskService(AppStore(tmp_path))
    task = tasks.create(
        {
            "title": "Range",
            "starts_at": "2026-10-18T09:00:00",
            "due_at": "2026-10-18T10:00:00+08:00",
            "reminder_minutes": 0,
        }
    )
    with pytest.raises(WebError):
        tasks.update(task["id"], {"starts_at": "2026-10-19"})
    with pytest.raises(WebError):
        tasks.update(task["id"], {"starts_at": None, "due_at": None})
    aware = tasks.create(
        {
            "title": "Zone",
            "starts_at": "2026-10-18T09:00:00+08:00",
            "due_at": "2026-10-18T02:00:00+00:00",
        }
    )
    assert aware["starts_at"] == "2026-10-18T09:00:00+08:00"
