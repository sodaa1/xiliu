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
    }
    assert tasks.create({"title": "Existing client"})["scope"] == "day"


def test_invalid_scope_and_missing_parent_are_rejected(tmp_path):
    tasks = TaskService(AppStore(tmp_path))
    with pytest.raises(WebError):
        tasks.create({"title": "Bad", "scope": "unknown"})
    with pytest.raises(WebError):
        tasks.create({"title": "Bad", "parent_id": "missing"})
