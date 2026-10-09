"""Seed only public packaged defaults, preserving the user's MCP settings."""

from pathlib import Path


def seed_mcp_defaults(data_dir: Path, defaults_dir: Path) -> None:
    source = defaults_dir / "mcp" / "aihot" / "mcp.json"
    target = data_dir / "mcp" / "aihot" / "mcp.json"
    if not source.is_file():
        raise FileNotFoundError("Desktop MCP defaults are missing; rebuild the sidecar")
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        with target.open("x", encoding="utf-8") as file:
            file.write(source.read_text(encoding="utf-8"))
    except FileExistsError:
        pass
