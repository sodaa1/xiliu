"""Optional per-chunk vectors. Document embedding runs only in index jobs."""

from __future__ import annotations

import json
import math

from xiliu.rag.ingestion import same_document


def unit_vector(raw, dimension=None):
    if (
        not isinstance(raw, list)
        or not raw
        or any(type(n) not in (int, float) or not math.isfinite(n) for n in raw)
    ):
        raise ValueError("invalid embedding vector")
    if dimension is not None and len(raw) != dimension:
        raise ValueError("embedding dimension changed")
    norm = math.sqrt(sum(n * n for n in raw))
    if norm == 0:
        raise ValueError("zero embedding vector")
    return [float(n) / norm for n in raw]


class ChunkEmbeddings:
    def __init__(self, content, provider):
        self.content, self.provider = content, provider

    def index(self, item, chunks):
        model = self.provider.model
        if not isinstance(model, str) or not model.strip():
            raise ValueError("embedding model must be explicit")
        dimension = getattr(self.provider, "dimensions", None)
        cached, pending = {}, []
        with self.content.store.connect() as db:
            for chunk in chunks:
                row = db.execute(
                    "SELECT vector_json,dimension FROM rag_chunk_vectors "
                    "WHERE document_id=? AND content_hash=? AND model=? LIMIT 1",
                    (item["id"], chunk["content_hash"], model),
                ).fetchone()
                if row:
                    try:
                        cached[chunk["chunk_id"]] = unit_vector(
                            json.loads(row["vector_json"]), dimension
                        )
                        if dimension is None:
                            dimension = len(cached[chunk["chunk_id"]])
                        continue
                    except (ValueError, TypeError):
                        pass
                pending.append(chunk)
        if pending:
            raw = self.provider.embed_documents([chunk["text"] for chunk in pending])
            if len(raw) != len(pending):
                raise ValueError("invalid embedding response count")
            for chunk, vector in zip(pending, raw, strict=True):
                normalized = unit_vector(vector, dimension)
                dimension = len(normalized)
                cached[chunk["chunk_id"]] = normalized
        with self.content.store.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            current = db.execute("SELECT * FROM content_items WHERE id=?", (item["id"],)).fetchone()
            if not same_document(current, item):
                return False
            for chunk in chunks:
                vector = cached[chunk["chunk_id"]]
                db.execute(
                    "INSERT OR REPLACE INTO rag_chunk_vectors VALUES(?,?,?,?,?,?)",
                    (
                        chunk["chunk_id"],
                        item["id"],
                        model,
                        len(vector),
                        chunk["content_hash"],
                        json.dumps(vector),
                    ),
                )
            db.execute(
                "DELETE FROM rag_chunk_vectors WHERE document_id=? AND chunk_id NOT IN "
                "(SELECT chunk_id FROM rag_chunks WHERE document_id=?)",
                (item["id"], item["id"]),
            )
        return True

    def search(self, items, query):
        if not items:
            return []
        raw = self.provider.embed_documents([query])
        if len(raw) != 1:
            raise ValueError("invalid query embedding response")
        vector = unit_vector(raw[0], getattr(self.provider, "dimensions", None))
        allowed = {item["id"] for item in items}
        with self.content.store.connect() as db:
            rows = db.execute(
                """SELECT v.* FROM rag_chunk_vectors v
                JOIN rag_chunks c ON c.chunk_id=v.chunk_id
                JOIN content_items d ON d.id=c.document_id
                WHERE v.model=? AND c.revision=d.revision AND d.status='knowledge' """,
                (self.provider.model,),
            ).fetchall()
        scores = {}
        for row in rows:
            if row["document_id"] not in allowed:
                continue
            other = unit_vector(json.loads(row["vector_json"]), len(vector))
            score = sum(a * b for a, b in zip(vector, other, strict=True))
            if score > 0:
                scores[row["document_id"]] = max(scores.get(row["document_id"], 0), score)
        return sorted(scores, key=lambda key: (-scores[key], key))
