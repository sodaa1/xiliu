from __future__ import annotations

import json
from typing import Any

from langchain_core.tools import BaseTool, StructuredTool

from xiliu.execution.gateway import ExecutionGateway, active_run


def build_meta_tools(*, role: str) -> list[BaseTool]:
    """Expose a small fixed tool surface when a workflow run is active."""
    context = active_run.get()
    if context is None or context.capability_manager is None:
        return []
    manager = context.capability_manager

    def capability_search(query: str, kind: str = "", limit: int = 5) -> str:
        """Find relevant built-in, Skill or MCP capabilities by a short query."""
        if kind not in {"", "app", "builtin", "skill", "mcp", "agent"}:
            return json.dumps({"ok": False, "error": "invalid_capability_kind"})
        if context.data_dir is not None:
            from xiliu.capabilities.agent_registry import AgentRegistry

            manager.refresh_agents(AgentRegistry(context.data_dir).specs())
        if manager.mcp_manager is not None and kind in {"", "mcp"}:
            for server_id in manager.mcp_manager.servers():
                ExecutionGateway().discover_mcp(server_id, context)
        selected = manager.search(query, kind=kind or None, limit=limit)  # type: ignore[arg-type]
        results: list[dict[str, Any]] = []
        for spec in selected:
            entry: dict[str, Any] = {
                "kind": spec.kind,
                "id": spec.id,
                "name": spec.name,
                "description": spec.description[:300],
            }
            if spec.kind == "agent" and context.data_dir is not None:
                from xiliu.capabilities.agent_registry import AgentRegistry

                manifest = AgentRegistry(context.data_dir).agents.get(spec.source_id)
                if manifest is not None:
                    entry["allowed_paths"] = manifest.allowed_paths
                    entry["allowed_tools"] = manifest.allowed_tools
            if spec.kind == "mcp" and manager.mcp_manager is not None:
                schema = manager.mcp_manager.schema(spec.id)
                entry["schema_preview"] = {
                    "properties": list(schema.get("properties", {}))[:20],
                    "required": schema.get("required", [])[:20],
                }
            results.append(entry)
        return json.dumps({"ok": True, "results": results}, ensure_ascii=False)

    def skill_load(skill_id: str) -> str:
        """Load the complete SKILL.md instructions for one selected Skill."""
        try:
            content = manager.load_skill(skill_id)
            if context.event_sink is not None:
                context.event_sink(
                    {"type": "skill_activation", "run_id": context.run_id, "skill_id": skill_id}
                )
            return json.dumps(
                {"ok": True, "skill_id": skill_id, "content": content}, ensure_ascii=False
            )
        except ValueError as exc:
            return json.dumps({"ok": False, "error": "skill_load_failed", "reason": str(exc)})

    def skill_resource_read(skill_id: str, relative_path: str) -> str:
        """Read one explicitly named reference file inside a loaded Skill."""
        try:
            content = manager.read_skill_resource(skill_id, relative_path)
            return json.dumps({"ok": True, "content": content}, ensure_ascii=False)
        except ValueError as exc:
            return json.dumps({"ok": False, "error": "skill_resource_failed", "reason": str(exc)})

    def mcp_call(capability_id: str, arguments: dict[str, Any]) -> str:
        """Invoke one discovered and locally allowlisted MCP tool."""
        if manager.mcp_manager is None:
            return json.dumps({"ok": False, "error": "mcp_unavailable"})
        try:
            result = manager.mcp_manager.call(capability_id, arguments)
            return json.dumps(result, ensure_ascii=False)
        except (ValueError, TimeoutError, RuntimeError) as exc:
            return json.dumps({"ok": False, "error": "mcp_call_failed", "reason": str(exc)})

    functions = [capability_search, skill_load, skill_resource_read, mcp_call]
    return [StructuredTool.from_function(function) for function in functions]
