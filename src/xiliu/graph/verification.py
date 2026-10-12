from __future__ import annotations

import re

from xiliu.agents.react import payload, unresolved_failures
from xiliu.execution.evidence import evidence_from_events


def _app_action_failure(state) -> str | None:
    """Verify app writes against the actual library, rather than workspace deliverables."""
    events = [
        event
        for event in state["tool_events"]
        if event.get("tool") == "app" and event.get("args", {}).get("operation") == "execute"
    ]
    if not events:
        return "Missing verified app action receipt"
    for event in events:
        receipt = payload(event.get("output", ""))
        if (
            not event.get("ok")
            or receipt.get("ok") is not True
            or not receipt.get("verification", {}).get("passed")
        ):
            return "App action did not complete a verified write"
    return None


def _persisted_automation(state) -> bool:
    return any(
        event.get("tool") == "app"
        and event.get("args", {}).get("action_id") == "automations.create"
        and payload(event.get("output", "")).get("verification", {}).get("passed")
        for event in state["tool_events"]
    )


def requirements_failure(state) -> str | None:
    if not state.get("execution_ok", state.get("supervisor_ok", False)):
        return "Execution did not finish a valid round"
    from xiliu.graph.routing import app_action

    if app_action(state["task"]):
        return _app_action_failure(state)
    task = state["task"].lower()
    automation_intent = bool(
        re.search(r"automation|scheduled? task|定时任务|自动任务|每日任务|提醒", task)
    )
    code_intent = bool(
        re.search(
            r"python|code|implement|build|fix|edit|pytest|test|文件|代码|编写|实现|修复|修改|测试",
            task,
        )
    )
    if automation_intent and not code_intent:
        return None if _persisted_automation(state) else "Missing persisted automation evidence"
    preference_events = [
        event
        for event in state["tool_events"]
        if event["agent"] == "planner" and event["tool"] == "preference_write"
    ]
    preference_only_intent = bool(
        re.match(
            r"^\s*(?:please\s+)?(?:remember|forget)\b"
            r"|^\s*(?:set|update)\b.*\bpreference\b"
            r"|^\s*(?:请)?(?:记住|忘记|设置偏好|更新偏好)",
            task,
        )
    )
    additional_action = bool(
        re.search(
            r"\b(?:and|then|also)\s+(?:implement|build|create|fix|edit|research|search)\b"
            r"|(?:并|同时)(?:实现|创建|修复|修改|搜索|研究)",
            task,
        )
    )
    preference_only_complete = bool(
        preference_only_intent
        and not additional_action
        and preference_events
        and preference_events[-1]["ok"]
    )
    todos_required = bool(state["todos"])
    if (
        todos_required
        and (not state["todos"] or any(t["status"] != "completed" for t in state["todos"]))
        and not preference_only_complete
    ):
        return "Todos are missing or incomplete"
    if preference_only_complete:
        return None
    research_task = re.sub(
        r"\b(?:no|without|do not|don't|never)\s+(?:web\s+)?(?:research|search)\b"
        r"|(?:不需要|无需|不要|禁止)(?:进行)?(?:联网)?(?:搜索|研究|查阅|联网)",
        "",
        task,
    )
    research_task = re.sub(r"研究数据库|research database", "database", research_task)
    agents = state["agent_results"]
    events = [
        e
        for e in state["tool_events"]
        if e["agent"] in {"code_agent", "subagent:code", "planner", "fast_react"}
    ]
    coding = bool(
        re.search(
            r"implement|code|python|build|tdd|fix|create|write|edit|refactor|debug"
            r"|实现|代码|编写|开发|修复|创建|修改|调试|重构",
            task,
        )
        or re.search(r"\.(?:py|js|ts|tsx|jsx|java|go|rs|rb|php|cs|cpp|c|h)\b", task)
    )
    code_results = [a for a in agents if a["agent"] == "code_agent"]
    if code_results and not code_results[-1]["ok"]:
        return "Latest codeAgent result failed"
    if (
        coding
        and not code_results
        and not any(
            e.get("ok") and e.get("tool") in {"file_read", "file_write", "file_edit", "bash"}
            for e in state["tool_events"]
        )
    ):
        return "Missing actual workspace execution evidence"
    search_results = [a for a in agents if a["agent"] == "search_agent"]
    actual = evidence_from_events(state["tool_events"])
    supported = any(e["tool_ok"] and e["matched"] and e["source_id"] for e in actual)
    from xiliu.graph.routing import external_scope, local_scope

    if (
        local_scope(task)
        and not external_scope(task)
        and not any(
            e["tool_ok"] and e["matched"] and e["source_type"] == "knowledge" for e in actual
        )
    ):
        return "Missing matched local Knowledge evidence"
    if (
        re.search(r"\bresearch\b|\bsearch\b|搜索|研究|查阅|联网", research_task)
        and not supported
        and (
            not search_results
            or not search_results[-1]["ok"]
            or not any(r["sources"] for r in state["research_notes"])
        )
    ):
        return "Missing successful research and source URLs"
    if unresolved_failures(events):
        return "Unresolved failed or incomplete tool action"
    last_write = max(
        (
            i
            for i, e in enumerate(events)
            if e["tool"] in {"file_write", "file_edit"}
            and e["ok"]
            and not str(e["args"].get("path", "")).endswith((".md", ".txt", ".html"))
        ),
        default=-1,
    )
    tdd = bool(re.search(r"tdd|test-driven|测试驱动", task))
    required = []
    if tdd or re.search(r"\btests?\b|pytest|测试", task):
        required.append("test_green")
    if re.search(r"demo|演示", task):
        required.append("demo")
    for phase in required:
        matches = [
            (i, e) for i, e in enumerate(events) if e["tool"] == "bash" and e["phase"] == phase
        ]
        if not matches:
            return f"Missing successful {phase} evidence"
        index, e = matches[-1]
        data = payload(e["output"])
        if not e["ok"] or data.get("exit_code") != 0 or index <= last_write:
            return f"Latest {phase} must succeed after file changes"
        if phase == "demo" and "test_green" in required:
            green = max(i for i, x in enumerate(events) if x["phase"] == "test_green")
            if index <= green:
                return "Demo must run after passing tests"
    if tdd:
        reds = [
            i
            for i, e in enumerate(events)
            if e["tool"] == "bash"
            and e["phase"] == "test_red"
            and payload(e["output"]).get("exit_code") in {1, 2}
            and not payload(e["output"]).get("timed_out")
            and not payload(e["output"]).get("truncated")
        ]
        if not any(red < last_write for red in reds):
            return "Missing ordered TDD red, implementation and green evidence"
    for checker in ("ruff", "pyright"):
        if checker in task:
            checks = [
                (i, e)
                for i, e in enumerate(events)
                if e["tool"] == "bash" and e["args"].get("argv", [])[1:3] == ["-m", checker]
            ]
            if not checks or not checks[-1][1]["ok"] or checks[-1][0] <= last_write:
                return f"Missing successful {checker} check after file changes"
    return None
