"""Agent adapters for the same services used by the Inbox UI."""

from __future__ import annotations

import json
from contextvars import ContextVar
from typing import Any

from langchain_core.tools import BaseTool, tool
from pydantic import BaseModel, ConfigDict, Field

from xiliu.api.errors import WebError

app_inbox: ContextVar[Any] = ContextVar("app_inbox", default=None)


class ImportInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=1, max_length=200_000)
    use_ai: bool = True


class ClassifyInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    item_ids: list[str] = Field(min_length=1, max_length=100)
    save_to_knowledge: bool = False


def build_app_tools() -> list[BaseTool]:
    inbox = app_inbox.get()
    if inbox is None:
        return []

    def result(action):
        try:
            return json.dumps({"ok": True, **action()}, ensure_ascii=False)
        except WebError as exc:
            return json.dumps(
                {"ok": False, "error": exc.code, "reason": exc.message}, ensure_ascii=False
            )

    @tool(args_schema=ImportInput)
    def inbox_import(text: str, use_ai: bool = True) -> str:
        """Import text or ONE URL into Inbox using the existing app import service.

        Call separately for each URL. Returns the actual persisted item ID and status.
        AI metadata runs in the background; use inbox_list to inspect its progress.
        """
        return result(lambda: {"item": inbox.import_item({"text": text, "use_ai": use_ai})})

    @tool
    def inbox_list() -> str:
        """List actual Inbox cards with IDs, processing status, tags and summaries."""
        return result(lambda: {"items": inbox.content.list("inbox")})

    @tool
    def knowledge_folders() -> str:
        """List existing Knowledge folders and their classification tags."""
        return result(lambda: {"folders": inbox.knowledge.list_folders()})

    @tool(args_schema=ClassifyInput)
    def inbox_classify(item_ids: list[str], save_to_knowledge: bool = False) -> str:
        """Classify actual card IDs using the same batch service as the Inbox UI.

        Set save_to_knowledge=true ONLY when the user asked to save to Knowledge.
        This also saves unmatched cards as unfiled Knowledge. Returns persisted cards;
        inspect processing_error to distinguish AI failure from successful local saving.
        """

        return result(lambda: inbox.classify_batch(item_ids, save_to_knowledge=save_to_knowledge))

    return [inbox_import, inbox_list, knowledge_folders, inbox_classify]
