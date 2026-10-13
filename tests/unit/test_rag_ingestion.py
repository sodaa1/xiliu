from xiliu.api.services.content import ContentService
from xiliu.api.services.knowledge import KnowledgeService
from xiliu.api.store import AppStore


def services(tmp_path, provider=None):
    from xiliu.rag.service import RAGService

    content = ContentService(AppStore(tmp_path))
    return content, RAGService(content, KnowledgeService(content), embedding_provider=provider)


def test_incremental_revision_repeated_jobs_edit_and_delete(tmp_path):
    content, rag = services(tmp_path)
    item = content.create({"content": "Agent memory persistent store", "status": "knowledge"})
    report = rag.index_document(item["id"], item["revision"])
    assert report["status"] == "indexed"
    hits = rag.search("persistent")["hits"]
    assert hits[0]["document_id"] == item["id"] and hits[0]["chunk_id"]
    with content.store.connect() as db:
        first = list(db.execute("SELECT chunk_id FROM rag_chunks"))
    rag.index_document(item["id"], item["revision"])
    with content.store.connect() as db:
        assert list(db.execute("SELECT chunk_id FROM rag_chunks")) == first
    revised = content.update(item["id"], {"content": "changed content about cognition"})
    assert rag.index_document(item["id"], item["revision"])["status"] == "stale"
    rag.index_document(item["id"], revised["revision"])
    assert rag.search("cognition")["hits"][0]["revision"] == revised["revision"]
    assert rag.search("persistent")["matched"] is False
    content.delete(item["id"])
    rag.worker.process_pending()
    assert rag.search("cognition")["matched"] is False
    with content.store.connect() as db:
        assert db.execute("SELECT count(*) FROM rag_chunks").fetchone()[0] == 0


def test_embedding_failure_is_partial_and_search_never_indexes(tmp_path):
    class Broken:
        model = "broken"

        def embed_documents(self, texts):
            raise TimeoutError("offline")

    content, rag = services(tmp_path, Broken())
    item = content.create({"content": "Offline keyword search", "status": "knowledge"})
    assert rag.index_document(item["id"], item["revision"])["status"] == "partial"
    result = rag.search("Offline")
    assert result["ok"] and result["matched"]
    assert result["retrieval_mode"] == "fts_only"
    assert result["degraded"] is True
    with content.store.connect() as db:
        assert db.execute("SELECT state FROM rag_index_jobs").fetchone()[0] == "partial"


def test_content_writes_enqueue_without_running_search(tmp_path):
    content, rag = services(tmp_path)
    item = content.create({"content": "background indexing", "status": "knowledge"})
    with content.store.connect() as db:
        assert db.execute("SELECT state FROM rag_index_jobs").fetchone()[0] == "pending"
    assert rag.worker.process_pending() == 1
    assert rag.search("background")["hits"][0]["document_id"] == item["id"]


def test_deleting_folder_preserves_semantic_retrieval_after_indexing(tmp_path):
    class Provider:
        model = "folder-delete-test"
        dimensions = 2

        def embed_documents(self, texts):
            return [[1.0, 0.0] for _ in texts]

    content, rag = services(tmp_path, Provider())
    knowledge = content.knowledge
    folder = knowledge.create_folder({"name": "Manual", "tags": []})
    item = content.create(
        {
            "content": "A guide to automobile maintenance",
            "status": "knowledge",
            "folder_id": folder["id"],
        }
    )
    rag.worker.process_pending()
    assert rag.search("vehicle")["hits"][0]["document_id"] == item["id"]

    knowledge.delete_folder(folder["id"])
    rag.worker.process_pending()

    current = content.get(item["id"])
    assert current["status"] == "knowledge"
    assert current["folder_id"] is None
    result = rag.search("vehicle")
    assert result["matched"] is True
    assert result["hits"][0]["document_id"] == item["id"]
    assert result["hits"][0]["revision"] == current["revision"]


def test_only_changed_chunks_are_embedded_and_search_does_not_embed_documents(tmp_path):
    class Provider:
        model = "chunk-test"
        dimensions = 2

        def __init__(self):
            self.documents = []

        def embed_documents(self, texts):
            self.documents.extend(texts)
            return [[1.0, 0.0] for text in texts]

    provider = Provider()
    content, rag = services(tmp_path, provider)
    item = content.create({"content": "a" * 1200 + "b" * 1200, "status": "knowledge"})
    rag.index_document(item["id"], item["revision"])
    indexed = len(provider.documents)
    assert indexed == 3
    rag.search("semantic")
    assert len(provider.documents) == indexed + 1
    changed = content.update(item["id"], {"content": "a" * 1200 + "b" * 1199 + "c"})
    rag.index_document(item["id"], changed["revision"])
    assert len(provider.documents) == indexed + 2


def test_same_revision_internal_edit_cannot_publish_stale_index(tmp_path):
    class EditingProvider:
        model = "edit-during-index"

        def embed_documents(self, texts):
            content.update(item["id"], {"content": "new internal content"}, internal=True)
            return [[1.0, 0.0] for _ in texts]

    content, rag = services(tmp_path, EditingProvider())
    item = content.create({"content": "old internal content", "status": "knowledge"})
    assert rag.index_document(item["id"], item["revision"])["status"] == "stale"
    with content.store.connect() as db:
        assert db.execute("SELECT state FROM rag_index_jobs").fetchone()[0] == "pending"
    assert rag.search("new internal")["hits"][0]["snippet"] == "new internal content"
