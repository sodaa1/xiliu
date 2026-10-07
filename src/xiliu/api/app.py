from __future__ import annotations

from pathlib import Path
from urllib.parse import urlsplit

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse

from xiliu.api.errors import WebError
from xiliu.api.routes import capabilities, conversations, models
from xiliu.api.services.chat import ChatService
from xiliu.api.services.commands import CommandService
from xiliu.api.services.conversations import ConversationService
from xiliu.api.services.model_settings import ModelSettingsService
from xiliu.api.store import AppStore


def create_app(
    *,
    data_dir: Path | None = None,
    env_file: Path = Path(".env"),
    static_dir: Path | None = None,
) -> FastAPI:
    app = FastAPI(title="息流 · xiliu", version="0.1.0")
    app.state.model_settings = ModelSettingsService(env_file)
    values = app.state.model_settings.values()
    app.state.data_dir = data_dir or Path(values.get("XILIU_DATA_DIR", ".xiliu"))

    app.state.store = AppStore(app.state.data_dir)
    app.state.conversations = ConversationService(app.state.store, app.state.model_settings)
    app.state.chat = ChatService(app.state.conversations)
    app.state.commands = CommandService(app.state.conversations)
    app.state.chat.commands = app.state.commands

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
    app.include_router(capabilities.router)
    app.include_router(conversations.router)
    dist = (static_dir or Path(__file__).resolve().parents[3] / "web" / "dist").resolve()

    @app.get("/{path:path}", include_in_schema=False)
    def frontend(path: str):
        if path == "api" or path.startswith("api/"):
            raise WebError("not_found", "接口不存在。", 404)
        target = (dist / path).resolve()
        if not target.is_relative_to(dist):
            raise WebError("not_found", "页面不存在。", 404)
        if target.is_file():
            return FileResponse(target)
        if Path(path).suffix:
            raise WebError("not_found", "文件不存在。", 404)
        if (dist / "index.html").is_file():
            return FileResponse(dist / "index.html", headers={"Cache-Control": "no-cache"})
        raise WebError("frontend_not_built", "请先在 web 目录运行 npm run build。", 503)

    return app
