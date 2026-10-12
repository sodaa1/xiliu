"""Conversation data for semantic matching; never grants execution permission."""

import json


def conversation_data(context: str) -> dict:
    prefix = "Previous conversation context:\n"
    if not context.startswith(prefix):
        return {}
    try:
        value, _ = json.JSONDecoder().raw_decode(context[len(prefix) :])
        return value if isinstance(value, dict) else {}
    except ValueError:
        return {}


def provenance(context: str, text: str) -> tuple[str, set[str]]:
    """Only user-supplied values and verified receipt selectors qualify as sources."""
    data = conversation_data(context)
    sources = [text]
    selectors = set()
    for message in data.get("messages", []):
        if isinstance(message, dict) and message.get("role") == "user":
            sources.append(str(message.get("content", "")))
    for entry in data.get("object_memory", []):
        if not isinstance(entry, dict):
            continue
        sources.append(str(entry.get("user_request", "")))
        for record in entry.get("records", []):
            if isinstance(record, dict):
                selectors.update(
                    str(record[k]).casefold()
                    for k in ("id", "title", "name", "url")
                    if record.get(k)
                )
    for pending in data.get("pending_requests", []):
        if isinstance(pending, dict):
            sources.append(str(pending.get("user_request", "")))
            sources.extend(str(update) for update in pending.get("updates", []))
    return "\n".join(sources), selectors
