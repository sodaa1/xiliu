from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import secrets
from threading import BoundedSemaphore

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, ConfigDict, Field
from starlette.datastructures import Headers
from starlette.responses import JSONResponse

from xiliu.api.errors import WebError
from xiliu.cloud.config import CloudConfig
from xiliu.cloud.identity import IdentityStore

COOKIE = "xiliu_cloud_session"


def csrf_token(config: CloudConfig, token: str) -> str:
    return hmac.new(
        base64.urlsafe_b64decode(config.master_key), b"csrf:" + token.encode(), hashlib.sha256
    ).hexdigest()


def error_response(error: WebError) -> JSONResponse:
    return JSONResponse(
        {"error": {"code": error.code, "message": error.message}}, status_code=error.status
    )


class CloudRequestGuard:
    """Host/origin/CSRF checks and bounded auth bodies, before any route runs."""

    def __init__(self, app, *, config: CloudConfig, identity: IdentityStore):
        self.app, self.config, self.identity = app, config, identity
        self.body_slots = BoundedSemaphore(4)
        self.body_timeout = 30

    async def _auth_body(self, receive):
        if not self.body_slots.acquire(blocking=False):
            raise WebError("upload_busy", "登录请求繁忙，请稍后再试。", 429)
        try:
            raw = bytearray()
            async with asyncio.timeout(self.body_timeout):
                while True:
                    message = await receive()
                    if message["type"] == "http.disconnect":
                        return None
                    raw.extend(message.get("body", b""))
                    if len(raw) > 4096:
                        raise WebError("body_too_large", "请求内容过大。", 413)
                    if not message.get("more_body"):
                        return raw
        except TimeoutError:
            raise WebError("request_timeout", "请求上传超时。", 408) from None
        finally:
            self.body_slots.release()

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        from urllib.parse import urlsplit

        request = Request(scope)
        headers = Headers(scope=scope)
        path = scope["path"].rstrip("/")
        try:
            if headers.getlist("host") != [urlsplit(self.config.public_origin).netloc]:
                raise WebError("invalid_host", "无效的访问地址。", 400)
            if scope["method"] in {"POST", "PUT", "PATCH", "DELETE"}:
                if headers.getlist("origin") != [self.config.public_origin]:
                    raise WebError("invalid_origin", "无效来源，请刷新后重试。", 403)
                if path not in {"/api/auth/login", "/api/auth/register"}:
                    token = request.cookies.get(COOKIE, "")
                    user = self.identity.session(token)
                    provided = headers.get("x-csrf-token", "")
                    if not provided.isascii() or not secrets.compare_digest(
                        provided, csrf_token(self.config, token)
                    ):
                        raise WebError("invalid_csrf", "登录验证已失效，请刷新后重试。", 403)
                    scope["xiliu.user"] = user
            if path in {"/api/auth/login", "/api/auth/register"} and scope["method"] == "POST":
                raw = await self._auth_body(receive)
                if raw is None:
                    return
                consumed = False

                async def bounded_receive():
                    nonlocal consumed
                    if consumed:
                        return await receive()
                    consumed = True
                    return {"type": "http.request", "body": bytes(raw), "more_body": False}

                return await self.app(scope, bounded_receive, send)
        except WebError as error:
            return await error_response(error)(scope, receive, send)
        return await self.app(scope, receive, send)


class Credentials(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str = Field(min_length=1, max_length=32)
    password: str = Field(min_length=1, max_length=128)


def current_user(request: Request) -> dict:
    return request.app.state.identity.session(request.cookies.get(COOKIE, ""))


def session_payload(request: Request, user: dict, token: str) -> dict:
    ledger = getattr(request.app.state, "trial_ledger", None)
    trial = ledger.balance(user["id"]) if ledger else {"limit": 5, "remaining": 5}
    return {
        "user": {"id": user["id"], "username": user["username"]},
        "workspace": {"id": user["workspace_id"]},
        "csrf_token": csrf_token(request.app.state.cloud_config, token),
        "trial": {"enabled": request.app.state.cloud_config.trial_enabled, **trial},
    }


def create_auth_app(config: CloudConfig) -> FastAPI:
    app = FastAPI(title="息流云端", docs_url=None, redoc_url=None, openapi_url=None)
    identity = IdentityStore(config.data_dir, max_users=config.max_users)
    app.state.identity, app.state.cloud_config = identity, config
    app.add_middleware(CloudRequestGuard, config=config, identity=identity)

    @app.exception_handler(WebError)
    async def web_error(_request: Request, error: WebError):
        return error_response(error)

    @app.exception_handler(RequestValidationError)
    async def validation_error(_request: Request, _error: RequestValidationError):
        return error_response(WebError("invalid_request", "请求格式不正确。", 422))

    @app.get("/api/cloud/bootstrap")
    def bootstrap():
        return {
            "mode": "cloud",
            "signup_enabled": config.signup_enabled,
            "guest_url": "/demo/#/today",
        }

    @app.get("/api/auth/session")
    def session(request: Request):
        return session_payload(request, current_user(request), request.cookies.get(COOKIE, ""))

    def authenticate(request: Request, response: Response, body: Credentials):
        token = identity.login(body.username, body.password, ttl=config.session_seconds)
        response.set_cookie(
            COOKIE,
            token,
            max_age=config.session_seconds,
            httponly=True,
            secure=config.secure_cookies,
            samesite="lax",
            path="/",
        )
        response.headers["Cache-Control"] = "no-store"
        return session_payload(request, identity.session(token), token)

    @app.post("/api/auth/register", status_code=201)
    def register(request: Request, response: Response, body: Credentials):
        if not config.signup_enabled:
            raise WebError("signup_closed", "当前暂未开放注册。", 403)
        identity.rate_limit(
            "signup",
            request.client.host if request.client else "unknown",
            limit=config.signup_limit,
            seconds=3600,
        )
        identity.register(body.username, body.password)
        return authenticate(request, response, body)

    @app.post("/api/auth/login")
    def login(request: Request, response: Response, body: Credentials):
        identity.rate_limit(
            "login-ip",
            request.client.host if request.client else "unknown",
            limit=config.login_limit,
            seconds=600,
        )
        identity.rate_limit(
            "login-user", body.username.lower(), limit=config.login_limit, seconds=600
        )
        return authenticate(request, response, body)

    @app.post("/api/auth/logout", status_code=204)
    def logout(request: Request):
        identity.revoke(request.cookies.get(COOKIE, ""))
        response = Response(status_code=204, headers={"Cache-Control": "no-store"})
        response.delete_cookie(
            COOKIE, secure=config.secure_cookies, httponly=True, samesite="lax", path="/"
        )
        return response

    @app.middleware("http")
    async def no_identity_cache(request: Request, call_next):
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        return response

    return app
