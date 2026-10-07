from __future__ import annotations

from collections.abc import Callable, Generator, Iterator
from contextlib import contextmanager
from threading import Lock
from typing import Any

from xiliu.api.errors import WebError, provider_code
from xiliu.api.services.conversations import ConversationService
from xiliu.events import ErrorEvent, FinalEvent, PlannerEvent, ProgressEvent, VerifierEvent
from xiliu.providers.openai_compatible import classify_provider_error
from xiliu.runtime import create_runtime


class ChatService:
    def __init__(
        self,
        conversations: ConversationService,
        *,
        runtime_factory: Callable[..., Any] = create_runtime,
    ):
        self.conversations = conversations
        self.store = conversations.store
        self.runtime_factory = runtime_factory
        self.commands: Any = None
        self._active: set[str] = set()
        self._lock = Lock()

    @contextmanager
    def reserve(self, cid: str) -> Iterator[None]:
        with self._lock:
            if cid in self._active:
                raise WebError("conversation_busy", "这段对话正在处理中，请稍后再试。", 409)
            self._active.add(cid)
        try:
            yield
        finally:
            with self._lock:
                self._active.discard(cid)

    def stream_turn(self, conversation_id: str, text: str) -> Generator[dict[str, Any], None, None]:
        try:
            with self.reserve(conversation_id):
                yield from self._turn(conversation_id, text)
        except WebError as exc:
            yield {"type": "error", "code": exc.code, "message": exc.message}
        except Exception as exc:
            error = classify_provider_error(exc)
            yield {"type": "error", "code": provider_code(error.code), "message": str(error)}

    def _turn(self, cid: str, text: str) -> Iterator[dict[str, Any]]:
        conversation = self.conversations.get(cid)
        user = self.store.append_message(cid, "user", text)
        yield {"type": "status", "stage": "routing", "message": "正在处理"}
        task = text
        if text.lstrip().startswith("/"):
            if self.commands is None:
                raise WebError("invalid_command", "命令暂未开放。")
            result = self.commands.resolve(cid, text, conversation["model_override"])
            if result.task is None:
                message = self.store.append_message(
                    cid, result.role, result.message, metadata={"command": result.command}
                )
                yield {
                    "type": "final",
                    "message_id": message["id"],
                    "text": message["content"],
                    "role": message["role"],
                }
                return
            task = result.task
        if conversation["title"] == "New Chat" and not text.startswith("/"):
            self.store.update(cid, title=text.splitlines()[0][:24])
        settings = self.conversations.model_settings.runtime_settings(
            conversation["model_override"]
        )
        settings = settings.model_copy(update={"data_dir": self.store.path.parent})
        runtime = self.runtime_factory(settings, approval_mode="deny")
        events = None
        try:
            events = iter(
                runtime.stream_session(
                    task=task,
                    session_id=cid,
                    context_summary=self.conversations.build_context(cid, before_seq=user["seq"]),
                    include_workspace_history=False,
                )
            )
            for event in events:
                if isinstance(event, FinalEvent):
                    message = self.store.append_message(cid, "assistant", event.text)
                    yield {
                        "type": "final",
                        "message_id": message["id"],
                        "text": event.text,
                        "role": "assistant",
                    }
                    return
                if isinstance(event, ErrorEvent):
                    yield {
                        "type": "error",
                        "code": provider_code(event.code),
                        "message": event.message,
                    }
                    return
                if isinstance(event, ProgressEvent):
                    yield {"type": "progress", "stage": event.stage, "message": "正在处理…"}
                elif isinstance(event, PlannerEvent):
                    yield {"type": "progress", "stage": "planner", "message": "正在整理思路…"}
                elif isinstance(event, VerifierEvent):
                    yield {"type": "progress", "stage": "verifier", "message": "正在核对结果…"}
            yield {"type": "error", "code": "provider_error", "message": "本次对话未返回回答。"}
        finally:
            if events is not None and callable(getattr(events, "close", None)):
                events.close()
            if callable(getattr(runtime, "close", None)):
                runtime.close()
