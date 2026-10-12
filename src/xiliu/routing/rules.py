"""Conservative intent rules; object names and source text never grant permission."""

import re
from typing import Literal

from xiliu.graph.state import StructuredIntent


def intent(
    kind: Literal["chat", "task", "control", "clarification"] = "task",
    domain="workspace",
    action="",
    complexity: Literal["simple", "bounded", "multi_step"] = "bounded",
    **extra,
):
    return StructuredIntent(
        intent=kind,
        domain=domain,
        action=action,
        complexity=complexity,
        source="rule",
        preferred_capability="",
        confidence=1.0,
        **extra,
    )


def match_rules(task: str) -> StructuredIntent | None:
    from xiliu.app.intent import resolve_intent
    from xiliu.graph.routing import external_scope, local_scope

    if re.search(r"删除所有数据|清空全部数据|delete all data|wipe everything", task, re.I):
        return intent("clarification", "security", complexity="simple")
    if re.fullmatch(
        r"\s*(?:删除它|整理一下|运行一个Skill|修改模型设置|只使用本地知识库回答|"
        r"不要联网寻找资料|恢复之前任务|继续上一次分析)[。！!？?]?\s*",
        task,
        re.I,
    ):
        return intent("clarification", complexity="simple")
    if re.search(
        r"批量|过去.{0,10}(?:月|周)|多个来源|多来源|多篇|研究计划|资料体系|"
        r"报告|工作总结|研究数据库|比较.{0,15}(?:文档|文章)|"
        r"\b(?:implement|refactor|debug|fix|tdd|report|multiple sources)\b|"
        r"实现|修复|重构|检查代码|代码.*修改|创建每日",
        task,
        re.I,
    ):
        return intent(complexity="multi_step")
    if re.search(
        r"知识库里.{0,20}资料|搜索我的收藏|总结我的Inbox|整理.{0,10}文件|"
        r"移动桌面|查找并整理|读取项目文件|查看MCP列表|查看Skill列表",
        task,
        re.I,
    ):
        return intent(domain="knowledge" if local_scope(task) else "workspace")
    if re.search(r"最近保存|recently saved", task, re.I):
        return intent(domain="knowledge")
    if external_scope(task) or re.search(r"搜索最新论文", task):
        return intent(domain="network")
    app = resolve_intent(task)
    if app is not None:
        if app.kind == "explain":
            return intent(domain=app.domain, action="app:explain", complexity="simple")
        return intent(domain=app.domain, action=app.action_id or "app:clarify", complexity="simple")
    if re.search(r"查看今天任务|创建Knowledge文件夹", task, re.I):
        return intent(
            domain="tasks" if "任务" in task else "knowledge",
            action="today.read" if "任务" in task else "knowledge.folders.create",
            complexity="simple",
        )
    if local_scope(task):
        return intent(domain="knowledge")
    if re.match(r"\s*(?:解释什么是|什么是|LangGraph中的|\bexplain\b|\bwhat is\b)", task, re.I):
        return intent("chat", "general", complexity="simple")
    if re.search(
        r"文件|代码|归档|保存|测试|工作区|automation|workspace|pytest|file|code", task, re.I
    ):
        return intent()
    return None
