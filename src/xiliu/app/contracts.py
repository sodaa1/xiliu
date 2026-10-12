"""Registry-derived contracts for bounded semantic repair, before any execution."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, ValidationError

from xiliu.app.intent import AppIntent


class LinkArchive(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    url: str
    folder_name: str
    use_ai: bool


def contract_errors(candidate: AppIntent, registry, allowed: set[str]) -> list[dict]:
    if candidate.kind in {"clarify", "explain"}:
        return []
    if candidate.kind == "workflow":
        if candidate.action_id or candidate.domain not in {"inbox", "knowledge"}:
            return [
                {
                    "code": "workflow_contract",
                    "message": "workflow 是链接导入归档组合；单个注册操作应按其 side_effect 执行。",
                }
            ]
        required = {"inbox.import_url", "knowledge.folders.ensure", "inbox.classify_selected"}
        if not required <= allowed:
            return [
                {"code": "capability_unavailable", "message": "组合所需工具不在当前允许清单内。"}
            ]
        try:
            LinkArchive.model_validate(candidate.arguments)
        except ValidationError as error:
            return [
                {"code": "invalid_arguments", "fields": [list(e["loc"]) for e in error.errors()]}
            ]
        return []
    if candidate.action_id not in allowed:
        return [
            {
                "code": "capability_unavailable"
                if candidate.action_id in registry
                else "invalid_action_selection",
                "message": "必须选择当前清单内的 action_id。",
            }
        ]
    spec = registry[candidate.action_id]
    errors = []
    if candidate.kind != spec.side_effect:
        errors.append({"code": "kind_mismatch", "expected": spec.side_effect})
    if candidate.scope == "all" and spec.side_effect == "write" and not spec.supports_batch:
        errors.append({"code": "unsupported_bulk_write", "message": "所选工具不支持集合写入。"})
    try:
        spec.args_schema.model_validate(candidate.arguments)
    except ValidationError as error:
        deferred = {"expected_revision"}
        if candidate.selector:
            deferred.update({"item_id", "task_id", "folder_id", "cid", "item_ids"})
        invalid = [
            e for e in error.errors() if not (e["type"] == "missing" and e["loc"][0] in deferred)
        ]
        if invalid:
            errors.append(
                {"code": "invalid_arguments", "fields": [list(e["loc"]) for e in invalid]}
            )
    due = candidate.arguments.get("due_at")
    if due:
        try:
            if datetime.fromisoformat(due).tzinfo is None:
                raise ValueError("timezone required")
        except (TypeError, ValueError):
            errors.append({"code": "invalid_datetime", "message": "due_at 必须含有效时间和时区。"})
    return errors
