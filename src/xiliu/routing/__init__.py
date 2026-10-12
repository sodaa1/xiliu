import re

from xiliu.routing.classifier import IntentOutput, classify
from xiliu.routing.rules import intent, match_rules


def command_adapter(task: str):
    match = re.match(r"^\s*/(clear|compress|skill|mcp)\b(?:\s+(.*))?\s*$", task, re.I | re.S)
    if not match:
        return None
    command, args = match.group(1).lower(), (match.group(2) or "").strip()
    if command in {"clear", "compress"}:
        return {
            **intent(
                "control" if not args else "clarification", "command", command, complexity="simple"
            ),
            "source": "command",
        }
    parts = args.split(maxsplit=1)
    # A selected capability name is optional; bare commands constrain the capability kind.
    named = parts and re.fullmatch(r"[a-zA-Z0-9_.-]+", parts[0])
    preference = f"{command}:{parts[0]}" if named else command
    return {
        **intent(complexity="multi_step"),
        "source": "command",
        "preferred_capability": preference,
    }


def recognize_intent(task, *, model, context="", embedding_matcher=None):
    from xiliu.app.memory import conversation_data

    command = command_adapter(task)
    result = command or match_rules(task)
    if (
        not command
        and conversation_data(context).get("pending_requests")
        and (result is None or result["domain"] != "security")
    ):
        # Only the model can tell whether a new utterance fills a pending slot.
        return classify(task, context, model)
    if (
        context
        and not command
        and result
        and result["domain"] in {"workspace", "knowledge"}
        and not result["action"]
        and result["complexity"] != "multi_step"
    ):
        # Generic keyword matches cannot resolve references to earlier App objects.
        return classify(task, context, model)
    if result is not None:
        return result
    if embedding_matcher is not None:
        result = embedding_matcher(task)
        if result:
            try:
                validated = IntentOutput.model_validate(
                    {k: v for k, v in result.items() if k != "source"}
                )
                if validated.confidence >= 0.88:
                    return {**validated.model_dump(), "source": "embedding"}
            except ValueError:
                pass
    return classify(task, context, model)


def select_execution(structured):
    kind = structured["intent"]
    if kind == "control":
        return "control"
    if kind == "clarification":
        return "clarification"
    if structured["preferred_capability"]:
        return "planner"
    if kind == "chat":
        return "chat_responder"
    if structured["complexity"] == "multi_step":
        return "planner"
    action = structured["action"]
    if action:
        from xiliu.app.actions import get_registry

        if action in get_registry() or (
            action in {"app:match", "app:clarify", "app:explain"}
            and structured["domain"]
            in {
                "today",
                "tasks",
                "feed",
                "inbox",
                "knowledge",
                "preferences",
                "automations",
                "conversations",
                "settings",
            }
        ):
            return "app_executor"
    return "fast_react"
