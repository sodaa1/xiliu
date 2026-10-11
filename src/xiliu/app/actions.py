"""Single authoritative action catalog; handlers only call existing services."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlencode

from pydantic import BaseModel, ConfigDict, Field, create_model

from xiliu.api.errors import WebError


class Arguments(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


def schema(model_name: str, **fields: Any) -> type[BaseModel]:
    return create_model(model_name, __base__=Arguments, **fields)


EMPTY = schema("Empty")
QUERY = schema("Query", q=(str, ""), tag=(str, ""))
ITEM = schema("Item", item_id=(str, ...))
TASK = schema("Task", task_id=(str, ...))
FOLDER = schema("Folder", folder_id=(str, ...))
CONVERSATION = schema("Conversation", cid=(str, ...))
FOLDER_CREATE = schema(
    "FolderCreate",
    name=(str, ...),
    summary=(str, ""),
    tags=(list[str], Field(default_factory=list)),
    priority=(int, 0),
)
TASK_CREATE = schema(
    "TaskCreate", title=(str, ...), completed=(bool, False), due_at=(str | None, None)
)
TASK_PATCH = schema(
    "TaskPatch", title=(str | None, None), completed=(bool | None, None), due_at=(str | None, None)
)
CONTENT_PATCH = schema(
    "ContentPatch",
    title=(str | None, None),
    content=(str | None, None),
    summary=(str | None, None),
    tags=(list[str] | None, None),
    status=(Literal["inbox", "knowledge"] | None, None),
    folder_id=(str | None, None),
)
FOLDER_PATCH = schema(
    "FolderPatch",
    name=(str | None, None),
    summary=(str | None, None),
    tags=(list[str] | None, None),
    priority=(int | None, None),
)
PREFERENCE_PATCH = schema(
    "PreferencePatch",
    displayName=(str | None, None),
    email=(str | None, None),
    bio=(str | None, None),
    theme=(Literal["light", "dark", "system"] | None, None),
    fontSize=(Literal["small", "medium", "large"] | None, None),
    fontFamily=(Literal["system", "rounded", "serif"] | None, None),
    density=(Literal["comfortable", "compact"] | None, None),
    reducedMotion=(bool | None, None),
)


UI_BINDINGS: dict[str, tuple[str, ...]] = {
    "today.read": ("workspaceApi.today",),
    "content.create": ("workspaceApi.createContent",),
    "inbox.list": ("workspaceApi.inbox", "workspaceApi.content"),
    "inbox.get": ("workspaceApi.contentItem",),
    "inbox.update": ("workspaceApi.updateContent",),
    "inbox.delete": ("workspaceApi.deleteContent",),
    "knowledge.items.list": ("workspaceApi.content",),
    "knowledge.items.get": ("workspaceApi.contentItem",),
    "knowledge.items.update": ("workspaceApi.updateContent",),
    "knowledge.items.delete": ("workspaceApi.deleteContent",),
    "inbox.import_text": ("workspaceApi.importContent",),
    "inbox.import_url": ("workspaceApi.importContent",),
    "inbox.import_file": ("workspaceApi.importContent",),
    "inbox.retry": ("workspaceApi.retryContent",),
    "inbox.archive_after_metadata": ("agent_only:inbox.archive_after_metadata",),
    "inbox.archive_job": ("api.archiveJob",),
    "inbox.classify_selected": ("workspaceApi.classifyBatch",),
    "inbox.classify_all": ("workspaceApi.classifyBatch",),
    "inbox.move": ("workspaceApi.updateContent",),
    "content.move_to_inbox": ("workspaceApi.updateContent",),
    "knowledge.search": ("workspaceApi.searchKnowledge",),
    "knowledge.get": ("agent_only:knowledge.get",),
    "knowledge.folders.list": ("workspaceApi.folders",),
    "knowledge.folders.get": ("agent_only:knowledge.folders.get",),
    "knowledge.folders.create": ("workspaceApi.createFolder",),
    "knowledge.folders.ensure": ("agent_only:knowledge.folders.ensure",),
    "knowledge.folders.update": ("workspaceApi.updateFolder",),
    "knowledge.folders.delete": ("workspaceApi.deleteFolder",),
    "knowledge.folders.items": ("workspaceApi.folderItems",),
    "tasks.list": ("agent_only:tasks.list",),
    "tasks.create": ("workspaceApi.createTask",),
    "tasks.update": ("workspaceApi.updateTask",),
    "tasks.complete": ("workspaceApi.updateTask",),
    "tasks.delete": ("workspaceApi.deleteTask",),
    "feed.list": ("workspaceApi.feed",),
    "feed.refresh": ("workspaceApi.refreshFeed",),
    "feed.save_to_inbox": ("workspaceApi.saveFeed",),
    "feed.add_manual": ("workspaceApi.addManualFeed",),
    "feed.update_manual": ("workspaceApi.updateManualFeed",),
    "feed.remove_manual": ("workspaceApi.removeManualFeed",),
    "feed.restore_manual": ("workspaceApi.restoreManualFeed",),
    "feed.hide_external": ("workspaceApi.hideExternalFeed",),
    "feed.unhide_external": ("workspaceApi.unhideExternalFeed",),
    "automations.list": ("workspaceApi.automations",),
    "automations.create": ("workspaceApi.createAutomation",),
    "automations.toggle": ("workspaceApi.toggleAutomation",),
    "automations.delete": ("workspaceApi.deleteAutomation",),
    "automations.runs": ("workspaceApi.runs",),
    "conversations.list": ("api.conversations",),
    "conversations.create": ("api.create",),
    "conversations.get": ("api.conversation",),
    "conversations.messages": ("api.messages",),
    "conversations.update": ("api.patch",),
    "conversations.model": ("api.patch",),
    "conversations.stop": ("api.stop",),
    "conversations.delete": ("api.remove",),
    "preferences.get": ("syncPreferences",),
    "preferences.update": ("savePreferences",),
    "preferences.reset": ("agent_only:preferences.reset",),
    "settings.model.read": ("api.settings",),
    "settings.model.update": ("api.saveSettings",),
    "settings.data.read": ("workspaceApi.dataSettings",),
    "capabilities.skills": ("api.skills",),
    "capabilities.mcp": ("api.mcp",),
    "settings.models.catalog": ("api.catalog",),
    "capabilities.commands": ("api.commands",),
}


@dataclass
class AppServices:
    state: Any
    owned: bool = False

    @classmethod
    def from_state(cls, state: Any) -> AppServices:
        return cls(state)

    @classmethod
    def open(cls, data_dir: Path) -> AppServices:
        # CLI/background use precisely the same Service construction as HTTP.
        from xiliu.api.app import create_app

        return cls(create_app(data_dir=data_dir).state, owned=True)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.state, name)

    def close(self) -> None:
        if self.owned:
            self.inbox.shutdown()
            self.retrieval.worker.shutdown()
            self.automations.shutdown()


@dataclass(frozen=True)
class ActionSpec:
    id: str
    domain: str
    args_schema: type[BaseModel]
    handler: Callable[[Any, dict, Any], Any]
    side_effect: Literal["read", "write"]
    permission: str
    service_binding: str | tuple[str, ...]
    postcondition: Callable[[Any, dict, Any], bool]
    description: str
    requires_network: bool = False
    confirmation_policy: str = "none"
    idempotency: str = "request"
    agent_availability: str = "enabled"
    ui_binding: tuple[str, ...] = ()
    constant_catalog: str | None = None


def _records(value: Any) -> list[dict]:
    if isinstance(value, list):
        return [v for v in value if isinstance(v, dict)]
    if isinstance(value, dict):
        for field in ("items", "records", "hits"):
            if isinstance(value.get(field), list):
                return _records(value[field])
        return [value] if "id" in value or "document_id" in value else []
    return []


def _verify(service: str, services: Any, args: dict, value: Any) -> bool:
    """Read back stored records, rather than trusting handler prose."""
    records = _records(value)
    for item in records:
        identifier = item.get("id")
        if not identifier:
            continue
        if service in {"content", "inbox"}:
            persisted = services.content.get(identifier)
        elif service == "knowledge":
            persisted = services.knowledge.get_folder(identifier)
        elif service == "feed":
            if not services.feed._verify_persisted(item):
                return False
            continue
        elif service == "tasks":
            persisted = next((r for r in services.tasks.list() if r["id"] == identifier), None)
        elif service == "automations":
            persisted = next(
                (r for r in services.automations.list() if r["id"] == identifier), None
            )
        elif service in {"conversations", "store"}:
            persisted = services.store.get(identifier)
        else:
            continue
        if persisted is None or any(
            persisted.get(k) != item[k]
            for k in (
                "title",
                "name",
                "content",
                "summary",
                "source",
                "type",
                "url",
                "status",
                "folder_id",
                "tags",
                "priority",
                "completed",
                "due_at",
                "enabled",
                "model_override",
                "prompt",
                "schedule",
                "timezone",
            )
            if k in item
        ):
            return False
    return True


def _search(services: Any, args: dict, context: Any) -> dict:
    result = services.retrieval.search(args["query"], args["limit"], args["mode"])
    for item in result["items"]:
        item["citation_url"] = "/knowledge?" + urlencode(
            {"folder": "all", "document": item["document_id"]}
        )
    return {**result, "matched": bool(result["items"]), "hits": result["items"]}


def _document(services: Any, args: dict, context: Any) -> dict:
    item = services.retrieval.get_document(args["document_id"])
    return {
        "matched": item is not None,
        "document": {**item, "content": item["content"][:16000], "snippet": item["content"][:1000]}
        if item
        else None,
    }


def _import(services: Any, args: dict, context: Any) -> dict:
    payload = {"text": args.get("url", args.get("text", "")), "use_ai": args["use_ai"]}
    return services.inbox.import_item(payload)


def _restricted_file_import(services: Any, args: dict, context: Any) -> dict:
    # UI uploads already use InboxService. No session-bound attachment grants
    # exist yet, so Agent import must not reference a fictitious attachment service.
    raise WebError("capability_unavailable", "请通过界面上传文件。", 403)


def _classify(services: Any, args: dict, context: Any) -> dict:
    if args.get("folder_id") is not None:
        services.knowledge.get_folder(args["folder_id"])
    ids = args.get("item_ids")
    if ids is None:
        ids = [item["id"] for item in services.content.list(status="inbox")]
    if args.get("use_ai"):
        return services.inbox.queue_archive_batch(ids, folder_id=args.get("folder_id"))
    items = []
    failures = []
    for offset in range(0, len(ids), 100):
        from xiliu.execution.cancellation import check_cancelled

        check_cancelled()
        for identifier in ids[offset : offset + 100]:
            try:
                result = services.inbox.classify_batch(
                    [identifier],
                    save_to_knowledge=True,
                    folder_id=args.get("folder_id"),
                    use_ai=args.get("use_ai", False),
                )
                saved = result["items"][0]
                if (
                    saved["id"] == identifier
                    and saved["status"] == "knowledge"
                    and (args.get("folder_id") is None or saved["folder_id"] == args["folder_id"])
                ):
                    items.append(saved)
                else:
                    failures.append({"id": identifier, "error": "conflict"})
            except WebError as error:
                failures.append({"id": identifier, "error": error.code})
    return {
        "items": items,
        "failures": failures,
        "counts": {
            "total": len(ids),
            "succeeded": len(items),
            "failed": len(failures),
            "skipped": 0,
        },
    }


def _verify_classify(services: Any, args: dict, value: dict) -> bool:
    if not args.get("use_ai"):
        return _verify("inbox", services, args, value)
    stored = services.inbox.get_archive_job(value["job_id"])
    fields = ("job_id", "item_id", "revision", "folder_id", "created_at")
    returned, persisted = value["items"], stored["items"]
    return (
        value["created_at"] == stored["created_at"]
        and len(returned) == len(persisted) == value["counts"]["total"]
        and all(
            all(record[key] == actual[key] for key in fields)
            and record["folder_id"] == args.get("folder_id")
            for record, actual in zip(returned, persisted, strict=True)
        )
        and (
            "item_ids" not in args
            or {record["item_id"] for record in returned} == set(args["item_ids"])
        )
    )


def _ensure_folder(services: Any, args: dict, context: Any) -> dict:
    return services.knowledge.ensure_folder(args)


def get_registry() -> dict[str, ActionSpec]:
    registry: dict[str, ActionSpec] = {}

    def add(
        identifier: str,
        model: type[BaseModel],
        handler: Callable,
        binding: str,
        *,
        write=False,
        network=False,
        confirm=False,
        restricted=False,
        permission: str | None = None,
        postcondition: Callable | None = None,
        description="",
    ):
        domain = identifier.split(".")[0]
        service = binding.split(".")[0]
        service_classes = {
            "tasks": "TaskService",
            "content": "ContentService",
            "inbox": "InboxService",
            "knowledge": "KnowledgeService",
            "retrieval": "RAGService",
            "feed": "FeedService",
            "automations": "AutomationService",
            "conversations": "ConversationService",
            "store": "AppStore",
            "chat": "ChatService",
            "preferences": "PreferencesService",
            "model_settings": "ModelSettingsService",
            "commands": "CommandService",
        }
        class_binding = service_classes[service] + "." + binding.split(".", 1)[1]
        if identifier == "today.read":
            class_binding = ("FeedService.list", "TaskService.list", "ContentService.list")
        elif identifier in {"inbox.classify_selected", "inbox.classify_all"}:
            class_binding = ("InboxService.classify_batch", "InboxService.queue_archive_batch")
        elif identifier == "settings.models.catalog":
            class_binding = "constant:xiliu.api.model_catalog.MODEL_CATALOG"
        elif identifier == "capabilities.commands":
            class_binding = "constant:xiliu.api.services.commands.COMMANDS"
        catalog = {
            "settings.models.catalog": "xiliu.api.model_catalog.MODEL_CATALOG",
            "capabilities.commands": "xiliu.api.services.commands.COMMANDS",
        }.get(identifier)
        if catalog:
            class_binding = ()
        registry[identifier] = ActionSpec(
            identifier,
            domain,
            model,
            handler,
            "write" if write else "read",
            permission or f"{domain}.{'write' if write else 'read'}",
            class_binding,
            postcondition or (lambda s, a, v: _verify(service, s, a, v)),
            description
            or {
                "tasks.delete": "删除待办",
                "inbox.delete": "删除收件箱资料",
                "knowledge.items.delete": "删除知识库资料",
                "knowledge.folders.delete": "删除知识库文件夹",
                "feed.remove_manual": "删除手动资讯",
                "automations.create": "创建自动任务",
                "automations.toggle": "更改自动任务状态",
                "automations.delete": "删除自动任务",
            }.get(identifier, identifier.replace(".", " ")),
            network,
            "explicit" if confirm else "none",
            agent_availability="restricted" if restricted else "enabled",
            ui_binding=UI_BINDINGS.get(identifier, ()),
            constant_catalog=catalog,
        )

    add(
        "today.read",
        EMPTY,
        lambda s, a, c: {
            "feed": s.feed.list()["items"],
            "tasks": s.tasks.list(),
            "inbox_count": len(s.content.list("inbox")),
        },
        "tasks.list",
    )
    add(
        "content.create",
        schema(
            "ContentCreate",
            type=(Literal["note", "link"], "note"),
            title=(str, "未命名笔记"),
            content=(str, ""),
            summary=(str, ""),
            source=(str, ""),
            status=(Literal["inbox", "knowledge"], "inbox"),
            folder_id=(str | None, None),
            tags=(list[str], Field(default_factory=list)),
        ),
        lambda s, a, c: s.content.create(a),
        "content.create",
        write=True,
        permission="knowledge.write",
    )
    for domain, status in (("inbox", "inbox"), ("knowledge.items", "knowledge")):
        add(
            f"{domain}.list",
            QUERY,
            lambda s, a, c, status=status: s.content.list(status, **a),
            "content.list",
            permission="knowledge.read",
        )
        add(
            f"{domain}.get",
            ITEM,
            lambda s, a, c: s.content.get(a["item_id"]),
            "content.get",
            permission="knowledge.read",
        )
        add(
            f"{domain}.update",
            schema(
                domain + "Update",
                item_id=(str, ...),
                changes=(CONTENT_PATCH, ...),
                expected_revision=(int, ...),
            ),
            lambda s, a, c: s.content.update(
                a["item_id"], a["changes"], expected_revision=a["expected_revision"]
            ),
            "content.update",
            write=True,
            permission="knowledge.write",
        )
        add(
            f"{domain}.delete",
            ITEM,
            lambda s, a, c: s.content.delete(a["item_id"]),
            "content.delete",
            write=True,
            confirm=True,
            permission="knowledge.write",
            postcondition=lambda s, a, v: all(
                x["id"] != a["item_id"]
                for status in ("inbox", "knowledge")
                for x in s.content.list(status)
            ),
        )
    add(
        "inbox.import_text",
        schema("ImportText", text=(str, ...), use_ai=(bool, False)),
        _import,
        "inbox.import_item",
        write=True,
        permission="knowledge.write",
    )
    add(
        "inbox.import_url",
        schema("ImportURL", url=(str, ...), use_ai=(bool, False)),
        _import,
        "inbox.import_item",
        write=True,
        permission="knowledge.write",
    )
    add(
        "inbox.import_file",
        schema("ImportFile", attachment_id=(str, ...)),
        _restricted_file_import,
        "inbox.import_item",
        write=True,
        permission="knowledge.write",
        restricted=True,
        description="文件上传仅限界面；当前未开放会话附件授权引用。",
    )
    add(
        "inbox.retry",
        ITEM,
        lambda s, a, c: s.inbox.retry(a["item_id"]),
        "inbox.retry",
        write=True,
        permission="knowledge.write",
    )
    add(
        "inbox.archive_after_metadata",
        schema(
            "ArchiveAfterMetadata",
            item_id=(str, ...),
            folder_id=(str, ...),
            expected_revision=(int, ...),
        ),
        lambda s, a, c: s.inbox.queue_archive(a["item_id"], a["folder_id"], a["expected_revision"]),
        "inbox.queue_archive",
        write=True,
        permission="knowledge.write",
        postcondition=lambda s, a, v: all(
            s.inbox.get_archive_job(v["job_id"])[key] == v[key]
            for key in ("job_id", "item_id", "folder_id", "revision")
        ),
    )
    add(
        "inbox.archive_job",
        schema("ArchiveJob", job_id=(str, ...)),
        lambda s, a, c: s.inbox.get_archive_job(a["job_id"]),
        "inbox.get_archive_job",
        permission="knowledge.read",
    )
    classify = schema(
        "Classify", item_ids=(list[str], ...), folder_id=(str | None, None), use_ai=(bool, False)
    )
    add(
        "inbox.classify_selected",
        classify,
        _classify,
        "inbox.classify_batch",
        write=True,
        permission="knowledge.write",
        postcondition=_verify_classify,
    )
    add(
        "inbox.classify_all",
        schema("ClassifyAll", folder_id=(str | None, None), use_ai=(bool, False)),
        _classify,
        "inbox.classify_batch",
        write=True,
        permission="knowledge.write",
        postcondition=_verify_classify,
    )
    add(
        "inbox.move",
        schema(
            "Move", item_id=(str, ...), folder_id=(str | None, None), expected_revision=(int, ...)
        ),
        lambda s, a, c: s.content.update(
            a["item_id"],
            {"status": "knowledge", "folder_id": a["folder_id"]},
            expected_revision=a["expected_revision"],
        ),
        "content.update",
        write=True,
        permission="knowledge.write",
        postcondition=lambda s, a, v: (
            v.get("status") == "knowledge"
            and v.get("folder_id") == a["folder_id"]
            and _verify("content", s, a, v)
        ),
    )
    add(
        "content.move_to_inbox",
        schema("MoveToInbox", item_id=(str, ...), expected_revision=(int, ...)),
        lambda s, a, c: s.content.update(
            a["item_id"],
            {"status": "inbox", "folder_id": None},
            expected_revision=a["expected_revision"],
        ),
        "content.update",
        write=True,
        permission="knowledge.write",
    )
    add(
        "knowledge.search",
        schema("Search", query=(str, ...), limit=(int, 6), mode=(str, "auto")),
        _search,
        "retrieval.search",
        permission="knowledge.read",
    )
    add(
        "knowledge.get",
        schema("Document", document_id=(str, ...)),
        _document,
        "retrieval.get_document",
        permission="knowledge.read",
    )
    add(
        "knowledge.folders.list",
        EMPTY,
        lambda s, a, c: s.knowledge.list_folders(),
        "knowledge.list_folders",
        permission="knowledge.read",
    )
    add(
        "knowledge.folders.get",
        FOLDER,
        lambda s, a, c: s.knowledge.get_folder(a["folder_id"]),
        "knowledge.get_folder",
        permission="knowledge.read",
    )
    add(
        "knowledge.folders.create",
        FOLDER_CREATE,
        lambda s, a, c: s.knowledge.create_folder(a),
        "knowledge.create_folder",
        write=True,
        permission="knowledge.write",
    )
    add(
        "knowledge.folders.ensure",
        FOLDER_CREATE,
        _ensure_folder,
        "knowledge.ensure_folder",
        write=True,
        permission="knowledge.write",
    )
    add(
        "knowledge.folders.update",
        schema("FolderUpdate", folder_id=(str, ...), changes=(FOLDER_PATCH, ...)),
        lambda s, a, c: s.knowledge.update_folder(a["folder_id"], a["changes"]),
        "knowledge.update_folder",
        write=True,
        permission="knowledge.write",
    )
    add(
        "knowledge.folders.delete",
        FOLDER,
        lambda s, a, c: s.knowledge.delete_folder(a["folder_id"]),
        "knowledge.delete_folder",
        write=True,
        confirm=True,
        permission="knowledge.write",
        postcondition=lambda s, a, v: all(
            f["id"] != a["folder_id"] for f in s.knowledge.list_folders()
        ),
    )
    add(
        "knowledge.folders.items",
        schema("FolderItems", folder_id=(str | None, None), q=(str, ""), tag=(str, "")),
        lambda s, a, c: s.knowledge.folder_items(**a),
        "knowledge.folder_items",
        permission="knowledge.read",
        postcondition=lambda s, a, v: _verify("content", s, a, v),
    )
    add("tasks.list", EMPTY, lambda s, a, c: s.tasks.list(), "tasks.list")
    add("tasks.create", TASK_CREATE, lambda s, a, c: s.tasks.create(a), "tasks.create", write=True)
    add(
        "tasks.update",
        schema("TaskUpdate", task_id=(str, ...), changes=(TASK_PATCH, ...)),
        lambda s, a, c: s.tasks.update(a["task_id"], a["changes"]),
        "tasks.update",
        write=True,
    )
    add(
        "tasks.complete",
        schema("Complete", task_id=(str, ...), completed=(bool, True)),
        lambda s, a, c: s.tasks.update(a["task_id"], {"completed": a["completed"]}),
        "tasks.update",
        write=True,
    )
    add(
        "tasks.delete",
        TASK,
        lambda s, a, c: s.tasks.delete(a["task_id"]),
        "tasks.delete",
        write=True,
        confirm=True,
        postcondition=lambda s, a, v: all(t["id"] != a["task_id"] for t in s.tasks.list()),
    )
    add(
        "feed.list",
        schema("FeedList", source=(str, ""), q=(str, ""), include_hidden=(bool, False)),
        lambda s, a, c: s.feed.list(**a),
        "feed.list",
    )
    add(
        "feed.refresh",
        EMPTY,
        lambda s, a, c: s.feed.refresh(),
        "feed.refresh",
        network=True,
        permission="network.read",
    )
    add(
        "feed.save_to_inbox",
        ITEM,
        lambda s, a, c: s.feed.save(a["item_id"]),
        "feed.save",
        write=True,
        permission="knowledge.write",
        postcondition=lambda s, a, v: _verify("content", s, a, v),
    )
    feed_fields = {
        "url": (str, ...),
        "title": (str, ""),
        "summary": (str, ""),
        "tags": (list[str], Field(default_factory=list)),
        "fetch_title": (bool, False),
    }
    add(
        "feed.add_manual",
        schema("ManualFeed", **feed_fields),
        lambda s, a, c: s.feed.add_manual(a),
        "feed.add_manual",
        write=True,
    )
    add(
        "feed.update_manual",
        schema(
            "ManualUpdate",
            item_id=(str, ...),
            changes=(
                schema(
                    "ManualPatch",
                    url=(str | None, None),
                    title=(str | None, None),
                    summary=(str | None, None),
                    tags=(list[str] | None, None),
                    fetch_title=(bool, False),
                ),
                ...,
            ),
        ),
        lambda s, a, c: s.feed.update_manual(a["item_id"], a["changes"]),
        "feed.update_manual",
        write=True,
    )
    for action, method in (
        ("remove_manual", "remove_manual"),
        ("restore_manual", "restore_manual"),
        ("hide_external", "hide_external"),
        ("unhide_external", "unhide_external"),
    ):
        add(
            "feed." + action,
            ITEM,
            lambda s, a, c, method=method: getattr(s.feed, method)(a["item_id"]),
            "feed." + method,
            write=True,
            confirm=action == "remove_manual",
        )
    add(
        "automations.list",
        EMPTY,
        lambda s, a, c: s.automations.list(),
        "automations.list",
        permission="automation.read",
    )
    add(
        "automations.create",
        schema(
            "AutomationCreate",
            name=(str, ...),
            prompt=(str, ...),
            hour=(int, ...),
            minute=(int, ...),
            timezone=(str, "Asia/Shanghai"),
        ),
        lambda s, a, c: s.automations.create(a),
        "automations.create",
        write=True,
        confirm=True,
        permission="automation.manage",
    )
    add(
        "automations.toggle",
        schema("AutomationToggle", task_id=(str, ...), enabled=(bool, ...)),
        lambda s, a, c: s.automations.toggle(a["task_id"], a["enabled"]),
        "automations.toggle",
        write=True,
        confirm=True,
        permission="automation.manage",
    )
    add(
        "automations.delete",
        TASK,
        lambda s, a, c: s.automations.delete(a["task_id"]),
        "automations.delete",
        write=True,
        confirm=True,
        permission="automation.manage",
        postcondition=lambda s, a, v: all(t["id"] != a["task_id"] for t in s.automations.list()),
    )
    add(
        "automations.runs",
        TASK,
        lambda s, a, c: s.automations.runs(a["task_id"]),
        "automations.runs",
        permission="automation.read",
    )
    add("conversations.list", EMPTY, lambda s, a, c: s.store.list(), "store.list")
    add("conversations.create", EMPTY, lambda s, a, c: s.store.create(), "store.create", write=True)
    add(
        "conversations.get",
        CONVERSATION,
        lambda s, a, c: s.conversations.get(a["cid"]),
        "conversations.get",
    )
    add(
        "conversations.messages",
        CONVERSATION,
        lambda s, a, c: s.store.messages(a["cid"]),
        "store.messages",
        postcondition=lambda s, a, v: s.store.messages(a["cid"]) == v,
    )
    add(
        "conversations.update",
        schema("ConversationUpdate", cid=(str, ...), title=(str, ...)),
        lambda s, a, c: s.conversations.update(a["cid"], {"title": a["title"]}),
        "conversations.update",
        write=True,
    )
    add(
        "conversations.model",
        schema("ConversationModel", cid=(str, ...), model=(str | None, None)),
        lambda s, a, c: s.conversations.update(a["cid"], {"model_override": a["model"]}),
        "conversations.update",
        write=True,
    )
    add(
        "conversations.stop",
        CONVERSATION,
        lambda s, a, c: s.chat.cancel(a["cid"]),
        "chat.cancel",
        write=True,
        restricted=True,
    )
    add(
        "conversations.delete",
        CONVERSATION,
        lambda s, a, c: s.store.delete(a["cid"]),
        "store.delete",
        write=True,
        confirm=True,
        restricted=True,
    )
    add("preferences.get", EMPTY, lambda s, a, c: s.preferences.get(), "preferences.get")
    add(
        "preferences.update",
        schema("PreferencesUpdate", changes=(PREFERENCE_PATCH, ...), expected_revision=(int, ...)),
        lambda s, a, c: s.preferences.update(
            a["changes"], expected_revision=a["expected_revision"]
        ),
        "preferences.update",
        write=True,
        postcondition=lambda s, a, v: s.preferences.get() == v,
    )
    add(
        "preferences.reset",
        schema("PreferenceReset", expected_revision=(int, ...)),
        lambda s, a, c: s.preferences.reset(expected_revision=a["expected_revision"]),
        "preferences.reset",
        write=True,
        postcondition=lambda s, a, v: s.preferences.get() == v,
    )
    add(
        "settings.model.read",
        EMPTY,
        lambda s, a, c: s.model_settings.read(),
        "model_settings.read",
        permission="settings.read",
    )
    add(
        "settings.model.update",
        EMPTY,
        lambda s, a, c: None,
        "model_settings.update",
        write=True,
        restricted=True,
        permission="settings.write",
    )
    add(
        "settings.data.read",
        EMPTY,
        lambda s, a, c: {
            "data_dir": str(s.store.path.parent),
            "content_count": sum(len(s.content.list(status)) for status in ("inbox", "knowledge")),
        },
        "content.list",
        permission="settings.read",
    )
    add("capabilities.skills", EMPTY, lambda s, a, c: s.commands.skills(), "commands.skills")
    add("capabilities.mcp", EMPTY, lambda s, a, c: s.commands.mcp(), "commands.mcp")
    from xiliu.api.model_catalog import MODEL_CATALOG
    from xiliu.api.services.commands import COMMANDS

    add(
        "settings.models.catalog",
        EMPTY,
        lambda s, a, c: MODEL_CATALOG,
        "model_settings.read",
        permission="settings.read",
    )
    add("capabilities.commands", EMPTY, lambda s, a, c: COMMANDS, "commands.skills")
    return registry
