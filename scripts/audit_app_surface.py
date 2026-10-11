"""Machine inventory. Every source occurrence has an independently classified identity.

Python surfaces use AST; TSX uses balanced-expression lexical scanning. This is an
inventory, not proof of browser behavior. Review the generated records and classify
in coverage-manifest.json; the verifier refuses unmatched new records.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _expression(source: str, start: int) -> str:
    """Read one balanced JS expression (including multiline event handlers)."""
    if start >= len(source):
        return ""
    if source[start] != "{":
        match = re.match(r"[^\s>]+", source[start:])
        return match.group() if match else ""
    depth, quote, escaped = 0, "", False
    for position in range(start, len(source)):
        char = source[position]
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = ""
        elif char in "\"'`":
            quote = char
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[start : position + 1]
    return source[start:]


def _page(path: str, symbol: str = "") -> str:
    if "/features/" in path:
        name = path.split("/features/", 1)[1].split("/")[0]
        return {"content": "Inbox / shared content", "intro": "Intro"}.get(name, name.title())
    if "/app/" in path or "/components/" in path:
        return "Launch / Navigation / shared UI"
    route = re.search(r" /api/([^/{ ]+)", symbol)
    domain = route.group(1) if route else ""
    pages = {
        "feed": "Feed",
        "tasks": "Today",
        "today": "Today",
        "inbox": "Inbox",
        "knowledge": "Knowledge",
        "content": "Inbox / shared content",
        "conversations": "Assistant",
        "automations": "Automations",
        "settings": "Settings",
        "models": "Settings",
        "commands": "Assistant",
        "capabilities": "Settings",
    }
    if domain in pages:
        return pages[domain]
    for service, page in {
        "FeedService": "Feed",
        "TaskService": "Today",
        "InboxService": "Inbox",
        "KnowledgeService": "Knowledge",
        "RAGService": "Knowledge",
        "RetrievalService": "Knowledge",
        "ContentService": "Inbox / shared content",
        "ConversationService": "Assistant",
        "AppStore": "Assistant",
        "ChatService": "Assistant",
        "CommandService": "Assistant",
        "AutomationService": "Automations",
        "ModelSettingsService": "Settings",
        "PreferencesService": "Settings",
    }.items():
        if symbol.startswith(service + "."):
            return page
    if path.endswith("/lib/preferences.ts"):
        return "Settings"
    return "API / Service / Agent"


def scan_surface(root: Path) -> list[dict]:
    records: list[dict] = []
    identities: Counter = Counter()

    def add(path: Path, kind: str, symbol: str, position: int, source: str, **details):
        relative = path.relative_to(root).as_posix()
        normalized = " ".join(symbol.split())
        key = f"{relative}|{kind}|{normalized}"
        identities[key] += 1
        digest = hashlib.sha256(key.encode()).hexdigest()[:20]
        records.append(
            {
                "id": f"{kind}:{digest}:{identities[key]}",
                "kind": kind,
                "page": _page(relative, normalized),
                "file": relative,
                "line": source.count("\n", 0, position) + 1,
                "symbol": normalized,
                **details,
            }
        )

    ui = list((root / "web/src/features").rglob("*.tsx"))
    ui += list((root / "web/src/features").rglob("*.ts"))
    ui += list((root / "web/src/app").glob("*.tsx"))
    ui += list((root / "web/src/components").rglob("*.tsx"))
    ui += [
        root / "web/src/lib/api.ts",
        root / "web/src/lib/workspace-api.ts",
        root / "web/src/lib/preferences.ts",
        root / "web/src/desktop/bridge.ts",
    ]
    for path in sorted(set(ui)):
        if not path.exists() or any(part in path.name for part in (".test.", ".spec.", ".d.ts")):
            continue
        source = path.read_text(encoding="utf-8-sig")
        patterns = {
            "ui_button": r"<button\b",
            "ui_link": r"<(?:a|Link|NavLink)\b",
            "ui_api": r"\b(?:workspaceApi|api)\.([A-Za-z_]\w*)\b",
            "ui_mutation": r"\buseMutation\s*(?:<[^;]*?>)?\s*\(",
            "ui_query": r"\b(?:mutationFn|queryFn)\s*:\s*",
            "ui_event": r"\b(on[A-Z]\w*)\s*=\s*",
            "ui_fetch": r"\bfetch\s*\(",
        }
        for kind, pattern in patterns.items():
            for match in re.finditer(pattern, source):
                end = match.end()
                symbol = match.group()
                if kind in {"ui_event", "ui_query", "ui_mutation", "ui_fetch"}:
                    symbol += _expression(source, end)
                elif kind in {"ui_button", "ui_link"}:
                    # Include attributes, reading arrow operators inside braces correctly.
                    while end < len(source) and source[end] != ">":
                        if source[end] == "{":
                            end += len(_expression(source, end))
                        else:
                            end += 1
                    symbol = source[match.start() : end + 1]
                add(path, kind, symbol, match.start(), source)
        if path.name in {"api.ts", "workspace-api.ts"}:
            declaration = re.search(r"export const (?:api|workspaceApi)\s*=\s*", source)
            if declaration:
                offset = declaration.end()
                body = _expression(source, offset)
                for match in re.finditer(r"^\s{2}(?:async\s+)?(\w+)\s*(?::\s*\(|\()", body, re.M):
                    add(path, "api_client", match.group(1), offset + match.start(), source)

    python_paths = list((root / "src/xiliu/api/routes").glob("*.py"))
    python_paths += list((root / "src/xiliu/api/services").glob("*.py"))
    python_paths += list((root / "src/xiliu/tools").glob("*.py"))
    python_paths += [
        root / "src/xiliu/api/app.py",
        root / "src/xiliu/api/store.py",
        root / "src/xiliu/rag/service.py",
        root / "desktop/server.py",
    ]
    for path in sorted(set(python_paths)):
        if not path.exists():
            continue
        source = path.read_text(encoding="utf-8-sig")
        tree = ast.parse(source)
        prefix = ""
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "APIRouter":
                prefix = next(
                    (
                        kw.value.value
                        for kw in node.keywords
                        if kw.arg == "prefix"
                        and isinstance(kw.value, ast.Constant)
                        and isinstance(kw.value.value, str)
                    ),
                    "",
                )
        for node in ast.walk(tree):
            line_number = getattr(node, "lineno", None)
            position = (
                sum(len(line) for line in source.splitlines(keepends=True)[: line_number - 1])
                if isinstance(line_number, int)
                else 0
            )
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "add_api_route"
                and node.args
                and isinstance(node.args[0], ast.Constant)
            ):
                methods = next(
                    (ast.literal_eval(kw.value) for kw in node.keywords if kw.arg == "methods"),
                    ["GET"],
                )
                for method in methods:
                    add(
                        path,
                        "http_route",
                        f"{method.upper()} {prefix + str(node.args[0].value)}",
                        position,
                        source,
                        service_calls=[],
                    )
            if isinstance(node, ast.ClassDef):
                if node.name.endswith("Service") or node.name == "AppStore":
                    for method in node.body:
                        if isinstance(
                            method, (ast.FunctionDef, ast.AsyncFunctionDef)
                        ) and not method.name.startswith("_"):
                            pos = sum(
                                len(line)
                                for line in source.splitlines(keepends=True)[: method.lineno - 1]
                            )
                            add(path, "service_method", f"{node.name}.{method.name}", pos, source)
                if any(
                    ast.unparse(base).split(".")[-1] in {"BaseTool", "StructuredTool"}
                    for base in node.bases
                ):
                    names = [
                        ast.literal_eval(child.value)
                        for child in node.body
                        if isinstance(child, (ast.Assign, ast.AnnAssign))
                        and child.value is not None
                        and isinstance(child.value, ast.Constant)
                        and (
                            (
                                isinstance(child, ast.AnnAssign)
                                and getattr(child.target, "id", "") == "name"
                            )
                            or (
                                isinstance(child, ast.Assign)
                                and any(
                                    getattr(target, "id", "") == "name" for target in child.targets
                                )
                            )
                        )
                    ]
                    add(path, "base_tool", node.name, position, source, tool_names=names)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for decorator in node.decorator_list:
                    name = ast.unparse(
                        decorator.func if isinstance(decorator, ast.Call) else decorator
                    )
                    if name == "tool" or name.endswith(".tool"):
                        add(path, "base_tool", node.name, position, source, tool_names=[node.name])
                    if (
                        isinstance(decorator, ast.Call)
                        and isinstance(decorator.func, ast.Attribute)
                        and decorator.func.attr
                        in {"get", "post", "put", "patch", "delete", "options", "head", "api_route"}
                        and decorator.args
                        and isinstance(decorator.args[0], ast.Constant)
                    ):
                        route = prefix + str(decorator.args[0].value)
                        calls = sorted(
                            {
                                ast.unparse(call.func)
                                for call in ast.walk(node)
                                if isinstance(call, ast.Call)
                                and isinstance(call.func, ast.Attribute)
                                and (
                                    "state." in ast.unparse(call.func)
                                    or "service." in ast.unparse(call.func)
                                )
                            }
                        )
                        methods = (
                            next(
                                (
                                    ast.literal_eval(kw.value)
                                    for kw in decorator.keywords
                                    if kw.arg == "methods"
                                ),
                                ["GET"],
                            )
                            if decorator.func.attr == "api_route"
                            else [decorator.func.attr.upper()]
                        )
                        for method in methods:
                            add(
                                path,
                                "http_route",
                                f"{method.upper()} {route}",
                                position,
                                source,
                                service_calls=calls,
                            )
    return sorted(records, key=lambda item: (item["file"], item["line"], item["kind"], item["id"]))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, default=ROOT / "docs/audit/surface-inventory.json")
    args = parser.parse_args()
    items = scan_surface(args.root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(
            {
                "format_version": 1,
                "items": items,
                "counts": dict(Counter(item["kind"] for item in items)),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "output": str(args.output),
                "total": len(items),
                "counts": dict(Counter(item["kind"] for item in items)),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
