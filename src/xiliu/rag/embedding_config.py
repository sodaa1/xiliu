"""Optional embedding configuration shared by AppServices and Runtime."""

from contextvars import ContextVar
from typing import Any

embedding_provider: ContextVar[Any] = ContextVar("knowledge_embedding_provider", default=None)


def embedding_provider_from_settings(settings: Any) -> Any:
    model = (getattr(settings, "embedding_model", None) or "").strip()
    if not model:
        return None
    from langchain_openai import OpenAIEmbeddings

    return OpenAIEmbeddings(
        model=model, api_key=settings.api_key, base_url=settings.base_url, timeout=10, max_retries=0
    )
