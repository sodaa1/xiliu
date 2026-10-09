from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from langchain_core.tools import BaseTool

from xiliu.tools.app_tools import build_app_tools
from xiliu.tools.approval_context import approval_config
from xiliu.tools.bash_tool import BashTool
from xiliu.tools.calculator import calculator
from xiliu.tools.command import CommandTool
from xiliu.tools.current_time import current_time
from xiliu.tools.file_edit import FileEditTool
from xiliu.tools.file_read import FileReadTool
from xiliu.tools.file_write import FileWriteTool
from xiliu.tools.grep import GrepTool
from xiliu.tools.knowledge_search import build_knowledge_tools
from xiliu.tools.notepad import NotepadAppendTool, NotepadReadTool
from xiliu.tools.preferences import PreferenceWriteTool, UserPreferenceStore
from xiliu.tools.todo import TodoStore, TodoUpdateTool, TodoWriteTool


def get_builtin_tools() -> list[BaseTool]:
    """Return the safe tools registered on the main Agent by default."""

    return [calculator, current_time, *build_knowledge_tools(), *build_app_tools()]


def get_workspace_tools(workspace: Path) -> list[BaseTool]:
    """Return file tools permanently bound to one session workspace."""

    return [
        FileReadTool(workspace=workspace),
        FileWriteTool(workspace=workspace),
        FileEditTool(workspace=workspace),
        GrepTool(workspace=workspace),
        CommandTool(workspace=workspace),
    ]


def build_tools(state: Mapping[str, Any]) -> list[BaseTool]:
    workspace = state["workspace"]
    approval = approval_config.get()
    return [
        *build_knowledge_tools(),
        FileReadTool(workspace=workspace),
        FileWriteTool(workspace=workspace),
        FileEditTool(workspace=workspace),
        GrepTool(workspace=workspace),
        BashTool(
            workspace=workspace,
            approval_mode=approval.mode,
            approval_handler=approval.handler,
        ),
        NotepadReadTool(workspace=workspace),
        NotepadAppendTool(workspace=workspace),
    ]


__all__ = [
    "BashTool",
    "build_tools",
    "calculator",
    "CommandTool",
    "current_time",
    "get_builtin_tools",
    "get_workspace_tools",
    "NotepadAppendTool",
    "NotepadReadTool",
    "PreferenceWriteTool",
    "TodoStore",
    "TodoUpdateTool",
    "TodoWriteTool",
    "UserPreferenceStore",
]
