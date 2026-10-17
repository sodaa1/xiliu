from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Request
from starlette.middleware import Middleware

from xiliu.api.app import include_business_routes, install_frontend
from xiliu.api.errors import WebError
from xiliu.cloud.auth import COOKIE, create_auth_app, error_response
from xiliu.cloud.config import CloudConfig
from xiliu.cloud.jobs import CloudJobCoordinator
from xiliu.cloud.limits import BodyLimit, RequestSlots, check_storage
from xiliu.cloud.workspaces import WorkspaceRegistry

_IDENTITY_PATHS = {
    "/api/health",
    "/api/cloud/bootstrap",
    "/api/auth/session",
    "/api/auth/login",
    "/api/auth/register",
    "/api/auth/logout",
}


class WorkspaceBinding:
    def __init__(self, app, *, registry: WorkspaceRegistry, identity):
        self.app, self.registry, self.identity = app, registry, identity
        self.slots = RequestSlots()

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        path = scope["path"].rstrip("/")
        if not (path == "/api" or path.startswith("/api/")) or path in _IDENTITY_PATHS:
            return await self.app(scope, receive, send)
        lease = None
        slot = None
        try:
            user = self.identity.session(Request(scope).cookies.get(COOKIE, ""))
            scope["xiliu.user"] = user
            slot = self.slots.acquire(user["workspace_id"])
            slot.__enter__()
            lease = self.registry.acquire(user["workspace_id"])
            scope["xiliu.services"] = await asyncio.to_thread(lease.__enter__)
            scope["xiliu.workspace_lease"] = lambda: self.registry.acquire(user["workspace_id"])
            if scope["method"] in {"POST", "PUT", "PATCH"} and not path.endswith("/stop"):
                await asyncio.to_thread(check_storage, scope["xiliu.services"].data_dir)
        except WebError as error:
            if lease is not None and "xiliu.services" in scope:
                await asyncio.shield(asyncio.to_thread(lease.__exit__, None, None, None))
            if slot is not None:
                slot.__exit__(None, None, None)
            return await error_response(error)(scope, receive, send)
        except BaseException:
            if lease is not None and "xiliu.services" in scope:
                await asyncio.shield(asyncio.to_thread(lease.__exit__, None, None, None))
            if slot is not None:
                slot.__exit__(None, None, None)
            raise
        try:
            return await self.app(scope, receive, send)
        finally:
            if lease is not None:
                await asyncio.shield(asyncio.to_thread(lease.__exit__, None, None, None))
            if slot is not None:
                slot.__exit__(None, None, None)


def create_cloud_app(config: CloudConfig | None = None, *, static_dir: Path | None = None):
    config = config or CloudConfig.from_env()
    app = create_auth_app(config)
    registry = WorkspaceRegistry(config)
    app.state.cloud_mode = True
    app.state.workspaces = registry
    jobs = CloudJobCoordinator(app.state.identity, registry)
    app.state.cloud_jobs = jobs
    app.user_middleware.append(Middleware(BodyLimit))
    app.user_middleware.append(
        Middleware(WorkspaceBinding, registry=registry, identity=app.state.identity)
    )

    @asynccontextmanager
    async def lifespan(_app):
        try:
            await asyncio.to_thread(jobs.start)
            yield
        finally:
            try:
                await asyncio.to_thread(jobs.shutdown)
            finally:
                await asyncio.to_thread(registry.close)

    app.router.lifespan_context = lifespan

    @app.get("/api/health")
    def health():
        return {"status": "ok", "mode": "cloud"}

    include_business_routes(app)
    install_frontend(
        app, (static_dir or Path(__file__).resolve().parents[3] / "web/dist").resolve()
    )
    return app
