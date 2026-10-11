from pathlib import Path
from typing import Annotated, Any, Literal, NotRequired

from typing_extensions import TypedDict

from xiliu.execution.evidence import (
    merge_agent_results_by_call_id,
    merge_events_by_id,
    merge_evidence_by_event_id,
)
from xiliu.graph.memory import AgentHandoff, CompressionEvent, LayeredMemory

GraphStatus = Literal["planning", "verifying", "passed", "failed"]
TodoStatus = Literal["pending", "in_progress", "completed", "blocked"]


class TodoDraft(TypedDict):
    id: str
    content: str


class TodoItem(TodoDraft):
    status: TodoStatus
    note: str


class ResearchNote(TypedDict):
    summary: str
    queries: list[str]
    sources: list[str]
    attempt: int


class ToolEvent(TypedDict):
    event_id: NotRequired[str]
    agent: str
    tool: str
    args: dict[str, Any]
    output: str
    ok: bool
    attempt: int
    phase: str | None


class AgentResult(TypedDict):
    call_id: NotRequired[str]
    agent_id: NotRequired[str]
    parent_call_id: NotRequired[str]
    status: NotRequired[str]
    child_events: NotRequired[list[dict[str, Any]]]
    evidence_ids: NotRequired[list[str]]
    hit_ids: NotRequired[list[str]]
    answer_supported: NotRequired[bool]
    agent: str
    instruction: str
    ok: bool
    summary: str
    attempt: int


class GraphState(TypedDict):
    app_receipts: NotRequired[list[dict[str, Any]]]
    app_model_calls: NotRequired[int]
    intent: NotRequired[Literal["chat", "task"]]
    mode: NotRequired[Literal["fast", "standard", "deep"]]
    requested_mode: NotRequired[str]
    route_reason: NotRequired[str]
    evidence: Annotated[NotRequired[list[dict[str, Any]]], merge_evidence_by_event_id]
    retrieval_hits: NotRequired[list[dict[str, Any]]]
    intent_route: NotRequired[Literal["chat", "workflow"]]
    intent_reason: NotRequired[str]
    intent_confidence: NotRequired[float]
    chat_response: NotRequired[str]
    resume_node: Literal["planner", "verifier", "final"]
    supervisor_ok: bool
    task: str
    todos: list[TodoItem]
    research_notes: list[ResearchNote]
    agent_results: Annotated[list[AgentResult], merge_agent_results_by_call_id]
    tool_events: Annotated[list[ToolEvent], merge_events_by_id]
    result: str
    graph_state: GraphStatus
    verification: str
    attempt: int
    max_attempts: int
    final_answer: str
    session_id: str
    workspace: Path
    memory: LayeredMemory
    current_node: Literal["planner", "verifier", "final"]
    plan_summary: str
    acceptance_criteria: list[str]
    agent_handoffs: list[AgentHandoff]
    code_agent_summary: str
    verifier_summary: str
    last_error: str
    context_summary: str
    compression_events: list[CompressionEvent]
