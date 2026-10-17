"""Disposable container acceptance; never run against a public/production site."""

from __future__ import annotations

import argparse
import base64
import http.cookiejar
import json
import secrets
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


class Client:
    def __init__(self, origin):
        self.origin, self.csrf = origin, ""
        self.opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}),
            urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()),
        )

    def request(self, path, body=None, *, method="GET", status=200, raw=False) -> Any:
        headers = {"Origin": self.origin, "X-CSRF-Token": self.csrf}
        if body is not None:
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(
            self.origin + path,
            method=method,
            headers=headers,
            data=json.dumps(body).encode() if body is not None else None,
        )
        try:
            response = self.opener.open(request, timeout=30)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            result = response.read()
            assert response.status == status, (path, response.status, result[:200])
        return result if raw else json.loads(result) if result else None

    def authenticate(self, username, password, *, register=False):
        result = self.request(
            "/api/auth/register" if register else "/api/auth/login",
            {"username": username, "password": password},
            method="POST",
            status=201 if register else 200,
        )
        self.csrf = result["csrf_token"]
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["create", "verify"])
    parser.add_argument("--origin", default="http://127.0.0.1:8765")
    parser.add_argument("--state", type=Path, default=Path(".preview/cloud-container-state.json"))
    args = parser.parse_args()
    if urlsplit(args.origin).hostname not in {"localhost", "127.0.0.1"}:
        parser.error("Acceptance is limited to disposable loopback deployments")
    a, b = Client(args.origin), Client(args.origin)
    a.request("/api/health")
    a.request("/api/content", status=401)
    guest = a.request("/demo/", raw=True)
    assert b"/demo/assets/" in guest
    if args.phase == "create":
        password = secrets.token_urlsafe(24)
        alice = a.authenticate("cloudalice", password, register=True)
        bob = b.authenticate("cloudbobby", password, register=True)
        note = a.request(
            "/api/content",
            {
                "type": "note",
                "status": "inbox",
                "title": "Alice only",
                "content": "Private Alice note",
            },
            method="POST",
            status=201,
        )
        attachment = a.request(
            "/api/content",
            {
                "type": "file",
                "status": "inbox",
                "title": "File",
                "filename": "sample.txt",
                "data_base64": base64.b64encode(b"private attachment").decode(),
            },
            method="POST",
            status=201,
        )
        task = a.request("/api/tasks", {"title": "Alice plan"}, method="POST", status=201)
        a.request("/api/tasks/" + task["id"], {"completed": True}, method="PATCH")
        a.request(
            "/api/settings/model",
            {
                "provider": "custom",
                "model": "fake",
                "base_url": "https://model.example/v1",
                "api_key": "disposable-user-api-key",
            },
            method="PUT",
        )
        cid = a.request("/api/conversations", {}, method="POST", status=201)["id"]
        response = a.request(
            f"/api/conversations/{cid}/chat",
            {"text": "test", "source": "trial", "request_id": "container-trial-1"},
            method="POST",
            raw=True,
        )
        assert b"trial_unavailable" in response
        state = {
            "password": password,
            "alice": alice["workspace"]["id"],
            "bob": bob["workspace"]["id"],
            "note": note["id"],
            "file": attachment["id"],
            "task": task["id"],
        }
        args.state.parent.mkdir(parents=True, exist_ok=True)
        args.state.write_text(json.dumps(state), encoding="utf-8")
    else:
        state = json.loads(args.state.read_text(encoding="utf-8"))
        alice = a.authenticate("cloudalice", state["password"])
        bob = b.authenticate("cloudbobby", state["password"])
        assert alice["workspace"]["id"] == state["alice"]
        assert bob["workspace"]["id"] == state["bob"]
        assert a.request("/api/settings/model")["api_key_set"]
        assert a.request("/api/content/" + state["note"])["title"] == "Alice only"
        assert any(
            task["id"] == state["task"] and task["completed"] for task in a.request("/api/tasks")
        )
    assert (
        a.request("/api/content/" + state["file"] + "/original", raw=True) == b"private attachment"
    )
    b.request("/api/content/" + state["note"], status=404)
    b.request("/api/content/" + state["file"] + "/original", status=404)
    b.request("/api/tasks/" + state["task"], method="DELETE", status=404)
    assert state["note"] not in str(b.request("/api/content"))
    assert a.request("/api/auth/session")["trial"]["remaining"] == 5
    a.request("/api/auth/logout", method="POST", status=204)
    a.request("/api/content/" + state["file"] + "/original", status=401)
    print(f"cloud {args.phase}: two-account CRUD, attachment, guest, quota and logout passed")


if __name__ == "__main__":
    main()
