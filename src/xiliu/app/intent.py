"""Small explicit command grammar; ambiguous language gets one typed parse, never guesses."""

from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

type Domain = Literal[
    "tasks", "feed", "inbox", "knowledge", "preferences", "automations", "conversations", "settings"
]

DOMAINS: dict[Domain, str] = {
    "automations": r"自动化|自动任务|定时任务|\bautomations?\b",
    "tasks": r"待办|todo|\btasks?\b",
    "feed": r"feed|资讯",
    "inbox": r"inbox|收件箱",
    "knowledge": r"知识库|knowledge|文件夹",
    "preferences": r"个人设置|偏好|外观|昵称|邮箱|简介|头像|主题|字号|字体|密度|动画|preferences",
    "conversations": r"会话|对话|conversations?",
}
VERBS = {
    "create": r"创建|新建|新增|添加|加入|\b(?:create|add|new)\b",
    "delete": r"删除|移除|清空|\b(?:delete|remove|clear)\b",
    "rename": r"改名|重命名|改为|修改|\b(?:rename|update|edit)\b",
    "read": r"查看|列出|浏览|看看|有什么|\b(?:list|show|view|browse)\b",
    "import": r"导入|放入|放进|放到|收录|收藏|保存|\b(?:import|save)\b",
    "classify": r"分类|归类|整理|归入|搬到|归档|移到|\b(?:classify|archive|organize|move)\b",
    "restore": r"恢复|重新打开|取消隐藏|\b(?:restore|reopen|unhide)\b",
    "complete": r"完成|做完|勾选|\b(?:complete|finish|done)\b",
    "refresh": r"刷新|\brefresh\b",
    "hide": r"隐藏|\bhide\b",
    "retry": r"重试|\bretry\b",
    "enable": r"开启|启用|\b(?:enable|resume)\b",
    "disable": r"暂停|关闭|停用|\b(?:disable|pause)\b",
}
URL = re.compile(r"https?://[^\s<>，。；,\"'“‘\u4e00-\u9fff]+", re.I)
QUOTED = re.compile(r"[\"'“‘「](.*?)[\"'”’」]")


class AppIntent(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    kind: Literal["read", "write", "workflow", "explain", "clarify"]
    domain: Domain
    action_id: str | None = None
    arguments: dict[str, Any] = Field(default_factory=dict)
    selector: str | None = None
    scope: Literal["single", "all"] = "single"
    confidence: float = Field(default=1.0, ge=0, le=1)
    clarification: str = ""


def _has(verb: str, text: str) -> bool:
    return bool(re.search(VERBS[verb], text, re.I))


def explicit_ai_metadata(text: str) -> bool:
    grammar = QUOTED.sub("", URL.sub("", text))
    if re.search(
        r"(?:不用|无需|不需要|不要|禁止|别)\s*(?:使用|用)?\s*(?:AI|人工智能)"
        r"|\b(?:without|no|not using|don't use|do not use)\s+AI\b",
        grammar,
        re.I,
    ):
        return False
    return bool(
        re.search(
            r"(?:(?<![A-Za-z0-9_])AI(?![A-Za-z0-9_])|人工智能)\s*(?:来|帮我)?\s*"
            r"(?:生成|提取|整理|创建)\s*(?:标签|元数据)"
            r"|(?:生成|提取|整理)\s*(?:标签|元数据)\s*(?:时)?\s*(?:用|使用|通过)\s*"
            r"(?:(?<![A-Za-z0-9_])AI(?![A-Za-z0-9_])|人工智能)"
            r"|\b(?:generate|extract)\s+(?:tags|metadata)\s+(?:using|with)\s+AI\b",
            grammar,
            re.I,
        )
    )


def explicit_title_fetch(text: str) -> bool:
    grammar = QUOTED.sub("", re.sub(r"https?://[^\s<>，。；,]+", "", text, flags=re.I))
    if re.search(
        r"(?:不要|不用|无需|不需要|不|禁止|别)\s*(?:联网)?\s*抓取标题"
        r"|\b(?:without|not|don't|do not)\s+fetch\s+(?:the\s+)?title\b",
        grammar,
        re.I,
    ):
        return False
    return bool(re.search(r"抓取标题|\bfetch\s+(?:the\s+)?title\b", grammar, re.I))


def resolve_intent(text: str) -> AppIntent | None:
    text = re.sub(r"^\s*/(?:fast|standard|deep)\s+", "", text, flags=re.I).strip()
    from xiliu.graph.routing import capability_command

    if capability_command(text):
        return None
    quotes = QUOTED.findall(text)
    urls = [match.rstrip(").]）") for match in URL.findall(text)]
    grammar = QUOTED.sub("", URL.sub("", text))
    domains: list[Domain] = [
        name for name, pattern in DOMAINS.items() if re.search(pattern, grammar, re.I)
    ]
    if not domains:
        return None
    domain: Domain = domains[0]
    # Link-only/network prohibitions constrain the requested operation, not its existence.
    guards = re.sub(r"(?:不要|不用|无需|不需要|不)\s*(?:克隆|联网|抓取|上网)", "", grammar)
    if re.search(
        r"不要|(?<!分)(?<!告)别(?=删除|添加|创建|修改|移动|导入|归类|保存|操作|执行)|不想|禁止|如果|假设|解释|怎么|如何|应该|能否|可不可以|"
        r"\b(?:do not|don't|never|explain|how to|what if|if I)\b",
        guards,
        re.I,
    ):
        return AppIntent(kind="explain", domain=domain)
    if re.search(
        r"(?:写|编写|实现|开发|修复).*(?:代码|脚本|功能)|\b(?:implement|code|script)\b",
        grammar,
        re.I,
    ):
        return None

    def action(identifier: str, arguments: dict | None = None, *, selector=None, read=False):
        return AppIntent(
            kind="read" if read else "write",
            domain=domain,
            action_id=identifier,
            arguments=arguments or {},
            selector=selector,
        )

    def clarify(reason="请明确操作、对象名称或 ID；不会猜测对象和日期。"):
        return AppIntent(kind="clarify", domain=domain, confidence=0.0, clarification=reason)

    selector = quotes[0] if quotes else None
    folder_name = quotes[0] if quotes else None
    if not folder_name:
        folder = re.search(r"(?:叫|名为|名称为)\s*([^，,。\s]{1,100}?)的?文件夹", text)
        folder_name = folder.group(1) if folder else None
    if not folder_name and urls and "knowledge" in domains:
        folder = re.search(
            r"(?:归类|归档|整理|保存|收录|收藏)(?:到|进|至)\s*"
            r"(?:知识库(?:里|中|的)?\s*)?([^，,。\s]{1,100}?)"
            r"(?:下面|下|文件夹|目录)\s*(?=[，,。；;]|$)",
            grammar,
        )
        folder_name = folder.group(1) if folder else None
    if (
        urls
        and "knowledge" in domains
        and folder_name
        and (_has("import", grammar) or _has("classify", grammar))
    ):
        if len(urls) != 1:
            return clarify("请一次提供一个链接。")
        return AppIntent(
            kind="workflow",
            domain="knowledge",
            arguments={
                "url": urls[0],
                "folder_name": folder_name,
                "use_ai": explicit_ai_metadata(text),
            },
        )
    if len(domains) > 1 and set(domains) != {"inbox", "knowledge"}:
        return clarify("请明确本次操作的页面和对象。")
    if domain == "knowledge" and selector and _has("classify", grammar) and "文件夹" not in grammar:
        domain = "inbox"
    if domain == "tasks":
        if _has("create", grammar):
            if re.search(r"明天|后天|下午|上午|今晚|下周|tomorrow|next week", grammar, re.I):
                return clarify("请提供明确日期、时间和时区。")
            if not selector:
                return clarify("请提供待办名称。")
            due = re.search(
                r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2})?(?:Z|[+-]\d{2}:\d{2})", grammar
            )
            return action(
                "tasks.create", {"title": selector, **({"due_at": due.group()} if due else {})}
            )
        if _has("rename", grammar) and len(quotes) >= 2:
            return action("tasks.update", {"changes": {"title": quotes[1]}}, selector=selector)
        if _has("delete", grammar):
            return action("tasks.delete", selector=selector)
        if _has("restore", grammar) or _has("complete", grammar):
            return action(
                "tasks.complete", {"completed": not _has("restore", grammar)}, selector=selector
            )
        if _has("read", grammar):
            return action("tasks.list", read=True)
    elif domain == "feed":
        if _has("refresh", grammar):
            return action("feed.refresh", read=True)
        if urls and (_has("create", grammar) or _has("import", grammar)):
            if len(urls) != 1:
                return clarify("请一次提供一个资讯链接。")
            return action(
                "feed.add_manual", {"url": urls[0], "fetch_title": explicit_title_fetch(text)}
            )
        if _has("restore", grammar):
            return action(
                "feed.unhide_external" if _has("hide", grammar) else "feed.restore_manual",
                selector=selector,
            )
        if _has("hide", grammar):
            return action("feed.hide_external", selector=selector)
        if _has("delete", grammar):
            return action("feed.remove_manual", selector=selector)
        if _has("rename", grammar) and len(quotes) >= 2:
            return action(
                "feed.update_manual", {"changes": {"title": quotes[1]}}, selector=selector
            )
        if _has("import", grammar) and selector:
            return action("feed.save_to_inbox", selector=selector)
        if _has("read", grammar):
            return action("feed.list", read=True)
    elif domain == "inbox":
        if _has("classify", grammar):
            if selector:
                return action(
                    "inbox.classify_selected",
                    {"use_ai": explicit_ai_metadata(text)},
                    selector=selector,
                )
            if re.search(r"全部|所有|里面内容|还没整理|都搬|一键|\ball\b", grammar, re.I):
                return action("inbox.classify_all", {"use_ai": explicit_ai_metadata(text)})
            return clarify("请选择具体资料，或明确整理全部收件箱。")
        if _has("import", grammar) or _has("create", grammar):
            if urls:
                return (
                    action(
                        "inbox.import_url", {"url": urls[0], "use_ai": explicit_ai_metadata(text)}
                    )
                    if len(urls) == 1
                    else clarify()
                )
            if selector:
                return action(
                    "inbox.import_text", {"text": selector, "use_ai": explicit_ai_metadata(text)}
                )
            return clarify("请提供文字、链接或已授权的附件。")
        if _has("retry", grammar):
            return action("inbox.retry", selector=selector)
        if _has("delete", grammar):
            return action("inbox.delete", selector=selector)
        if _has("rename", grammar) and len(quotes) >= 2:
            return action("inbox.update", {"changes": {"title": quotes[1]}}, selector=selector)
        if _has("read", grammar):
            return (
                action("inbox.get", selector=selector, read=True)
                if selector
                else action("inbox.list", read=True)
            )
    elif domain == "knowledge":
        if "文件夹" in grammar or re.search(r"\bfolders?\b", grammar, re.I):
            if _has("create", grammar):
                return (
                    action("knowledge.folders.create", {"name": folder_name})
                    if folder_name
                    else clarify()
                )
            if _has("rename", grammar) and len(quotes) >= 2:
                return action(
                    "knowledge.folders.update", {"changes": {"name": quotes[1]}}, selector=selector
                )
            if _has("delete", grammar):
                return action("knowledge.folders.delete", selector=selector)
            if _has("read", grammar):
                return (
                    action("knowledge.folders.get", selector=selector, read=True)
                    if selector
                    else action("knowledge.folders.list", read=True)
                )
        if _has("delete", grammar):
            return action("knowledge.items.delete", selector=selector)
        if _has("read", grammar) or re.search(r"有.+资料|搜索|检索|相关|\bsearch\b", grammar, re.I):
            return action("knowledge.search", {"query": quotes[0] if quotes else text}, read=True)
    elif domain == "preferences":
        if _has("restore", grammar) and "默认" in grammar:
            return action("preferences.reset")
        changes: dict[str, Any] = {}
        for label, field in (("昵称", "displayName"), ("邮箱", "email"), ("简介", "bio")):
            if label in grammar and selector and _has("rename", grammar):
                changes[field] = selector
        if "主题" in grammar:
            for label, theme in (("深色", "dark"), ("浅色", "light"), ("跟随系统", "system")):
                if label in grammar:
                    changes["theme"] = theme
        if "字号" in grammar:
            for label, size in (("大", "large"), ("中", "medium"), ("小", "small")):
                if label in grammar:
                    changes["fontSize"] = size
        if "减少动画" in grammar and (_has("enable", grammar) or _has("disable", grammar)):
            changes["reducedMotion"] = _has("enable", grammar)
        if changes:
            return action("preferences.update", {"changes": changes})
        if _has("read", grammar):
            return action("preferences.get", read=True)
    elif domain == "automations":
        if _has("create", grammar):
            when = re.search(r"(?:每日|每天)\s*(\d{1,2}):(\d{2})", grammar)
            if len(quotes) < 2 or not when:
                return clarify("请提供每日时间、名称和提示词。")
            return action(
                "automations.create",
                {
                    "name": quotes[0],
                    "prompt": quotes[1],
                    "hour": int(when.group(1)),
                    "minute": int(when.group(2)),
                    "timezone": "Asia/Shanghai",
                },
            )
        if _has("delete", grammar):
            return action("automations.delete", selector=selector)
        if _has("enable", grammar) or _has("disable", grammar):
            return action(
                "automations.toggle", {"enabled": _has("enable", grammar)}, selector=selector
            )
        if re.search(r"运行记录|历史|\bruns\b", grammar):
            return action("automations.runs", selector=selector, read=True)
        if _has("read", grammar):
            return action("automations.list", read=True)
    elif domain == "conversations":
        if _has("create", grammar):
            return action("conversations.create")
        if _has("rename", grammar) and len(quotes) >= 2:
            return action("conversations.update", {"title": quotes[1]}, selector=selector)
        if _has("delete", grammar):
            return clarify("会话删除需要在界面明确操作。")
        if "消息" in grammar or "历史" in grammar:
            return action("conversations.messages", selector=selector, read=True)
        if _has("read", grammar):
            return (
                action("conversations.get", selector=selector, read=True)
                if selector
                else action("conversations.list", read=True)
            )
    return clarify()
