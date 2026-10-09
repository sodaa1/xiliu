"""Offline proof using real Runtime/Gateway/SQLite and deterministic fake models."""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from langchain_core.messages import AIMessage

from xiliu.api.services.content import ContentService
from xiliu.api.services.knowledge import KnowledgeService
from xiliu.api.store import AppStore
from xiliu.events import FinalEvent
from xiliu.rag.service import RAGService
from xiliu.runtime import Runtime


class LocalModel:
    def __init__(self, delegated=False):
        self.calls = 0
        self.delegated = delegated

    def bind_tools(self, tools):
        return self

    def invoke(self, messages):
        if "Verifier" in messages[0].content:
            return AIMessage(
                content='{"status":"passed","reason":"Actual local IDs support answer"}'
            )
        self.calls += 1
        if self.delegated:
            if self.calls == 1:
                return AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "id": "delegate",
                            "name": "agent_call",
                            "args": {
                                "agent_id": "rag",
                                "instruction": "比较我的知识库中的两篇 Memory 文章",
                            },
                        }
                    ],
                )
            return AIMessage(
                content=json.dumps(
                    {
                        "summary": "两篇 Memory 资料均有本地来源证据。",
                        "plan_summary": "Local RAG comparison",
                        "acceptance_criteria": ["Two local documents"],
                        "ready_for_verification": True,
                    },
                    ensure_ascii=False,
                )
            )
        if self.calls == 1:
            return AIMessage(
                content="",
                tool_calls=[
                    {"id": "local-query", "name": "knowledge_search", "args": {"query": "Refero"}}
                ],
            )
        return AIMessage(content="你保存的 UI 网站是 Refero。")


class RewriteModel:
    def invoke(self, messages):
        return AIMessage(content='{"query":"Memory"}')


def main():
    destination = Path("logs/development/xiliu-02-proof.json")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix="xiliu-02-proof-") as temporary:
        data_dir = Path(temporary)
        content = ContentService(AppStore(data_dir))
        documents = [
            content.create({"title": title, "content": body, "status": "knowledge"})
            for title, body in [
                ("Refero", "UI design reference"),
                ("Memory A", "Memory uses durable records"),
                ("Memory B", "Memory uses retrieval and summaries"),
            ]
        ]
        rag = RAGService(content, KnowledgeService(content))
        jobs = rag.worker.process_pending()
        result = {
            "fixture_documents": [d["id"] for d in documents],
            "index_jobs_processed": jobs,
            "retrieval": rag.search("Memory"),
            "runs": {},
        }
        for label, mode, task in [
            ("fast", "fast", "我的收藏 Refero 网站叫什么？"),
            ("deep_rag", "deep", "比较多篇我的知识库 Memory 文章"),
        ]:
            runtime = Runtime(
                LocalModel(delegated=label == "deep_rag"),
                data_dir=data_dir,
                agent_model_factory=RewriteModel,
                checkpoint_mode="off",
                trace_mode="full",
            )
            session = str(uuid4())
            try:
                events = list(runtime.stream_session(task, session, "", mode=mode))
                final = next(event.text for event in events if isinstance(event, FinalEvent))
                trace = (
                    data_dir / "workspaces" / session / ".xiliu" / "traces" / runtime.last_trace_id
                )
                updates = [
                    json.loads(line)
                    for line in (trace / "events.jsonl").read_text(encoding="utf-8").splitlines()
                ]
                result["runs"][label] = {"final_answer": final, "trace_events": updates}
                assert "failed" not in final
            finally:
                runtime.close()
        destination.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Offline proof saved: {destination.resolve()}")


if __name__ == "__main__":
    main()
