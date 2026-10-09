from __future__ import annotations

import json
from contextvars import ContextVar
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from langchain_core.tools import BaseTool
from langchain_core.tools.base import ArgsSchema
from pydantic import BaseModel, ConfigDict, Field, StrictInt

from xiliu.execution.gateway import active_run

embedding_provider: ContextVar[Any] = ContextVar("knowledge_embedding_provider", default=None)


def embedding_provider_from_settings(settings: Any) -> Any:
    """Use the existing account only when a distinct embedding model was configured."""
    model = (getattr(settings, "embedding_model", None) or "").strip()
    if not model:
        return None
    from langchain_openai import OpenAIEmbeddings

    return OpenAIEmbeddings(
        model=model,
        api_key=settings.api_key,
        base_url=settings.base_url,
        timeout=10,
        max_retries=0,
    )


class SearchInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str = Field(min_length=1, max_length=1000)
    limit: StrictInt = Field(default=6, ge=1, le=20)
    mode: str = "auto"


class KnowledgeSearchTool(BaseTool):
    name: str = "knowledge_search"
    description: str = (
        "Search the user's local Knowledge library (知识库/资料/标签/文件夹). "
        "Use auto for browsing tags or folders, hybrid for questions and relationships. "
        "Returns document_id, title, summary, matched_tags, snippets and citation_url. "
        "Cite evidence with Markdown [title](citation_url), using the exact returned URL; "
        "include document_id where useful. Never fabricate references. Inbox is excluded."
    )
    args_schema: ArgsSchema | None = SearchInput
    data_dir: Path
    provider: Any = Field(default=None, exclude=True)

    def _run(self, query: str, limit: int = 6, mode: str = "auto") -> str:
        from xiliu.api.services.content import ContentService
        from xiliu.api.services.knowledge import KnowledgeService
        from xiliu.api.store import AppStore
        from xiliu.rag.service import RAGService

        try:
            content = ContentService(AppStore(self.data_dir))
            retrieval = RAGService(
                content, KnowledgeService(content), embedding_provider=self.provider
            )
            result = retrieval.search(query, limit, mode)
            for item in result["items"]:
                item["citation_url"] = "/knowledge?" + urlencode(
                    {"folder": "all", "document": item["document_id"]}
                )
            result.update(ok=True, matched=bool(result["items"]), hits=result["items"])
            return json.dumps(result, ensure_ascii=False)
        except ValueError as exc:
            return json.dumps({"ok": False, "error": "invalid_search", "reason": str(exc)})


def build_knowledge_tools() -> list[BaseTool]:
    context = active_run.get()
    if context is None or context.data_dir is None:
        return []
    return [KnowledgeSearchTool(data_dir=context.data_dir, provider=embedding_provider.get()),
            KnowledgeGetTool(data_dir=context.data_dir)]


class GetInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    document_id: str = Field(min_length=1, max_length=100)


class KnowledgeGetTool(BaseTool):
    name: str = 'knowledge_get'
    description: str = 'Read one local Knowledge document by an actual returned document_id.'
    args_schema: ArgsSchema | None = GetInput
    data_dir: Path

    def _run(self, document_id: str) -> str:
        from xiliu.api.services.content import ContentService
        from xiliu.api.services.knowledge import KnowledgeService
        from xiliu.api.store import AppStore
        from xiliu.rag.service import RAGService

        content = ContentService(AppStore(self.data_dir))
        item = RAGService(content, KnowledgeService(content)).get_document(document_id)
        if item is None:
            return json.dumps({'ok': True, 'matched': False, 'document': None})
        return json.dumps({'ok': True, 'matched': True,
                           'document': {**item, 'content': item['content'][:16000],
                                        'snippet': item['content'][:1000]}}, ensure_ascii=False)
