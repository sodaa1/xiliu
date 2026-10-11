"""The only Agent-visible application business tool."""

from __future__ import annotations

import json
from typing import Any, Literal

from langchain_core.tools import BaseTool
from langchain_core.tools.base import ArgsSchema
from pydantic import BaseModel, ConfigDict, Field

from xiliu.app.dispatch import AppDispatcher


class AppInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    operation: Literal["catalog", "describe", "execute"]
    action_id: str | None = None
    arguments: dict[str, Any] = Field(default_factory=dict)
    request_id: str | None = None
    confirmation_id: str | None = None


class AppTool(BaseTool):
    name: str = "app"
    description: str = (
        "Application actions. Call catalog, then describe an action for its strict schema, "
        "then execute. Returns persisted records and verification. "
        "Confirmation is approved only by the human UI."
    )
    args_schema: ArgsSchema | None = AppInput
    services: Any = Field(default=None, exclude=True)
    allowed_actions: set[str] | None = Field(default=None, exclude=True)

    def _run(
        self,
        operation: str,
        action_id: str | None = None,
        arguments: dict | None = None,
        request_id: str | None = None,
        confirmation_id: str | None = None,
    ) -> str:
        from xiliu.execution.gateway import active_run

        context = active_run.get()
        if context is None:
            result = {"ok": False, "error": "service_unavailable"}
        else:
            dispatcher = AppDispatcher(
                self.services or context.app_services, context, allowed_actions=self.allowed_actions
            )
            if operation == "catalog":
                result = dispatcher.catalog()
            elif operation == "describe":
                result = dispatcher.describe(action_id or "")
            else:
                result = dispatcher.execute(
                    action_id or "",
                    arguments or {},
                    request_id=request_id,
                    confirmation_id=confirmation_id,
                )
        return json.dumps(result, ensure_ascii=False)


def build_app_tool(services: Any = None, *, allowed_actions: set[str] | None = None) -> AppTool:
    return AppTool(services=services, allowed_actions=allowed_actions)
