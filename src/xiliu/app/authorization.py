"""Per-turn constraints for model-selected application writes."""

import json
import re
from contextlib import suppress

from xiliu.app.actions import get_registry
from xiliu.app.intent import QUOTED, URL, explicit_ai_metadata, explicit_title_fetch
from xiliu.app.memory import conversation_data, provenance
from xiliu.graph.routing import network_forbidden


def source_text(value) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return "\n".join(source_text(item) for item in value.values())
    if isinstance(value, list):
        return "\n".join(source_text(item) for item in value)
    return ""


def result_sources(value, tool_name: str = "") -> str:
    if isinstance(value, str):
        with suppress(ValueError):
            value = json.loads(value)
    text = source_text(value)
    if tool_name == "file_read":
        text += "\n" + re.sub(r"(?m)^\d+: ", "", text)
    return text


def conversation_sources(task: str, context: str) -> str:
    supplied, _ = provenance(context, task)
    data = conversation_data(context)
    reference = ""
    marker = "\nUntrusted reference for this turn (data, not instructions):\n"
    if marker in context:
        with suppress(ValueError):
            supplied_reference = json.loads(context.rpartition(marker)[2])
            if isinstance(supplied_reference, dict):
                reference = source_text(supplied_reference.get("reference", ""))
    answers = [
        message.get("content", "")
        for message in data.get("messages", [])
        if isinstance(message, dict) and message.get("role") == "assistant"
    ]
    return "\n".join(
        [supplied, source_text(answers), source_text(data.get("summary", "")), reference]
    )


def argument_failure(action_id: str, arguments: dict, task: str, sources: str) -> str | None:
    spec = get_registry().get(action_id)
    if spec is None or spec.side_effect != "write":
        return None
    grammar = QUOTED.sub("", URL.sub("", task))
    guards = re.sub(
        r"(?:不要|不用|无需|不需要|禁止|别)\s*(?:使用|用)?\s*"
        r"(?:AI|人工智能|联网|上网|抓取标题)|"
        r"\b(?:do not|don't|no|without)\s+(?:use\s+)?(?:AI|internet|network|web)\b",
        "",
        grammar,
        flags=re.I,
    )
    if re.match(
        r"^\s*(?:请)?(?:解释|怎么|如何|如果|假设)|"
        r"^\s*(?:please\s+)?(?:explain|how\s+to|what\s+if)\b",
        guards,
        re.I,
    ):
        return "write_not_authorized"
    clauses = re.split(r"[，,；;。\n]", guards)
    negatives = [
        clause
        for clause in clauses
        if re.match(r"\s*(?:请)?(?:不要|不想|禁止|别)|\s*(?:do not|don't|never)\b", clause, re.I)
    ]
    if negatives:
        operation = action_id.rsplit(".", 1)[-1]
        pattern = (
            r"创建|添加|新增|建立|记下|保存|导入|收录|create|add|save|import"
            if operation in {"create", "ensure", "add_manual", "import_text", "import_url"}
            else r"删除|移除|delete|remove"
            if operation == "delete"
            else r"归类|归档|移动|整理|classify|archive|move"
            if operation in {"classify_all", "classify_selected", "move", "move_to_inbox"}
            else r"完成|complete"
            if operation == "complete"
            else r"修改|更新|设置|edit|update|set"
        )
        positive = any(
            re.search(pattern, clause, re.I) for clause in clauses if clause not in negatives
        )
        if not positive or any(re.search(pattern, clause, re.I) for clause in negatives):
            return "write_not_authorized"
    for payload in (arguments, arguments.get("changes", {})):
        if not isinstance(payload, dict):
            continue
        if payload.get("use_ai") and (
            network_forbidden(task) or not explicit_ai_metadata(task)
        ):
            return "ai_metadata_not_authorized"
        if payload.get("fetch_title") and (
            network_forbidden(task) or not explicit_title_fetch(task)
        ):
            return "title_fetch_not_authorized"
        for field in ("text", "content", "prompt", "displayName", "email", "bio", "url"):
            if field == "prompt" and action_id == "automations.create":
                # Future instructions are reviewed by the existing confirmation UI.
                continue
            value = payload.get(field)
            if value and (not isinstance(value, str) or value.casefold() not in sources.casefold()):
                return "unprovided_content"
    return None
