"""Deterministic checks that reject receipts unrelated to the requested effects."""

import re
import sqlite3

from xiliu.agents.react import payload
from xiliu.core.checkpoint import workspace_manifest
from xiliu.tools.workspace import resolve_workspace_path


def goal_failure(state, events):
    task = state["task"]
    successful = [e for e in events if e.get("ok")]
    writes = [e for e in successful if e["tool"] in {"file_write", "file_edit"}]
    latest = {e["args"].get("path"): e for e in writes}
    if re.search(r"(?:md|markdown)\s*文件|\bmarkdown\s+file\b", task, re.I) and not any(
        str(path).lower().endswith(".md") for path in latest
    ):
        return "Missing requested Markdown file artifact"
    for path, event in latest.items():
        try:
            target = resolve_workspace_path(state["workspace"], path)
            text = target.read_text(encoding="utf-8")
            args = event["args"]
            if event["tool"] == "file_write" and text != args.get("content"):
                return "Written artifact does not match persisted content"
            if (
                event["tool"] == "file_edit"
                and args.get("new_string")
                and args["new_string"] not in text
            ):
                return "Edited artifact does not contain the requested replacement"
        except (OSError, ValueError, TypeError):
            return "Cannot read back the workspace artifact"
    if re.search(r"移动.{0,30}文件|文件.{0,20}移动|\bmove\b.{0,40}\bfile", task, re.I):
        before = state.get("workspace_before", {})
        after = {e["path"]: e["sha256"] for e in workspace_manifest(state["workspace"])}
        removed = {digest for path, digest in before.items() if path not in after}
        added = {digest for path, digest in after.items() if path not in before}
        if not removed.intersection(added):
            return "Missing actual file move effects"
    if (
        re.search(r"修改.{0,15}(?:文件|代码)|代码.{0,15}修改|\bedit\b.{0,30}\bfile", task, re.I)
        and not writes
    ):
        return "A file read cannot prove requested edits"
    if re.search(r"检查代码|\bcheck\b.{0,20}\bcode", task, re.I) and not any(
        e["tool"] == "bash"
        and payload(e["output"]).get("exit_code") == 0
        and any(x in e["args"].get("argv", []) for x in ("compileall", "ruff", "pyright", "pytest"))
        for e in successful
    ):
        return "Missing actual successful code check"
    if (
        re.search(r"工作总结|work summary|weekly report", task, re.I)
        and not any(
            e["tool"] == "app"
            and e["args"].get("action_id") in {"tasks.list", "today.read", "inbox.list"}
            or e["tool"] == "file_read"
            for e in successful
        )
        and not state.get("context_summary", "").strip()
    ):
        return "Missing actual work records for the summary"
    if re.search(r"比较.{0,20}(?:文档|文章)|compare.{0,30}(?:documents|papers)", task, re.I):
        sources = {
            e.get("source_id")
            for e in state.get("evidence", [])
            if e.get("matched") and e.get("tool_ok")
        }
        if len(sources - {None, ""}) < 2:
            return "Comparison requires two distinct actual documents"
    if re.search(
        r"(?:建立|创建).{0,15}(?:研究)?数据库|(?:create|build).{0,25}database", task, re.I
    ):
        created = False
        before = state.get("workspace_before", {})
        for file in workspace_manifest(state["workspace"]):
            if not file["path"].lower().endswith((".db", ".sqlite", ".sqlite3")):
                continue
            if before.get(file["path"]) == file["sha256"]:
                continue
            if not any(e["tool"] == "bash" for e in successful):
                continue
            path = resolve_workspace_path(state["workspace"], file["path"])
            try:
                with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True) as db:
                    created = db.execute("PRAGMA integrity_check").fetchone()[0] == "ok" and bool(
                        db.execute(
                            "SELECT name FROM sqlite_master WHERE type='table' "
                            "AND name NOT LIKE 'sqlite_%'"
                        ).fetchall()
                    )
            except sqlite3.Error:
                continue
            if created:
                break
        if not created:
            return "Missing an actual persisted research database; a schema file is insufficient"
    return None
