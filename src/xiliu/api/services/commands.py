from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Literal

from langchain_core.messages import AIMessage, HumanMessage

from xiliu.api.errors import WebError
from xiliu.api.services.conversations import ConversationService
from xiliu.capabilities.mcp import MCPManager
from xiliu.capabilities.skills import SkillRegistry
from xiliu.graph.memory import summarize_messages
from xiliu.providers.openai_compatible import create_chat_model

COMMANDS = [
    {"name": "clear", "description": "清除当前对话内容"},
    {"name": "compress", "description": "压缩当前上下文，保留历史"},
    {"name": "skill", "description": "使用一个已安装技能"},
    {"name": "mcp", "description": "使用一个已连接服务"},
]


@dataclass(frozen=True)
class CommandResult:
    command: str
    task: str | None = None
    message: str = ""
    role: Literal["assistant", "event"] = "assistant"
    reset_messages: bool = False


class CommandService:
    def __init__(self, conversations: ConversationService):
        self.conversations = conversations
        self.store = conversations.store
        self.data_dir = self.store.path.parent

    def skills(self) -> list[dict[str, str]]:
        try:
            return [
                {"name": spec.name, "description": spec.description}
                for spec in SkillRegistry(self.data_dir / "skills").scan()
            ]
        except (OSError, ValueError):
            raise WebError("capabilities_unavailable", "技能配置无法读取。", 503) from None

    def mcp(self) -> list[dict[str, str]]:
        manager = None
        try:
            manager = MCPManager(self.data_dir / "mcp")
            return [
                {"name": name, "description": "已连接的 MCP 服务"} for name in manager.servers()
            ]
        except (OSError, ValueError):
            raise WebError("capabilities_unavailable", "连接配置无法读取。", 503) from None
        finally:
            if manager is not None:
                manager.close()

    def resolve(self, cid: str, text: str, model: str | None = None) -> CommandResult:
        parts = text.strip().split(maxsplit=2)
        command = parts[0].removeprefix("/")
        if command in {"clear", "compress"}:
            if len(parts) != 1:
                raise WebError("invalid_command", f"/{command} 不接受附加参数。")
            if command == "clear":
                self.store.clear_messages(cid)
                return CommandResult(
                    command, message="已清除对话内容", role="event", reset_messages=True
                )
            return self.compress(cid, model)
        if command not in {"skill", "mcp"} or len(parts) < 2:
            raise WebError(
                "invalid_command", "请输入 /clear、/compress、/skill 名称 或 /mcp 名称。"
            )
        name = parts[1]
        entries = self.skills() if command == "skill" else self.mcp()
        selected = next((entry for entry in entries if entry["name"] == name), None)
        if selected is None:
            raise WebError(f"{command}_not_found", "找不到指定的技能或连接。")
        if len(parts) < 3 or not parts[2].strip():
            return CommandResult(
                command,
                message=(
                    f"**{name}**\n\n{selected['description']}\n\n"
                    f"用法：`/{command} {name} 你的问题或指令`"
                ),
            )
        instruction = parts[2]
        request = json.dumps(
            {"selected_name": name, "user_request": instruction}, ensure_ascii=False
        )
        if command == "skill":
            task = (
                f"This task requires reading an installed skill through the workflow. "
                f"The user explicitly requested skill:{name}. "
                f"Load that skill with the existing skill_load capability before answering. "
                f"Use the existing Execution Gateway, policy and hooks. "
                f"User request (JSON): {request}"
            )
        else:
            task = (
                f"This task requires MCP tools through the workflow. "
                f"The user explicitly requested MCP server {name}. "
                f'Use capability_search(kind="mcp") to discover capabilities on that server, '
                f"then use mcp_call through the existing Execution Gateway, policy and hooks. "
                f"Do not call other MCP servers for this request. "
                f"User request (JSON): {request}"
            )
        return CommandResult(command, task=task)

    def compress(self, cid: str, model: str | None = None) -> CommandResult:
        conversation = self.store.get(cid)
        active = [
            message
            for message in self.conversations.active_messages(cid)
            if not (message["role"] == "user" and message["content"].startswith("/"))
        ]
        if not active:
            return CommandResult("compress", message="没有新的上下文需要压缩。", role="event")
        settings = self.conversations.model_settings.runtime_settings(model)
        messages = [
            HumanMessage(content=message["content"])
            if message["role"] == "user"
            else AIMessage(content=message["content"])
            for message in active
        ]
        summary = summarize_messages(
            create_chat_model(settings),
            messages,
            {"context_summary": conversation["context_summary"]},
        )
        if not summary.strip():
            raise WebError("compression_failed", "本次摘要为空，原上下文已保留。")
        latest_seq = self.store.messages(cid)[-1]["seq"]
        self.store.save_summary(cid, summary, latest_seq)
        return CommandResult("compress", message="Context compressed", role="event")
