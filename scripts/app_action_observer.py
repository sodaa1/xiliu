"""Optional pytest-only action observer; stores IDs/outcomes, never argument values."""

from __future__ import annotations

import functools
import json
import re
from pathlib import Path

import pytest


def pytest_addoption(parser):
    parser.addoption("--app-action-report", default=None)


def pytest_configure(config):
    config._app_action_events = []
    config._app_action_outcomes = {}
    config._app_http_events = []
    from scripts.audit_app_surface import scan_surface

    templates = [
        row["symbol"] for row in scan_surface(Path(config.rootpath)) if row["kind"] == "http_route"
    ]
    config._app_http_routes = _http_patterns(templates)


def _http_patterns(templates: list[str]) -> list[tuple[str, str, re.Pattern[str]]]:
    routes = []
    templates = sorted(
        templates, key=lambda value: ("{path:path}" in value, value.count("{"), -len(value))
    )
    for template in templates:
        method, path = template.split(" ", 1)
        escaped = re.escape(path)
        pattern = re.sub(r"\\\{[^{}]+\\\}", "[^/]+", escaped)
        if "{path:path}" in path:
            pattern = re.escape(path.split("{path:path}")[0]) + ".*"
        routes.append((method, template, re.compile("^" + pattern + "$")))
    return routes


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    report = (yield).get_result()
    outcomes = item.config._app_action_outcomes
    if report.failed or report.when == "call":
        outcomes[item.nodeid] = report.outcome


def _record(config, nodeid, layer, action, result):
    if not isinstance(action, str) or not action:
        return
    if isinstance(result, str):
        try:
            result = json.loads(result)
        except (ValueError, TypeError):
            return
    if not isinstance(result, dict):
        return
    verification = result.get("verification")
    error = result.get("error")
    if isinstance(error, dict):
        error = error.get("code")
    if not isinstance(error, str):
        error = None
    config._app_action_events.append(
        {
            "test": nodeid,
            "layer": layer,
            "action_id": action,
            "ok": result.get("ok") is True,
            "status": result.get("status"),
            "error": error,
            "verified": isinstance(verification, dict) and verification.get("passed") is True,
        }
    )


@pytest.fixture(autouse=True)
def observe_app_actions(request, monkeypatch):
    if not request.config.getoption("--app-action-report"):
        return
    from starlette.testclient import TestClient

    from xiliu.app.dispatch import AppDispatcher
    from xiliu.execution.gateway import ExecutionGateway
    from xiliu.tools.app import AppTool

    original_request = TestClient.request

    @functools.wraps(original_request)
    def observed_request(client, method, url, *args, **kwargs):
        response = original_request(client, method, url, *args, **kwargs)
        # Store route templates and disposable-test paths, never query strings or payloads.
        for route_method, template, pattern in request.config._app_http_routes:
            if method.upper() == route_method and pattern.fullmatch(response.request.url.path):
                request.config._app_http_events.append(
                    {
                        "test": request.node.nodeid,
                        "actual_path": response.request.url.path,
                        "route": template,
                        "status_code": response.status_code,
                    }
                )
                break
        if method.upper() == "POST" and response.request.url.path == "/api/app":
            body = kwargs.get("json")
            if isinstance(body, dict) and body.get("operation") == "execute":
                _record(
                    request.config,
                    request.node.nodeid,
                    "http_app",
                    body.get("action_id"),
                    response.json(),
                )
        return response

    monkeypatch.setattr(TestClient, "request", observed_request)

    def wrap(owner, method, layer, action_at):
        original = getattr(owner, method)

        @functools.wraps(original)
        def observed(*args, **kwargs):
            result = original(*args, **kwargs)
            _record(request.config, request.node.nodeid, layer, action_at(args, kwargs), result)
            return result

        monkeypatch.setattr(owner, method, observed)

    wrap(
        AppDispatcher,
        "execute",
        "dispatcher",
        lambda args, kwargs: args[1] if len(args) > 1 else kwargs.get("action_id"),
    )
    wrap(
        AppTool,
        "_run",
        "app_tool",
        lambda args, kwargs: args[2] if len(args) > 2 else kwargs.get("action_id"),
    )
    wrap(
        ExecutionGateway,
        "invoke",
        "gateway",
        lambda args, kwargs: (args[2] if len(args) > 2 else kwargs.get("arguments", {})).get(
            "action_id"
        ),
    )


def pytest_sessionfinish(session, exitstatus):
    output = session.config.getoption("--app-action-report")
    if not output:
        return
    from xiliu.app.actions import get_registry

    events = session.config._app_action_events
    outcomes = session.config._app_action_outcomes
    actions = {}
    for name in sorted(get_registry()):
        observed = [
            event
            for event in events
            if event["action_id"] == name and outcomes.get(event["test"]) == "passed"
        ]
        successful = [event for event in observed if event["ok"] and event["verified"]]
        denied = [
            event
            for event in observed
            if event["error"] in {"policy_denied", "capability_unavailable", "permission_denied"}
        ]
        full_chain = sorted(
            {event["test"] for event in successful if event["layer"] == "gateway"}
            & {event["test"] for event in successful if event["layer"] == "app_tool"}
            & {event["test"] for event in successful if event["layer"] == "dispatcher"}
        )
        actions[name] = {
            "status": "passed" if successful else "denied" if denied else "not_run",
            "gateway_tool_dispatcher_passed_tests": full_chain,
            "successful_tests": sorted({event["test"] for event in successful}),
            "denied_tests": sorted({event["test"] for event in denied}),
            "events": observed,
        }
    payload = {
        "scope": "Actual calls in this pytest run; passed test outcomes only. "
        "Denied is permission evidence, not successful business execution. "
        "Browser/UI controls are reported separately.",
        "pytest_exit_code": exitstatus,
        "actions": actions,
        "totals": {
            status: sum(row["status"] == status for row in actions.values())
            for status in ("passed", "denied", "not_run")
        },
        "remaining_without_successful_execution": [
            name for name, row in actions.items() if row["status"] != "passed"
        ],
        "test_outcomes": outcomes,
        "http_route_events": [
            event
            for event in session.config._app_http_events
            if outcomes.get(event["test"]) == "passed"
        ],
    }
    target = Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
