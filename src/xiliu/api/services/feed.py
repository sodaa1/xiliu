from __future__ import annotations

import hashlib
import json
import re
from html import unescape
from threading import RLock
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse
from uuid import uuid4

import httpx

from xiliu.api.errors import WebError
from xiliu.api.store import AppStore, now
from xiliu.capabilities.langchain_tools import build_meta_tools
from xiliu.capabilities.manager import CapabilityManager
from xiliu.capabilities.mcp import MCPManager
from xiliu.execution.gateway import ExecutionGateway, RunContext, active_run
from xiliu.hooks.engine import HookEngine
from xiliu.policy.engine import PolicyEngine

if TYPE_CHECKING:
    from xiliu.api.services.content import ContentService

SOURCE_LABELS = {"aihot": "AI Hot", "github": "GitHub Top 5"}


def _plain(value: str) -> str:
    return " ".join(unescape(re.sub(r"<[^>]+>", " ", value)).split())


def _item(source: str, title: str, url: str, summary: str = "", **kwargs: Any) -> dict[str, Any]:
    return {
        "id": source + "-" + hashlib.sha256(url.encode()).hexdigest()[:24],
        "source": source,
        "title": title[:500],
        "summary": summary[:4000],
        "url": url,
        "published_at": kwargs.get("published_at"),
        "tags": kwargs.get("tags", []),
        "metadata": kwargs.get("metadata", {}),
    }


def normalize_github(html: str) -> list[dict[str, Any]]:
    items = []
    for article in re.findall(
        r'<article\b[^>]*\bclass="[^"]*Box-row[^"]*"[^>]*>(.*?)</article>', html, re.S
    ):
        heading = re.search(r"<h2\b[^>]*>(.*?)</h2>", article, re.S)
        link = re.search(r'href="(/[^/\s"]+/[^/\s"?#]+)"', heading[1] if heading else "")
        if not link:
            continue
        description = re.search(r"<p\b[^>]*>(.*?)</p>", article, re.S)
        language = re.search(r'itemprop="programmingLanguage"[^>]*>(.*?)</span>', article, re.S)
        path = unescape(link[1])
        items.append(
            _item(
                "github",
                path.lstrip("/"),
                "https://github.com" + path,
                _plain(description[1]) if description else "",
                tags=[_plain(language[1])] if language else [],
                metadata={"rank": len(items) + 1},
            )
        )
        if len(items) == 5:
            break
    if not items:
        raise ValueError("GitHub Trending did not contain repository entries")
    return items


def normalize_aihot(payload: Any) -> list[dict[str, Any]]:
    """Accept structured news lists or the MCP's Markdown link output."""
    if isinstance(payload, str):
        try:
            return normalize_aihot(json.loads(payload))
        except (ValueError, TypeError):
            entries = []
            for title, url in re.findall(r"\[([^\]\n]+)\]\((https?://[^\s)]+)\)", payload):
                entries.append({"title": title, "url": url})
            payload = entries
    if isinstance(payload, dict):
        for key in ("items", "news", "articles", "results", "data", "content", "text"):
            if key in payload:
                return normalize_aihot(payload[key])
        payload = [payload]
    if not isinstance(payload, list):
        raise ValueError("Unsupported AI Hot response")
    items: dict[str, dict[str, Any]] = {}
    for entry in payload:
        if not isinstance(entry, dict):
            continue
        title = entry.get("title") or entry.get("name")
        url = entry.get("url") or entry.get("link") or entry.get("source_url")
        links = entry.get("links", {})
        if not url and isinstance(links, dict):
            url = links.get("original") or links.get("aihot")
        if not isinstance(title, str) or not title.strip() or not isinstance(url, str):
            continue
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            continue
        summary = entry.get("summary") or entry.get("description") or entry.get("excerpt") or ""
        tags = entry.get("tags", [])
        if not tags and isinstance(entry.get("category"), str):
            tags = [entry["category"]]
        timestamp = entry.get("published_at") or entry.get("publishedAt") or entry.get("date")
        metadata = {}
        if isinstance(entry.get("source"), dict) and isinstance(entry["source"].get("name"), str):
            metadata["source_name"] = entry["source"]["name"]
        if isinstance(links, dict) and isinstance(links.get("aihot"), str):
            metadata["aihot_url"] = links["aihot"]
        if type(entry.get("score")) in {int, float}:
            metadata["score"] = entry["score"]
        item = _item(
            "aihot",
            title.strip(),
            url,
            str(summary),
            tags=[tag for tag in tags if isinstance(tag, str)] if isinstance(tags, list) else [],
            published_at=timestamp if isinstance(timestamp, str) else None,
            metadata=metadata,
        )
        items[item["id"]] = item
        if len(items) == 30:
            break
    if not items:
        raise ValueError("AI Hot response did not contain news links")
    return list(items.values())


class FeedService:
    def __init__(self, store: AppStore, content: ContentService):
        self.store, self.content = store, content
        self._lock = RLock()
        with store.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS feed_cache (
                    source TEXT PRIMARY KEY, items_json TEXT NOT NULL DEFAULT '[]',
                    status TEXT NOT NULL, message TEXT NOT NULL, updated_at TEXT
                );
                CREATE TABLE IF NOT EXISTS feed_saves (
                    feed_id TEXT PRIMARY KEY, content_id TEXT NOT NULL
                );
            """)
            for source in SOURCE_LABELS:
                db.execute(
                    "INSERT OR IGNORE INTO feed_cache(source,status,message) VALUES(?,?,?)",
                    (source, "idle", "尚未刷新资讯。"),
                )

    def list(self, source: str = "", q: str = "") -> dict[str, Any]:
        if source and source not in SOURCE_LABELS:
            raise WebError("invalid_feed_source", "资讯来源无效。")
        with self.store.connect() as db:
            rows = {row["source"]: dict(row) for row in db.execute("SELECT * FROM feed_cache")}
        items, sources = [], []
        for name, label in SOURCE_LABELS.items():
            row = rows[name]
            sources.append(
                {
                    "source": name,
                    "label": label,
                    "status": row["status"],
                    "message": row["message"],
                    "updated_at": row["updated_at"],
                }
            )
            if source and source != name:
                continue
            for item in json.loads(row["items_json"]):
                if (
                    not q
                    or q.casefold()
                    in (
                        item["title"] + " " + item["summary"] + " " + " ".join(item["tags"])
                    ).casefold()
                ):
                    items.append(item)
        return {"items": items, "sources": sources}

    def _fetch_github(self) -> list[dict[str, Any]]:
        with httpx.Client(timeout=15, follow_redirects=True) as client:
            response = client.get(
                "https://github.com/trending?since=daily", headers={"User-Agent": "xiliu/0.1"}
            )
            response.raise_for_status()
            return normalize_github(response.text)

    def _fetch_aihot(self) -> list[dict[str, Any]]:
        data_dir = self.store.path.parent
        manager = MCPManager(data_dir / "mcp")
        try:
            if "aihot" not in manager.servers():
                raise WebError("aihot_unavailable", "AI Hot 尚未连接。")
            capabilities = CapabilityManager(mcp_manager=manager)
            context = RunContext(
                run_id=str(uuid4()),
                session_id="feed-refresh",
                workspace=data_dir,
                data_dir=data_dir,
                capability_manager=capabilities,
                approval_mode="deny",
                policy_engine=PolicyEngine(
                    data_dir / "policy.json", trusted_mcp_servers=set(manager.servers())
                ),
                hook_engine=HookEngine(data_dir / "hooks.json"),
            )
            gateway = ExecutionGateway()
            discovered = gateway.discover_mcp("aihot", context)
            capability_id = "mcp:aihot:aihot_get_latest"
            if not discovered.get("ok") or capabilities.get(capability_id) is None:
                raise WebError("aihot_unavailable", "AI Hot 暂时不可用，请检查连接设置。")
            schema = manager.schema(capability_id)
            arguments = {}
            for name in schema.get("required", []):
                prop = schema.get("properties", {}).get(name, {})
                if "default" in prop:
                    arguments[name] = prop["default"]
                elif name in {"limit", "count", "page_size"}:
                    arguments[name] = 10
                else:
                    raise ValueError("AI Hot latest requires unsupported arguments")
            token = active_run.set(context)
            try:
                tool = next(
                    tool for tool in build_meta_tools(role="planner") if tool.name == "mcp_call"
                )
                result = json.loads(
                    gateway.invoke(
                        tool, {"capability_id": capability_id, "arguments": arguments}, context
                    )
                )
            finally:
                active_run.reset(token)
            if result.get("ok") is not True:
                raise WebError("aihot_unavailable", "AI Hot 暂时不可用，请检查连接设置。")
            return normalize_aihot(result.get("structured_content") or result.get("text"))
        finally:
            manager.close()

    def refresh(self) -> dict[str, Any]:
        with self._lock:
            for source, fetch in (("aihot", self._fetch_aihot), ("github", self._fetch_github)):
                try:
                    items = fetch()
                except Exception as exc:
                    message = (
                        exc.message
                        if isinstance(exc, WebError)
                        else f"{SOURCE_LABELS[source]} 刷新失败，保留上次资讯。"
                    )
                    with self.store.connect() as db:
                        db.execute(
                            "UPDATE feed_cache SET status='error', message=? WHERE source=?",
                            (message, source),
                        )
                else:
                    with self.store.connect() as db:
                        db.execute(
                            "UPDATE feed_cache SET items_json=?, status='ready', "
                            "message=?, updated_at=? WHERE source=?",
                            (json.dumps(items, ensure_ascii=False), "资讯已更新。", now(), source),
                        )
            return self.list()

    def save(self, item_id: str) -> Any:
        with self._lock:
            with self.store.connect() as db:
                saved = db.execute(
                    "SELECT content_id FROM feed_saves WHERE feed_id=?", (item_id,)
                ).fetchone()
            if saved:
                try:
                    return self.content.get(saved["content_id"])
                except WebError as exc:
                    if exc.status != 404:
                        raise
            item = next((item for item in self.list()["items"] if item["id"] == item_id), None)
            if item is None:
                raise WebError("feed_not_found", "资讯不存在，请刷新后重试。", 404)
            saved_item = self.content.create(
                {
                    "type": "link",
                    "title": item["title"],
                    "content": item["summary"],
                    "source": item["url"],
                    "tags": item["tags"],
                },
                dedupe_key="feed:" + item_id,
            )
            with self.store.connect() as db:
                db.execute(
                    "INSERT INTO feed_saves VALUES(?,?) ON CONFLICT(feed_id) "
                    "DO UPDATE SET content_id=excluded.content_id",
                    (item_id, saved_item["id"]),
                )
            return saved_item
