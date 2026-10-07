from __future__ import annotations

from pathlib import Path
from urllib.parse import urlsplit

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from xiliu.api.errors import WebError
from xiliu.api.routes import models
from xiliu.api.services.model_settings import ModelSettingsService


def create_app(*, data_dir: Path | None = None, env_file: Path = Path(".env")) -> FastAPI:
    app = FastAPI(title="息流 · xiliu", version="0.1.0")
    app.state.model_settings = ModelSettingsService(env_file)
    values = app.state.model_settings.values()
    app.state.data_dir = data_dir or Path(values.get("XILIU_DATA_DIR", ".xiliu"))

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
        origin = request.headers.get("origin")
        if request.method in {"POST", "PUT", "PATCH", "DELETE"} and origin:
            parsed = urlsplit(origin)
            if parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
                return JSONResponse(
                    {"error": {"code": "invalid_origin", "message": "无效来源。"}}, status_code=403
                )
        return await call_next(request)

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    app.include_router(models.router)
    return app
