"""Local knowledge retrieval. Routing and rank fusion never require a chat model."""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Callable
from typing import Any

from xiliu.api.services.content import ContentService


def _terms(query: str) -> list[str]:
    terms = re.findall(r"[a-z0-9_]+|[\u3400-\u9fff]+", query.casefold())
    expanded = []
    for term in terms:
        expanded.append(term)
        if re.fullmatch(r"[\u3400-\u9fff]{3,}", term):
            expanded.extend(term[i : i + 2] for i in range(len(term) - 1))
    return list(dict.fromkeys(expanded))


class RetrievalService:
    def __init__(
        self,
        content: ContentService,
        knowledge: Any,
        *,
        embedding_provider: Any = None,
        indexed_only: bool = False,
    ):
        self.content = content
        self.knowledge = knowledge
        self.embedding_provider = embedding_provider
        self.indexed_only = indexed_only
        self.vector_retriever: Callable[[list[dict[str, Any]], str], list[str]] | None = None

    def _vectors(self, items: list[dict[str, Any]], query: str) -> list[str]:
        provider = self.embedding_provider
        model = provider.model
        expected_dimension = getattr(provider, "dimensions", None)
        if not isinstance(model, str) or not model.strip():
            raise ValueError("embedding model must be explicit")

        def validate(raw: Any, dimension: int | None = None) -> list[float]:
            if (
                not isinstance(raw, list)
                or not raw
                or any(
                    type(number) not in (int, float) or not math.isfinite(number) for number in raw
                )
            ):
                raise ValueError("invalid embedding vector")
            if dimension is not None and len(raw) != dimension:
                raise ValueError("embedding dimensions changed")
            vector = [float(number) for number in raw]
            norm = math.sqrt(sum(number * number for number in vector))
            if not norm:
                raise ValueError("zero embedding vector")
            return [number / norm for number in vector]

        query_vectors = provider.embed_documents([query])
        if len(query_vectors) != 1:
            raise ValueError("invalid embedding response count")
        query_vector = validate(query_vectors[0], expected_dimension)
        dimension = len(query_vector)
        vectors = {}
        pending = []
        with self.content.store.connect() as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS knowledge_vectors ("
                "document_id TEXT PRIMARY KEY, model TEXT NOT NULL, dimension INTEGER NOT NULL, "
                "content_hash TEXT NOT NULL, vector_json TEXT NOT NULL)"
            )
            db.execute(
                "DELETE FROM knowledge_vectors WHERE document_id NOT IN "
                "(SELECT id FROM content_items WHERE status='knowledge')"
            )
            for item in items:
                text = "\n".join(
                    [item["title"], item["summary"], " ".join(item["tags"]), item["content"]]
                )
                digest = hashlib.sha256(text.encode()).hexdigest()
                row = db.execute(
                    "SELECT * FROM knowledge_vectors WHERE document_id=?", (item["id"],)
                ).fetchone()
                if (
                    row
                    and row["model"] == model
                    and row["dimension"] == dimension
                    and row["content_hash"] == digest
                ):
                    try:
                        vectors[item["id"]] = validate(json.loads(row["vector_json"]), dimension)
                        continue
                    except (ValueError, TypeError):
                        pass
                if not self.indexed_only:
                    pending.append((item["id"], text, digest))
        if pending:
            embedded = provider.embed_documents([text for _, text, _ in pending])
            if len(embedded) != len(pending):
                raise ValueError("invalid embedding response count")
            valid = [validate(vector, dimension) for vector in embedded]
            with self.content.store.connect() as db:
                db.execute("BEGIN IMMEDIATE")
                for (item_id, _, digest), vector in zip(pending, valid, strict=True):
                    current = db.execute(
                        "SELECT title,summary,tags_json,content FROM content_items "
                        "WHERE id=? AND status='knowledge'",
                        (item_id,),
                    ).fetchone()
                    if current is None:
                        continue
                    current_text = "\n".join(
                        [
                            current["title"],
                            current["summary"],
                            " ".join(json.loads(current["tags_json"])),
                            current["content"],
                        ]
                    )
                    if hashlib.sha256(current_text.encode()).hexdigest() != digest:
                        continue
                    db.execute(
                        "INSERT OR REPLACE INTO knowledge_vectors VALUES(?,?,?,?,?)",
                        (item_id, model, dimension, digest, json.dumps(vector)),
                    )
                    vectors[item_id] = vector
        scores = [
            (sum(a * b for a, b in zip(query_vector, vector, strict=True)), item_id)
            for item_id, vector in vectors.items()
        ]
        return [
            item_id
            for score, item_id in sorted(scores, key=lambda pair: (-pair[0], pair[1]))
            if score > 0
        ]

    def search(
        self, query: str, limit: int = 6, mode: str = "auto", *, filters=None
    ) -> dict[str, Any]:
        if not isinstance(query, str) or not query.strip() or len(query) > 1000:
            raise ValueError("query must contain 1 to 1000 characters")
        if type(limit) is not int or not 1 <= limit <= 20:
            raise ValueError("limit must be an integer from 1 to 20")
        if not isinstance(mode, str) or mode not in {"auto", "tag", "hybrid"}:
            raise ValueError("mode must be auto, tag or hybrid")
        query = query.strip().casefold()
        items = self.content.list(status="knowledge")

        def visible(item):
            return not filters or (
                ("tags" not in filters or set(filters["tags"]) <= set(item["tags"]))
                and ("folder_id" not in filters or item.get("folder_id") == filters["folder_id"])
                and ("document_ids" not in filters or item["id"] in filters["document_ids"])
            )

        items = [item for item in items if visible(item)]
        folders = self.knowledge.list_folders()
        matched_folders = {
            folder["id"]
            for folder in folders
            if folder["name"].casefold() in query or folder["id"].casefold() == query
        }
        tag_items = [
            item
            for item in items
            if (
                any(tag.casefold() in query for tag in item["tags"])
                or item.get("folder_id") in matched_folders
            )
        ]
        relation = re.search(
            r"关系|区别|比较|为什么|如何|怎么|影响|联系|原因|谁|哪个|什么|\?|？|"
            r"\b(why|how|who|what|compare|difference|relationship|between)\b",
            query,
        )
        browse = re.search(r"标签|文件夹|浏览|列出|查看|\b(tag|folder|browse|list)\b", query)
        exact = any(query == tag.casefold() for item in items for tag in item["tags"])
        exact = exact or any(query == folder["name"].casefold() for folder in folders)
        if tag_items and (mode == "tag" or (mode == "auto" and not relation and (browse or exact))):
            return self._result("tag", ["tags"], tag_items[:limit], query)
        terms = _terms(query)
        ranks: list[list[str]] = [self._fts(terms)]
        scored = []
        for item in items:
            text = f"{item['title']} {item['summary']} {' '.join(item['tags'])}".casefold()
            score = sum(term in text for term in terms)
            score += 4 * sum(tag.casefold() in query for tag in item["tags"])
            score += 4 * (item.get("folder_id") in matched_folders)
            if score:
                scored.append((-score, item["id"]))
        ranks.append([item_id for _, item_id in sorted(scored)])
        channels = ["fts", "metadata"]
        if self.embedding_provider is not None:
            try:
                vector_ranking = (
                    self.vector_retriever(items, query)
                    if self.vector_retriever
                    else self._vectors(items, query)
                )
                ranks.append(vector_ranking)
                if vector_ranking or not self.indexed_only:
                    channels.append("embedding")
            except Exception:
                # An unavailable optional endpoint must not disable local knowledge search.
                pass
        fused: dict[str, float] = {}
        for ranking in ranks:
            for rank, item_id in enumerate(ranking):
                fused[item_id] = fused.get(item_id, 0) + 1 / (60 + rank + 1)
        # Optional remote embeddings can overlap a manual edit, move or deletion.
        # Return current Knowledge evidence rather than the pre-request snapshot.
        by_id = {
            item["id"]: item for item in self.content.list(status="knowledge") if visible(item)
        }
        selected = [
            by_id[item_id]
            for item_id in sorted(fused, key=lambda item_id: (-fused[item_id], item_id))
            if item_id in by_id
        ][:limit]
        return self._result("hybrid", channels, selected, query)

    def _fts(self, terms: list[str]) -> list[str]:
        if not terms:
            return []
        long = [term for term in terms if len(term) >= 3]
        short = [term for term in terms if len(term) < 3]
        ranked = []
        with self.content.store.connect() as db:
            if long:
                expression = " OR ".join('"' + term.replace('"', '""') + '"' for term in long)
                if db.execute("SELECT 1 FROM sqlite_master WHERE name='rag_chunk_fts'").fetchone():
                    ranked.extend(
                        row["id"]
                        for row in db.execute(
                            "SELECT d.id FROM rag_chunk_fts f "
                            "JOIN rag_chunks c ON c.chunk_id=f.chunk_id "
                            "JOIN content_items d ON d.id=c.document_id "
                            "WHERE d.status='knowledge' AND c.revision=d.revision "
                            "AND rag_chunk_fts MATCH ? ORDER BY bm25(rag_chunk_fts),d.id",
                            (expression,),
                        )
                    )
                ranked.extend(
                    row["id"]
                    for row in db.execute(
                        "SELECT content_fts.id FROM content_fts JOIN content_items c "
                        "ON c.id=content_fts.id WHERE c.status='knowledge' AND content_fts MATCH ? "
                        "ORDER BY bm25(content_fts), c.id",
                        (expression,),
                    )
                )
            if short:
                clauses = " OR ".join(
                    "(title || content || summary) LIKE ? ESCAPE '|'" for _ in short
                )
                params = [
                    "%" + term.replace("|", "||").replace("%", "|%").replace("_", "|_") + "%"
                    for term in short
                ]
                ranked.extend(
                    row["id"]
                    for row in db.execute(
                        "SELECT id FROM content_items WHERE status='knowledge' AND ("
                        + clauses
                        + ") ORDER BY updated_at DESC, id",
                        params,
                    )
                )
        return list(dict.fromkeys(ranked))

    @staticmethod
    def _result(mode: str, channels: list[str], items: list[dict[str, Any]], query: str):
        results = []
        for item in items:
            text = item["content"] or item["summary"]
            positions = [text.casefold().find(term) for term in _terms(query)]
            start = max(0, min((pos for pos in positions if pos >= 0), default=0) - 60)
            results.append(
                {
                    "document_id": item["id"],
                    "title": item["title"],
                    "summary": item["summary"],
                    "matched_tags": [tag for tag in item["tags"] if tag.casefold() in query],
                    "snippet": ("…" if start else "")
                    + text[start : start + 400]
                    + ("…" if len(text) > start + 400 else ""),
                }
            )
        return {"mode_used": mode, "channels": channels, "items": results}
