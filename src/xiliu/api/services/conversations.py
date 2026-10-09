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
        if (
            settings["provider"] == "deepseek"
            and conversation["model_override"] == "deepseek-flash"
        ):
            conversation = self.store.update(cid, model_override="deepseek-v4-flash")
        if (
            conversation["model_override"]
            and conversation["model_override"] not in MODEL_CATALOG[settings["provider"]]["models"]
        ):
            conversation = self.store.update(cid, model_override=None)
        return conversation

    def update(self, cid: str, changes: dict[str, Any]) -> dict[str, Any]:
        override = changes.get("model_override")
        provider = self.model_settings.read()["provider"]
        if override and override not in MODEL_CATALOG[provider]["models"]:
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
            },
            ensure_ascii=False,
        )
