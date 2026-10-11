import pytest

from xiliu.api.services.content import ContentService
from xiliu.api.store import AppStore


class Folders:
    def list_folders(self):
        return []


def service(tmp_path):
    from xiliu.api.services.retrieval import RetrievalService

    content = ContentService(AppStore(tmp_path))
    return content, RetrievalService(content, Folders())


def test_explicit_tag_browse_and_relation_question_choose_different_paths(tmp_path):
    content, retrieval = service(tmp_path)
    item = content.create(
        dict(content="数据库设计包含索引和事务", tags=["数据库"], status="knowledge")
    )
    content.create(dict(content="数据库私密收件箱", tags=["数据库"]))
    browse = retrieval.search("浏览标签 数据库")
    assert browse["mode_used"] == "tag"
    assert [i["document_id"] for i in browse["items"]] == [item["id"]]
    relation = retrieval.search("数据库中的索引和事务有什么关系？")
    assert relation["mode_used"] == "hybrid"
    assert relation["items"][0]["document_id"] == item["id"]
    assert relation["channels"] == ["fts", "metadata"]


def test_short_chinese_fallback_and_strict_arguments(tmp_path):
    content, retrieval = service(tmp_path)
    item = content.create(dict(content="猫在窗边晒太阳", status="knowledge"))
    result = retrieval.search("猫", mode="hybrid", limit=1)
    assert result["items"][0]["document_id"] == item["id"]
    assert retrieval.search("不存在标签", mode="auto")["mode_used"] == "hybrid"
    for kwargs in [dict(limit=0), dict(limit=True), dict(limit=21), dict(mode="unknown")]:
        with pytest.raises(ValueError):
            retrieval.search("猫", **kwargs)


def test_embedding_cache_reuses_vectors_invalidates_edits_and_rejects_wrong_dimensions(tmp_path):
    from xiliu.api.services.retrieval import RetrievalService

    class Provider:
        model = "test-embedding"
        dimensions = 2

        def __init__(self):
            self.texts = []

        def embed_documents(self, texts):
            self.texts.extend(texts)
            return [[1.0, 0.0] for _ in texts]

    content, _ = service(tmp_path)
    item = content.create(dict(content="向量知识", status="knowledge"))
    provider = Provider()
    retrieval = RetrievalService(content, Folders(), embedding_provider=provider)
    assert "embedding" in retrieval.search("语义")["channels"]
    assert retrieval.search("语义")["items"][0]["document_id"] == item["id"]
    assert len(provider.texts) == 3  # one document, two query embeddings
    content.update(item["id"], {"content": "新向量知识"})
    retrieval.search("语义")
    assert len(provider.texts) == 5
    provider.dimensions = 3
    assert "embedding" not in retrieval.search("语义")["channels"]


def test_knowledge_tool_uses_runtime_directory_and_gateway_read_permission(tmp_path):
    import json

    from xiliu.app.actions import AppServices
    from xiliu.capabilities.manager import CapabilityManager
    from xiliu.execution.gateway import ExecutionGateway, RunContext
    from xiliu.policy.engine import PolicyEngine
    from xiliu.tools.app import build_app_tool

    services = AppServices.open(tmp_path)
    item = services.content.create(dict(content="本地知识引用", status="knowledge"))
    events, manager = [], CapabilityManager()
    context = RunContext(
        "test",
        "test",
        tmp_path,
        data_dir=tmp_path,
        app_services=services,
        policy_engine=PolicyEngine(tmp_path / "policy.json"),
        capability_manager=manager,
        event_sink=events.append,
    )
    tool = ExecutionGateway().wrap_tool(build_app_tool(), context)
    args = {"operation": "execute", "action_id": "knowledge.search", "arguments": {"query": "知识"}}
    result = json.loads(tool.invoke(args))
    assert result["data"]["items"][0]["document_id"] == item["id"]
    assert (
        result["data"]["items"][0]["citation_url"] == "/knowledge?folder=all&document=" + item["id"]
    )
    assert events[-1]["decision"] == "allow"
    assert manager.search("知识库")[0].id == "builtin:app"
    (tmp_path / "policy.json").write_text(
        json.dumps({"profiles": {"interactive": {"knowledge.read": "deny"}}})
    )
    denied = RunContext(
        "test",
        "test",
        tmp_path,
        app_services=services,
        policy_engine=PolicyEngine(tmp_path / "policy.json"),
    )
    result = ExecutionGateway().invoke(build_app_tool(), args, denied)
    assert json.loads(result)["error"] == "policy_denied"
    services.close()


def test_runtime_tool_factory_and_embedding_factory_require_explicit_model(tmp_path, monkeypatch):
    import json
    from types import SimpleNamespace

    from xiliu.rag.embedding_config import embedding_provider_from_settings
    from xiliu.tools import get_builtin_tools
    from xiliu.tools.app import build_app_tool

    monkeypatch.delenv("XILIU_EMBEDDING_MODEL", raising=False)
    assert embedding_provider_from_settings(SimpleNamespace(model="chat-model")) is None
    assert [t.name for t in get_builtin_tools()] == ["calculator", "current_time", "app"]
    assert (
        json.loads(build_app_tool().invoke({"operation": "catalog"}))["error"]
        == "service_unavailable"
    )


def test_explicit_embedding_model_loads_from_settings_without_using_chat_model(monkeypatch):
    from xiliu.config import Settings
    from xiliu.rag.embedding_config import embedding_provider_from_settings

    monkeypatch.delenv("XILIU_EMBEDDING_MODEL", raising=False)
    settings = Settings.from_env(
        {
            "XILIU_API_KEY": "test-unused-key",
            "XILIU_MODEL": "chat-only",
            "XILIU_EMBEDDING_MODEL": "dedicated-embedding",
            "XILIU_BASE_URL": "https://example.invalid/v1",
        }
    )
    provider = embedding_provider_from_settings(settings)
    assert provider.model == "dedicated-embedding"
    assert provider.openai_api_base == "https://example.invalid/v1"


def test_embedding_completion_does_not_reinsert_or_return_removed_knowledge(tmp_path):
    from xiliu.api.services.retrieval import RetrievalService

    content, _ = service(tmp_path)
    item = content.create(dict(content="并发移动的知识", status="knowledge"))

    class Provider:
        model = "test"

        def embed_documents(self, texts):
            content.update(item["id"], {"status": "inbox"})
            return [[1.0, 0.0] for _ in texts]

    result = RetrievalService(content, Folders(), embedding_provider=Provider()).search("知识")
    assert result["items"] == []
    with content.store.connect() as db:
        assert db.execute("SELECT COUNT(*) FROM knowledge_vectors").fetchone()[0] == 0
