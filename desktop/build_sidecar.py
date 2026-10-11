"""Build a directory bundle; never include developer .env or user data."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    if not (ROOT / "web/dist/index.html").is_file():
        raise SystemExit("Build web first: cd web && npm run build")
    output = ROOT / ".preview/desktop-sidecar"
    web_assets = ROOT / ".preview/desktop-web"
    # Stage only production browser assets, leaving project documentation behind.
    if web_assets.exists():
        if not web_assets.resolve().is_relative_to((ROOT / ".preview").resolve()):
            raise RuntimeError("Refusing to replace assets outside the build workspace")
        shutil.rmtree(web_assets)
    shutil.copytree(
        ROOT / "web/dist",
        web_assets,
        ignore=shutil.ignore_patterns("*.md", "*.map", "*.test.*", "*.spec.*", ".env*"),
    )
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onedir",
        "--name",
        "xiliu-service",
        "--distpath",
        str(output),
        "--workpath",
        str(ROOT / ".preview/desktop-build"),
        "--specpath",
        str(ROOT / ".preview"),
        "--paths",
        str(ROOT / "src"),
        "--add-data",
        f"{web_assets}:web/dist",
        "--add-data",
        f"{ROOT / 'desktop/defaults'}:desktop/defaults",
    ]
    # Desktop uses the API and Runtime, not the terminal UI or development tools.
    # Exclude optional test imports that PyInstaller can discover in dependencies.
    for package in (
        "xiliu.cli",
        "textual",
        "pytest",
        "_pytest",
        "py",
        "ruff",
        "pyright",
        "tests",
        "hypothesis",
        "IPython",
        "notebook",
        "jupyter",
    ):
        command.extend(["--exclude-module", package])
    # Xiliu is an MCP client. Collect its client transports; PyInstaller follows
    # reachable imports from mcp.__init__ without bundling every unused server CLI.
    for package in (
        "xiliu",
        "uvicorn",
        "tiktoken_ext",
        "langgraph",
        "langchain_openai",
        "mcp.client",
    ):
        command.extend(["--collect-submodules", package])
    for package in ("langchain-core", "langchain-openai", "langgraph", "tiktoken", "pydantic"):
        command.extend(["--copy-metadata", package])
    command.append(str(ROOT / "desktop/server.py"))
    subprocess.run(command, cwd=ROOT, check=True)
    source = output / "xiliu-service"
    target = ROOT / "desktop/src-tauri/binaries"
    if not target.resolve().is_relative_to((ROOT / "desktop/src-tauri").resolve()):
        raise RuntimeError("Refusing to write binaries outside the desktop workspace")
    target.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source / "xiliu-service.exe", target / "xiliu-service-x86_64-pc-windows-msvc.exe")
    internal = (target / "_internal").resolve()
    if not internal.is_relative_to(target.resolve()) or internal.name != "_internal":
        raise RuntimeError("Refusing to replace resources outside generated binaries")
    if internal.exists():
        shutil.rmtree(internal)
    shutil.copytree(source / "_internal", internal)
    print(f"Sidecar ready: {target}")


if __name__ == "__main__":
    main()
