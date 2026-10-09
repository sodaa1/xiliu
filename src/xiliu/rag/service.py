from __future__ import annotations

from xiliu.api.errors import WebError
from xiliu.api.services.retrieval import RetrievalService, _terms
from xiliu.rag.chunking import chunk_document
from xiliu.rag.embeddings import ChunkEmbeddings
from xiliu.rag.ingestion import IndexWorker, index_document, remove_chunks


class RAGService:
    def __init__(self, content, knowledge, *, embedding_provider=None):
        self.content = content
        self.embedding_provider = embedding_provider
        self.vectors = ChunkEmbeddings(content, embedding_provider)
        self.retrieval = RetrievalService(
            content, knowledge, embedding_provider=embedding_provider, indexed_only=True
        )
        self.retrieval.vector_retriever = self.vectors.search
        self.worker = IndexWorker(self)

    def get_document(self, document_id: str) -> dict | None:
        try:
            item = self.content.get(document_id)
        except WebError as exc:
            if exc.status == 404:
                return None
            raise
        if item["status"] != "knowledge":
            return None
        return {**item, "document_id": item["id"], "source_uri": item["source"] or None}

    def search(self, query: str, limit: int = 6, mode: str = "auto", *, filters=None, top_k=None):
        if top_k is not None:
            limit = top_k
        if filters is not None and (
            not isinstance(filters, dict) or set(filters) - {"tags", "folder_id", "document_ids"}
        ):
            raise ValueError("invalid search filters")
        if filters:
            for key in ("tags", "document_ids"):
                if key in filters and (
                    not isinstance(filters[key], list)
                    or any(not isinstance(value, str) for value in filters[key])
                ):
                    raise ValueError("invalid filter values")
            if "folder_id" in filters and not isinstance(filters["folder_id"], (str, type(None))):
                raise ValueError("invalid folder filter")
        result = self.retrieval.search(query, limit=limit, mode=mode, filters=filters)
        hits = []
        for hit in result["items"]:
            item = self.get_document(hit["document_id"])
            if item is None:
                continue
            if filters and (
                ("tags" in filters and not set(filters["tags"]) <= set(item["tags"]))
                or ("folder_id" in filters and item["folder_id"] != filters["folder_id"])
                or ("document_ids" in filters and item["id"] not in filters["document_ids"])
            ):
                continue
            with self.content.store.connect() as db:
                chunks = [
                    dict(row)
                    for row in db.execute(
                        "SELECT * FROM rag_chunks WHERE document_id=? AND revision=? "
                        "ORDER BY start_offset",
                        (item["id"], item["revision"]),
                    )
                ]
            if not chunks:
                # Legacy or pending documents remain readable through the existing content FTS.
                chunks = chunk_document(item["id"], item["content"] or item["summary"])
            terms = _terms(query)
            chunk = max(
                chunks, key=lambda c: sum(t in c["text"].casefold() for t in terms), default=None
            )
            hits.append(
                {
                    **hit,
                    "title": item["title"],
                    "summary": item["summary"],
                    "chunk_id": chunk["chunk_id"] if chunk else None,
                    "snippet": chunk["text"][:600] if chunk else hit["snippet"],
                    "revision": item["revision"],
                    "source_uri": item["source"] or None,
                    "tags": item["tags"],
                }
            )
        hits = hits[:limit]
        vector = "embedding" in result["channels"]
        return {
            **result,
            "items": hits,
            "hits": hits,
            "ok": True,
            "matched": bool(hits),
            "retrieval_mode": "hybrid" if vector else "fts_only",
            "degraded": self.embedding_provider is not None and not vector,
        }

    def index_document(self, document_id: str, revision: int):
        return index_document(self, document_id, revision)

    def delete_document(self, document_id: str, revision: int):
        with self.content.store.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            current = db.execute(
                "SELECT revision,status FROM content_items WHERE id=?", (document_id,)
            ).fetchone()
            if current and (current["revision"] != revision or current["status"] == "knowledge"):
                return {"status": "stale", "document_id": document_id}
            remove_chunks(db, document_id)
            db.execute("DELETE FROM rag_chunk_vectors WHERE document_id=?", (document_id,))
            if db.execute("SELECT 1 FROM sqlite_master WHERE name='knowledge_vectors'").fetchone():
                db.execute("DELETE FROM knowledge_vectors WHERE document_id=?", (document_id,))
            db.execute(
                "UPDATE rag_index_jobs SET state='deleted',error=NULL "
                "WHERE document_id=? AND revision=?",
                (document_id, revision),
            )
        return {"status": "deleted", "document_id": document_id, "revision": revision}
