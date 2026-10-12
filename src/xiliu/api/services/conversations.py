from __future__ import annotations

import json
from typing import Any

from xiliu.api.errors import WebError
from xiliu.api.model_catalog import MODEL_CATALOG
from xiliu.api.services.model_settings import ModelSettingsService
from xiliu.api.store import AppStore


class ConversationService:
    def __init__(self, store: AppStore, model_settings: ModelSettingsService):
        self.store = store
        self.model_settings = model_settings

    def get(self, cid: str) -> dict[str, Any]:
        conversation = self.store.get(cid)
        settings = self.model_settings.read()
        connection_ids = {c["id"] for c in settings.get("connections", [])}
        if (
            settings["provider"] == "deepseek"
            and conversation["model_override"] == "deepseek-flash"
        ):
            conversation = self.store.update(cid, model_override="deepseek-v4-flash")
        if (
            conversation["model_override"]
            and conversation["model_override"] not in connection_ids
            and conversation["model_override"] not in MODEL_CATALOG[settings["provider"]]["models"]
        ):
            conversation = self.store.update(cid, model_override=None)
        return conversation

    def update(self, cid: str, changes: dict[str, Any]) -> dict[str, Any]:
        override = changes.get("model_override")
        settings = self.model_settings.read()
        provider = settings["provider"]
        connection_ids = {c["id"] for c in settings.get("connections", [])}
        if (
            override
            and override not in connection_ids
            and override not in MODEL_CATALOG[provider]["models"]
        ):
            raise WebError("invalid_model", "模型不属于当前厂商。")
        if "title" in changes and changes["title"] is None:
            raise WebError("invalid_request", "标题不能为空。", 422)
        return self.store.update(cid, **changes)

    def active_messages(self, cid: str, *, before_seq: int | None = None) -> list[dict[str, Any]]:
        conversation = self.store.get(cid)
        cutoff = max(conversation["context_cutoff_seq"], conversation["compressed_through_seq"])
        return [
            message
            for message in self.store.messages(cid)
            if message["role"] in {"user", "assistant"}
            and message["seq"] > cutoff
            and (before_seq is None or message["seq"] < before_seq)
        ]

    def build_context(self, cid: str, *, before_seq: int | None = None) -> str:
        conversation = self.store.get(cid)
        # Preserve object identity across compression, but never across /clear.
        object_memory = []
        pending_requests: dict[str, dict[str, Any]] = {}
        user_request = ""
        for message in self.store.messages(cid):
            if message["seq"] <= conversation["context_cutoff_seq"] or (
                before_seq is not None and message["seq"] >= before_seq
            ):
                continue
            if message["role"] == "user":
                user_request = message["content"]
            if message["role"] != "assistant":
                continue
            try:
                metadata = json.loads(message["metadata_json"])
            except (ValueError, TypeError):
                continue
            execution = metadata.get("execution_result", {})
            decision = execution.get("semantic_decision", {})
            domain = decision.get("domain")
            status = execution.get("status")
            if domain and status in {"clarification_required", "confirmation_required"}:
                previous = pending_requests.get(domain)
                updates = list(previous.get("updates", [])) if previous else []
                if previous and user_request != previous["user_request"]:
                    updates.append(user_request)
                pending_requests[domain] = {
                    "seq": message["seq"],
                    "domain": domain,
                    "action_id": decision.get("action_id"),
                    "user_request": previous["user_request"] if previous else user_request,
                    "updates": updates,
                    "clarification": message["content"],
                    "status": status,
                }
            if (
                execution.get("verified")
                and domain
                and decision.get("kind") in {"write", "workflow"}
            ):
                pending_requests.pop(domain, None)
            for receipt in metadata.get("app_receipts", []):
                if not receipt.get("ok") or not receipt.get("verification", {}).get("passed"):
                    continue
                action_domain = str(receipt.get("action_id", "")).split(".")[0]
                from xiliu.app.actions import get_registry

                spec = get_registry().get(receipt.get("action_id", ""))
                if spec and spec.side_effect == "write":
                    pending_requests.pop(action_domain, None)
                records = [
                    {
                        key: row[key]
                        for key in ("id", "title", "name", "url", "status")
                        if key in row
                    }
                    for row in receipt.get("records", [])
                    if isinstance(row, dict)
                ]
                if records:
                    object_memory.append(
                        {
                            "seq": message["seq"],
                            "user_request": user_request,
                            "action_id": receipt.get("action_id"),
                            "records": records,
                        }
                    )
        messages = [
            {"role": message["role"], "content": message["content"]}
            for message in self.active_messages(cid, before_seq=before_seq)
            if not (message["role"] == "user" and message["content"].lstrip().startswith("/"))
        ]
        if not messages and not conversation["context_summary"]:
            return ""
        # Clearly labelled serialized conversation, never a new system instruction.
        return "Previous conversation context:\n" + json.dumps(
            {
                "summary": conversation["context_summary"],
                "messages": messages,
                "object_memory": object_memory,
                "pending_requests": sorted(
                    pending_requests.values(), key=lambda entry: entry["seq"]
                ),
            },
            ensure_ascii=False,
        )
