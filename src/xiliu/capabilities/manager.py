from __future__ import annotations

import re
from typing import TYPE_CHECKING

from xiliu.capabilities.models import CapabilityKind, CapabilitySpec

if TYPE_CHECKING:
    from xiliu.capabilities.mcp import MCPManager
    from xiliu.capabilities.skills import SkillRegistry

BUILTIN_PERMISSIONS = {
    "agent_call": "agent.delegate",
    "agent_catalog": "knowledge.read",
    "app": "compute.safe",
    "calculator": "compute.safe",
    "current_time": "time.read",
    "file_read": "filesystem.read.workspace",
    "file_write": "filesystem.write.workspace",
    "file_edit": "filesystem.write.workspace",
    "grep": "filesystem.read.workspace",
    "command": "process.execute.safe",
    "bash": "process.execute.safe",
    "notepad_read": "filesystem.read.workspace",
    "notepad_append": "filesystem.write.workspace",
    "todo_write": "filesystem.write.workspace",
    "todo_update": "filesystem.write.workspace",
    "preference_write": "filesystem.write.workspace",
    "web_search": "network.read",
    "call_search_agent": "agent.delegate",
    "call_code_agent": "agent.delegate",
    "capability_search": "capabilities.read",
    "skill_load": "filesystem.read.workspace",
    "skill_resource_read": "filesystem.read.workspace",
}

CAPABILITY_ALIASES = {
    "builtin:app": ("知识库 知识 检索 本地资料 搜索 标签 文件夹 knowledge search tags folders"),
    "mcp:aihot:aihot_get_latest": "AI 新闻 最新资讯 每日简报",
    "mcp:aihot:aihot_search": "AI 搜索 资讯检索",
    "mcp:aihot:aihot_get_hot_topics": "AI 热点 热榜",
}


class CapabilityManager:
    def __init__(
        self, *, skill_registry: SkillRegistry | None = None, mcp_manager: MCPManager | None = None
    ) -> None:
        self._specs: dict[str, CapabilitySpec] = {}
        self.skill_registry = skill_registry
        self.mcp_manager = mcp_manager
        from xiliu.app.actions import get_registry

        for action in get_registry().values():
            self.register(
                CapabilitySpec(
                    id=f"app:{action.id}",
                    kind="app",
                    source_id=action.id,
                    name=action.id,
                    description=action.description,
                    permission=action.permission,
                    requires_confirmation=action.confirmation_policy != "none",
                    enabled=action.agent_availability == "enabled",
                )
            )
        if skill_registry is not None:
            for spec in skill_registry.scan():
                self.register(spec)

    def register(self, spec: CapabilitySpec) -> None:
        if spec.id in self._specs:
            raise ValueError(f"duplicate capability: {spec.id}")
        self._specs[spec.id] = spec

    def get(self, capability_id: str) -> CapabilitySpec | None:
        return self._specs.get(capability_id)

    def catalog(self, kind: CapabilityKind | None = None) -> list[CapabilitySpec]:
        """Metadata only; execution remains authorized by the Gateway and Dispatcher."""
        return [s for s in self._specs.values() if s.enabled and (kind is None or s.kind == kind)]

    def refresh_agents(self, specs: list[CapabilitySpec]) -> None:
        self._specs = {
            identifier: spec for identifier, spec in self._specs.items() if spec.kind != "agent"
        }
        for spec in specs:
            if spec.kind != "agent":
                raise ValueError("agent refresh accepts only agent manifests")
            self.register(spec)

    def load_skill(self, skill_id: str) -> str:
        if self.skill_registry is None or not skill_id.startswith("skill:"):
            raise ValueError("skill is unavailable")
        name = skill_id.removeprefix("skill:")
        if skill_id not in self._specs:
            raise ValueError("skill is not registered")
        return self.skill_registry.load(name)

    def read_skill_resource(self, skill_id: str, relative_path: str) -> str:
        if self.skill_registry is None or skill_id not in self._specs:
            raise ValueError("skill is unavailable")
        return self.skill_registry.read_resource(skill_id.removeprefix("skill:"), relative_path)

    def mcp_tools(self, server_id: str) -> list[CapabilitySpec]:
        if self.mcp_manager is None:
            raise ValueError("MCP is unavailable")
        specs = self.mcp_manager.tools(server_id)
        for spec in specs:
            self._specs[spec.id] = spec
        return specs

    def search(
        self, query: str, kind: CapabilityKind | None = None, limit: int = 5
    ) -> list[CapabilitySpec]:
        terms = re.findall(r"[\w-]+", query.casefold())
        ranked: list[tuple[int, CapabilitySpec]] = []
        for spec in self._specs.values():
            if not spec.enabled or (kind is not None and spec.kind != kind):
                continue
            alias = CAPABILITY_ALIASES.get(spec.id, "")
            haystack = f"{spec.id} {spec.name} {spec.description} {alias}".casefold()
            if terms and not all(term in haystack for term in terms):
                continue
            score = sum(3 * (term in spec.name.casefold()) + 2 * (term in alias) for term in terms)
            ranked.append((-score, spec))
        ranked.sort(key=lambda item: (item[0], item[1].id))
        return [spec for _, spec in ranked[: max(0, min(limit, 5))]]
