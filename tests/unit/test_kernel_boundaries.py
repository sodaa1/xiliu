import json
from uuid import uuid4

import pytest
from langchain_core.messages import AIMessage

from xiliu.api.app import create_app
from xiliu.api.services.content import ContentService
from xiliu.api.services.knowledge import KnowledgeService
from xiliu.api.store import AppStore
from xiliu.events import FinalEvent
from xiliu.runtime import Runtime


def test_planner_can_use_local_tools_without_todos_or_delegation(tmp_path):
    ContentService(AppStore(tmp_path)).create({"content": "Refero", "status": "knowledge"})

    class Model:
        calls = 0

        def bind_tools(self, tools):
            return self

        def invoke(self, messages):
            if "Verifier" in messages[0].content:
                return AIMessage(content='{"status":"passed","reason":"Local evidence complete"}')
            self.calls += 1
            if self.calls == 1:
                return AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "id": "local",
                            "name": "app",
                            "args": {
                                "operation": "execute",
                                "action_id": "knowledge.search",
                                "arguments": {"query": "Refero"},
                            },
                        }
                    ],
                )
            return AIMessage(
                content=json.dumps(
                    {
                        "summary": "Refero",
                        "plan_summary": "Read local source",
                        "acceptance_criteria": ["Real local source"],
                        "ready_for_verification": True,
                    }
                )
            )

    model = Model()
    runtime = Runtime(model, data_dir=tmp_path, checkpoint_mode="off", trace_mode="off")
    try:
        events = list(runtime.stream_session("比较多篇我的收藏 Refero", str(uuid4()), ""))
    finally:
        runtime.close()
    assert isinstance(events[-1], FinalEvent) and "状态：passed" in events[-1].text
    assert model.calls == 2


def test_filters_do_not_lose_target_outside_global_top_twenty(tmp_path):
    from xiliu.rag.service import RAGService

    content = ContentService(AppStore(tmp_path))
    items = [content.create({"content": "same keyword", "status": "knowledge"}) for _ in range(25)]
    rag = RAGService(content, KnowledgeService(content))
    ranked = rag.search("keyword", limit=20)["hits"]
    excluded = next(item for item in items if item["id"] not in {h["document_id"] for h in ranked})
    result = rag.search("keyword", filters={"document_ids": [excluded["id"]]})
    assert result["hits"][0]["document_id"] == excluded["id"]


@pytest.mark.asyncio
async def test_failed_inbox_start_cleans_up_rag_worker(tmp_path, monkeypatch):
    app = create_app(data_dir=tmp_path, env_file=tmp_path / ".env")

    def fail():
        raise RuntimeError("startup failed")

    monkeypatch.setattr(app.state.inbox, "start", fail)
    with pytest.raises(RuntimeError, match="startup failed"):
        async with app.router.lifespan_context(app):
            pass
    assert app.state.retrieval.worker.thread is None
