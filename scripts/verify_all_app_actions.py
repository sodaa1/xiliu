"""Fail CI on unclassified surfaces, incomplete contracts or additional business Tools.

Evidence references prove that an actual named test exists; they never imply it
ran or passed. Execution results belong to independent test-run reports.
"""

from __future__ import annotations

import argparse
import ast
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLASSIFICATIONS = {"agent_enabled", "restricted", "ui_only", "missing_implementation"}
REQUIRED_FIELDS = (
    "id",
    "domain",
    "args_schema",
    "handler",
    "side_effect",
    "permission",
    "requires_network",
    "confirmation_policy",
    "idempotency",
    "postcondition",
    "ui_binding",
    "service_binding",
    "agent_availability",
)
LEGACY_BUSINESS_TOOLS = {
    "inbox_import",
    "inbox_list",
    "knowledge_folders",
    "knowledge_folder_create",
    "inbox_classify",
    "knowledge_search",
    "knowledge_get",
}


def literal_catalog_binding(binding: str, root: Path) -> bool:
    """Constant catalogs must name an existing JSON-serializable literal, not a fake Service."""
    if not binding.startswith("constant:"):
        return False
    module, _, symbol = binding.removeprefix("constant:").rpartition(".")
    if not module or not symbol:
        return False
    path = (root / "src" / Path(*module.split("."))).with_suffix(".py").resolve()
    if not path.is_relative_to((root / "src").resolve()) or not path.is_file():
        return False
    for node in ast.parse(path.read_text(encoding="utf-8-sig")).body:
        if isinstance(node, ast.Assign):
            names = [getattr(target, "id", "") for target in node.targets]
        elif isinstance(node, ast.AnnAssign):
            names = [getattr(node.target, "id", "")]
        else:
            continue
        if symbol in names and node.value is not None:
            try:
                json.dumps(ast.literal_eval(node.value))
                return True
            except (ValueError, TypeError):
                return False
    return False


def _test_reference(reference: str, root: Path) -> bool:
    filename, _, name = reference.partition("::")
    path = (root / filename).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file() or not name:
        return False
    source = path.read_text(encoding="utf-8-sig")
    if path.suffix == ".py":
        return any(
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name
            for node in ast.walk(ast.parse(source))
        )
    return name in source and any(
        marker in source for marker in ("test(", "it(", "test.each(", "it.each(")
    )


def validate_coverage(
    items: list[dict], manifest: dict, registry: dict, root: Path, *, baseline: bool = False
) -> list[str]:
    errors: list[str] = []
    references: dict[str, bool] = {}

    def valid_reference(reference: str) -> bool:
        if reference not in references:
            references[reference] = _test_reference(reference, root)
        return references[reference]

    grouped: dict[str, list] = {}
    for mark in manifest.get("surfaces", []):
        grouped.setdefault(mark.get("surface_id", ""), []).append(mark)
    ui_actions: dict[str, set[str]] = {}
    for action_id, action in registry.items():
        for binding in getattr(action, "ui_binding", ()):
            ui_actions.setdefault(binding, set()).add(action_id)
    live = {item["id"] for item in items}
    for identifier in sorted(set(grouped) - live):
        errors.append(f"stale classification: {identifier}")
    for item in items:
        identifier = item["id"]
        marks = grouped.get(identifier, [])
        if not marks:
            errors.append(
                f"unclassified {item['kind']}: {item['file']} {item['symbol']} ({identifier})"
            )
            continue
        if len(marks) != 1:
            errors.append(f"duplicate classification: {identifier}")
        mark = marks[0]
        classification = mark.get("classification")
        if classification not in CLASSIFICATIONS:
            errors.append(f"invalid classification: {identifier}")
            continue
        if classification in {"restricted", "ui_only", "missing_implementation"}:
            if not str(mark.get("reason", "")).strip():
                errors.append(f"exception requires reason: {identifier}")
            if (
                not baseline
                and item["kind"].startswith("ui_")
                and classification != "missing_implementation"
            ):
                evidence = mark.get("ui_tests", [])
                if not evidence or not all(valid_reference(ref) for ref in evidence):
                    errors.append(f"exception requires actual named UI test evidence: {identifier}")
        if classification == "missing_implementation" and not baseline:
            errors.append(f"missing implementation: {identifier}")
        if classification == "agent_enabled":
            action_ids = mark.get("action_ids", [])
            if not action_ids:
                errors.append(f"agent_enabled requires Action ID: {identifier}")
            for action_id in action_ids:
                if action_id not in registry:
                    errors.append(f"unknown registered action: {identifier} -> {action_id}")
        if not baseline:
            action_ids = set(mark.get("action_ids", []))
            binding = item["symbol"] if item["kind"] == "ui_api" else None
            if item["kind"] == "api_client":
                owner = "workspaceApi" if item["file"].endswith("workspace-api.ts") else "api"
                binding = f"{owner}.{item['symbol']}"
            if binding:
                expected = ui_actions.get(binding, set())
                if action_ids != expected:
                    errors.append(f"Registry UI binding mismatch: {identifier} {binding}")
            if item["kind"] == "service_method" and action_ids:
                for action_id in action_ids:
                    action = registry.get(action_id)
                    bindings = getattr(action, "service_binding", ())
                    if isinstance(bindings, str):
                        bindings = (bindings,)
                    if item["symbol"] not in bindings:
                        errors.append(
                            f"Service mapping lacks actual registered binding: {identifier}"
                            f" -> {action_id}"
                        )
        if item["kind"] == "base_tool" and not baseline:
            names = set(item.get("tool_names", []))
            allowed = manifest.get("specialist_tools", {})
            if names != {"app"}:
                if names & LEGACY_BUSINESS_TOOLS or classification == "agent_enabled":
                    errors.append(f"business Tool must expose only app: {item['file']} {names}")
                elif not names or not all(
                    name in allowed and allowed[name].get("reason") for name in names
                ):
                    errors.append(
                        "unreviewed additional business Tool must expose only app: "
                        f"{item['file']} {names}"
                    )
    service_methods = {item["symbol"] for item in items if item["kind"] == "service_method"}
    evidence = manifest.get("action_evidence", {})
    for action_id, action in registry.items():
        for field in REQUIRED_FIELDS:
            if not hasattr(action, field):
                errors.append(f"{action_id}: missing ActionSpec field {field}")
        if getattr(action, "id", None) != action_id:
            errors.append(f"{action_id}: Registry key/id mismatch")
        schema = getattr(action, "args_schema", None)
        if (
            not callable(getattr(schema, "model_json_schema", None))
            or getattr(schema, "model_config", {}).get("extra") != "forbid"
        ):
            errors.append(f"{action_id}: strict schema must reject unknown fields")
        else:
            assert schema is not None
            try:
                json.dumps(schema.model_json_schema())
            except Exception:
                errors.append(f"{action_id}: schema is not JSON serializable")
        if getattr(schema, "model_config", {}).get("strict") is not True:
            errors.append(f"{action_id}: strict scalar validation must reject coercion")
        if not callable(getattr(action, "handler", None)):
            errors.append(f"{action_id}: handler must be callable")
        if not str(getattr(action, "permission", "") or "").strip():
            errors.append(f"{action_id}: permission policy missing")
        if not callable(getattr(action, "postcondition", None)):
            errors.append(f"{action_id}: persisted postcondition must be callable")
        bindings = getattr(action, "service_binding", ())
        if isinstance(bindings, str):
            bindings = (bindings,)
        catalog = getattr(action, "constant_catalog", None)
        if catalog:
            if bindings or not literal_catalog_binding("constant:" + catalog, root):
                errors.append(f"{action_id}: unavailable explicit constant catalog {catalog}")
            if action.side_effect != "read" or action.requires_network:
                errors.append(f"{action_id}: constant catalog must be local read-only")
        elif not isinstance(bindings, (tuple, list)) or not bindings:
            errors.append(f"{action_id}: explicit Service binding missing")
        else:
            for binding in bindings:
                if binding not in service_methods and not literal_catalog_binding(binding, root):
                    errors.append(f"{action_id}: unavailable Service binding {binding}")
        if getattr(action, "side_effect", None) not in {"read", "write"}:
            errors.append(f"{action_id}: invalid side effect")
        if not isinstance(getattr(action, "requires_network", None), bool):
            errors.append(f"{action_id}: requires_network must be explicit boolean")
        if not getattr(action, "idempotency", None):
            errors.append(f"{action_id}: idempotency policy missing")
        if getattr(action, "confirmation_policy", None) not in {"none", "explicit"}:
            errors.append(f"{action_id}: explicit confirmation policy missing")
        if getattr(action, "agent_availability", None) not in {"enabled", "restricted", "ui_only"}:
            errors.append(f"{action_id}: invalid agent availability")
        record = evidence.get(action_id, {})
        tests = record.get("tests", [])
        if not tests or not all(valid_reference(ref) for ref in tests):
            errors.append(f"{action_id}: actual named test evidence missing")
        if record.get("status", "not_run") not in {"passed", "failed", "not_run"}:
            errors.append(f"{action_id}: invalid test execution status")
    return errors


def validate_execution(registry: dict, execution: dict) -> list[str]:
    """A referenced negative test cannot substitute for a real successful action."""
    errors = []
    if execution.get("pytest_exit_code") != 0:
        errors.append("Actual action execution report requires a successful full pytest run")
    actions = execution.get("actions", {})
    if set(actions) != set(registry):
        errors.append("Actual execution report action IDs must exactly match the current Registry")
    for identifier, spec in registry.items():
        row = actions.get(identifier, {})
        if spec.agent_availability == "enabled":
            if row.get("status") != "passed" or not row.get("gateway_tool_dispatcher_passed_tests"):
                errors.append(
                    f"{identifier}: successful Gateway/AppTool/Dispatcher execution missing"
                )
        elif spec.agent_availability == "restricted" and (
            row.get("status") != "denied"
            or not any(
                event.get("error") == "capability_unavailable" for event in row.get("events", [])
            )
        ):
            errors.append(f"{identifier}: actual explicit restricted denial missing")
    return errors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--execution-report",
        type=Path,
        help="CI runtime gate: current pytest observer report is mandatory in CI.",
    )
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--manifest", type=Path, default=ROOT / "docs/audit/coverage-manifest.json")
    parser.add_argument("--output", type=Path, default=ROOT / "docs/audit/coverage-results.json")
    parser.add_argument(
        "--baseline",
        action="store_true",
        help="Inventory-only baseline validation; never a final CI acceptance.",
    )
    args = parser.parse_args()
    module_spec = importlib.util.spec_from_file_location(
        "surface", args.root / "scripts/audit_app_surface.py"
    )
    assert module_spec is not None and module_spec.loader is not None
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    items = module.scan_surface(args.root)
    manifest = json.loads(args.manifest.read_text(encoding="utf-8-sig"))
    registry = {}
    registry_error = None
    if not args.baseline:
        sys.path.insert(0, str(args.root / "src"))
        try:
            from xiliu.app.actions import get_registry

            registry = get_registry()
        except Exception as exc:
            registry_error = f"Registry unavailable: {type(exc).__name__}"
    errors = validate_coverage(items, manifest, registry, args.root, baseline=args.baseline)
    if args.execution_report is not None:
        if not args.execution_report.is_file():
            errors.append("Actual action execution report is missing")
        else:
            execution = json.loads(args.execution_report.read_text(encoding="utf-8-sig"))
            errors.extend(validate_execution(registry, execution))
    if registry_error:
        errors.append(registry_error)
    marks = {mark["surface_id"]: mark for mark in manifest.get("surfaces", [])}
    pages = {}
    for item in items:
        page = pages.setdefault(item["page"], Counter())
        page["total"] += 1
        page[marks.get(item["id"], {}).get("classification", "unclassified")] += 1
    report = {
        "format_version": 1,
        "status": "passed" if not errors else "failed",
        "scope": "baseline inventory only" if args.baseline else "final contract/surface guard",
        "surface_count": len(items),
        "registry_action_count": len(registry),
        "runtime_gate": "passed"
        if args.execution_report is not None and not errors
        else "failed"
        if args.execution_report is not None
        else "not_run",
        "pages": pages,
        "errors": errors,
        "ui_e2e": manifest.get("runtime_evidence", {}).get(
            "browser",
            {"status": "not_run", "scope": "Static mapping does not establish browser execution"},
        ),
        "action_business_execution": {
            key: value.get("actual_execution", {}).get("status", "not_run")
            for key, value in manifest.get("action_evidence", {}).items()
        },
        "gateway_tool_dispatcher_execution": {
            key: "passed"
            if value.get("actual_execution", {}).get("gateway_tool_dispatcher_passed_tests")
            else "not_run"
            for key, value in manifest.get("action_evidence", {}).items()
        },
        "test_reference_execution": {
            key: value.get("status", "not_run")
            for key, value in manifest.get("action_evidence", {}).items()
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "status": report["status"],
                "surface_count": len(items),
                "errors": len(errors),
                "output": str(args.output),
            }
        )
    )
    if errors:
        for error in errors[:30]:
            print(error)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
