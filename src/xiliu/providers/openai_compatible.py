from __future__ import annotations

from typing import Any
from urllib.parse import urlsplit

from langchain_core.messages import AIMessage
from langchain_openai import ChatOpenAI
from langgraph.config import get_stream_writer
from openai import APITimeoutError, DefaultAsyncHttpxClient, DefaultHttpxClient

from xiliu.config import Settings
from xiliu.errors import (
    AuthenticationProviderError,
    ProviderError,
    RateLimitProviderError,
    TimeoutProviderError,
)


class CancellableChatOpenAI(ChatOpenAI):
    def _stream(self, *args, **kwargs):
        from xiliu.execution.cancellation import check_cancelled

        for chunk in super()._stream(*args, **kwargs):
            check_cancelled()
            content = chunk.message.content
            if isinstance(content, list):
                for block in content:
                    if not isinstance(block, dict) or block.get("type") != "reasoning":
                        continue
                    for part in block.get("summary", []):
                        text = part.get("text") if isinstance(part, dict) else None
                        if isinstance(text, str) and text:
                            try:
                                writer = get_stream_writer()
                            except RuntimeError:
                                writer = None
                            if writer:
                                writer({"type": "reasoning", "stage": "model", "message": text})
            yield chunk

    def _get_request_payload(self, input_, *, stop=None, **kwargs):
        from xiliu.execution.cancellation import check_cancelled

        check_cancelled()
        return super()._get_request_payload(input_, stop=stop, **kwargs)

    def _convert_chunk_to_generation_chunk(self, chunk, default_chunk_class, base_generation_info):
        from xiliu.execution.cancellation import check_cancelled

        check_cancelled()
        return super()._convert_chunk_to_generation_chunk(
            chunk, default_chunk_class, base_generation_info
        )


class DeepSeekChatOpenAI(CancellableChatOpenAI):
    """Retain DeepSeek reasoning that the generic OpenAI adapter discards."""

    def _convert_chunk_to_generation_chunk(
        self, chunk: dict, default_chunk_class: type, base_generation_info: dict | None
    ):
        result = super()._convert_chunk_to_generation_chunk(
            chunk, default_chunk_class, base_generation_info
        )
        choices = chunk.get("choices", [])
        reasoning = choices[0].get("delta", {}).get("reasoning_content") if choices else None
        if result is not None and isinstance(reasoning, str) and reasoning:
            result.message.additional_kwargs["reasoning_content"] = reasoning
            try:
                writer = get_stream_writer()
            except RuntimeError:
                writer = None
            if writer:
                writer({"type": "reasoning", "stage": "model", "message": reasoning})
        return result

    def _get_request_payload(self, input_, *, stop=None, **kwargs):
        result = super()._get_request_payload(input_, stop=stop, **kwargs)
        messages = self._convert_input(input_).to_messages()
        for original, serialized in zip(messages, result["messages"], strict=True):
            if (
                isinstance(original, AIMessage)
                and "reasoning_content" in original.additional_kwargs
            ):
                serialized["reasoning_content"] = original.additional_kwargs["reasoning_content"]
        return result


def lightweight_model(model: Any, *, routing: bool = False) -> Any:
    """Lower model effort without bypassing the existing intent/workflow graph."""
    if isinstance(model, DeepSeekChatOpenAI):
        if routing:
            return model.bind(extra_body={"thinking": {"type": "disabled"}})
        return model.bind(reasoning_effort="low")
    if isinstance(model, ChatOpenAI) and model.model_name.startswith(("gpt-5", "gpt-6")):
        return model.bind(reasoning_effort="low")
    return model


def create_chat_model(settings: Settings) -> ChatOpenAI:
    """Create a streaming OpenAI-compatible chat model from validated settings."""

    kwargs: dict[str, Any] = {
        "api_key": settings.api_key,
        "model": settings.model,
        "temperature": settings.temperature,
        "timeout": settings.timeout_seconds,
        "streaming": True,
        "max_retries": 0,
    }
    if settings.base_url:
        kwargs["base_url"] = settings.base_url
        if urlsplit(settings.base_url).hostname in {"localhost", "127.0.0.1", "::1"}:
            kwargs["http_client"] = DefaultHttpxClient(trust_env=False)
            kwargs["http_async_client"] = DefaultAsyncHttpxClient(trust_env=False)
    if (
        settings.provider == "openai"
        and settings.model.startswith(("gpt-5", "gpt-6", "o1", "o3", "o4"))
        and (not settings.base_url or urlsplit(settings.base_url).hostname == "api.openai.com")
    ):
        kwargs.update(
            use_responses_api=True,
            reasoning={"effort": "low", "summary": "auto"},
            output_version="responses/v1",
        )
    adapter = (
        DeepSeekChatOpenAI
        if settings.provider in {"deepseek", "mimo"}
        or settings.model.startswith("deepseek-")
        else CancellableChatOpenAI
    )
    return adapter(**kwargs)


def _status_code(error: Exception) -> int | None:
    direct = getattr(error, "status_code", None)
    if isinstance(direct, int):
        return direct
    response = getattr(error, "response", None)
    response_status = getattr(response, "status_code", None)
    return response_status if isinstance(response_status, int) else None


def classify_provider_error(error: Exception) -> ProviderError:
    """Map provider failures to stable, secret-free application errors."""

    status = _status_code(error)
    if status in {401, 403}:
        return AuthenticationProviderError("Provider authentication failed")
    if status == 429:
        return RateLimitProviderError("Provider rate limit exceeded")
    if isinstance(error, (TimeoutError, APITimeoutError, TimeoutProviderError)):
        return TimeoutProviderError("Provider request timed out")
    return ProviderError("Provider request failed")
