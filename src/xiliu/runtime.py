from __future__ import annotations

from collections.abc import Callable, Generator, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, cast
from uuid import uuid4

from langchain_core.messages import BaseMessage
from langgraph.checkpoint.memory import InMemorySaver
from pydantic import SecretStr

from xiliu.agents.react import model_factory
from xiliu.capabilities.manager import CapabilityManager
from xiliu.capabilities.mcp import MCPManager
from xiliu.capabilities.skills import SkillRegistry
from xiliu.config import Settings
from xiliu.core.agent import stream_agent
from xiliu.core.approval import ApprovalDecision, ApprovalRequest, normalize_approval_mode
from xiliu.core.checkpoint import CheckpointManager
from xiliu.core.trace import TraceRecorder
from xiliu.errors import CheckpointError, WorkspaceError, XiliuError
from xiliu.events import ErrorEvent, FinalEvent, RuntimeEvent
from xiliu.execution.gateway import RunContext, active_run
from xiliu.graph.memory import MemoryLimits, MemoryManager
from xiliu.graph.state import GraphState
from xiliu.hooks.engine import HookEngine
from xiliu.policy.engine import PolicyEngine
from xiliu.providers.openai_compatible import classify_provider_error, create_chat_model
from xiliu.rag.embedding_config import embedding_provider, embedding_provider_from_settings
from xiliu.tools.approval_context import ApprovalConfig, approval_config
from xiliu.tools.preferences import UserPreferenceStore
from xiliu.tools.todo import TodoStore
from xiliu.tools.web_search_tool import search_api_key
from xiliu.tools.workspace import create_explicit_workspace, create_session_workspace


@dataclass(frozen=True)
class _RunContext:
    owner: Runtime
    workspace: Path
    data_dir: Path
    checkpoint_mode: str
    trace_mode: str
    trace_id: str | None
    approval_mode: str
    approval_handler: Callable[[ApprovalRequest], ApprovalDecision] | None
    session_id: str = ""
    event_sink: Callable[[dict[str, Any]], None] | None = None
    actor_type: str = "interactive"
    policy_profile: str = "interactive"
    hook_failures: list[str] = field(default_factory=list)
    local_only: bool = False
    execution_run_id: str = ""
    request_text: str | None = None
    source_text: str = ""
    source_outputs: list[str] = field(default_factory=list)


@contextmanager
def _activate_run_context(context: _RunContext) -> Iterator[None]:
    from xiliu.cloud.budget import active_budget

    budget_token = None
    if getattr(context.owner, "_cloud_budget", None) is not None:
        budget_token = active_budget.set(active_budget.get() or context.owner._cloud_budget)
    embedding_token = embedding_provider.set(context.owner._embedding_provider)
    model_token = model_factory.set(context.owner._agent_model_factory)
    search_token = search_api_key.set(context.owner._tavily_api_key)
    approval_token = approval_config.set(
        ApprovalConfig(context.approval_mode, context.approval_handler)
    )
    capability_token = active_run.set(
        RunContext(
            run_id=context.execution_run_id or context.trace_id or context.session_id,
            session_id=context.session_id,
            workspace=context.workspace,
            data_dir=context.data_dir,
            actor_type=context.actor_type,
            policy_profile=context.policy_profile,
            event_sink=context.event_sink,
            capability_manager=context.owner._capabilities,
            policy_engine=context.owner._policy_engine,
            approval_handler=context.approval_handler,
            approval_mode=context.approval_mode,
            hook_engine=context.owner._hook_engine,
            hook_failures=context.hook_failures,
            local_only=context.local_only,
            app_services=context.owner._app_services,
            request_text=context.request_text,
            source_text=context.source_text,
            source_outputs=context.source_outputs,
        )
    )
    try:
        yield
    finally:
        if budget_token is not None:
            active_budget.reset(budget_token)
        embedding_provider.reset(embedding_token)
        active_run.reset(capability_token)
        approval_config.reset(approval_token)
        search_api_key.reset(search_token)
        model_factory.reset(model_token)


class Runtime:
    """Own session workspaces and expose synchronous, stable graph events."""

    def __init__(
        self,
        model: Any,
        checkpointer: Any | None = None,
        data_dir: Path = Path(".xiliu"),
        agent_model_factory: Callable[[], Any] | None = None,
        tavily_api_key: SecretStr | None = None,
        memory_limits: MemoryLimits | None = None,
        model_name: str = "unknown-model",
        token_counter: Callable[[Sequence[BaseMessage], str], int] | None = None,
        checkpoint_mode: str = "light",
        trace_mode: str = "full",
        trace_id: str | None = None,
        approval_mode: str = "inline",
        approval_handler: Callable[[ApprovalRequest], ApprovalDecision] | None = None,
        actor_type: str = "interactive",
        policy_profile: str = "interactive",
        knowledge_embedding_provider: Any = None,
        app_services: Any = None,
        intent_embedding_matcher: Any = None,
        cloud_mode: bool = False,
    ) -> None:
        self._model = model
        self._app_services = app_services
        self._owns_app_services = app_services is None
        self._embedding_provider = knowledge_embedding_provider
        self._checkpointer = checkpointer or InMemorySaver()
        self._data_dir = data_dir
        self._mcp_manager = MCPManager(data_dir / "mcp")
        self._capabilities = CapabilityManager(
            skill_registry=None if cloud_mode else SkillRegistry(data_dir / "skills"),
            mcp_manager=None if cloud_mode else self._mcp_manager,
        )
        from xiliu.capabilities.agent_registry import AgentRegistry

        for spec in AgentRegistry(data_dir).specs():
            self._capabilities.register(spec)
        if cloud_mode:
            from xiliu.cloud.policy import CloudPolicyEngine, NoCloudHooks

            self._policy_engine = CloudPolicyEngine()
            self._hook_engine = NoCloudHooks()
        else:
            self._policy_engine = PolicyEngine(
                data_dir / "policy.json", trusted_mcp_servers=set(self._mcp_manager.servers())
            )
            self._hook_engine = HookEngine(data_dir / "hooks.json")
        self._agent_model_factory = agent_model_factory
        self._tavily_api_key = tavily_api_key
        self._memory_limits = memory_limits or MemoryLimits(64_000, 0.8, 8_000)
        self._model_name = model_name
        self._token_counter = token_counter
        self._checkpoint_mode = checkpoint_mode
        self._trace_mode = trace_mode
        self._trace_id = trace_id
        self._approval_mode = normalize_approval_mode(approval_mode)
        self._approval_handler = approval_handler
        self._actor_type = actor_type
        self._policy_profile = "cloud" if cloud_mode else policy_profile
        self._cloud_budget = None
        if cloud_mode:
            from xiliu.cloud.budget import CloudCallBudget

            self._cloud_budget = CloudCallBudget(maximum_calls=16)
        self.last_trace_id: str | None = None
        self.last_state: dict[str, Any] = {}
        self.last_node_path: list[str] = []
        self._embedding_matcher = intent_embedding_matcher

    def close(self) -> None:
        """Release lazy MCP resources when a short-lived adapter finishes a turn."""
        self._mcp_manager.close()
        if self._owns_app_services and self._app_services is not None:
            self._app_services.close()

    def _context(self, workspace: Path, session_id: str = "") -> _RunContext:
        if self._app_services is None:
            from xiliu.app.actions import AppServices

            self._app_services = AppServices.open(self._data_dir)
        return _RunContext(
            self,
            workspace,
            self._data_dir,
            self._checkpoint_mode,
            self._trace_mode,
            self._trace_id,
            self._approval_mode,
            self._approval_handler,
            session_id,
            actor_type=self._actor_type,
            policy_profile=self._policy_profile,
        )

    def _memory(self, workspace: Path, *, include_workspace_history: bool = True) -> MemoryManager:
        return MemoryManager(
            workspace,
            UserPreferenceStore(self._data_dir),
            self._memory_limits,
            model_name=self._model_name,
            token_counter=self._token_counter,
            include_workspace_history=include_workspace_history,
        )

    def _fresh_inputs(
        self,
        task: str,
        workspace: Path,
        session_id: str,
        max_attempts: int,
        context_summary: str = "",
        *,
        include_workspace_history: bool = True,
    ) -> tuple[GraphState, MemoryManager]:
        memory_manager = self._memory(
            workspace, include_workspace_history=include_workspace_history
        )
        initial: dict[str, Any] = {
            "execution_run_id": uuid4().hex,
            "resume_node": "intent_router",
            "task": task,
            "todos": [],
            "research_notes": [],
            "agent_results": [],
            "tool_events": [],
            "evidence": [],
            "retrieval_hits": [],
            "result": "",
            "graph_state": "planning",
            "verification": "",
            "attempt": 0,
            "max_attempts": max_attempts,
            "final_answer": "",
            "session_id": session_id,
            "workspace": workspace,
            "current_node": "planner",
            "plan_summary": "",
            "acceptance_criteria": [],
            "agent_handoffs": [],
            "code_agent_summary": "",
            "verifier_summary": "",
            "last_error": "",
            "context_summary": context_summary,
            "compression_events": [],
        }
        return cast(
            GraphState,
            {
                **initial,
                "memory": memory_manager.assemble(initial, current_node="planner"),
            },
        ), memory_manager

    def resume(
        self, workspace: Path, *, task: str | None = None, max_attempts: int = 3
    ) -> Generator[RuntimeEvent, None, None]:
        try:
            context = self._context(workspace)
            restored, resume_event = CheckpointManager.load_resume_inputs(
                context, task=task, max_attempts=max_attempts
            )
            if restored.pop("runtime", None) is not self:
                raise CheckpointError("Invalid resume runtime.")
            context = replace(
                context, workspace=restored["workspace"], session_id=restored["session_id"]
            )
        except CheckpointError as exc:
            yield ErrorEvent(code=exc.code, message=str(exc))
            return
        except Exception:
            yield ErrorEvent(code="checkpoint_error", message="Could not resume checkpoint.")
            return

        try:
            yield from self._run(
                cast(GraphState, restored),
                self._memory(context.workspace),
                context,
                resumed=True,
                resume_event=resume_event,
            )
        except XiliuError as exc:
            yield ErrorEvent(code=getattr(exc, "code", "runtime_error"), message=str(exc))
        except Exception as exc:
            error = classify_provider_error(exc)
            yield ErrorEvent(code=error.code, message=str(error))

    def stream(
        self,
        task: str,
        session_id: str,
        max_attempts: int = 3,
    ) -> Generator[RuntimeEvent, None, None]:
        try:
            workspace = create_session_workspace(self._data_dir, session_id)
            TodoStore(workspace).start_task()
        except WorkspaceError as exc:
            yield ErrorEvent(code=exc.code, message=str(exc))
            return
        except OSError:
            yield ErrorEvent(code="workspace_error", message="could not initialize task progress")
            return

        try:
            inputs, memory_manager = self._fresh_inputs(task, workspace, session_id, max_attempts)
            yield from self._run(inputs, memory_manager, self._context(workspace, session_id))
        except XiliuError as exc:
            yield ErrorEvent(code=getattr(exc, "code", "runtime_error"), message=str(exc))
        except Exception as exc:
            error = classify_provider_error(exc)
            yield ErrorEvent(code=error.code, message=str(error))

    def stream_session(
        self,
        task: str,
        session_id: str,
        context_summary: str,
        max_attempts: int = 3,
        *,
        include_workspace_history: bool = True,
    ) -> Generator[RuntimeEvent, None, None]:
        """Route one session turn and answer lightweight chat directly."""
        try:
            from xiliu.routing import command_adapter

            control = command_adapter(task)
            if control and control["intent"] == "control":
                self.last_node_path, self.last_state = [], {}
                if control["action"] == "clear":
                    answer = "已清除当前上下文。"
                elif not context_summary.strip():
                    answer = "没有新的上下文需要压缩。"
                else:
                    from langchain_core.messages import HumanMessage

                    from xiliu.graph.memory import summarize_messages

                    answer = summarize_messages(
                        self._model,
                        [HumanMessage(content=context_summary)],
                        {"task": "Compress conversation context"},
                    )
                yield FinalEvent(text=answer, session_id=session_id)
                return
            workspace = create_session_workspace(self._data_dir, session_id)
            inputs, memory_manager = self._fresh_inputs(
                task,
                workspace,
                session_id,
                max_attempts,
                context_summary,
                include_workspace_history=include_workspace_history,
            )
            context = self._context(workspace, session_id)
            TodoStore(workspace).start_task()
            yield from self._run(inputs, memory_manager, context)
        except XiliuError as exc:
            yield ErrorEvent(code=getattr(exc, "code", "runtime_error"), message=str(exc))
        except Exception as exc:
            error = classify_provider_error(exc)
            yield ErrorEvent(code=error.code, message=str(error))

    def stream_workspace(
        self,
        task: str,
        workspace: Path,
        max_attempts: int = 3,
    ) -> Generator[RuntimeEvent, None, None]:
        try:
            resolved = create_explicit_workspace(self._data_dir, workspace)
            TodoStore(resolved).start_task()
        except WorkspaceError as exc:
            yield ErrorEvent(code=exc.code, message=str(exc))
            return
        except OSError:
            yield ErrorEvent(code="workspace_error", message="could not initialize task progress")
            return

        try:
            inputs, memory_manager = self._fresh_inputs(task, resolved, resolved.name, max_attempts)
            yield from self._run(inputs, memory_manager, self._context(resolved, resolved.name))
        except XiliuError as exc:
            yield ErrorEvent(code=getattr(exc, "code", "runtime_error"), message=str(exc))
        except Exception as exc:
            error = classify_provider_error(exc)
            yield ErrorEvent(code=error.code, message=str(error))

    def _observe_state(self, node, state):
        self.last_state = state
        if node is None:
            self.last_node_path = []
        else:
            self.last_node_path.append(node)

    def _run(
        self,
        inputs: GraphState,
        memory_manager: MemoryManager,
        context: _RunContext,
        *,
        resumed: bool = False,
        resume_event: Any = None,
    ) -> Iterator[RuntimeEvent]:
        from xiliu.app.authorization import conversation_sources, result_sources
        from xiliu.graph.routing import external_scope, local_scope, network_forbidden

        context = replace(
            context,
            execution_run_id=inputs.get("execution_run_id", ""),
            request_text=inputs["task"],
            source_text=conversation_sources(inputs["task"], inputs.get("context_summary", "")),
            source_outputs=[
                result_sources(event.get("output", ""), event.get("tool", ""))
                for event in inputs.get("tool_events", [])
                if event.get("ok")
            ],
            local_only=(
                network_forbidden(inputs["task"])
                or local_scope(inputs["task"])
                and not external_scope(inputs["task"])
            ),
        )
        checkpoint = CheckpointManager(context, task=inputs["task"])
        trace = TraceRecorder(context, task=inputs["task"])
        self.last_trace_id = trace.trace_id
        context = replace(context, trace_id=trace.trace_id, event_sink=trace.record_custom_event)
        checkpoint.trace_id = trace.trace_id
        events = None
        try:
            with _activate_run_context(context):
                events = iter(
                    stream_agent(
                        self._model,
                        inputs,
                        checkpointer=self._checkpointer,
                        memory_manager=memory_manager,
                        checkpoint_manager=checkpoint,
                        trace_recorder=trace,
                        resumed=resumed,
                        resume_event=resume_event,
                        model_name=self._model_name,
                        state_observer=self._observe_state,
                        embedding_matcher=self._embedding_matcher,
                    )
                )
            while True:
                with _activate_run_context(context):
                    event = next(events)
                yield event
        except StopIteration:
            return
        finally:
            if events is not None:
                close = getattr(events, "close", None)
                if callable(close):
                    with _activate_run_context(context):
                        close()


def create_runtime(
    settings: Settings,
    *,
    approval_mode: str = "inline",
    approval_handler: Callable[[ApprovalRequest], ApprovalDecision] | None = None,
    checkpoint_mode: str | None = None,
    trace_mode: str | None = None,
    data_dir: Path | None = None,
    actor_type: str = "interactive",
    policy_profile: str = "interactive",
    app_services: Any = None,
) -> Runtime:
    """Construct the unified graph runtime with independent specialist models."""

    main_model = create_chat_model(settings)
    return Runtime(
        main_model,
        knowledge_embedding_provider=embedding_provider_from_settings(settings),
        data_dir=settings.data_dir if data_dir is None else data_dir,
        agent_model_factory=lambda: create_chat_model(settings),
        tavily_api_key=settings.tavily_api_key,
        memory_limits=MemoryLimits(
            settings.context_window_tokens,
            settings.compression_trigger_ratio,
            settings.compression_keep_tokens,
        ),
        model_name=settings.model,
        checkpoint_mode=settings.checkpoint_mode if checkpoint_mode is None else checkpoint_mode,
        trace_mode=(
            settings.trace_mode
            if trace_mode is None
            else "full"
            if trace_mode == "on"
            else trace_mode
        ),
        trace_id=settings.trace_id,
        approval_mode=approval_mode,
        approval_handler=approval_handler,
        actor_type=actor_type,
        policy_profile=policy_profile,
        app_services=app_services,
        cloud_mode=getattr(settings, "cloud_mode", False),
    )
