from __future__ import annotations

import hashlib
import ipaddress
import json
import re
import socket
import sqlite3
import time
from html import unescape
from queue import Empty, Queue
from threading import Lock, RLock, Thread
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse, urlunparse
from uuid import uuid4

import httpx

from xiliu.api.errors import WebError
from xiliu.api.store import AppStore, now
from xiliu.capabilities.langchain_tools import build_meta_tools
from xiliu.capabilities.manager import CapabilityManager
from xiliu.capabilities.mcp import MCPManager
from xiliu.execution.cancellation import check_cancelled
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
        "editable": source == "manual",
        "hidden": False,
    }


def _canonical_url(value: Any) -> str:
    if not isinstance(value, str) or not value or len(value) > 2048:
        raise WebError("invalid_feed_url", "请填写有效的 HTTP 或 HTTPS 链接。")
    if any(character.isspace() or ord(character) < 32 for character in value):
        raise WebError("invalid_feed_url", "链接不能包含空白或控制字符。")
    try:
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("unsupported URL")
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("credentials in URL")
        hostname = parsed.hostname.rstrip(".").encode("idna").decode("ascii").lower()
        if not hostname:
            raise ValueError("missing hostname")
        host = f"[{hostname}]" if ":" in hostname else hostname
        port = parsed.port
        if port and port != (443 if parsed.scheme == "https" else 80):
            host += f":{port}"
        return urlunparse(
            (parsed.scheme, host, parsed.path or "/", parsed.params, parsed.query, "")
        )
    except (ValueError, UnicodeError) as exc:
        raise WebError("invalid_feed_url", "请填写有效的 HTTP 或 HTTPS 链接。") from exc


def _manual_payload(payload: dict[str, Any], *, partial: bool = False) -> dict[str, Any]:
    allowed = {"url", "title", "summary", "tags", "fetch_title"}
    if not isinstance(payload, dict) or set(payload) - allowed:
        raise WebError("invalid_feed_arguments", "资讯参数无效。")
    values = dict(payload)
    if not partial:
        values = {"title": "", "summary": "", "tags": [], "fetch_title": False, **values}
        if "url" not in values:
            raise WebError("invalid_feed_url", "请填写资讯链接。")
    if "url" in values:
        _canonical_url(values["url"])
    for key, limit in (("title", 500), ("summary", 4000)):
        if key in values:
            if not isinstance(values[key], str) or len(values[key]) > limit:
                raise WebError("invalid_feed_arguments", "资讯标题或摘要过长或格式无效。")
            values[key] = values[key].strip()
    if "tags" in values:
        tags = values["tags"]
        if (
            not isinstance(tags, list)
            or len(tags) > 30
            or any(not isinstance(tag, str) or len(tag) > 100 for tag in tags)
        ):
            raise WebError("invalid_feed_arguments", "资讯标签无效。")
        values["tags"] = list(dict.fromkeys(tag.strip() for tag in tags if tag.strip()))
    if "fetch_title" in values and type(values["fetch_title"]) is not bool:
        raise WebError("invalid_feed_arguments", "抓取标题选项无效。")
    return values


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
        self._metadata_lock = Lock()
        with store.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS feed_cache (
                    source TEXT PRIMARY KEY, items_json TEXT NOT NULL DEFAULT '[]',
                    status TEXT NOT NULL, message TEXT NOT NULL, updated_at TEXT
                );
                CREATE TABLE IF NOT EXISTS feed_saves (
                    feed_id TEXT PRIMARY KEY, content_id TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS feed_manual_items (
                    id TEXT PRIMARY KEY, canonical_url TEXT NOT NULL UNIQUE,
                    url TEXT NOT NULL, title TEXT NOT NULL, summary TEXT NOT NULL DEFAULT '',
                    tags_json TEXT NOT NULL DEFAULT '[]', metadata_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL, updated_at TEXT NOT NULL, deleted_at TEXT
                );
                CREATE TABLE IF NOT EXISTS feed_hidden_items (
                    feed_id TEXT PRIMARY KEY, source TEXT NOT NULL,
                    hidden_at TEXT NOT NULL, item_json TEXT NOT NULL
                );
            """)
            for source in SOURCE_LABELS:
                db.execute(
                    "INSERT OR IGNORE INTO feed_cache(source,status,message) VALUES(?,?,?)",
                    (source, "idle", "尚未刷新资讯。"),
                )

    def list(self, source: str = "", q: str = "", include_hidden: bool = False) -> dict[str, Any]:
        if source and source not in {*SOURCE_LABELS, "manual"}:
            raise WebError("invalid_feed_source", "资讯来源无效。")
        with self.store.connect() as db:
            rows = {row["source"]: dict(row) for row in db.execute("SELECT * FROM feed_cache")}
            manual = [
                self._manual_item(row)
                for row in db.execute(
                    "SELECT * FROM feed_manual_items ORDER BY created_at DESC, id"
                )
            ]
            hidden = {
                row["feed_id"]: dict(row) for row in db.execute("SELECT * FROM feed_hidden_items")
            }
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
                item.setdefault("editable", False)
                item["hidden"] = item["id"] in hidden
                if include_hidden or not item["hidden"]:
                    items.append(item)
        if include_hidden:
            included = {item["id"] for item in items}
            for item_id, record in hidden.items():
                if item_id not in included and (not source or source == record["source"]):
                    items.append(
                        {**json.loads(record["item_json"]), "hidden": True, "editable": False}
                    )
        sources.append(
            {
                "source": "manual",
                "label": "我的资讯",
                "status": "ready",
                "message": "手动添加的资讯会持续保留。",
                "updated_at": None,
            }
        )
        if not source or source == "manual":
            items.extend(item for item in manual if include_hidden or not item["deleted_at"])
        if q:
            items = [
                item
                for item in items
                if q.casefold()
                in (
                    item["title"]
                    + " "
                    + item["summary"]
                    + " "
                    + item["url"]
                    + " "
                    + " ".join(item["tags"])
                ).casefold()
            ]
        return {"items": items, "sources": sources}

    @staticmethod
    def _manual_item(row: Any) -> dict[str, Any]:
        value = dict(row)
        value.pop("canonical_url")
        value["tags"] = json.loads(value.pop("tags_json"))
        value["metadata"] = json.loads(value.pop("metadata_json"))
        return {
            **value,
            "source": "manual",
            "published_at": value["created_at"],
            "editable": True,
            "hidden": False,
        }

    def _manual_get(self, db: sqlite3.Connection, item_id: str) -> dict[str, Any]:
        row = db.execute("SELECT * FROM feed_manual_items WHERE id=?", (item_id,)).fetchone()
        if row is None:
            provider = next(
                (item for item in self.list(include_hidden=True)["items"] if item["id"] == item_id),
                None,
            )
            if provider:
                raise WebError("feed_not_editable", "外部资讯仅支持隐藏或取消隐藏。", 403)
            raise WebError("feed_not_found", "资讯不存在。", 404)
        return self._manual_item(row)

    def _request_title(self, url: str) -> str:
        """One request to a pinned public address; never follow a redirect or use a proxy."""
        parsed = urlparse(_canonical_url(url))
        hostname = parsed.hostname or ""
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        if port not in {80, 443}:
            raise ValueError("unsupported fetch port")
        deadline = time.monotonic() + 5
        addresses = {
            answer[4][0]
            for answer in socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
            if isinstance(answer[4][0], str)
        }
        resolved = [ipaddress.ip_address(address) for address in addresses]
        if not resolved or any(
            not address.is_global or address.is_multicast or address.is_reserved
            for address in resolved
        ):
            raise ValueError("non-public address")
        address = sorted(addresses)[0]
        host = f"[{address}]" if ":" in address else address
        pinned = urlunparse(parsed._replace(netloc=f"{host}:{port}", fragment=""))
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("DNS timeout")
        authority = parsed.netloc
        with (
            httpx.Client(
                timeout=min(remaining, 3), follow_redirects=False, trust_env=False
            ) as client,
            client.stream(
                "GET",
                pinned,
                headers={
                    "Host": authority,
                    "User-Agent": "xiliu/0.4",
                    "Accept": "text/html",
                    "Accept-Encoding": "identity",
                },
                extensions={"sni_hostname": hostname},
            ) as response,
        ):
            if response.is_redirect:
                raise ValueError("redirect refused")
            response.raise_for_status()
            if "html" not in response.headers.get("content-type", "").lower():
                raise ValueError("non-HTML response")
            if response.headers.get("content-encoding", "identity").lower() != "identity":
                raise ValueError("compressed response refused")
            limit = 256 * 1024
            if int(response.headers.get("content-length", "0")) > limit:
                raise ValueError("response too large")
            body = bytearray()
            for chunk in response.iter_bytes():
                if time.monotonic() > deadline or len(body) + len(chunk) > limit:
                    raise ValueError("response limit exceeded")
                body.extend(chunk)
            title = re.search(
                r"<title\b[^>]*>(.*?)</title>",
                body.decode(response.encoding or "utf-8", errors="replace"),
                re.S | re.I,
            )
            if not title or not _plain(title[1]):
                raise ValueError("no title")
            return _plain(title[1])[:500]

    def _fetch_title(self, url: str) -> tuple[str | None, dict[str, Any]]:
        # The daemon bounds DNS/slow-response wall time without accumulating concurrent fetches.
        failed = {"fetch_status": "failed", "fetch_error": "网页标题未补齐，链接已保留。"}
        if not self._metadata_lock.acquire(blocking=False):
            return None, failed
        result: Queue[str | None] = Queue(maxsize=1)

        def fetch():
            try:
                result.put(self._request_title(url))
            except Exception:
                result.put(None)
            finally:
                self._metadata_lock.release()

        Thread(target=fetch, daemon=True, name="feed-title-fetch").start()
        try:
            title = result.get(timeout=6)
        except Empty:
            return None, failed
        return (title, {"fetch_status": "ready"}) if title else (None, failed)

    def add_manual(self, payload: dict[str, Any]) -> dict[str, Any]:
        values = _manual_payload(payload)
        canonical = _canonical_url(values["url"])
        with self.store.connect() as db:
            existing = db.execute(
                "SELECT * FROM feed_manual_items WHERE canonical_url=?", (canonical,)
            ).fetchone()
        if existing:
            if existing["deleted_at"]:
                raise WebError("feed_removed", "这条资讯已删除，请先恢复。", 409)
            return self._manual_item(existing)
        title, metadata = (None, {"fetch_status": "not_requested"})
        if values["fetch_title"]:
            title, metadata = self._fetch_title(values["url"])
        check_cancelled()
        item_id, timestamp = "manual-" + str(uuid4()), now()
        with self.store.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute(
                "INSERT OR IGNORE INTO feed_manual_items "
                "(id,canonical_url,url,title,summary,tags_json,metadata_json,"
                "created_at,updated_at) "
                "VALUES(?,?,?,?,?,?,?,?,?)",
                (
                    item_id,
                    canonical,
                    values["url"],
                    values["title"] or title or values["url"],
                    values["summary"],
                    json.dumps(values["tags"], ensure_ascii=False),
                    json.dumps(metadata),
                    timestamp,
                    timestamp,
                ),
            )
            row = db.execute(
                "SELECT * FROM feed_manual_items WHERE canonical_url=?", (canonical,)
            ).fetchone()
            if row["deleted_at"]:
                raise WebError("feed_removed", "这条资讯已删除，请先恢复。", 409)
            return self._manual_item(row)

    def update_manual(self, item_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        changes = _manual_payload(payload, partial=True)
        with self.store.connect() as db:
            current = self._manual_get(db, item_id)
        if current["deleted_at"]:
            raise WebError("feed_removed", "请先恢复这条资讯再编辑。", 409)
        metadata = None
        if changes.pop("fetch_title", False):
            title, metadata = self._fetch_title(changes.get("url", current["url"]))
            if title and "title" not in changes:
                changes["title"] = title
        check_cancelled()
        with self.store.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            current = self._manual_get(db, item_id)
            if current["deleted_at"]:
                raise WebError("feed_removed", "请先恢复这条资讯再编辑。", 409)
            value = {**current, **changes}
            canonical = _canonical_url(value["url"])
            if db.execute(
                "SELECT id FROM feed_manual_items WHERE canonical_url=? AND id<>?",
                (canonical, item_id),
            ).fetchone():
                raise WebError("feed_conflict", "这个链接已有一条资讯。", 409)
            if metadata is None:
                metadata = (
                    {"fetch_status": "not_requested"}
                    if value["url"] != current["url"]
                    else current["metadata"]
                )
            db.execute(
                "UPDATE feed_manual_items SET canonical_url=?,url=?,title=?,summary=?,"
                "tags_json=?,metadata_json=?,updated_at=? WHERE id=?",
                (
                    canonical,
                    value["url"],
                    value["title"] or value["url"],
                    value["summary"],
                    json.dumps(value["tags"], ensure_ascii=False),
                    json.dumps(metadata),
                    now(),
                    item_id,
                ),
            )
            return self._manual_get(db, item_id)

    def remove_manual(self, item_id: str) -> dict[str, Any]:
        return self._manual_visibility(item_id, deleted=True)

    def restore_manual(self, item_id: str) -> dict[str, Any]:
        return self._manual_visibility(item_id, deleted=False)

    def _manual_visibility(self, item_id: str, *, deleted: bool) -> dict[str, Any]:
        with self.store.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            current = self._manual_get(db, item_id)
            timestamp = now()
            db.execute(
                "UPDATE feed_manual_items SET deleted_at=?,updated_at=? WHERE id=?",
                ((current["deleted_at"] or timestamp) if deleted else None, timestamp, item_id),
            )
            return self._manual_get(db, item_id)

    def hide_external(self, item_id: str) -> dict[str, Any]:
        return self._external_visibility(item_id, hidden=True)

    def unhide_external(self, item_id: str) -> dict[str, Any]:
        return self._external_visibility(item_id, hidden=False)

    def _external_visibility(self, item_id: str, *, hidden: bool) -> dict[str, Any]:
        with self._lock:
            item = next(
                (item for item in self.list(include_hidden=True)["items"] if item["id"] == item_id),
                None,
            )
            if item is None:
                raise WebError("feed_not_found", "资讯不存在。", 404)
            if item["source"] == "manual":
                raise WebError("feed_not_external", "手动资讯请使用删除或恢复操作。", 403)
            with self.store.connect() as db:
                if hidden:
                    db.execute(
                        "INSERT OR IGNORE INTO feed_hidden_items VALUES(?,?,?,?)",
                        (item_id, item["source"], now(), json.dumps(item, ensure_ascii=False)),
                    )
                else:
                    db.execute("DELETE FROM feed_hidden_items WHERE feed_id=?", (item_id,))
            return {**item, "hidden": hidden}

    def _verify_persisted(self, item: dict[str, Any]) -> bool:
        """Internal readback for Agent receipts, including provider items outside the cache."""
        with self.store.connect() as db:
            if item.get("source") == "manual":
                row = db.execute(
                    "SELECT * FROM feed_manual_items WHERE id=?", (item.get("id"),)
                ).fetchone()
                if row is None:
                    return False
                persisted = self._manual_item(row)
            else:
                hidden = db.execute(
                    "SELECT 1 FROM feed_hidden_items WHERE feed_id=?", (item.get("id"),)
                ).fetchone()
                if bool(hidden) != bool(item.get("hidden")):
                    return False
                persisted = next(
                    (
                        value
                        for value in self.list(include_hidden=True)["items"]
                        if value["id"] == item.get("id")
                    ),
                    None,
                )
                # Unhiding a retired provider item removes the local recovery record.
                if persisted is None:
                    return not hidden and item.get("hidden") is False
        return all(
            persisted.get(key) == item[key]
            for key in ("id", "source", "title", "url", "summary", "tags", "deleted_at", "hidden")
            if key in item
        )

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
