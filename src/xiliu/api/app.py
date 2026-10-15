from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse

from xiliu import __version__
from xiliu.api.errors import WebError
from xiliu.api.routes import (
    app as app_actions,
)
from xiliu.api.routes import (
    capabilities,
    content,
    conversations,
    feed,
    inbox,
    knowledge,
    models,
    preferences,
    workspace,
)
from xiliu.api.services.automations import AutomationService
from xiliu.api.services.chat import ChatService
from xiliu.api.services.commands import CommandService
from xiliu.api.services.content import ContentService
from xiliu.api.services.conversations import ConversationService
from xiliu.api.services.feed import FeedService
from xiliu.api.services.inbox import InboxService
from xiliu.api.services.knowledge import KnowledgeService
from xiliu.api.services.model_settings import ModelSettingsService
from xiliu.api.services.preferences import PreferencesService
from xiliu.api.services.tasks import TaskService
from xiliu.api.store import AppStore
from xiliu.app.actions import AppServices
from xiliu.rag.embedding_config import embedding_provider_from_settings
from xiliu.rag.service import RAGService


def create_app(
    *,
    data_dir: Path | None = None,
    env_file: Path = Path(".env"),
    static_dir: Path | None = None,
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(application: FastAPI):
        async def heartbeat():
            while True:
                await asyncio.sleep(10)
                await asyncio.to_thread(application.state.automations.sync)

        owner = None
        try:
            await asyncio.to_thread(application.state.retrieval.worker.start)
            await asyncio.to_thread(application.state.inbox.start)
            await asyncio.to_thread(application.state.automations.start)
            owner = asyncio.create_task(heartbeat())
            yield
        finally:
            try:
                # Keep renewing ownership while running automation jobs drain.
                try:
                    await asyncio.to_thread(application.state.automations.shutdown)
                finally:
                    try:
                        await asyncio.to_thread(application.state.inbox.shutdown)
                    finally:
                        await asyncio.to_thread(application.state.retrieval.worker.shutdown)
            finally:
                if owner is not None:
                    owner.cancel()
                    with suppress(asyncio.CancelledError):
                        await owner

    app = FastAPI(title="息流 · xiliu", version=__version__, lifespan=lifespan)
    app.state.model_settings = ModelSettingsService(env_file)
    values = app.state.model_settings.values()
    app.state.data_dir = (data_dir or Path(values.get("XILIU_DATA_DIR", ".xiliu"))).resolve()

    app.state.store = AppStore(app.state.data_dir)
    app.state.conversations = ConversationService(app.state.store, app.state.model_settings)
    app.state.chat = ChatService(app.state.conversations)
    app.state.commands = CommandService(app.state.conversations)
    app.state.chat.commands = app.state.commands
    app.state.content = ContentService(app.state.store)
    app.state.knowledge = KnowledgeService(app.state.content)
    app.state.inbox = InboxService(app.state.content, app.state.knowledge, app.state.model_settings)
    app.state.chat.inbox = app.state.inbox
    embedding_provider = None
    if values.get("XILIU_EMBEDDING_MODEL", "").strip():
        embedding_provider = embedding_provider_from_settings(
            app.state.model_settings.runtime_settings()
        )
    app.state.retrieval = RAGService(
        app.state.content, app.state.knowledge, embedding_provider=embedding_provider
    )
    app.state.feed = FeedService(
        app.state.store, app.state.content, app.state.model_settings
    )
    app.state.tasks = TaskService(app.state.store)
    app.state.preferences = PreferencesService(app.state.store)
    app.state.automations = AutomationService(app.state.data_dir, app.state.model_settings)
    app.state.app_services = AppServices.from_state(app.state)
    app.state.chat.app_services = app.state.app_services
    app.state.automations.app_services = app.state.app_services

    @app.exception_handler(WebError)
    async def web_error(_request: Request, exc: WebError):
        return JSONResponse(
            {"error": {"code": exc.code, "message": exc.message}}, status_code=exc.status
        )

    @app.exception_handler(RequestValidationError)
    async def invalid_request(_request: Request, _exc: RequestValidationError):
        # Never echo Pydantic inputs: the body may contain an API key.
        return JSONResponse(
            {"error": {"code": "invalid_request", "message": "请求格式不正确。"}}, status_code=422
        )

    @app.middleware("http")
    async def local_origin(request: Request, call_next):
        loopback = {"localhost", "127.0.0.1", "::1"}
        try:
            hostname = request.url.hostname
        except ValueError:
            hostname = None
        if hostname not in loopback:
            return JSONResponse(
                {"error": {"code": "invalid_host", "message": "仅允许本机访问。"}}, status_code=400
            )
        origin = request.headers.get("origin")
        if request.method in {"POST", "PUT", "PATCH", "DELETE"} and origin:
            try:
                origin_host = urlsplit(origin).hostname
            except ValueError:
                origin_host = None
            if origin_host not in loopback:
                return JSONResponse(
                    {"error": {"code": "invalid_origin", "message": "无效来源。"}}, status_code=403
                )
        return await call_next(request)

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    app.include_router(models.router)
    app.include_router(app_actions.router)
    app.include_router(preferences.router)
    app.include_router(capabilities.router)
    app.include_router(conversations.router)
    app.include_router(content.router)
    app.include_router(feed.router)
    app.include_router(inbox.router)
    app.include_router(knowledge.router)
    app.include_router(workspace.router)
    dist = (static_dir or Path(__file__).resolve().parents[3] / "web" / "dist").resolve()

    @app.get("/{path:path}", include_in_schema=False)
    def frontend(path: str):
        if path == "api" or path.startswith("api/"):
            raise WebError("not_found", "接口不存在。", 404)
        target = (dist / path).resolve()
        if not target.is_relative_to(dist):
            raise WebError("not_found", "页面不存在。", 404)
        if target.is_dir():
            target = (target / "index.html").resolve()
            if not target.is_relative_to(dist):
                raise WebError("not_found", "页面不存在。", 404)
        if target.is_file():
            headers = {"Cache-Control": "no-cache"} if target.suffix == ".html" else None
            return FileResponse(target, headers=headers)
        if Path(path).suffix:
            raise WebError("not_found", "文件不存在。", 404)
        if (dist / "index.html").is_file():
            return FileResponse(dist / "index.html", headers={"Cache-Control": "no-cache"})
        raise WebError("frontend_not_built", "请先在 web 目录运行 npm run build。", 503)

    return app
