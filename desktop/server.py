"""Private loopback service owned by the desktop shell (also runs unfrozen)."""

from __future__ import annotations

import argparse
import asyncio
import hmac
import os
import socket
import sys
import threading
from pathlib import Path

import uvicorn
from fastapi import Header, HTTPException

from xiliu.api.app import create_app
from xiliu.api.desktop_defaults import seed_mcp_defaults


async def serve(data_dir: Path, token: str, port: int = 0) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
    seed_mcp_defaults(data_dir, root / "desktop" / "defaults")
    if not (root / "web/dist/index.html").is_file():
        raise FileNotFoundError("Desktop web assets are missing; rebuild the web bundle")
    app = create_app(data_dir=data_dir, env_file=data_dir / ".env", static_dir=root / "web/dist")
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", log_level="warning"))

    def authorize(value: str | None) -> None:
        if not value or not hmac.compare_digest(value, token):
            raise HTTPException(status_code=403, detail="Desktop owner required")

    async def ready(x_xiliu_desktop_token: str | None = Header(default=None)):
        authorize(x_xiliu_desktop_token)
        return {"ready": server.started}

    async def shutdown(x_xiliu_desktop_token: str | None = Header(default=None)):
        authorize(x_xiliu_desktop_token)
        server.should_exit = True
        return {"closing": True}

    # The web SPA catch-all must remain last.
    app.add_api_route("/api/desktop/ready", ready, methods=["GET"], include_in_schema=False)
    app.router.routes.insert(0, app.router.routes.pop())
    app.add_api_route("/api/desktop/shutdown", shutdown, methods=["POST"], include_in_schema=False)
    app.router.routes.insert(0, app.router.routes.pop())

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", port))
        listener.listen(128)
        listener.setblocking(False)
        actual_port = listener.getsockname()[1]

        async def announce():
            while not server.started and not server.should_exit:
                await asyncio.sleep(0.02)
            if server.started:
                print(f"XILIU_READY http://127.0.0.1:{actual_port}", flush=True)

        # EOF closes the service if its owning shell crashes or closes its pipe.
        def watch_owner():
            try:
                # Raw fd reads avoid holding Python's buffered-reader lock
                # while the interpreter finalizes a daemon watcher.
                while os.read(sys.stdin.fileno(), 4096):
                    pass
            except OSError:
                pass
            finally:
                server.should_exit = True

        threading.Thread(target=watch_owner, daemon=True, name="desktop-owner").start()
        announcement = asyncio.create_task(announce())
        try:
            await server.serve(sockets=[listener])
        finally:
            announcement.cancel()
            await asyncio.gather(announcement, return_exceptions=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--port", type=int, default=0)
    args = parser.parse_args()
    token = os.environ.get("XILIU_DESKTOP_TOKEN", "")
    if len(token) < 32:
        parser.error("A private desktop owner token is required")
    asyncio.run(serve(args.data_dir.resolve(), token, args.port))


if __name__ == "__main__":
    main()
