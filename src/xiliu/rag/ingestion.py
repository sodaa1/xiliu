"""Durable incremental index jobs; publish only against the current document revision."""

from __future__ import annotations

import json
import sqlite3
import time
from threading import Event, Thread

from xiliu.api.errors import WebError
from xiliu.rag.chunking import CHUNK_VERSION, chunk_document


def migrate(store) -> None:
    with store.connect() as db:
        present = db.execute("SELECT 1 FROM sqlite_master WHERE name='rag_migrations'").fetchone()
        if not present:
            backup = store.path.with_suffix(".pre-rag.sqlite3")
            if not backup.exists():
                with sqlite3.connect(backup) as destination:
                    db.backup(destination)
        db.executescript("""
            CREATE TABLE IF NOT EXISTS rag_migrations(version INTEGER PRIMARY KEY);
            CREATE TABLE IF NOT EXISTS rag_chunks(
                chunk_id TEXT PRIMARY KEY, document_id TEXT NOT NULL, revision INTEGER NOT NULL,
                content_hash TEXT NOT NULL, text TEXT NOT NULL,
                start_offset INTEGER NOT NULL, end_offset INTEGER NOT NULL,
                config_version TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS rag_chunk_document ON rag_chunks(document_id,revision);
            CREATE VIRTUAL TABLE IF NOT EXISTS rag_chunk_fts USING fts5(
                chunk_id UNINDEXED, text, tokenize='trigram');
            CREATE TABLE IF NOT EXISTS rag_index_jobs(
                document_id TEXT PRIMARY KEY, revision INTEGER NOT NULL,
                state TEXT NOT NULL DEFAULT 'pending', attempts INTEGER NOT NULL DEFAULT 0,
                next_run REAL NOT NULL DEFAULT 0, error TEXT,
                last_indexed_revision INTEGER, embedding_model_version TEXT);
            CREATE TABLE IF NOT EXISTS rag_chunk_vectors(
                chunk_id TEXT PRIMARY KEY, document_id TEXT NOT NULL, model TEXT NOT NULL,
                dimension INTEGER NOT NULL, content_hash TEXT NOT NULL, vector_json TEXT NOT NULL);
            INSERT OR IGNORE INTO rag_migrations VALUES(1);
            INSERT OR IGNORE INTO rag_index_jobs(document_id,revision)
                SELECT id,revision FROM content_items WHERE status='knowledge';
        """)


def enqueue(db, item: dict) -> None:
    db.execute(
        """INSERT INTO rag_index_jobs(document_id,revision,state)
        VALUES(?,?,'pending') ON CONFLICT(document_id) DO UPDATE SET
        revision=excluded.revision,state='pending',attempts=0,next_run=0,error=NULL
        WHERE rag_index_jobs.revision<=excluded.revision""",
        (item["id"], item["revision"]),
    )


def remove_chunks(db, document_id: str) -> None:
    db.execute(
        "DELETE FROM rag_chunk_fts WHERE chunk_id IN "
        "(SELECT chunk_id FROM rag_chunks WHERE document_id=?)",
        (document_id,),
    )
    db.execute("DELETE FROM rag_chunks WHERE document_id=?", (document_id,))


def same_document(row, item) -> bool:
    return bool(
        row
        and row["revision"] == item["revision"]
        and row["status"] == "knowledge"
        and all(row[key] == item[key] for key in ("title", "content", "summary", "source"))
        and json.loads(row["tags_json"]) == item["tags"]
    )


class IndexWorker:
    def __init__(self, service):
        self.service = service
        self.stop = Event()
        self.thread: Thread | None = None

    def start(self):
        if self.thread and self.thread.is_alive():
            return
        with self.service.content.store.connect() as db:
            db.execute("UPDATE rag_index_jobs SET state='pending' WHERE state='indexing'")
            provider = self.service.embedding_provider
            if provider is not None:
                db.execute(
                    "UPDATE rag_index_jobs SET state='pending',attempts=0,next_run=0 "
                    "WHERE state IN ('indexed','partial') AND embedding_model_version IS NOT ?",
                    (getattr(provider, "model", None),),
                )
        self.stop.clear()
        self.thread = Thread(target=self._run, name="xiliu-rag-index", daemon=False)
        self.thread.start()

    def shutdown(self):
        self.stop.set()
        if self.thread:
            self.thread.join()
        self.thread = None

    def _run(self):
        while not self.stop.is_set():
            self.process_pending()
            self.stop.wait(0.5)

    def process_pending(self) -> int:
        with self.service.content.store.connect() as db:
            jobs = db.execute(
                "SELECT * FROM rag_index_jobs WHERE state IN ('pending','partial') "
                "AND attempts<3 AND next_run<=? ORDER BY document_id LIMIT 20",
                (time.time(),),
            ).fetchall()
        for job in jobs:
            if self.stop.is_set():
                break
            try:
                self.service.index_document(job["document_id"], job["revision"])
            except Exception as exc:
                with self.service.content.store.connect() as db:
                    db.execute(
                        "UPDATE rag_index_jobs SET attempts=attempts+1,error=?,"
                        "state=CASE WHEN attempts>=2 THEN 'failed' ELSE 'pending' END,"
                        "next_run=? WHERE document_id=? AND revision=?",
                        (
                            type(exc).__name__,
                            time.time() + 2 ** (job["attempts"] + 1),
                            job["document_id"],
                            job["revision"],
                        ),
                    )
        return len(jobs)


def index_document(service, document_id: str, revision: int) -> dict:
    content = service.content
    try:
        item = content.get(document_id)
    except WebError as exc:
        if exc.status != 404:
            raise
        return service.delete_document(document_id, revision)
    if item["revision"] != revision:
        return {"status": "stale", "document_id": document_id, "revision": revision}
    if item["status"] != "knowledge":
        return service.delete_document(document_id, revision)
    chunks = chunk_document(document_id, item["content"] or item["summary"])
    with content.store.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        current = db.execute("SELECT * FROM content_items WHERE id=?", (document_id,)).fetchone()
        if not same_document(current, item):
            return {"status": "stale", "document_id": document_id}
        row = db.execute(
            "SELECT revision FROM rag_index_jobs WHERE document_id=?", (document_id,)
        ).fetchone()
        if not row or row["revision"] != revision:
            enqueue(db, item)
        remove_chunks(db, document_id)
        for chunk in chunks:
            db.execute(
                "INSERT INTO rag_chunks VALUES(?,?,?,?,?,?,?,?)",
                (
                    chunk["chunk_id"],
                    document_id,
                    revision,
                    chunk["content_hash"],
                    chunk["text"],
                    chunk["start"],
                    chunk["end"],
                    CHUNK_VERSION,
                ),
            )
            db.execute("INSERT INTO rag_chunk_fts VALUES(?,?)", (chunk["chunk_id"], chunk["text"]))
        db.execute("UPDATE rag_index_jobs SET state='indexing' WHERE document_id=?", (document_id,))
    status, error = "indexed", None
    provider = service.embedding_provider
    if provider is not None:
        try:
            # Reuse the existing validated, hash-cached embedding implementation.
            service.vectors.index(item, chunks)
        except Exception as exc:
            status, error = "partial", type(exc).__name__
    with content.store.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        current = db.execute("SELECT * FROM content_items WHERE id=?", (document_id,)).fetchone()
        if not same_document(current, item):
            return {"status": "stale", "document_id": document_id}
        db.execute(
            """UPDATE rag_index_jobs SET state=?,error=?,last_indexed_revision=?,
            embedding_model_version=?,attempts=attempts+?,next_run=?
            WHERE document_id=? AND revision=?""",
            (
                status,
                error,
                revision,
                getattr(provider, "model", None),
                int(status == "partial"),
                time.time() + 5 if status == "partial" else 0,
                document_id,
                revision,
            ),
        )
    return {"status": status, "document_id": document_id, "revision": revision, "error": error}
