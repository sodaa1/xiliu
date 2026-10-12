"""The original 51 queries drive the production graph and real isolated App databases.

Only model and remote provider responses are controlled. Ambiguous requests have
explicit safe outcomes; a passing evaluation never means an ambiguous goal was completed.
"""

import json
import sqlite3
from pathlib import Path
from uuid import uuid4

import pytest
from langchain_core.messages import AIMessage

from xiliu.api.app import create_app
from xiliu.events import ErrorEvent, FinalEvent, VerifierEvent
from xiliu.runtime import Runtime

TASKS = [
    json.loads(line)
    for line in (Path(__file__).parents[1] / "fixtures/graph-v2/eval_50.jsonl")
    .read_text(encoding="utf-8")
    .splitlines()
]

# Independent oracle: intended execution class and whether missing parameters must block writes.
APP = {3, 4, 5, 6, 7, 8, 9, 10, 27, 37, 39}
FAST = {11, 12, 13, 14, 15, 30, 31, 34, 35, 41, 42, 45}
PLAN = {16, 17, 18, 19, 20, 23, 24, 25, 36, 38, 44, 46, 47, 50, 51}
CLARIFY = {26, 28, 29, 32, 33, 40, 43, 48, 49}
APP_BLOCKED = {3, 4, 7, 9, 10, 27, 39}
INCOMPLETE = APP_BLOCKED | CLARIFY | {11, 19, 35, 38}


def app_call(action, arguments=None):
    return {
        "name": "app",
        "args": {"operation": "execute", "action_id": action, "arguments": arguments or {}},
    }


class EvalModel:
    def __init__(self, task, item_id):
        self.task = task
        self.item_id = item_id
        self.index = 0

    def bind_tools(self, tools):
        return self

    def invoke(self, messages):
        prompt = str(messages[0].content)
        if "intent router" in prompt:
            return AIMessage(
                content=json.dumps({"intent": "task", "complexity": "bounded", "confidence": 1})
            )
        if "lightweight chat node" in prompt:
            return AIMessage(content="RAG 使用检索证据回答；State 保存工作流共享状态。")
        if "Verifier" in prompt:
            return AIMessage(content='{"status":"passed","reason":"Actual local evidence checked"}')
        identifier = self.task["id"]
        scripts = {
            11: [{"name": "file_read", "args": {"path": "../Desktop/paper.pdf"}}],
            12: [app_call("knowledge.search", {"query": "Agent"})],
            13: [app_call("inbox.list")],
            14: [{"name": "file_read", "args": {"path": "paper.txt"}}],
            15: [app_call("knowledge.search", {"query": "Agent"})],
            16: [
                app_call("inbox.list"),
                app_call(
                    "inbox.classify_selected",
                    {
                        "item_ids": [self.item_id],
                        "use_ai": False,
                    },
                ),
            ],
            17: [
                app_call("knowledge.search", {"query": "Agent"}),
                {
                    "name": "file_write",
                    "args": {
                        "path": "report.md",
                        "content": (
                            "# Agent research report\nAgent research evidence\nCompare Gr"
                            "aph state evidence with Agent coordination."
                        ),
                    },
                },
            ],
            18: [
                app_call("knowledge.search", {"query": "Agent"}),
                app_call("knowledge.folders.create", {"name": "AI研究资料"}),
                app_call("knowledge.folders.create", {"name": "论文"}),
                app_call("knowledge.folders.create", {"name": "实验"}),
                {
                    "name": "file_write",
                    "args": {
                        "path": "research-index.md",
                        "content": (
                            "# AI研究资料体系\n论文：保存证据与引用。\n"
                            "实验：记录问题、方法、结果。\n"
                            "来源：Agent research evidence; Graph state evidence."
                        ),
                    },
                },
            ],
            19: [
                app_call(
                    "knowledge.items.delete", {"item_id": self.item_id, "expected_revision": 1}
                )
            ],
            20: [
                app_call("knowledge.search", {"query": "Agent"}),
                {
                    "name": "file_write",
                    "args": {
                        "path": "research-plan.md",
                        "content": (
                            "# Research plan\nSources: Agent research evidence; Graph st"
                            "ate evidence.\nQuestion: compare agent coordination and gra"
                            "ph state.\nMethod: collect two documents, compare evidence,"
                            " run an experiment."
                        ),
                    },
                },
            ],
            23: [
                {"name": "skill_load", "args": {"skill_id": "skill:research"}},
                {
                    "name": "file_write",
                    "args": {
                        "path": "knowledge-workflow.md",
                        "content": (
                            "# 知识整理流程\n读取资料 -> 标注来源 -> "
                            "分类到论文/实验 -> 核对数据库 -> 人工确认删除。"
                        ),
                    },
                },
            ],
            24: [{"name": "capability_search", "args": {"query": "", "kind": "mcp"}}],
            25: [
                {"name": "skill_load", "args": {"skill_id": "skill:research"}},
                app_call("knowledge.search", {"query": "Agent"}),
            ],
            30: [{"name": "web_search", "args": {"query": self.task["query"]}}],
            31: [{"name": "web_search", "args": {"query": self.task["query"]}}],
            34: [app_call("inbox.list")],
            35: [app_call("knowledge.search", {"query": "AI"})],
            36: [
                app_call("tasks.list"),
                {
                    "name": "file_write",
                    "args": {
                        "path": "weekly.md",
                        "content": "# 本周工作总结\n买牛奶：未完成。暂无已完成工作记录。",
                    },
                },
            ],
            38: [app_call("automations.list")],
            41: [{"name": "capability_search", "args": {"query": "", "kind": "mcp"}}],
            42: [{"name": "capability_search", "args": {"query": "", "kind": "skill"}}],
            44: [
                {
                    "name": "file_edit",
                    "args": {
                        "path": "paper.txt",
                        "old_string": "Agent",
                        "new_string": "Graph Agent",
                    },
                }
            ],
            45: [{"name": "file_read", "args": {"path": "paper.txt"}}],
            46: [
                {
                    "name": "bash",
                    "args": {
                        "argv": ["python", "-m", "compileall", "-q", "project.py"],
                        "phase": "check",
                    },
                }
            ],
            47: [
                {
                    "name": "bash",
                    "args": {
                        "argv": ["python", "-m", "pytest", "test_project.py", "-q"],
                        "phase": "test_green",
                    },
                },
                {
                    "name": "file_write",
                    "args": {
                        "path": "test-report.md",
                        "content": (
                            "# Test report\nCommand: python -m pytest test_project.py -q"
                            "\nResult: 1 passed, exit code 0.\nScope: project.add(2, 3) ="
                            " 5."
                        ),
                    },
                },
            ],
            50: [app_call("knowledge.search", {"query": "Agent"})],
            51: [
                {
                    "name": "file_write",
                    "args": {
                        "path": "create_research.py",
                        "content": (
                            "import sqlite3\nwith sqlite3.connect('research.db') as db:\n"
                            "    db.execute('CREATE TABLE papers(id INTEGER PRIMARY KEY"
                            ", title TEXT NOT NULL, source TEXT NOT NULL)')\n    db.exec"
                            "ute('CREATE TABLE experiments(id INTEGER PRIMARY KEY, pape"
                            "r_id INTEGER REFERENCES papers(id), result TEXT)')\n"
                        ),
                    },
                },
                {
                    "name": "bash",
                    "args": {"argv": ["python", "create_research.py"], "phase": "other"},
                },
            ],
        }
        sequence = scripts.get(identifier, [])
        if identifier == 14:
            sequence = [
                *sequence,
                {
                    "name": "file_write",
                    "args": {
                        "path": "organized-paper.md",
                        "content": "# Organized paper\nSource paper.txt: Agent.",
                    },
                },
            ]
        if self.index < len(sequence):
            call = {**sequence[self.index], "id": f"eval-{identifier}-{self.index}"}
            self.index += 1
            return AIMessage(content="", tool_calls=[call])
        if identifier in PLAN:
            return AIMessage(
                content=json.dumps(
                    {
                        "summary": (
                            "Agent research evidence explains agent coordination; Graph"
                            " state evidence describes shared state. Result based on ac"
                            "tual tool data."
                        ),
                        "plan_summary": "Read evidence then perform scoped work",
                        "acceptance_criteria": ["Actual tool evidence"],
                        "ready_for_verification": True,
                    }
                )
            )
        return AIMessage(content="Result based on actual tool data")


@pytest.mark.parametrize("task", TASKS, ids=lambda task: f"eval-{task['id']:02}-{task['category']}")
def test_supplied_task_uses_real_graph_receipts_database_and_permissions(
    task, tmp_path, monkeypatch, record_property
):
    identifier = task["id"]
    skill = tmp_path / "skills/research"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        "---\nname: research\ndescription: Local research\n---\nUse actual local evidence.",
        encoding="utf-8",
    )
    if identifier in {21, 22}:
        app = create_app(data_dir=tmp_path, env_file=tmp_path / ".env")
        try:
            cid = app.state.store.create()["id"]
            app.state.store.append_message(cid, "assistant", "old context")
            if identifier == 22:
                # No active content means compression completes without a model/provider.
                app.state.store.clear_messages(cid)
            events = list(app.state.chat.stream_turn(cid, task["query"]))
            assert events[-1]["type"] == "final"
            assert not events[-1].get("metadata", {}).get("app_receipts")
            assert all(m["content"] != "old context" for m in app.state.store.messages(cid))
            record_property("task_id", identifier)
            record_property("query", task["query"])
            record_property("graph_path", "command_control")
            record_property("execution_status", "context_updated")
            record_property("verified", "control")
            record_property("tool_receipts", "[]")
        finally:
            app.state.app_services.close()
        return

    def remote_search(self, query, max_results=5):
        return json.dumps(
            {
                "ok": True,
                "query": query,
                "results": [
                    {
                        "url": "https://example.test/agent-paper",
                        "title": "Agent paper",
                        "content": "Research",
                    }
                ],
            }
        )

    monkeypatch.setattr("xiliu.tools.web_search_tool.WebSearchTool._run", remote_search)
    runtime = Runtime(
        object(), data_dir=tmp_path, checkpoint_mode="off", trace_mode="full", approval_mode="deny"
    )
    sid = str(uuid4())
    try:
        services = runtime._context(tmp_path).owner._app_services
        knowledge = services.content.create(
            {"title": "Agent AI", "content": "Agent research evidence", "status": "knowledge"}
        )
        second = services.content.create(
            {"title": "Graph Agent paper", "content": "Graph state evidence", "status": "knowledge"}
        )
        inbox = services.content.create(
            {"title": "AI Inbox", "content": "Agent note", "status": "inbox"}
        )
        services.tasks.create({"title": "买牛奶"})
        item = inbox if identifier == 16 else knowledge
        runtime._model = EvalModel(task, item["id"])
        from xiliu.tools.workspace import create_session_workspace

        workspace = create_session_workspace(tmp_path, sid)
        (workspace / "paper.txt").write_text("Agent", encoding="utf-8")
        (workspace / "project.py").write_text(
            "def add(a, b):\n    return a + b\n", encoding="utf-8"
        )
        (workspace / "test_project.py").write_text(
            "from project import add\n\ndef test_add():\n    assert add(2, 3) == 5\n",
            encoding="utf-8",
        )
        events = list(runtime.stream_session(task["query"], sid, "", max_attempts=1))
        assert not any(isinstance(e, ErrorEvent) for e in events), events
        assert isinstance(events[-1], FinalEvent)
        state, visits = runtime.last_state, runtime.last_node_path
        record_property("task_id", identifier)
        record_property("query", task["query"])
        record_property("graph_path", " -> ".join(visits))
        record_property("execution_status", state.get("execution_result", {}).get("status", "chat"))
        record_property("verified", state.get("execution_result", {}).get("verified", "chat"))
        record_property(
            "tool_receipts",
            json.dumps(
                [
                    {
                        "tool": e["tool"],
                        "ok": e["ok"],
                        "action": e["args"].get("action_id"),
                        "receipt_verified": json.loads(e["output"])
                        .get("verification", {})
                        .get("passed")
                        if e["tool"] == "app"
                        else None,
                    }
                    for e in state.get("tool_events", [])
                ],
                ensure_ascii=False,
            ),
        )
        want = (
            "app_executor"
            if identifier in APP
            else "fast_react"
            if identifier in FAST
            else "planner"
            if identifier in PLAN
            else "clarification"
            if identifier in CLARIFY
            else "chat_responder"
        )
        assert state["execution_path"] == want
        assert visits[0:2] == ["intent_router", "capability_router"]
        assert want in visits and visits[-1] == "final"
        if identifier not in {1, 2}:
            assert state["execution_result"]["verified"] is (identifier not in INCOMPLETE), state
        tools = state.get("tool_events", [])
        assert {e["event_id"] for e in tools} <= set(state.get("execution_ids", []))
        if identifier in CLARIFY or identifier in APP_BLOCKED:
            assert state.get("execution_result", {}).get("verified") is not True
            assert services.content.get(knowledge["id"])["status"] == "knowledge"
            assert services.content.get(inbox["id"])["status"] == "inbox"
            assert len(services.tasks.list()) == 1
        if identifier in FAST | PLAN:
            assert "capability_discovery" in visits
            assert "tool_execute" in visits and "state_collect" in visits
            assert any(isinstance(e, VerifierEvent) for e in events)
        for event in tools:
            if event["tool"] == "app" and event["ok"]:
                receipt = json.loads(event["output"])
                assert receipt["verification"]["passed"] is True
        if identifier == 11:
            assert tools[-1]["ok"] is False
            assert state["execution_result"]["verified"] is False
        if identifier == 16:
            assert services.content.get(inbox["id"])["status"] == "knowledge"
            assert state["execution_result"]["verified"] is True
        if identifier == 17:
            assert "Agent research evidence" in (workspace / "report.md").read_text()
            assert {knowledge["id"], second["id"]} <= {
                e["source_id"] for e in state["evidence"] if e.get("matched")
            }
        if identifier == 18:
            assert {"AI研究资料", "论文", "实验"} <= {
                f["name"] for f in services.knowledge.list_folders()
            }
            index = (workspace / "research-index.md").read_text(encoding="utf-8")
            assert "论文" in index and "实验" in index and "Graph state evidence" in index
        if identifier == 19:
            assert services.content.get(knowledge["id"])["id"] == knowledge["id"]
            assert state["execution_result"]["verified"] is False
        if identifier in {35, 38}:
            assert state["execution_result"]["verified"] is False
        if identifier in {23, 25}:
            assert any(e["tool"] == "skill_load" and e["ok"] for e in tools)
        if identifier == 23:
            assert "核对数据库" in (workspace / "knowledge-workflow.md").read_text(encoding="utf-8")
        if identifier == 36:
            assert "买牛奶" in (workspace / "weekly.md").read_text(encoding="utf-8")
            assert any(e["args"].get("action_id") == "tasks.list" and e["ok"] for e in tools)
        if identifier == 44:
            assert (workspace / "paper.txt").read_text() == "Graph Agent"
        if identifier in {46, 47}:
            actual = [json.loads(e["output"]) for e in tools if e["tool"] == "bash"]
            assert actual and actual[-1]["exit_code"] == 0
        if identifier == 47:
            assert "1 passed" in actual[-1]["stdout"]
            assert "exit code 0" in (workspace / "test-report.md").read_text()
        if identifier == 50:
            assert {knowledge["id"], second["id"]} <= {
                e["source_id"] for e in state["evidence"] if e.get("matched")
            }
        if identifier == 51:
            with sqlite3.connect(workspace / "research.db") as db:
                tables = {
                    row[0]
                    for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")
                }
                assert {"papers", "experiments"} <= tables
                assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        if identifier in {30, 31}:
            assert state["evidence"][0]["source_uri"] == "https://example.test/agent-paper"
        if identifier in {32, 33}:
            assert not tools
        # Independent read-back from SQLite, rather than the model's claimed result.
        with services.store.connect() as db:
            rows = db.execute("SELECT count(*) FROM tasks").fetchone()[0]
            assert rows == 1
            record_property("database_tasks", rows)
        record_property(
            "database_state",
            json.dumps(
                {
                    "inbox_status": services.content.get(inbox["id"])["status"],
                    "knowledge_status": services.content.get(knowledge["id"])["status"],
                    "folders": [f["name"] for f in services.knowledge.list_folders()],
                },
                ensure_ascii=False,
            ),
        )
    finally:
        runtime.close()
