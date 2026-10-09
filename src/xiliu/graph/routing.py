"""Explainable mode routing. Source scope never implies permission to go online."""

from __future__ import annotations

import re


def local_scope(task: str) -> bool:
    return bool(
        re.search(
            r"我的.{0,30}?(?:收藏|资料|笔记)|我收藏|我保存|本地知识|知识库|Knowledge|"
            r"知识标签|之前保存|本地资料|"
            r"\b(?:my saved|my bookmarks|local knowledge|knowledge library)\b",
            task,
            re.I,
        )
    )


def external_scope(task: str) -> bool:
    denied = re.search(
        r"(?:不要|不允许|禁止|无需|不需要|不|别)\s*(?:进行)?\s*(?:联网|上网|网络搜索|网上查)"
        r"|\b(?:no|without|never|do not|don\x27t)\s+(?:use\s+)?"
        r"(?:internet|online|web\s+search|network)(?:\s+access)?\b",
        task,
        flags=re.I,
    )
    if denied:
        return False
    if local_scope(task) and not re.search(
        r"联网|网上查|网络资料|外部|结合.*最新|\b(?:online|internet|web search)\b", task, re.I
    ):
        return False
    return bool(
        re.search(
            r"联网|网上查|网络资料|最新.*(?:新闻|资讯)|今天.*新闻|"
            r"\b(?:web search|online|latest news|internet)\b",
            task,
            re.I,
        )
    )


def app_action(task: str) -> bool:
    scope = local_scope(task) or bool(re.search(r"Inbox|收件箱|卡片|归类", task, re.I))
    action = re.search(
        r"收录|导入|存入|归类|创建.*卡片|"
        r"(?<!我)(?<!的)(?:保存|收藏)(?:到|至|进)|"
        r"^(?:请|帮我|帮忙)?(?:保存|收藏)|\b(?:import|classify|save)\b",
        task,
        re.I,
    )
    code = re.search(
        r"代码|编写|实现|开发|重构|\b(?:python|code|script|implement|build)\b", task, re.I
    )
    return bool(scope and action and not code)


def mode_router_node(state) -> dict:
    requested = state.get("requested_mode") or state.get("mode")
    task = state["task"]
    match = re.match(r"^\s*/(fast|standard|deep)\b", task, re.I)
    requested = requested or (match.group(1).lower() if match else None)
    if app_action(task) and requested in {None, "fast"}:
        mode, reason = "standard", "App mutation requires import/classification tools"
    elif requested in {"fast", "standard", "deep"}:
        mode, reason = requested, "Explicit user mode"
    elif requested:
        mode, reason = "standard", "Invalid requested mode; conservative fallback"
    elif re.search(
        r"跨.*Agent|深度研究|复杂代码|多来源|比较多篇|解释分歧|"
        r"\b(?:deep research|multi.agent|multiple sources)\b",
        task,
        re.I,
    ):
        mode, reason = "deep", "Multiple sources or complex analysis"
    elif re.search(
        r"报告|整理.*篇|实现|修复|修改|测试|产物|收录|导入|存入|归类|创建.*卡片|"
        r"\b(?:implement|fix|test|report|import|classify|save)\b",
        task,
        re.I,
    ):
        mode, reason = "standard", "Deliverable or multiple steps with acceptance criteria"
    elif local_scope(task) or external_scope(task):
        mode, reason = "fast", "Single retrieval task"
    else:
        mode, reason = "standard", "Conservative fallback for an unclassified task"
    return {"intent": "task", "mode": mode, "route_reason": reason}


def mode_route(state) -> str:
    return {"fast": "fast_react", "deep": "supervisor"}.get(state.get("mode"), "planner")
