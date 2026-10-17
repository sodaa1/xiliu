"""Regression tests for inventory completeness, using disposable source trees."""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def scanner():
    path = ROOT / "scripts/audit_app_surface.py"
    assert path.exists(), "machine surface scanner must exist"
    spec = importlib.util.spec_from_file_location("surface_audit", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_inventory_finds_ui_route_service_and_business_tool(tmp_path):
    files = {
        "web/src/features/feed/FeedPage.tsx": (
            "<button onClick={() => workspaceApi.addFeed()}>Add</button>\n"
            "const save = useMutation({mutationFn: workspaceApi.saveFeed})"
        ),
        "src/xiliu/api/routes/feed.py": (
            "from fastapi import APIRouter\nrouter = APIRouter(prefix='/api/feed')\n"
            "@router.post('/manual')\ndef add():\n    return state.feed.add_manual({})\n"
        ),
        "src/xiliu/api/services/feed.py": (
            "class FeedService:\n    def add_manual(self, payload):\n        pass\n"
        ),
        "src/xiliu/tools/feed.py": "class FeedAddTool(BaseTool):\n    name = 'feed_add'\n",
        "src/xiliu/cloud/auth.py": (
            "@app.post('/api/auth/login')\ndef login():\n    return {}\n"
        ),
    }
    for filename, source in files.items():
        path = tmp_path / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source, encoding="utf-8")
    items = scanner().scan_surface(tmp_path)
    assert {
        "ui_button",
        "ui_event",
        "ui_mutation",
        "ui_api",
        "http_route",
        "service_method",
        "base_tool",
    } <= {item["kind"] for item in items}
    assert any(item["symbol"] == "POST /api/feed/manual" for item in items)
    assert any(item["symbol"] == "POST /api/auth/login" for item in items)
    assert any(item["symbol"] == "FeedService.add_manual" for item in items)


def test_new_same_line_button_is_a_distinct_surface(tmp_path):
    path = tmp_path / "web/src/features/feed/FeedPage.tsx"
    path.parent.mkdir(parents=True)
    path.write_text("<button onClick={refresh}>Refresh</button>")
    before = scanner().scan_surface(tmp_path)
    path.write_text(
        "<button onClick={refresh}>Refresh</button><button onClick={remove}>Remove</button>"
    )
    after = scanner().scan_surface(tmp_path)
    assert len({item["id"] for item in after} - {item["id"] for item in before}) >= 2


def verifier():
    path = ROOT / "scripts/verify_all_app_actions.py"
    assert path.exists(), "CI surface verifier must exist"
    spec = importlib.util.spec_from_file_location("action_coverage", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_guard_rejects_every_new_surface_kind():
    kinds = (
        "ui_button",
        "ui_event",
        "ui_mutation",
        "ui_api",
        "api_client",
        "http_route",
        "service_method",
        "base_tool",
    )
    for kind in kinds:
        errors = verifier().validate_coverage(
            [{"id": "new:" + kind, "kind": kind, "file": "new.py", "symbol": "added"}],
            {"surfaces": [], "action_evidence": {}},
            {},
            ROOT,
            baseline=True,
        )
        assert any("unclassified" in error for error in errors), kind


def test_guard_rejects_duplicate_classification_and_unreasoned_exceptions():
    item = {"id": "button", "kind": "ui_button", "file": "button.tsx", "symbol": "Delete"}
    mark = {"surface_id": "button", "classification": "ui_only", "reason": "", "ui_tests": []}
    errors = verifier().validate_coverage([item], {"surfaces": [mark, mark]}, {}, ROOT)
    assert any("duplicate classification" in error for error in errors)
    assert any("reason" in error for error in errors)
    assert any("UI test" in error for error in errors)


def test_guard_does_not_accept_missing_implementation_as_final_coverage():
    item = {"id": "crud", "kind": "service_method", "file": "feed.py", "symbol": "add"}
    mark = {"surface_id": "crud", "classification": "missing_implementation", "reason": "pending"}
    errors = verifier().validate_coverage([item], {"surfaces": [mark]}, {}, ROOT)
    assert any("missing implementation" in error for error in errors)


def test_guard_requires_strict_schema_handler_policy_postcondition_and_tests():
    from types import SimpleNamespace

    from pydantic import BaseModel

    class Loose(BaseModel):
        title: str

    action = SimpleNamespace(
        id="feed.add",
        domain="feed",
        args_schema=Loose,
        handler=None,
        side_effect="write",
        permission="",
        requires_network=False,
        confirmation_policy="none",
        idempotency="request_id",
        postcondition="",
        ui_binding="Feed",
        service_binding="FeedService.add",
        agent_availability="enabled",
    )
    item = {"id": "crud", "kind": "service_method", "file": "feed.py", "symbol": "add"}
    mark = {"surface_id": "crud", "classification": "agent_enabled", "action_ids": ["feed.add"]}
    errors = verifier().validate_coverage([item], {"surfaces": [mark]}, {"feed.add": action}, ROOT)
    for expected in ("strict schema", "handler", "permission", "postcondition", "test evidence"):
        assert any(expected in error for error in errors), errors


def test_guard_requires_a_new_business_tool_to_use_single_app_entry():
    item = {
        "id": "tool",
        "kind": "base_tool",
        "file": "src/xiliu/tools/feed.py",
        "symbol": "FeedTool",
        "tool_names": ["feed_add"],
    }
    mark = {"surface_id": "tool", "classification": "agent_enabled", "action_ids": ["feed.add"]}
    errors = verifier().validate_coverage([item], {"surfaces": [mark]}, {}, ROOT)
    assert any("business Tool must expose only app" in error for error in errors)


def test_scanner_covers_custom_events_and_non_decorator_routes(tmp_path):
    ui = tmp_path / "web/src/features/feed/FeedPage.tsx"
    ui.parent.mkdir(parents=True)
    ui.write_text("<Editor onSave={save} onPointerMove={move} />")
    routes = tmp_path / "src/xiliu/api/routes/feed.py"
    routes.parent.mkdir(parents=True)
    routes.write_text(
        "router = APIRouter(prefix='/api/feed')\n"
        "@router.api_route('/custom', methods=['POST'])\ndef save():\n    pass\n"
        "router.add_api_route('/other', save, methods=['DELETE'])\n"
    )
    items = scanner().scan_surface(tmp_path)
    assert sum(item["kind"] == "ui_event" for item in items) == 2
    assert any(item["symbol"] == "POST /api/feed/custom" for item in items)
    assert any(item["symbol"] == "DELETE /api/feed/other" for item in items)


def test_guard_checks_each_explicit_service_binding_and_postcondition():
    from types import SimpleNamespace

    from pydantic import BaseModel, ConfigDict

    class Strict(BaseModel):
        model_config = ConfigDict(extra="forbid")

    action = SimpleNamespace(
        id="feed.read",
        domain="feed",
        args_schema=Strict,
        handler=lambda: None,
        side_effect="read",
        permission="feed.read",
        requires_network=False,
        confirmation_policy="none",
        idempotency="request",
        postcondition=lambda: True,
        ui_binding=(),
        service_binding=("FeedService.list", "FeedService.phantom"),
        agent_availability="enabled",
    )
    item = {
        "id": "method",
        "kind": "service_method",
        "file": "feed.py",
        "symbol": "FeedService.list",
    }
    mark = {"surface_id": "method", "classification": "agent_enabled", "action_ids": ["feed.read"]}
    errors = verifier().validate_coverage([item], {"surfaces": [mark]}, {"feed.read": action}, ROOT)
    assert any("unavailable Service binding FeedService.phantom" in error for error in errors)


def test_guard_accepts_only_real_literal_catalog_binding(tmp_path):
    constants = tmp_path / "src/demo/catalog.py"
    constants.parent.mkdir(parents=True)
    constants.write_text("CATALOG = {'models': ['test']}\n")
    assert verifier().literal_catalog_binding("constant:demo.catalog.CATALOG", tmp_path)
    assert not verifier().literal_catalog_binding("constant:demo.catalog.PHANTOM", tmp_path)


def test_api_declarations_are_scoped_to_exported_client_object(tmp_path):
    path = tmp_path / "web/src/lib/api.ts"
    path.parent.mkdir(parents=True)
    path.write_text(
        "function helper() {\n  if (ready) return true\n}\n"
        "export const api = {\n  list: () => request('/items'),\n}\n"
    )
    declarations = [
        item["symbol"] for item in scanner().scan_surface(tmp_path) if item["kind"] == "api_client"
    ]
    assert declarations == ["list"]


def test_all_registered_action_schemas_reject_unrecognized_fields():
    import pytest
    from pydantic import ValidationError

    from xiliu.app.actions import get_registry

    for identifier, action in get_registry().items():
        with pytest.raises(ValidationError) as rejected:
            action.args_schema.model_validate({"unrecognized_action_field": True})
        assert any(error["type"] == "extra_forbidden" for error in rejected.value.errors()), (
            identifier
        )
        assert callable(action.handler), identifier
        assert callable(action.postcondition), identifier
        assert action.permission and action.idempotency, identifier


def test_current_repository_surface_and_registry_contracts_are_fully_classified():
    import json

    from xiliu.app.actions import get_registry

    manifest = json.loads((ROOT / "docs/audit/coverage-manifest.json").read_text(encoding="utf-8"))
    errors = verifier().validate_coverage(
        scanner().scan_surface(ROOT), manifest, get_registry(), ROOT
    )
    assert not errors, "\n".join(errors)


def test_http_and_service_rows_are_attributed_to_actual_page(tmp_path):
    route = tmp_path / "src/xiliu/api/routes/workspace.py"
    route.parent.mkdir(parents=True)
    route.write_text(
        "router = APIRouter(prefix='/api')\n@router.get('/today')\ndef today():\n    pass\n"
    )
    service = tmp_path / "src/xiliu/api/services/feed.py"
    service.parent.mkdir(parents=True)
    service.write_text("class FeedService:\n    def list(self):\n        pass\n")
    items = scanner().scan_surface(tmp_path)
    assert next(item for item in items if item["kind"] == "http_route")["page"] == "Today"
    assert next(item for item in items if item["kind"] == "service_method")["page"] == "Feed"


def test_guard_rejects_client_mapping_that_drifts_from_registry():
    from types import SimpleNamespace

    item = {
        "id": "client",
        "kind": "api_client",
        "file": "web/src/lib/api.ts",
        "symbol": "archiveJob",
    }
    mark = {"surface_id": "client", "classification": "agent_enabled", "action_ids": ["inbox.list"]}
    registry = {
        "inbox.archive_job": SimpleNamespace(ui_binding=("api.archiveJob",)),
        "inbox.list": SimpleNamespace(ui_binding=("workspaceApi.inbox",)),
    }
    errors = verifier().validate_coverage([item], {"surfaces": [mark]}, registry, ROOT)
    assert any("Registry UI binding mismatch" in error for error in errors), errors


def test_guard_rejects_service_classification_bound_to_an_unrelated_action():
    from types import SimpleNamespace

    item = {
        "id": "method",
        "kind": "service_method",
        "file": "inbox.py",
        "symbol": "InboxService.queue_archive",
    }
    mark = {"surface_id": "method", "classification": "agent_enabled", "action_ids": ["inbox.list"]}
    action = SimpleNamespace(
        service_binding="InboxService.list", ui_binding=("workspaceApi.inbox",)
    )
    errors = verifier().validate_coverage(
        [item], {"surfaces": [mark]}, {"inbox.list": action}, ROOT
    )
    assert any("Service mapping lacks actual registered binding" in error for error in errors), (
        errors
    )


def test_guard_rejects_scalar_coercion_in_action_schema():
    from types import SimpleNamespace

    from pydantic import BaseModel, ConfigDict

    class Coercing(BaseModel):
        model_config = ConfigDict(extra="forbid")
        expected_revision: int

    action = SimpleNamespace(args_schema=Coercing, ui_binding=(), service_binding=())
    errors = verifier().validate_coverage([], {}, {"inbox.update": action}, ROOT)
    assert any("strict scalar validation" in error for error in errors), errors


def test_execution_guard_rejects_policy_denial_as_enabled_business_success():
    from types import SimpleNamespace

    registry = {"new.write": SimpleNamespace(agent_availability="enabled")}
    denied = {
        "pytest_exit_code": 0,
        "actions": {
            "new.write": {
                "status": "denied",
                "gateway_tool_dispatcher_passed_tests": [],
            }
        },
    }
    errors = verifier().validate_execution(registry, denied)
    assert any("new.write" in error and "successful Gateway" in error for error in errors)


def test_execution_guard_requires_complete_chain_and_explicit_restricted_denial():
    from types import SimpleNamespace

    registry = {
        "real.read": SimpleNamespace(agent_availability="enabled"),
        "file.import": SimpleNamespace(agent_availability="restricted"),
    }
    actual = {
        "pytest_exit_code": 0,
        "actions": {
            "real.read": {
                "status": "passed",
                "gateway_tool_dispatcher_passed_tests": ["actual_test"],
            },
            "file.import": {"status": "denied", "events": [{"error": "capability_unavailable"}]},
        },
    }
    assert verifier().validate_execution(registry, actual) == []
    actual["actions"]["real.read"]["gateway_tool_dispatcher_passed_tests"] = []
    assert verifier().validate_execution(registry, actual)
    actual["pytest_exit_code"] = 1
    assert any("pytest" in error for error in verifier().validate_execution(registry, actual))


def test_observer_http_patterns_prioritize_specific_routes_over_spa_fallback():
    from scripts.app_action_observer import _http_patterns

    routes = _http_patterns(
        [
            "GET /{path:path}",
            "GET /api/content/{item_id}",
            "GET /api/settings/preferences",
            "GET /api/content/{item_id}/original",
        ]
    )

    def matched(path):
        return next(
            template
            for method, template, pattern in routes
            if method == "GET" and pattern.fullmatch(path)
        )

    assert matched("/api/settings/preferences") == "GET /api/settings/preferences"
    assert matched("/api/content/fixture-id") == "GET /api/content/{item_id}"
    assert matched("/api/content/fixture-id/original") == "GET /api/content/{item_id}/original"
    assert matched("/intro") == "GET /{path:path}"
